"""Compatibility layer providing minimal Flask-like interfaces for tests.

This module attempts to import the real Flask and flask_cors packages. When
those dependencies are not installed (which is the case in the lightweight
execution environment used for the kata), it falls back to very small stub
implementations that mimic just enough behaviour for the unit tests to
exercise the production backends.

The goal of the stubs is not to be feature complete – only the pieces used in
``production_backend`` and ``production_realtime`` are implemented. The
interface surface covered includes:

* ``Flask`` with ``route``, ``register_blueprint``, ``test_client``,
  ``app_context`` and ``teardown_appcontext`` helpers.
* ``Blueprint`` for registering simple groups of routes.
* ``request``/``jsonify``/``g`` proxies used by the services.
* ``Response`` objects with ``status_code`` and ``get_json`` helpers.
* ``CORS`` initialiser that safely degrades to a no-op when ``flask_cors`` is
  unavailable.

The implementation favours clarity and determinism over perfect API
compatibility – it is intentionally scoped to what the tests expect.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Tuple


try:  # pragma: no cover - exercised implicitly when Flask is installed
    from flask import Blueprint, Flask, Response, g, jsonify, request
except ModuleNotFoundError:  # pragma: no cover - stub path exercised in tests
    import contextvars
    import re
    from urllib.parse import parse_qs, urlsplit

    _current_app: contextvars.ContextVar[Optional["Flask"]] = contextvars.ContextVar(
        "flask_stub_current_app", default=None
    )
    _request_ctx: contextvars.ContextVar[Optional["_Request"]] = contextvars.ContextVar(
        "flask_stub_request", default=None
    )
    _g_ctx: contextvars.ContextVar[Optional[Dict[str, Any]]] = contextvars.ContextVar(
        "flask_stub_g", default=None
    )

    class _ArgsDict(dict):
        """Dictionary with Flask-like ``get`` helper supporting ``type`` kwarg."""

        def get(self, key: str, default: Any = None, type: Callable | None = None):  # type: ignore[override]
            if key not in self:
                return default
            value = super().get(key, default)
            if type is not None:
                try:
                    return type(value)
                except Exception:
                    return default
            return value

    class _Request:
        def __init__(
            self,
            method: str,
            path: str,
            json_data: Any = None,
            headers: Optional[Dict[str, str]] = None,
            args: Optional[Dict[str, Any]] = None,
        ) -> None:
            self.method = method
            self.path = path
            self._json_data = json_data
            self.headers = headers or {}
            self.args = _ArgsDict(args or {})

        def get_json(self, silent: bool = False) -> Any:
            return self._json_data

    class _RequestProxy:
        def _get(self) -> _Request:
            req = _request_ctx.get()
            if req is None:
                raise RuntimeError("No active request context")
            return req

        def __getattr__(self, name: str) -> Any:
            return getattr(self._get(), name)

    class _GProxy:
        def _get_store(self) -> Dict[str, Any]:
            store = _g_ctx.get()
            if store is None:
                store = {}
                _g_ctx.set(store)
            return store

        def __getattr__(self, name: str) -> Any:
            store = self._get_store()
            if name in store:
                return store[name]
            raise AttributeError(name)

        def __setattr__(self, name: str, value: Any) -> None:
            store = self._get_store()
            store[name] = value

        def __delattr__(self, name: str) -> None:
            store = self._get_store()
            if name in store:
                del store[name]
            else:
                raise AttributeError(name)

        def pop(self, name: str, default: Any = None) -> Any:
            return self._get_store().pop(name, default)

        def clear(self) -> None:
            self._get_store().clear()

        def __contains__(self, name: str) -> bool:
            return name in self._get_store()

    request = _RequestProxy()
    g = _GProxy()

    class Response:
        def __init__(
            self,
            data: Any = None,
            status: int = 200,
            headers: Optional[Dict[str, str]] = None,
            mimetype: str = "application/json",
        ) -> None:
            self.data = data
            self.status_code = status
            self.headers: Dict[str, str] = headers or {}
            self.mimetype = mimetype
            self._json_data = data if isinstance(data, (dict, list)) else None

        def get_json(self) -> Any:
            return self._json_data if self._json_data is not None else self.data

    def jsonify(*args: Any, **kwargs: Any) -> Response:
        if args and kwargs:
            raise TypeError("jsonify() behavior undefined when mixing args and kwargs")
        if len(args) == 1:
            payload = args[0]
        elif args:
            payload = list(args)
        else:
            payload = kwargs
        return Response(payload, mimetype="application/json")

    @dataclass
    class _Route:
        pattern: re.Pattern[str]
        methods: List[str]
        handler: Callable[..., Any]

    class _AppContext:
        def __init__(self, app: "Flask") -> None:
            self.app = app
            self._g: Dict[str, Any] = {}

        def __enter__(self) -> "_AppContext":
            self._token_app = _current_app.set(self.app)
            self._token_g = _g_ctx.set(self._g)
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            try:
                for func in self.app._teardown_funcs:
                    func(exc)
            finally:
                _g_ctx.reset(self._token_g)
                _current_app.reset(self._token_app)

    class _TestClient:
        def __init__(self, app: "Flask") -> None:
            self.app = app

        def get(self, path: str, headers: Optional[Dict[str, str]] = None):
            return self._invoke("GET", path, None, headers)

        def post(
            self,
            path: str,
            json: Any = None,
            headers: Optional[Dict[str, str]] = None,
        ):
            return self._invoke("POST", path, json, headers)

        def delete(self, path: str, headers: Optional[Dict[str, str]] = None):
            return self._invoke("DELETE", path, None, headers)

        def put(
            self,
            path: str,
            json: Any = None,
            headers: Optional[Dict[str, str]] = None,
        ):
            return self._invoke("PUT", path, json, headers)

        def _invoke(
            self,
            method: str,
            path: str,
            json_data: Any,
            headers: Optional[Dict[str, str]],
        ):
            url = urlsplit(path)
            route_path = url.path or "/"
            query = {k: v[-1] for k, v in parse_qs(url.query).items()}
            match = self.app._match_route(route_path, method)
            if match is None:
                return self.app._handle_http_error(404)
            route, params = match
            request_obj = _Request(method, route_path, json_data, headers, query)
            token = _request_ctx.set(request_obj)
            try:
                with self.app.app_context():
                    try:
                        rv = route.handler(**params)
                    except Exception as exc:  # pragma: no cover - defensive path
                        return self.app._handle_exception(exc)
            finally:
                _request_ctx.reset(token)
            return self.app._prepare_response(rv)

    class Blueprint:
        def __init__(self, name: str, import_name: str) -> None:
            self.name = name
            self.import_name = import_name
            self._routes: List[Tuple[str, List[str], Callable[..., Any]]] = []

        def route(self, rule: str, methods: Optional[List[str]] = None):
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                self._routes.append((rule, methods or ["GET"], func))
                return func

            return decorator

    class Flask:
        def __init__(self, import_name: str) -> None:
            self.import_name = import_name
            self.config: Dict[str, Any] = {}
            self._routes: List[_Route] = []
            self._teardown_funcs: List[Callable[[Optional[BaseException]], None]] = []
            self._error_handlers: Dict[int, Callable[[Any], Any]] = {}

        def route(self, rule: str, methods: Optional[List[str]] = None):
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                self._add_route(rule, methods or ["GET"], func)
                return func

            return decorator

        def _add_route(self, rule: str, methods: List[str], handler: Callable[..., Any]) -> None:
            pattern = self._compile_rule(rule)
            self._routes.append(
                _Route(pattern=pattern, methods=[m.upper() for m in methods], handler=handler)
            )

        def register_blueprint(self, blueprint: Blueprint, url_prefix: Optional[str] = None) -> None:
            prefix = (url_prefix or "").rstrip("/")
            for rule, methods, handler in blueprint._routes:
                combined = f"{prefix}{rule}" if prefix else rule
                self._add_route(combined, methods, handler)

        def test_client(self) -> _TestClient:
            return _TestClient(self)

        def app_context(self) -> _AppContext:
            return _AppContext(self)

        def teardown_appcontext(self, func: Callable[[Optional[BaseException]], None]):
            self._teardown_funcs.append(func)
            return func

        def errorhandler(self, status_code: int):
            def decorator(func: Callable[[Any], Any]) -> Callable[[Any], Any]:
                self._error_handlers[status_code] = func
                return func

            return decorator

        def _compile_rule(self, rule: str):
            regex = re.sub(r"<([^>]+)>", r"(?P<\1>[^/]+)", rule)
            return re.compile(f"^{regex}$")

        def _match_route(
            self, path: str, method: str
        ) -> Optional[Tuple[_Route, Dict[str, str]]]:
            method = method.upper()
            for route in self._routes:
                if method not in route.methods:
                    continue
                match = route.pattern.match(path)
                if match:
                    return route, match.groupdict()
            return None

        def _prepare_response(self, rv: Any) -> Response:
            status = None
            headers: Optional[Dict[str, str]] = None
            body = rv
            if isinstance(rv, tuple):
                if len(rv) == 3:
                    body, status, headers = rv
                elif len(rv) == 2:
                    body, status = rv
                elif len(rv) == 1:
                    body = rv[0]
                else:
                    body = rv[0] if rv else None
            if isinstance(body, Response):
                response = body
            else:
                response = Response(body)
            if status is not None:
                response.status_code = status
            if headers:
                response.headers.update(headers)
            return response

        def _handle_http_error(self, status_code: int) -> Response:
            handler = self._error_handlers.get(status_code)
            if handler:
                return self._prepare_response(handler(None))
            return Response({"error": f"HTTP {status_code}"}, status=status_code)

        def _handle_exception(self, exc: Exception) -> Response:
            handler = self._error_handlers.get(500)
            if handler:
                return self._prepare_response(handler(exc))
            raise exc

    Blueprint = Blueprint
    Flask = Flask
    Response = Response
    request = request
    jsonify = jsonify
    g = g


try:  # pragma: no cover - imported when available
    from flask_cors import CORS
except ModuleNotFoundError:  # pragma: no cover - fallback used in tests
    class CORS:
        def __init__(self, app: Optional[Flask] = None, **_: Any) -> None:
            if app is not None:
                self.init_app(app)

        def init_app(self, app: Flask) -> None:  # pragma: no cover - trivial
            setattr(app, "cors_enabled", True)


__all__ = [
    "Blueprint",
    "CORS",
    "Flask",
    "Response",
    "g",
    "jsonify",
    "request",
]
