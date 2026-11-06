import argparse
import json
import signal
import sys
import time

from .analyzer import LogAnalyzer
from .collector import MetricsCollector
from .config import MonitorConfig
from .engine import DockerEngineClient
from .exceptions import ContainerNotFoundError, DockerMonitorError
from .logger import setup_logger
from .models import ContainerHealthInfo, ContainerMetrics, ContainerStatusReport, LogErrorSummary
from .recovery import AutoRecoveryEngine
from .reporter import HealthReporter
from .state import StateManager


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="FrappeCRM Docker Container Monitoring, Health Auditing & Auto-Recovery Tool"
	)
	parser.add_argument("--check", action="store_true", help="Run one-shot health check")
	parser.add_argument("--report", action="store_true", help="Save JSON health report to reports/")
	parser.add_argument(
		"--auto-restart",
		action="store_true",
		help="Enable guarded auto-restart for unhealthy/stopped containers",
	)
	parser.add_argument(
		"--dry-run", action="store_true", help="Simulate recovery actions without restarting containers"
	)
	parser.add_argument("--watch", action="store_true", help="Run continuously in background daemon mode")
	parser.add_argument(
		"--interval", type=int, default=30, help="Polling interval in seconds for --watch mode (default: 30)"
	)
	parser.add_argument("--containers", nargs="+", help="Explicit list of container names to monitor")
	parser.add_argument("--json", action="store_true", help="Print raw JSON report to stdout only")
	return parser.parse_args()


def run_single_cycle(
	config: MonitorConfig,
	engine: DockerEngineClient,
	state: StateManager,
	collector: MetricsCollector,
	analyzer: LogAnalyzer,
	recovery: AutoRecoveryEngine,
	reporter: HealthReporter,
	save_report: bool,
	json_stdout: bool,
) -> int:
	containers = config.target_containers or engine.list_crm_containers(config.project_name)
	container_reports: list[ContainerStatusReport] = []

	for name in containers:
		now_ts = int(time.time())
		c_state = state.get_container_state(name)
		try:
			cid, health_info, metrics, alerts = collector.collect_health_and_metrics(name)
			raw_logs = engine.get_container_logs(
				name, since_ts=c_state["last_log_cursor_ts"], tail=config.log_tail_lines
			)
			log_summary = analyzer.analyze(raw_logs)
			state.update_log_cursor(name, now_ts)
		except ContainerNotFoundError:
			cid = "missing"
			health_info = ContainerHealthInfo(status="missing", health="none", app_probe_status="failed")
			metrics = ContainerMetrics()
			alerts = [f"Container '{name}' does not exist"]
			log_summary = LogErrorSummary()

		container_reports.append(
			ContainerStatusReport(
				name=name,
				id=cid,
				state=health_info,
				metrics=metrics,
				threshold_alerts=alerts,
				log_analysis=log_summary,
			)
		)

	recovery_actions = recovery.evaluate_and_recover(container_reports)
	health_report = reporter.build_report(container_reports, recovery_actions)

	if save_report:
		reporter.save_json_report(health_report)

	if json_stdout:
		print(json.dumps(health_report.to_dict(), indent=2))
	else:
		reporter.print_terminal_summary(health_report)

	if health_report.cluster_status == "HEALTHY":
		return 0
	if health_report.cluster_status == "DEGRADED":
		return 1
	return 2


def main() -> int:
	args = parse_args()
	config = MonitorConfig(
		auto_restart_enabled=args.auto_restart,
		dry_run=args.dry_run,
	)
	if args.containers:
		config.target_containers = args.containers

	logger = setup_logger(config.logs_dir, quiet_console=args.json)

	try:
		engine = DockerEngineClient(config.socket_path)
		state = StateManager(config.state_file)
		collector = MetricsCollector(engine, config)
		analyzer = LogAnalyzer()
		recovery = AutoRecoveryEngine(engine, state, config, logger)
		reporter = HealthReporter(config)

		save_report = args.report or args.watch

		if not args.watch:
			return run_single_cycle(
				config, engine, state, collector, analyzer, recovery, reporter, save_report, args.json
			)

		stop_requested = False

		def _handle_sig(signum: int, _frame: object) -> None:
			nonlocal stop_requested
			logger.info(f"Received signal {signum}, shutting down watch loop gracefully...")
			stop_requested = True

		signal.signal(signal.SIGINT, _handle_sig)
		signal.signal(signal.SIGTERM, _handle_sig)

		logger.info(f"Starting continuous watch mode (interval={args.interval}s)...")
		exit_code = 0
		while not stop_requested:
			exit_code = run_single_cycle(
				config,
				engine,
				state,
				collector,
				analyzer,
				recovery,
				reporter,
				save_report=True,
				json_stdout=args.json,
			)
			for _ in range(args.interval):
				if stop_requested:
					break
				time.sleep(1)
		return exit_code

	except DockerMonitorError as exc:
		logger.critical(f"Fatal Monitor Error: {exc}")
		return 3
