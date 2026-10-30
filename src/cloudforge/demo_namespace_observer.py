"""Fixed observer executed only inside the owned Linux namespace fixture.

This file is not an authorization boundary. No caller-supplied executable,
network destination, path, command or credential is accepted.
"""
from __future__ import annotations

import http.client
import json
import select
import subprocess
import sys


def _start() -> tuple[subprocess.Popen[str], int]:
    child = subprocess.Popen(
        [sys.executable, "-I", "-S", "/app/app.py"],
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, close_fds=True,
    )
    try:
        if child.stdout is None or not select.select([child.stdout], [], [], 5)[0]:
            raise RuntimeError("reference application did not become ready")
        text = child.stdout.readline().strip()
        if not text.isascii() or not text.isdecimal():
            raise RuntimeError("invalid reference application port")
        port = int(text)
        if not 1 <= port <= 65535 or child.poll() is not None:
            raise RuntimeError("reference application did not start")
        return child, port
    except Exception:
        _stop(child)
        raise


def _stop(child: subprocess.Popen[str]) -> None:
    try:
        if child.poll() is None:
            child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=5)
            raise RuntimeError("reference application termination timed out")
    finally:
        if child.stdout is not None:
            child.stdout.close()
        if child.stderr is not None:
            child.stderr.close()


def _probe(port: int) -> str:
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("HEAD", "/health")
        response = connection.getresponse()
        status = response.status
        response.read()
    except (OSError, http.client.HTTPException):
        return "unknown"
    finally:
        connection.close()
    return "pass" if status == 204 else "fail"


def main() -> None:
    trace = []
    first, first_port = _start()
    try:
        trace.append({"phase": "running", "outcome": _probe(first_port)})
    finally:
        _stop(first)
    trace.append({"phase": "process-stopped", "outcome": _probe(first_port)})
    second, second_port = _start()
    try:
        trace.append({"phase": "process-restarted", "outcome": _probe(second_port)})
    finally:
        _stop(second)
    print(json.dumps({"trace": trace}, sort_keys=True, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
