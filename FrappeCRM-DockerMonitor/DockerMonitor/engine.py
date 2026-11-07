import http.client
import json
import os
import shutil
import socket
import subprocess
import urllib.parse
from typing import Any

from .exceptions import (
	ContainerInspectionError,
	ContainerNotFoundError,
	DockerDaemonUnavailableError,
	RecoveryExecutionError,
)


class UnixSocketHTTPConnection(http.client.HTTPConnection):
	"""Zero-dependency HTTP connection over /var/run/docker.sock."""

	def __init__(self, socket_path: str, timeout: int = 10) -> None:
		super().__init__("localhost", timeout=timeout)
		self.socket_path = socket_path

	def connect(self) -> None:
		self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		self.sock.settimeout(self.timeout)
		self.sock.connect(self.socket_path)


class DockerEngineClient:
	"""Dual-engine Docker client: Direct Unix Socket primary, subprocess CLI fallback."""

	def __init__(self, socket_path: str = "/var/run/docker.sock") -> None:
		self.socket_path = socket_path
		self.use_socket = os.path.exists(socket_path) and os.access(socket_path, os.R_OK | os.W_OK)
		if not self.use_socket and not shutil.which("docker"):
			raise DockerDaemonUnavailableError(
				f"Neither accessible socket '{socket_path}' nor 'docker' CLI found."
			)

	def _socket_request(self, method: str, path: str, timeout: int = 10) -> tuple[int, bytes]:
		conn = UnixSocketHTTPConnection(self.socket_path, timeout=timeout)
		try:
			conn.request(method, path)
			resp = conn.getresponse()
			data = resp.read()
			return resp.status, data
		except OSError as exc:
			raise DockerDaemonUnavailableError(f"Socket communication failed: {exc}") from exc
		finally:
			conn.close()

	def list_crm_containers(self, project_name: str = "crm") -> list[str]:
		if self.use_socket:
			status, data = self._socket_request("GET", "/containers/json?all=true")
			if status != 200:
				raise DockerDaemonUnavailableError("Failed to list containers via socket.")
			containers = json.loads(data.decode("utf-8"))
			matched = []
			for c in containers:
				names = [n.lstrip("/") for n in c.get("Names", [])]
				labels = c.get("Labels") or {}
				if labels.get("com.docker.compose.project") == project_name or any(
					n.startswith(f"{project_name}-") for n in names
				):
					if names:
						matched.append(names[0])
			return sorted(matched)

		res = subprocess.run(
			["docker", "ps", "-a", "--format", "{{.Names}}"],
			capture_output=True,
			text=True,
			check=False,
		)
		if res.returncode != 0:
			raise DockerDaemonUnavailableError(res.stderr.strip())
		return sorted(
			[line.strip() for line in res.stdout.splitlines() if line.startswith(f"{project_name}-")]
		)

	def inspect_container(self, name: str) -> dict[str, Any]:
		if self.use_socket:
			status, data = self._socket_request("GET", f"/containers/{name}/json")
			if status == 404:
				raise ContainerNotFoundError(f"Container '{name}' not found.")
			if status != 200:
				raise ContainerInspectionError(f"Inspect failed for '{name}' (HTTP {status}).")
			return json.loads(data.decode("utf-8"))

		res = subprocess.run(["docker", "inspect", name], capture_output=True, text=True, check=False)
		if res.returncode != 0:
			raise ContainerNotFoundError(f"Container '{name}' not found: {res.stderr.strip()}")
		return json.loads(res.stdout)[0]

	def get_container_stats(self, name: str) -> dict[str, Any]:
		if self.use_socket:
			status, data = self._socket_request("GET", f"/containers/{name}/stats?stream=false", timeout=15)
			if status != 200:
				raise ContainerInspectionError(f"Stats failed for '{name}' (HTTP {status}).")
			return json.loads(data.decode("utf-8"))

		res = subprocess.run(
			["docker", "stats", name, "--no-stream", "--format", "{{json .}}"],
			capture_output=True,
			text=True,
			check=False,
		)
		if res.returncode != 0 or not res.stdout.strip():
			raise ContainerInspectionError(f"CLI stats failed for '{name}'.")
		return {"_cli_format": True, "raw": json.loads(res.stdout.strip())}

	def get_container_logs(self, name: str, since_ts: int, tail: int = 250) -> str:
		res = subprocess.run(
			["docker", "logs", "--since", str(since_ts), "--tail", str(tail), name],
			capture_output=True,
			text=True,
			errors="replace",
			check=False,
		)
		return (res.stdout or "") + "\n" + (res.stderr or "")

	def exec_probe(self, name: str, cmd: list[str], timeout: int = 5) -> bool:
		try:
			res = subprocess.run(
				["docker", "exec", name, *cmd],
				capture_output=True,
				text=True,
				timeout=timeout,
				check=False,
			)
			return res.returncode == 0
		except subprocess.SubprocessError:
			return False

	def restart_container(self, name: str, timeout: int = 10) -> bool:
		if self.use_socket:
			q = urllib.parse.urlencode({"t": timeout})
			status, _ = self._socket_request("POST", f"/containers/{name}/restart?{q}", timeout=timeout + 10)
			if status in (204, 200):
				return True
			raise RecoveryExecutionError(f"Socket restart failed for '{name}' (HTTP {status}).")

		res = subprocess.run(
			["docker", "restart", "-t", str(timeout), name],
			capture_output=True,
			text=True,
			check=False,
		)
		if res.returncode != 0:
			raise RecoveryExecutionError(res.stderr.strip())
		return True
