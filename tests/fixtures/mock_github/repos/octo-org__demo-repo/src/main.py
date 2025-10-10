"""Entry point for the demo repo."""

from .utils import fibonacci, read_config


def build_summary(config_path: str) -> str:
    """Build a runtime summary using the configuration file."""

    config = read_config(config_path)
    sequence = fibonacci(config.get("depth", 5))
    lines = ["Demo Repository Runtime Summary:"]
    lines.append(f"Depth: {config.get('depth', 5)}")
    lines.append(f"Author: {config.get('author', 'unknown')}")
    lines.append(f"Fibonacci: {', '.join(str(num) for num in sequence)}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(build_summary("./config.json"))
