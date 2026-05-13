from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
SERVER_PATH = ROOT / "query-backend" / "server.py"
DEFAULT_BASE_URL = "http://127.0.0.1:8088"
DEFAULT_DEGRADED_BASE_URL = "http://127.0.0.1:8089"


def _port_open(host: str, port: int) -> bool:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
		probe.settimeout(0.2)
		return probe.connect_ex((host, port)) == 0


def _server_ready(base_url: str) -> bool:
	request_obj = urllib.request.Request(
		f"{base_url.rstrip('/')}/graph/query",
		data=json.dumps({"investigation_id": "pytest-bootstrap", "cypher": "RETURN 1 AS value"}).encode("utf-8"),
		headers={"Content-Type": "application/json"},
		method="POST",
	)
	try:
		with urllib.request.urlopen(request_obj, timeout=2) as response:
			return response.status == 200
	except (urllib.error.URLError, TimeoutError, ValueError):
		return False


def _find_free_port(host: str) -> int:
	with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
		probe.bind((host, 0))
		return int(probe.getsockname()[1])


def _resolve_base_url(base_url: str) -> str:
	parsed = urllib.parse.urlparse(base_url)
	host = parsed.hostname or "127.0.0.1"
	port = parsed.port
	if port is None:
		raise AssertionError(f"Missing port in query backend base URL: {base_url}")
	if _server_ready(base_url) or not _port_open(host, port):
		return base_url

	free_port = _find_free_port(host)
	return parsed._replace(netloc=f"{host}:{free_port}").geturl()


def _wait_until_ready(base_url: str, process: subprocess.Popen[str], timeout: float = 30.0) -> None:
	parsed = urllib.parse.urlparse(base_url)
	host = parsed.hostname or "127.0.0.1"
	port = parsed.port
	if port is None:
		raise AssertionError(f"Missing port in query backend base URL: {base_url}")

	deadline = time.time() + timeout
	while time.time() < deadline:
		if process.poll() is not None:
			stdout, stderr = process.communicate(timeout=5)
			raise AssertionError(
				f"Query backend exited before becoming ready at {base_url}. "
				f"returncode={process.returncode}\nstdout:\n{stdout}\nstderr:\n{stderr}"
			)
		if _port_open(host, port):
			return
		if _server_ready(base_url):
			return
		time.sleep(0.5)
	raise AssertionError(f"Query backend did not become ready at {base_url}")


def _start_backend(base_url: str, *, sync_status: str | None = None, staleness_seconds: str | None = None) -> subprocess.Popen[str] | None:
	host = urllib.parse.urlparse(base_url).hostname or "127.0.0.1"
	port = urllib.parse.urlparse(base_url).port
	if port is None:
		raise AssertionError(f"Missing port in query backend base URL: {base_url}")

	if _server_ready(base_url):
		return None

	env = os.environ.copy()
	env["QUERY_BACKEND_HOST"] = host
	env["QUERY_BACKEND_PORT"] = str(port)
	if sync_status is not None:
		env["QUERY_BACKEND_SYNC_STATUS"] = sync_status
	if staleness_seconds is not None:
		env["QUERY_BACKEND_STALENESS_SECONDS"] = staleness_seconds

	process = subprocess.Popen(
		[sys.executable, str(SERVER_PATH)],
		cwd=ROOT,
		env=env,
		stdout=subprocess.PIPE,
		stderr=subprocess.PIPE,
		text=True,
	)
	try:
		_wait_until_ready(base_url, process)
	except Exception:
		process.terminate()
		try:
			process.wait(timeout=5)
		except subprocess.TimeoutExpired:
			process.kill()
			process.wait(timeout=5)
		raise
	return process


@pytest.fixture(scope="session", autouse=True)
def query_backend_runtime() -> Iterator[None]:
	os.environ.setdefault("QUERY_BACKEND_BASE_URL", DEFAULT_BASE_URL)
	os.environ.setdefault("QUERY_BACKEND_DEGRADED_BASE_URL", DEFAULT_DEGRADED_BASE_URL)
	os.environ["QUERY_BACKEND_BASE_URL"] = _resolve_base_url(os.environ["QUERY_BACKEND_BASE_URL"])
	os.environ["QUERY_BACKEND_DEGRADED_BASE_URL"] = _resolve_base_url(os.environ["QUERY_BACKEND_DEGRADED_BASE_URL"])

	started_processes: list[subprocess.Popen[str]] = []
	healthy_process = _start_backend(os.environ["QUERY_BACKEND_BASE_URL"])
	if healthy_process is not None:
		started_processes.append(healthy_process)

	degraded_process = _start_backend(
		os.environ["QUERY_BACKEND_DEGRADED_BASE_URL"],
		sync_status="stale",
		staleness_seconds="960",
	)
	if degraded_process is not None:
		started_processes.append(degraded_process)

	try:
		yield
	finally:
		for process in reversed(started_processes):
			if process.poll() is not None:
				continue
			process.terminate()
			try:
				process.wait(timeout=5)
			except subprocess.TimeoutExpired:
				process.kill()
				process.wait(timeout=5)
