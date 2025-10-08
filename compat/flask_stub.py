"""Minimal fallback implementations for Flask primitives used in tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any, Callable, Dict, Iterable, Iterator, Optional, Tuple


class _Args(dict):
    """Dictionary with a Flask-like ``get`` helper supporting ``type``."""

    def get(self, key: str, default: Any = None, type: Callable[[Any], Any] | None = None):  # type: ignore[override]
        value = super().get(key, default)
        if type is not None and value is not None:
            try:
                return type(value)
            except Exception:
                return default
        return value


class _Request:
    """Very small request object supporting headers and JSON payloads."""

    def __init__(self) -> None:
        self._json: Any = None
        self.headers: Dict[str, str] = {}
        self.args: _Args = _Args()
        self.method: str = "GET"

    def get_json(self, silent: bool = False) -> Any:
        # ``silent`` is ignored – the stub only stores JSON payloads passed in
        # via the test client's helper methods.
        return self._json


request = _Request()


def _clear_request() -> None:
    request._json = None
    request.headers = {}
    request.args = _Args()
    request.method = "GET"


class _Globals(SimpleNamespace):
    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        return hasattr(self, key)

    def pop(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            value = getattr(self, key)
            delattr(self, key)
            return value
        return default


g: _Globals = _Globals()


class Response:
    """Tiny response object that mirrors the attributes used in tests."""

    def __init__(
        self,
        data: Any = None,
        status: int = 200,
        headers: Optional[Dict[str, str]] = None,
        mimetype: str | None = "application/json",
    ) -> None:
        self.status_code = status
        self.headers: Dict[str, str] = dict(headers or {})
        self.mimetype = mimetype
        self._json_data: Any = None
        self.data: Any = None
        self.set_data(data)

    def set_data(self, data: Any) -> None:
        if isinstance(data, Response):
            # Copy from another response instance.
            self.data = data.data
            self._json_data = data._json_data
            self.headers.update(data.headers)
            self.mimetype = data.mimetype
            return
        if isinstance(data, (dict, list)):
            self._json_data = data
            self.data = json.dumps(data)
        else:
            self._json_data = None if data is None else data
            self.data = data

    def get_json(self) -> Any:
        return self._json_data

    # Flask's Response is iterable for streaming responses; the tests only need
    # the object to be iterable when a generator is returned, so we provide a
    # no-op iterator over the payload when it is an iterable.
    def __iter__(self) -> Iterator[Any]:
        if hasattr(self.data, "__iter__") and not isinstance(self.data, (str, bytes)):
            yield from self.data
        else:
            yield self.data


def jsonify(*args: Any, **kwargs: Any) -> Response:
    if args and kwargs:
        raise TypeError("jsonify() behavior not implemented for args and kwargs together")
    if args:
        if len(args) == 1:
            payload = args[0]
        else:
            payload = list(args)
    else:
        payload = kwargs
    return Response(payload, status=200)


class _AppContext:
    def __init__(self, app: "Flask") -> None:
        self.app = app

    def __enter__(self) -> "Flask":
        self.app._push_app_context()
        return self.app

    def __exit__(self, exc_type, exc, tb) -> None:
        self.app._pop_app_context(exc)


class Flask:
    """Minimal in-memory Flask replacement for tests."""

    def __init__(self, import_name: str) -> None:
        self.import_name = import_name
        self.config: Dict[str, Any] = {}
        self._routes: list[dict[str, Any]] = []
        self._teardown_funcs: list[Callable[[Optional[BaseException]], None]] = []
        self._error_handlers: Dict[int, Callable[[Any], Response]] = {}

    # Routing -----------------------------------------------------------------
    def route(self, rule: str, methods: Optional[Iterable[str]] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        methods = tuple((methods or ("GET",)))

        pattern = self._compile_rule(rule)

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            for method in methods:
                self._routes.append(
                    {
                        "rule": rule,
                        "pattern": pattern,
                        "method": method.upper(),
                        "func": func,
                    }
                )
            return func

        return decorator

    def errorhandler(self, code: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._error_handlers[code] = func
            return func

        return decorator

    # Context management ------------------------------------------------------
    def app_context(self) -> _AppContext:
        return _AppContext(self)

    def _push_app_context(self) -> None:
        g.__dict__.clear()

    def _pop_app_context(self, exc: Optional[BaseException]) -> None:
        for func in self._teardown_funcs:
            try:
                func(exc)
            except Exception:
                # Teardown failures are ignored similarly to Flask's behaviour
                # (they are logged in real Flask, but tests do not require it).
                pass
        g.__dict__.clear()

    def teardown_appcontext(self, func: Callable[[Optional[BaseException]], None]) -> Callable[[Optional[BaseException]], None]:
        self._teardown_funcs.append(func)
        return func

    # Test client -------------------------------------------------------------
    def test_client(self) -> "_TestClient":
        return _TestClient(self)

    # Utility ----------------------------------------------------------------
    def _dispatch_request(self, path: str, method: str) -> Callable[..., Any]:
        clean_path = path
        for route in self._routes:
            if route["method"] != method.upper():
                continue
            matched, params = self._match_path(route["pattern"], clean_path)
            if matched:
                return lambda *args, **kwargs: route["func"](**params)

        error_handler = self._error_handlers.get(404)
        if error_handler:
            return lambda *args, **kwargs: error_handler(SimpleNamespace(description="Not found"))
        return lambda *args, **kwargs: Response({"error": "Not found"}, status=404)

    # Routing helpers -------------------------------------------------------
    @staticmethod
    def _compile_rule(rule: str) -> list[Tuple[str, str]]:
        if rule == "/":
            return []
        segments = []
        for part in filter(None, rule.strip("/").split("/")):
            if part.startswith("<") and part.endswith(">"):
                segments.append(("param", part[1:-1]))
            else:
                segments.append(("static", part))
        return segments

    @staticmethod
    def _match_path(pattern: list[Tuple[str, str]], path: str) -> Tuple[bool, Dict[str, str]]:
        if not pattern:
            return (path in ("", "/"), {})

        path_clean = path.strip("/")
        if not path_clean:
            return False, {}
        parts = path_clean.split("/")
        if len(parts) != len(pattern):
            return False, {}

        params: Dict[str, str] = {}
        for (kind, value), piece in zip(pattern, parts):
            if kind == "static":
                if value != piece:
                    return False, {}
            else:
                params[value] = piece
        return True, params

    def _make_response(self, rv: Any) -> Response:
        status: Optional[int] = None
        headers: Optional[Dict[str, str]] = None

        if isinstance(rv, tuple):
            if len(rv) == 2:
                rv, status = rv
            elif len(rv) == 3:
                rv, status, headers = rv
            else:
                raise ValueError("Unexpected response tuple length")

        if isinstance(rv, Response):
            response = Response(rv, status=rv.status_code)
        elif isinstance(rv, (dict, list)):
            response = Response(rv)
        elif hasattr(rv, "__iter__") and not isinstance(rv, (str, bytes)):
            response = Response(rv, mimetype="text/plain")
        else:
            response = Response(rv)

        if status is not None:
            response.status_code = status
        if headers:
            response.headers.update(headers)
        return response


class _TestClient:
    def __init__(self, app: Flask) -> None:
        self.app = app

    def open(
        self,
        path: str,
        method: str = "GET",
        json: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        from urllib.parse import parse_qsl

        if "?" in path:
            path, raw_query = path.split("?", 1)
            request.args = _Args({k: v for k, v in parse_qsl(raw_query)})
        handler = self.app._dispatch_request(path, method)
        request._json = json
        request.headers = dict(headers or {})
        request.method = method.upper()
        g.__dict__.clear()
        try:
            rv = handler()
        finally:
            _clear_request()
        response = self.app._make_response(rv)
        # Trigger teardown callbacks for request-scoped resources.
        for func in self.app._teardown_funcs:
            try:
                func(None)
            except Exception:
                pass
        return response

    def get(self, path: str, **kwargs: Any) -> Response:
        return self.open(path, method="GET", **kwargs)

    def post(self, path: str, **kwargs: Any) -> Response:
        return self.open(path, method="POST", **kwargs)

    def put(self, path: str, **kwargs: Any) -> Response:
        return self.open(path, method="PUT", **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Response:
        return self.open(path, method="DELETE", **kwargs)


class CORS:
    """No-op stand in for flask_cors.CORS."""

    def __init__(self, app: Flask, resources: Optional[Any] = None) -> None:  # noqa: D401 - intentional no-op
        self.app = app
        self.resources = resources


__all__ = [
    "Flask",
    "CORS",
    "jsonify",
    "request",
    "Response",
    "g",
]
