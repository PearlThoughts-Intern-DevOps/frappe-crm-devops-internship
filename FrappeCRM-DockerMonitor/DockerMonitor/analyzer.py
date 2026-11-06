import re
from typing import ClassVar

from .models import LogErrorSummary


class LogAnalyzer:
	"""Scans container logs with multi-line Python traceback folding and severity categorization."""

	PATTERNS: ClassVar[list[tuple[str, str, re.Pattern[str]]]] = [
		(
			"CRITICAL",
			"OOM_OR_FATAL",
			re.compile(r"Out of memory: Kill process|Segmentation fault|fatal error", re.I),
		),
		(
			"CRITICAL",
			"REDIS_PERSISTENCE",
			re.compile(r"MISCONF Errors writing to the AOF|OOM command not allowed", re.I),
		),
		(
			"CRITICAL",
			"DB_CONNECTIVITY",
			re.compile(r"Can't connect to MySQL server|Too many connections|Access denied for user", re.I),
		),
		(
			"ERROR",
			"PYTHON_EXCEPTION",
			re.compile(
				r"Traceback \(most recent call last\)|OperationalError|InternalServerError|WorkerTimeout"
			),
		),
		(
			"WARNING",
			"DB_DEADLOCK_OR_LOCK",
			re.compile(r"Deadlock found when trying to get lock|Lock wait timeout exceeded", re.I),
		),
		(
			"WARNING",
			"REDIS_WARNING",
			re.compile(r"Connection refused|LOADING Redis is loading the dataset", re.I),
		),
	]

	TIMESTAMP_OR_LOG_START = re.compile(
		r"^\d{4}-\d{2}-\d{2}|^(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b|^\[", re.I
	)
	EXCEPTION_LINE = re.compile(r"(Error|Exception):", re.I)

	def analyze(self, raw_logs: str) -> LogErrorSummary:
		raw_lines = raw_logs.splitlines()
		summary = LogErrorSummary(lines_scanned=len([l for l in raw_lines if l.strip()]))

		in_traceback = False
		for idx, raw_line in enumerate(raw_lines, start=1):
			line = raw_line.strip()
			if not line:
				continue

			if "Traceback (most recent call last):" in line:
				in_traceback = True
				summary.errors += 1
				summary.detected_issues.append(
					{"line": idx, "severity": "ERROR", "category": "PYTHON_TRACEBACK", "sample": line[:200]}
				)
				continue

			if in_traceback:
				# If a new log line starts with a timestamp or log level, traceback was interrupted/ended
				if self.TIMESTAMP_OR_LOG_START.search(line):
					in_traceback = False
				elif self.EXCEPTION_LINE.search(line):
					# Final exception line of traceback reached; consume and conclude traceback
					in_traceback = False
					continue
				else:
					# Intermediate stack frame or source code line
					continue

			for severity, category, regex in self.PATTERNS:
				if regex.search(line):
					if severity == "CRITICAL":
						summary.critical_errors += 1
					elif severity == "ERROR":
						summary.errors += 1
					else:
						summary.warnings += 1

					if len(summary.detected_issues) < 20:
						summary.detected_issues.append(
							{"line": idx, "severity": severity, "category": category, "sample": line[:200]}
						)
					break

		return summary
