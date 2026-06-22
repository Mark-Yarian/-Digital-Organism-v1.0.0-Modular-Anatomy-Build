"""
============================================================
TELEMETRY / OBSERVATORY ORGAN
============================================================

Project:
    Digital Organism

Build:
    1.1.0

Organism Name:
    ContinuityNode

Organ:
    Telemetry / Observatory Organ

File:
    organs/telemetry.py

Primary Function:
    Track local observability metrics, organism health, event counts,
    memory growth, reflex warnings, immune decisions, topology summary,
    and lifecycle state over time.

Scientific / Clinical Description:
    The Telemetry Organ is an observability and measurement component.

    It does not create awareness, self-awareness, consciousness, agency,
    autonomy, or intention. The observatory metaphor is used
    architecturally to describe structured monitoring of organism state.

Relationship To Existing Organs:
    Core Identity Organ:
        Provides organism identity.

    Sensorium Organ:
        Provides passive environment and topology observations.

    Network Cartography Organ:
        Provides dry-run cartography planning metrics.

    Memory Organ:
        Provides record counts and change markers.

    Event Bus Organ:
        Provides event activity.

    Metabolism Organ:
        Provides lifecycle and heartbeat activity.

    Reflex Organ:
        Provides warning and safe response metrics.

    Immune Organ:
        Provides allow/deny safety decision metrics.

    Interface Organ:
        Provides human-facing command usage metrics.

    Telemetry Organ:
        Collects safe metrics from approved state files and produces
        observability reports.

Important Safety Boundary:
    The Telemetry Organ is read-only except for its own output files.

    It may:
        - read approved JSON state/report files
        - count JSONL lines in approved logs
        - write telemetry metrics
        - append telemetry timeseries
        - generate observatory report
        - publish telemetry events through Event Bus

    It may not:
        - execute commands
        - access the network
        - scan arbitrary files
        - read private documents
        - store raw secrets
        - modify other organ files
        - delete history
        - make decisions
        - trigger actions
        - enable active cartography
        - bypass Immune

Storage Model:
    data/telemetry/
        telemetry_metrics.json
        telemetry_timeseries.jsonl
        latest_observatory_report.json

Build 1.1.0 Behavior:
    - Create telemetry directory.
    - Read approved JSON reports if present.
    - Extract safe counters and health markers.
    - Count approved JSONL logs if present.
    - Write telemetry_metrics.json.
    - Append telemetry_timeseries.jsonl.
    - Write latest_observatory_report.json.
"""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================


class TelemetryError(Exception):
    """
    Base exception for all Telemetry Organ errors.
    """


class TelemetryReadError(TelemetryError):
    """
    Raised when an approved telemetry input cannot be read.
    """


class TelemetryWriteError(TelemetryError):
    """
    Raised when telemetry output cannot be written.
    """


class TelemetryValidationError(TelemetryError):
    """
    Raised when telemetry structure is malformed.
    """


class TelemetrySafetyError(TelemetryError):
    """
    Raised when a telemetry operation violates safety boundaries.
    """


# ============================================================
# TELEMETRY ORGAN CLASS
# ============================================================


