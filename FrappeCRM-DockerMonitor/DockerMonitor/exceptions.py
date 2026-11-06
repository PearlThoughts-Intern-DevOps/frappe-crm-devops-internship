class DockerMonitorError(Exception):
	"""Base exception for FrappeCRM_DockerMonitor."""


class DockerDaemonUnavailableError(DockerMonitorError):
	"""Raised when neither /var/run/docker.sock nor the docker CLI can reach the daemon."""


class ContainerNotFoundError(DockerMonitorError):
	"""Raised when a target container does not exist."""


class ContainerInspectionError(DockerMonitorError):
	"""Raised when inspecting or collecting stats from a container fails."""


class RecoveryExecutionError(DockerMonitorError):
	"""Raised when a container restart command fails."""
