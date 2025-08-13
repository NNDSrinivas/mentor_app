# Stub for optional dependency 'docker'
from typing import Any

class Containers:
    def list(self, all: bool = ...) -> list[Any]: ...

class DockerClient:
    containers: Containers

def from_env() -> DockerClient: ...