class TelemetryOrgan:
    """
    Local observability organ.

    Build 1.1.0 is read-only toward the rest of the organism.

    Telemetry reads approved state/report files and writes only into
    data/telemetry/.
    """

    SCHEMA_VERSION = "1.0.0"
    TELEMETRY_MODE = "LOCAL_OBSERVABILITY"

    APPROVED_JSON_INPUTS = {
        "identity": "data/identity.json",
        "sensorium": "data/sensorium_snapshot.json",
        "cartography_report": "data/network_cartography_report.json",
        "cartography_policy": "data/network_cartography_policy.json",
        "memory_summary": "data/memory/summaries/latest_memory_summary.json",
        "memory_index": "data/memory/memory_index.json",
        "event_bus_state": "data/events/latest_event_bus_state.json",
        "metabolism_state": "data/metabolism/metabolism_state.json",
        "reflex_state": "data/reflex/latest_reflex_state.json",
        "immune_state": "data/immune/latest_immune_state.json",
        "interface_state": "data/interface/latest_interface_state.json",
    }

    APPROVED_JSONL_INPUTS = {
        "event_bus_log": "data/events/event_bus_log.jsonl",
        "memory_event_log": "data/memory/event_log.jsonl",
        "cartography_audit_log": "data/network_cartography_audit_log.jsonl",
        "metabolism_cycles_log": "data/metabolism/metabolism_cycles.jsonl",
        "reflex_log": "data/reflex/reflex_log.jsonl",
        "immune_decisions_log": "data/immune/immune_decisions.jsonl",
        "interface_log": "data/interface/interface_log.jsonl",
    }

    PROHIBITED_DETAIL_KEYS = [
        "raw_environment_values",
        "environment_values",
        "secret_values",
        "token_values",
        "password_values",
        "credential_values",
        "cookie_values",
        "raw_private_key",
        "private_key",
    ]

    def __init__(
        self,
        core_identity: Any,
        event_bus: Optional[Any] = None,
        immune: Optional[Any] = None,
        telemetry_root: str = "data/telemetry",
    ) -> None:
        """
        Initialize the Telemetry Organ.
        """

        self.core_identity = core_identity
        self.event_bus = event_bus
        self.immune = immune

        self.telemetry_root = Path(telemetry_root)
        self.metrics_path = self.telemetry_root / "telemetry_metrics.json"
        self.timeseries_path = self.telemetry_root / "telemetry_timeseries.jsonl"
        self.observatory_report_path = self.telemetry_root / "latest_observatory_report.json"

        self.reads_performed_this_run = 0
        self.missing_inputs_this_run = 0
        self.metrics_written_this_run = 0
        self.timeseries_records_written_this_run = 0
        self.reports_written_this_run = 0

        self.ensure_telemetry_structure()

    # ========================================================
    # TIME AND ID HELPERS
    # ========================================================

    def utc_now_iso(self) -> str:
        """
        Return current UTC timestamp.
        """

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_telemetry_id(self) -> str:
        """
        Generate telemetry record ID.
        """

        timestamp = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        short_id = uuid.uuid4().hex[:6]

        return f"telemetry-{timestamp}-{short_id}"

    # ========================================================
    # STRUCTURE
    # ========================================================

    def ensure_telemetry_structure(self) -> None:
        """
        Create telemetry output directory.
        """

        try:
            self.telemetry_root.mkdir(parents=True, exist_ok=True)

        except OSError as error:
            raise TelemetryWriteError(
                f"Could not create telemetry directory: {error}"
            ) from error

    # ========================================================
    # COLLECTION
    # ========================================================

    def collect_telemetry(self) -> Dict[str, Any]:
        """
        Collect telemetry from approved organism state files.

        This is the primary public method.
        """

        if self.immune is not None:
            self.immune.review_action_request(
                requested_action="telemetry.collect_metrics",
                source_organ="TelemetryOrgan",
                request={
                    "read_only": True,
                    "approved_paths_only": True,
                    "writes_only_to": str(self.telemetry_root),
                },
            )

        inputs = {
            key: self.safe_read_json(key, missing_ok=True)
            for key in self.APPROVED_JSON_INPUTS.keys()
        }

        log_counts = {
            key: self.safe_count_jsonl_lines(key, missing_ok=True)
            for key in self.APPROVED_JSONL_INPUTS.keys()
        }

        metrics = self.build_metrics(inputs=inputs, log_counts=log_counts)
        self.save_metrics(metrics)
        self.append_timeseries(metrics)

        report = self.build_observatory_report(metrics)
        self.save_observatory_report(report)

        self.publish_telemetry_event(
            event_type="telemetry.metrics.collected",
            payload={
                "telemetry_id": metrics["telemetry_id"],
                "health_status": report["health_summary"]["overall_status"],
                "metrics_path": str(self.metrics_path),
                "observatory_report_path": str(self.observatory_report_path),
            },
        )

        return copy.deepcopy(report)

    # ========================================================
    # SAFE INPUT READING
    # ========================================================

    def safe_read_json(
        self,
        key: str,
        missing_ok: bool = False,
    ) -> Dict[str, Any]:
        """
        Read an approved JSON input by key.

        This method does not accept arbitrary paths.
        """

        if key not in self.APPROVED_JSON_INPUTS:
            raise TelemetrySafetyError(
                f"Telemetry JSON input key is not approved: {key}"
            )

        path = Path(self.APPROVED_JSON_INPUTS[key])

        if not self.is_approved_json_input_path(path):
            raise TelemetrySafetyError(
                f"Telemetry path is not approved: {path}"
            )

        if not path.exists():
            self.missing_inputs_this_run += 1
            if missing_ok:
                return {}
            raise TelemetryReadError(f"Approved telemetry input is missing: {path}")

        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)

        except json.JSONDecodeError as error:
            raise TelemetryReadError(
                f"Approved telemetry input could not be parsed: {path}: {error}"
            ) from error

        except OSError as error:
            raise TelemetryReadError(
                f"Approved telemetry input could not be read: {path}: {error}"
            ) from error

        if not isinstance(data, dict):
            raise TelemetryReadError(
                f"Approved telemetry input must contain a JSON object: {path}"
            )

        self.reads_performed_this_run += 1

        return data

    def safe_count_jsonl_lines(
        self,
        key: str,
        missing_ok: bool = False,
    ) -> int:
        """
        Count lines in an approved JSONL log.

        This is a line count only. It does not parse every log entry.
        """

        if key not in self.APPROVED_JSONL_INPUTS:
            raise TelemetrySafetyError(
                f"Telemetry JSONL input key is not approved: {key}"
            )

        path = Path(self.APPROVED_JSONL_INPUTS[key])

        if not self.is_approved_jsonl_input_path(path):
            raise TelemetrySafetyError(
                f"Telemetry JSONL path is not approved: {path}"
            )

        if not path.exists():
            self.missing_inputs_this_run += 1
            if missing_ok:
                return 0
            raise TelemetryReadError(f"Approved telemetry JSONL input is missing: {path}")

        try:
            with path.open("r", encoding="utf-8") as file:
                count = sum(1 for line in file if line.strip())

        except OSError as error:
            raise TelemetryReadError(
                f"Approved telemetry JSONL input could not be read: {path}: {error}"
            ) from error

        self.reads_performed_this_run += 1

        return count

    def is_approved_json_input_path(self, path: Path) -> bool:
        """
        Confirm a path is exactly one approved JSON input.
        """

        normalized = str(path).replace("\\", "/")

        approved = {
            str(Path(value)).replace("\\", "/")
            for value in self.APPROVED_JSON_INPUTS.values()
        }

        return normalized in approved

    def is_approved_jsonl_input_path(self, path: Path) -> bool:
        """
        Confirm a path is exactly one approved JSONL input.
        """

        normalized = str(path).replace("\\", "/")

        approved = {
            str(Path(value)).replace("\\", "/")
            for value in self.APPROVED_JSONL_INPUTS.values()
        }

        return normalized in approved

    # ========================================================
    # METRIC BUILDING
    # ========================================================

    def build_metrics(
        self,
        inputs: Dict[str, Dict[str, Any]],
        log_counts: Dict[str, int],
    ) -> Dict[str, Any]:
        """
        Build safe telemetry metrics from approved inputs.
        """

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        identity = inputs.get("identity", {})
        sensorium = inputs.get("sensorium", {})
        cartography = inputs.get("cartography_report", {})
        memory = inputs.get("memory_summary", {})
        events = inputs.get("event_bus_state", {})
        metabolism = inputs.get("metabolism_state", {})
        reflex = inputs.get("reflex_state", {})
        immune = inputs.get("immune_state", {})
        interface = inputs.get("interface_state", {})

        topology = sensorium.get("topology_seed_matrix", {})
        network_interfaces = sensorium.get("network_interfaces", {})
        arp_table = sensorium.get("arp_table", {})
        dry_run_plan = cartography.get("dry_run_plan", {})

        metrics = {
            "schema_version": self.SCHEMA_VERSION,
            "telemetry_id": self.generate_telemetry_id(),
            "telemetry_timestamp_utc": self.utc_now_iso(),
            "telemetry_mode": self.TELEMETRY_MODE,
            "organism": {
                "organism_name": persistent.get("organism_name"),
                "lineage_id": persistent.get("lineage_id"),
                "runtime_instance_id": runtime.get("runtime_instance_id"),
                "current_build": persistent.get("current_build") or identity.get("current_build"),
            },
            "identity_metrics": {
                "identity_file_present": bool(identity),
                "first_build": identity.get("first_build"),
                "current_build": identity.get("current_build"),
                "locked_fields_count": len(identity.get("identity_locked_fields", [])),
            },
            "sensorium_metrics": {
                "snapshot_present": bool(sensorium),
                "snapshot_id": sensorium.get("snapshot_id"),
                "network_interface_count": network_interfaces.get("interface_count", 0),
                "ipv4_address_count": network_interfaces.get("ipv4_address_count", 0),
                "arp_entry_count": arp_table.get("entries_count", 0),
                "topology_nodes_count": topology.get("nodes_count", 0),
                "topology_edges_count": topology.get("edges_count", 0),
                "active_scan_performed": topology.get("active_scan_performed", False),
            },
            "cartography_metrics": {
                "report_present": bool(cartography),
                "report_id": cartography.get("report_id"),
                "cartography_mode": cartography.get("cartography_mode"),
                "active_discovery_performed": cartography.get("active_discovery_performed", False),
                "approved_scopes_count": dry_run_plan.get("approved_scopes_count", 0),
                "candidate_hosts_count": dry_run_plan.get("candidate_hosts_count", 0),
                "planned_probe_count": dry_run_plan.get("planned_probe_count", 0),
                "active_probes_sent": dry_run_plan.get("active_probes_sent", 0),
            },
            "memory_metrics": {
                "summary_present": bool(memory),
                "records_count": memory.get("records_count", 0),
                "sensorium_changed_since_previous": memory.get("change_markers", {}).get("sensorium_changed_since_previous"),
                "topology_changed_since_previous": memory.get("change_markers", {}).get("topology_changed_since_previous"),
                "cartography_plan_changed_since_previous": memory.get("change_markers", {}).get("cartography_plan_changed_since_previous"),
            },
            "event_metrics": {
                "event_state_present": bool(events),
                "events_published_this_run": events.get("events_published_this_run", 0),
                "total_events_recorded": events.get("total_events_recorded", 0),
                "known_event_types_count": events.get("known_event_types_count", 0),
            },
            "metabolism_metrics": {
                "metabolism_state_present": bool(metabolism),
                "runtime_mode": metabolism.get("runtime_mode"),
                "current_phase": metabolism.get("current_phase"),
                "cycle_count": metabolism.get("cycle_count", 0),
                "max_cycles": metabolism.get("max_cycles", 0),
                "heartbeat_count": metabolism.get("heartbeat_count", 0),
                "shutdown_recorded": metabolism.get("shutdown_recorded"),
                "finalized": metabolism.get("finalized"),
                "continuous_mode_enabled": metabolism.get("continuous_mode_enabled", False),
            },
            "reflex_metrics": {
                "reflex_state_present": bool(reflex),
                "checks_performed_this_run": reflex.get("checks_performed_this_run", 0),
                "reflexes_triggered_this_run": reflex.get("reflexes_triggered_this_run", 0),
                "warnings_raised_this_run": reflex.get("warnings_raised_this_run", 0),
                "safe_actions_performed_this_run": reflex.get("safe_actions_performed_this_run", 0),
                "unsafe_actions_blocked_this_run": reflex.get("unsafe_actions_blocked_this_run", 0),
            },
            "immune_metrics": {
                "immune_state_present": bool(immune),
                "immune_mode": immune.get("immune_mode"),
                "deny_by_default": immune.get("deny_by_default"),
                "decisions_this_run": immune.get("decisions_this_run", 0),
                "allowed_this_run": immune.get("allowed_this_run", 0),
                "denied_this_run": immune.get("denied_this_run", 0),
                "validation_checks_this_run": immune.get("validation_checks_this_run", 0),
            },
            "interface_metrics": {
                "interface_state_present": bool(interface),
                "interface_mode": interface.get("interface_mode"),
                "commands_handled_this_run": interface.get("commands_handled_this_run", 0),
                "reads_performed_this_run": interface.get("reads_performed_this_run", 0),
                "invalid_commands_this_run": interface.get("invalid_commands_this_run", 0),
                "interface_events_written_this_run": interface.get("interface_events_written_this_run", 0),
            },
            "log_counts": copy.deepcopy(log_counts),
            "telemetry_runtime_metrics": {
                "reads_performed_this_run": self.reads_performed_this_run,
                "missing_inputs_this_run": self.missing_inputs_this_run,
                "metrics_written_this_run": self.metrics_written_this_run,
                "timeseries_records_written_this_run": self.timeseries_records_written_this_run,
                "reports_written_this_run": self.reports_written_this_run,
            },
            "safety_summary": {
                "commands_executed": False,
                "network_access_performed": False,
                "arbitrary_files_read": False,
                "private_documents_read": False,
                "raw_secrets_stored": False,
                "other_organs_modified": False,
                "history_deleted": False,
                "decisions_made": False,
                "actions_triggered": False,
                "active_cartography_enabled": False,
                "immune_bypassed": False,
            },
        }

        self.validate_metrics(metrics)

        return metrics

    def build_observatory_report(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build human-readable observatory report.
        """

        health = self.calculate_health_summary(metrics)

        report = {
            "schema_version": self.SCHEMA_VERSION,
            "report_timestamp_utc": self.utc_now_iso(),
            "telemetry_id": metrics["telemetry_id"],
            "telemetry_mode": self.TELEMETRY_MODE,
            "organism": copy.deepcopy(metrics["organism"]),
            "health_summary": health,
            "key_metrics": {
                "current_build": metrics["organism"].get("current_build"),
                "memory_records_count": metrics["memory_metrics"].get("records_count"),
                "total_events_recorded": metrics["event_metrics"].get("total_events_recorded"),
                "heartbeat_count": metrics["metabolism_metrics"].get("heartbeat_count"),
                "reflex_warnings": metrics["reflex_metrics"].get("warnings_raised_this_run"),
                "immune_denials": metrics["immune_metrics"].get("denied_this_run"),
                "topology_nodes_count": metrics["sensorium_metrics"].get("topology_nodes_count"),
                "topology_edges_count": metrics["sensorium_metrics"].get("topology_edges_count"),
                "active_probes_sent": metrics["cartography_metrics"].get("active_probes_sent"),
            },
            "organ_presence": {
                "identity": metrics["identity_metrics"].get("identity_file_present"),
                "sensorium": metrics["sensorium_metrics"].get("snapshot_present"),
                "cartography": metrics["cartography_metrics"].get("report_present"),
                "memory": metrics["memory_metrics"].get("summary_present"),
                "events": metrics["event_metrics"].get("event_state_present"),
                "metabolism": metrics["metabolism_metrics"].get("metabolism_state_present"),
                "reflex": metrics["reflex_metrics"].get("reflex_state_present"),
                "immune": metrics["immune_metrics"].get("immune_state_present"),
                "interface": metrics["interface_metrics"].get("interface_state_present"),
            },
            "safety_summary": copy.deepcopy(metrics["safety_summary"]),
            "notes": [
                "Telemetry observes approved state files only.",
                "Telemetry does not execute commands.",
                "Telemetry does not access the network.",
                "Telemetry does not make decisions or trigger actions.",
            ],
        }

        self.validate_observatory_report(report)

        return report

    def calculate_health_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate simple health summary.

        This is not a decision engine. It is a measurement summary.
        """

        warnings = []
        status = "ok"

        if metrics["sensorium_metrics"].get("active_scan_performed") is True:
            warnings.append("Sensorium active scan marker was true.")
            status = "warning"

        if metrics["cartography_metrics"].get("active_discovery_performed") is True:
            warnings.append("Cartography active discovery marker was true.")
            status = "warning"

        if metrics["cartography_metrics"].get("active_probes_sent", 0) != 0:
            warnings.append("Cartography active probe count was non-zero.")
            status = "warning"

        if metrics["metabolism_metrics"].get("continuous_mode_enabled") is True:
            warnings.append("Metabolism continuous mode marker was true.")
            status = "warning"

        if metrics["immune_metrics"].get("deny_by_default") is False:
            warnings.append("Immune deny-by-default marker was false.")
            status = "warning"

        if metrics["telemetry_runtime_metrics"].get("missing_inputs_this_run", 0) > 0:
            warnings.append("Some approved telemetry inputs were missing.")
            if status == "ok":
                status = "notice"

        return {
            "overall_status": status,
            "warnings_count": len(warnings),
            "warnings": warnings,
        }

    # ========================================================
    # OUTPUT WRITING
    # ========================================================

    def save_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        Save telemetry_metrics.json.
        """

        self.validate_metrics(metrics)

        try:
            self.metrics_path.parent.mkdir(parents=True, exist_ok=True)

            with self.metrics_path.open("w", encoding="utf-8") as file:
                json.dump(metrics, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise TelemetryWriteError(
                f"Could not save telemetry metrics: {error}"
            ) from error

        self.metrics_written_this_run += 1

    def append_timeseries(self, metrics: Dict[str, Any]) -> None:
        """
        Append compact timeseries record to telemetry_timeseries.jsonl.
        """

        timeseries_record = {
            "schema_version": self.SCHEMA_VERSION,
            "telemetry_id": metrics["telemetry_id"],
            "timestamp_utc": metrics["telemetry_timestamp_utc"],
            "organism_name": metrics["organism"].get("organism_name"),
            "lineage_id": metrics["organism"].get("lineage_id"),
            "current_build": metrics["organism"].get("current_build"),
            "memory_records_count": metrics["memory_metrics"].get("records_count"),
            "total_events_recorded": metrics["event_metrics"].get("total_events_recorded"),
            "heartbeat_count": metrics["metabolism_metrics"].get("heartbeat_count"),
            "reflex_warnings": metrics["reflex_metrics"].get("warnings_raised_this_run"),
            "immune_denials": metrics["immune_metrics"].get("denied_this_run"),
            "topology_nodes_count": metrics["sensorium_metrics"].get("topology_nodes_count"),
            "topology_edges_count": metrics["sensorium_metrics"].get("topology_edges_count"),
            "active_probes_sent": metrics["cartography_metrics"].get("active_probes_sent"),
            "safety_summary": copy.deepcopy(metrics["safety_summary"]),
        }

        self.validate_timeseries_record(timeseries_record)

        try:
            self.timeseries_path.parent.mkdir(parents=True, exist_ok=True)

            with self.timeseries_path.open("a", encoding="utf-8") as file:
                json.dump(timeseries_record, file, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise TelemetryWriteError(
                f"Could not append telemetry timeseries record: {error}"
            ) from error

        self.timeseries_records_written_this_run += 1

    def save_observatory_report(self, report: Dict[str, Any]) -> None:
        """
        Save latest_observatory_report.json.
        """

        self.validate_observatory_report(report)

        try:
            self.observatory_report_path.parent.mkdir(parents=True, exist_ok=True)

            with self.observatory_report_path.open("w", encoding="utf-8") as file:
                json.dump(report, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise TelemetryWriteError(
                f"Could not save observatory report: {error}"
            ) from error

        self.reports_written_this_run += 1

    # ========================================================
    # EVENT BUS INTEGRATION
    # ========================================================

    def publish_telemetry_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Publish telemetry event through Event Bus if available.
        """

        if self.event_bus is None:
            return

        self.event_bus.publish_event(
            event_type=event_type,
            source_organ="TelemetryOrgan",
            payload=payload,
            priority="info",
        )

    # ========================================================
    # REPORTING
    # ========================================================

    def get_telemetry_report(self, observatory_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return short telemetry report for console output.
        """

        if observatory_report is None:
            observatory_report = self.collect_telemetry()

        return {
            "telemetry_root": str(self.telemetry_root),
            "telemetry_mode": observatory_report["telemetry_mode"],
            "telemetry_id": observatory_report["telemetry_id"],
            "overall_status": observatory_report["health_summary"]["overall_status"],
            "warnings_count": observatory_report["health_summary"]["warnings_count"],
            "current_build": observatory_report["key_metrics"]["current_build"],
            "memory_records_count": observatory_report["key_metrics"]["memory_records_count"],
            "total_events_recorded": observatory_report["key_metrics"]["total_events_recorded"],
            "heartbeat_count": observatory_report["key_metrics"]["heartbeat_count"],
            "reflex_warnings": observatory_report["key_metrics"]["reflex_warnings"],
            "immune_denials": observatory_report["key_metrics"]["immune_denials"],
            "topology_nodes_count": observatory_report["key_metrics"]["topology_nodes_count"],
            "topology_edges_count": observatory_report["key_metrics"]["topology_edges_count"],
            "active_probes_sent": observatory_report["key_metrics"]["active_probes_sent"],
            "safety_summary": observatory_report["safety_summary"],
        }

    # ========================================================
    # VALIDATION AND SAFETY
    # ========================================================

    def validate_metrics(self, metrics: Dict[str, Any]) -> bool:
        """
        Validate telemetry metrics payload.
        """

        required_fields = [
            "schema_version",
            "telemetry_id",
            "telemetry_timestamp_utc",
            "telemetry_mode",
            "organism",
            "identity_metrics",
            "sensorium_metrics",
            "cartography_metrics",
            "memory_metrics",
            "event_metrics",
            "metabolism_metrics",
            "reflex_metrics",
            "immune_metrics",
            "interface_metrics",
            "log_counts",
            "telemetry_runtime_metrics",
            "safety_summary",
        ]

        for field in required_fields:
            if field not in metrics:
                raise TelemetryValidationError(
                    f"Missing required telemetry metrics field: {field}"
                )

        return self.validate_safety_summary(metrics["safety_summary"])

    def validate_timeseries_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate compact timeseries record.
        """

        required_fields = [
            "schema_version",
            "telemetry_id",
            "timestamp_utc",
            "organism_name",
            "lineage_id",
            "current_build",
            "memory_records_count",
            "total_events_recorded",
            "heartbeat_count",
            "reflex_warnings",
            "immune_denials",
            "topology_nodes_count",
            "topology_edges_count",
            "active_probes_sent",
            "safety_summary",
        ]

        for field in required_fields:
            if field not in record:
                raise TelemetryValidationError(
                    f"Missing required telemetry timeseries field: {field}"
                )

        return self.validate_safety_summary(record["safety_summary"])

    def validate_observatory_report(self, report: Dict[str, Any]) -> bool:
        """
        Validate observatory report.
        """

        required_fields = [
            "schema_version",
            "report_timestamp_utc",
            "telemetry_id",
            "telemetry_mode",
            "organism",
            "health_summary",
            "key_metrics",
            "organ_presence",
            "safety_summary",
            "notes",
        ]

        for field in required_fields:
            if field not in report:
                raise TelemetryValidationError(
                    f"Missing required observatory report field: {field}"
                )

        return self.validate_safety_summary(report["safety_summary"])

    def validate_safety_summary(self, safety_summary: Dict[str, Any]) -> bool:
        """
        Validate telemetry safety summary.
        """

        prohibited_true_flags = [
            "commands_executed",
            "network_access_performed",
            "arbitrary_files_read",
            "private_documents_read",
            "raw_secrets_stored",
            "other_organs_modified",
            "history_deleted",
            "decisions_made",
            "actions_triggered",
            "active_cartography_enabled",
            "immune_bypassed",
        ]

        for flag in prohibited_true_flags:
            if safety_summary.get(flag) is True:
                raise TelemetrySafetyError(
                    f"Telemetry safety violation. This flag must be false: {flag}"
                )

        return True

    def validate_details_safety(self, details: Dict[str, Any]) -> bool:
        """
        Validate detail payloads for prohibited key names.
        """

        prohibited = self.find_prohibited_keys(details)

        if prohibited:
            raise TelemetrySafetyError(
                f"Telemetry details contain prohibited key names: {prohibited}"
            )

        return True

    def find_prohibited_keys(self, value: Any, path: str = "") -> List[str]:
        """
        Recursively find prohibited key names.
        """

        found = []

        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text

                if key_text in self.PROHIBITED_DETAIL_KEYS:
                    found.append(child_path)

                found.extend(self.find_prohibited_keys(child, child_path))

        elif isinstance(value, list):
            for index, item in enumerate(value):
                child_path = f"{path}[{index}]"
                found.extend(self.find_prohibited_keys(item, child_path))

        return found

    def get_safety_boundary(self) -> Dict[str, bool]:
        """
        Return Telemetry Organ safety boundary.
        """

        return {
            "may_read_approved_json_reports": True,
            "may_count_approved_jsonl_logs": True,
            "may_write_telemetry_metrics": True,
            "may_append_telemetry_timeseries": True,
            "may_generate_observatory_report": True,
            "may_publish_telemetry_events": True,

            "may_execute_commands": False,
            "may_access_network": False,
            "may_read_arbitrary_files": False,
            "may_read_private_documents": False,
            "may_store_raw_secrets": False,
            "may_modify_other_organs": False,
            "may_delete_history": False,
            "may_make_decisions": False,
            "may_trigger_actions": False,
            "may_enable_active_cartography": False,
            "may_bypass_immune": False,
        }
