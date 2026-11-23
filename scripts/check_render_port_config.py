#!/usr/bin/env python3
"""Fail CI if the Render web port differs across Docker and startup config."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]


def require(pattern: str, content: str, label: str) -> str:
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        print(f"ERROR: could not determine {label}", file=sys.stderr)
        raise SystemExit(1)
    return match.group(1)


dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
entrypoint = (ROOT / "backend" / "docker-entrypoint.sh").read_text(encoding="utf-8")
render_blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

docker_default = require(r"^\s*PORT=(\d+)\s*$", dockerfile, "Dockerfile PORT default")
docker_exposed = require(r"^EXPOSE\s+(\d+)\s*$", dockerfile, "Dockerfile EXPOSE port")
entrypoint_default = require(
    r'--bind\s+"0\.0\.0\.0:\$\{PORT:-(\d+)\}"',
    entrypoint,
    "entrypoint PORT fallback",
)
render_port = require(
    r"^\s*-\s*\n\s+key:\s*PORT\s*\n\s+value:\s*[\"']?(\d+)[\"']?\s*$",
    render_blueprint,
    "Render Blueprint PORT value",
)

ports = {
    "Dockerfile PORT default": docker_default,
    "Dockerfile EXPOSE": docker_exposed,
    "entrypoint fallback": entrypoint_default,
    "Render Blueprint PORT": render_port,
}
if len(set(ports.values())) != 1:
    for label, port in ports.items():
        print(f"{label}: {port}", file=sys.stderr)
    raise SystemExit("ERROR: Render web port configuration is inconsistent")

port = next(iter(ports.values()))
if port != "10000":
    raise SystemExit(f"ERROR: expected Render's configured default port 10000, found {port}")

print(f"Render web port configuration aligned: 0.0.0.0:{port}")
