"""
============================================================
REFLEX ORGAN
============================================================

Project:
    Digital Organism

Build:
    0.8.0

Organism Name:
    ContinuityNode

Organ:
    Reflex Organ

File:
    organs/reflex.py

Primary Function:
    Handle safe, low-risk automatic responses to known conditions.

Scientific / Clinical Description:
    The Reflex Organ is a bounded response component.

    It does not create instinct, intention, consciousness, biological
    reflex, or autonomous agency. The reflex metaphor is used
    architecturally to describe predefined, local, low-risk responses
    to known conditions.

Relationship To Existing Organs:
    Core Identity Organ answers:
        Who am I?

    Sensorium Organ answers:
        Where am I running?
        What does the host already know?

    Network Cartography Organ answers:
        What would I be allowed to map if active discovery were later
        approved?

    Memory Organ answers:
        What have I observed before?

    Event Bus Organ answers:
        What happened internally, and which organs should know?

    Metabolism Organ answers:
        What phase am I in?
        Did I heartbeat?
        Did I shut down cleanly?

    Reflex Organ answers:
        Is there a known low-risk condition I should respond to safely?

Important Safety Boundary:
    The Reflex Organ is not a broad self-repair system.

    It may:
        - create approved local directories
        - log warnings
        - publish warning events
        - detect policy contradictions
        - detect missing expected local paths
        - detect suspicious unsafe flags in reports

    It may not:
        - execute commands
        - access the network
        - edit source code
        - delete historical records
        - modify unrelated files
        - enable active scanning
        - change cartography policy to active
        - repair arbitrary system state
        - bypass safety boundaries

Storage Model:
    data/reflex/
        reflex_log.jsonl
        latest_reflex_state.json

Build 0.8.0 Behavior:
    - Create reflex directory structure.
    - Run boot reflex checks.
    - Evaluate Sensorium safety markers.
    - Evaluate Cartography dry-run safety markers.
    - Evaluate Memory safety markers.
    - Append reflex records.
    - Publish reflex warning events through Event Bus if available.
    - Generate latest_reflex_state.json.
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


class ReflexError(Exception):
    """
    Base exception for all Reflex Organ errors.
    """


class ReflexLogError(ReflexError):
    """
    Raised when the reflex log cannot be written.
    """


class ReflexStateError(ReflexError):
    """
    Raised when reflex state cannot be generated or saved.
    """


class ReflexSafetyError(ReflexError):
    """
    Raised when a reflex operation violates the safety boundary.
    """


class ReflexValidationError(ReflexError):
    """
    Raised when a reflex input is malformed.
    """


# ============================================================
# REFLEX ORGAN CLASS
# ============================================================


class ReflexOrgan:
    """
    Handles safe, bounded, low-risk responses.

    The Reflex Organ operates like a set of hard-coded guardrails and
    reactions.

    Build 0.8.0 reflexes are intentionally conservative:
        - warn
        - log
        - create approved local directories
        - publish warning events
        - block unsafe reflex requests

    It does not perform general repair.
    """

    SCHEMA_VERSION = "1.0.0"
    REFLEX_MODE = "SAFE_LOCAL_RESPONSES"

    VALID_REFLEX_TYPES = [
        "path.ensure_directory",
        "warning.raise",
        "safety.block",
        "state.note",
        "report.validate_marker",
    ]

    VALID_SEVERITIES = [
        "debug",
        "info",
        "notice",
        "warning",
        "error",
        "critical",
    ]

    # --------------------------------------------------------
    # The Reflex Organ may create only approved local directories.
    #
    # This prevents path traversal and arbitrary filesystem mutation.
    # --------------------------------------------------------
    APPROVED_DIRECTORY_PREFIXES = [
        "data",
        "data/events",
        "data/metabolism",
        "data/reflex",
        "data/memory",
        "data/memory/snapshots",
        "data/memory/summaries",
        "data/reflex",
    ]

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
        reflex_root: str = "data/reflex",
    ) -> None:
        """
        Initialize the Reflex Organ.

        Parameters:
            core_identity:
                Initialized CoreIdentityOrgan instance.

            event_bus:
                Optional EventBusOrgan instance.

            reflex_root:
                Root directory for reflex output.
        """

        self.core_identity = core_identity
        self.event_bus = event_bus
        self.reflex_root = Path(reflex_root)

        self.reflex_log_path = self.reflex_root / "reflex_log.jsonl"
        self.latest_state_path = self.reflex_root / "latest_reflex_state.json"

        self.checks_performed_this_run = 0
        self.reflexes_triggered_this_run = 0
        self.warnings_raised_this_run = 0
        self.safe_actions_performed_this_run = 0
        self.unsafe_actions_blocked_this_run = 0

        self.reflex_types_seen_this_run: Dict[str, int] = {}
        self.severities_seen_this_run: Dict[str, int] = {}

        self.ensure_reflex_structure()

        self.record_reflex(
            reflex_type="state.note",
            severity="info",
            source_organ="ReflexOrgan",
            condition="reflex.initialized",
            action_taken="recorded_initialization",
            details={
                "reflex_root": str(self.reflex_root),
                "reflex_mode": self.REFLEX_MODE,
            },
        )

    # ========================================================
    # TIME AND ID HELPERS
    # ========================================================

    def utc_now_iso(self) -> str:
        """
        Return the current UTC timestamp in ISO-8601 Z format.
        """

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_reflex_id(self, reflex_type: str) -> str:
        """
        Generate a unique reflex record ID.
        """

        safe_type = reflex_type.replace(".", "-").replace("_", "-")
        timestamp = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        short_id = uuid.uuid4().hex[:6]

        return f"reflex-{safe_type}-{timestamp}-{short_id}"

    # ========================================================
    # STRUCTURE
    # ========================================================

    def ensure_reflex_structure(self) -> None:
        """
        Create the Reflex Organ directory structure.

        This only creates reflex_root.
        """

        try:
            self.reflex_root.mkdir(parents=True, exist_ok=True)

        except OSError as error:
            raise ReflexStateError(
                f"Could not create reflex directory structure: {error}"
            ) from error

    # ========================================================
    # REFLEX CHECK SETS
    # ========================================================

    def run_boot_reflex_checks(
        self,
        expected_paths: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Run safe boot-time reflex checks.

        Current boot checks:
            - ensure approved local directories exist
            - warn if an expected path is not an approved directory path
        """

        context = context or {}
        self.validate_details_safety(context)

        results = []

        for path_text in expected_paths:
            self.checks_performed_this_run += 1

            if self.is_approved_directory_path(path_text):
                result = self.ensure_directory(
                    path_text=path_text,
                    source_organ="ReflexOrgan",
                    condition="boot.expected_directory",
                    context=context,
                )
                results.append(result)

            else:
                result = self.raise_warning(
                    source_organ="ReflexOrgan",
                    condition="boot.unapproved_expected_path",
                    message=f"Expected path is not approved for reflex directory creation: {path_text}",
                    details={
                        "path": path_text,
                        "context": context,
                    },
                    severity="warning",
                )
                results.append(result)

        return copy.deepcopy(results)

    def evaluate_sensorium_reflexes(
        self,
        sensorium_snapshot: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate Sensorium-derived reflex conditions.

        Current reflexes:
            - warn if Sensorium claims active scan occurred
            - warn if sensitive environment key names were detected
            - warn if raw environment values were stored
        """

        context = context or {}
        self.validate_details_safety(context)

        results = []

        self.checks_performed_this_run += 1

        topology = sensorium_snapshot.get("topology_seed_matrix", {})

        if topology.get("active_scan_performed") is not False:
            results.append(
                self.block_unsafe_action(
                    source_organ="SensoriumOrgan",
                    condition="sensorium.active_scan_marker_detected",
                    requested_action="accept_sensorium_active_scan_result",
                    reason="Sensorium must remain passive. Active scan marker was not false.",
                    details={
                        "context": context,
                    },
                )
            )

        environment = sensorium_snapshot.get("environment", {})

        self.checks_performed_this_run += 1

        if environment.get("sensitive_environment_keys_detected") is True:
            results.append(
                self.raise_warning(
                    source_organ="SensoriumOrgan",
                    condition="sensorium.sensitive_environment_key_names_detected",
                    message="Sensorium detected sensitive-looking environment key names. Values were not stored.",
                    details={
                        "categories": environment.get("sensitive_environment_categories_detected", []),
                        "raw_values_stored": environment.get("raw_environment_values_stored"),
                        "context": context,
                    },
                    severity="notice",
                )
            )

        self.checks_performed_this_run += 1

        if environment.get("raw_environment_values_stored") is True:
            results.append(
                self.block_unsafe_action(
                    source_organ="SensoriumOrgan",
                    condition="sensorium.raw_environment_values_stored",
                    requested_action="persist_sensorium_snapshot",
                    reason="Raw environment values must not be stored.",
                    details={
                        "context": context,
                    },
                )
            )

        return copy.deepcopy(results)

    def evaluate_cartography_reflexes(
        self,
        cartography_report: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate Cartography-derived reflex conditions.

        Current reflexes:
            - block if active discovery was performed in dry-run build
            - block if active probes were sent
            - warn if policy says cartography_enabled true while active
              implementation remains false
        """

        context = context or {}
        self.validate_details_safety(context)

        results = []

        self.checks_performed_this_run += 1

        if cartography_report.get("active_discovery_performed") is not False:
            results.append(
                self.block_unsafe_action(
                    source_organ="NetworkCartographyOrgan",
                    condition="cartography.active_discovery_detected",
                    requested_action="accept_cartography_report",
                    reason="Cartography active discovery must not occur in the current dry-run stage.",
                    details={
                        "report_id": cartography_report.get("report_id"),
                        "context": context,
                    },
                )
            )

        dry_run_plan = cartography_report.get("dry_run_plan", {})

        self.checks_performed_this_run += 1

        if dry_run_plan.get("active_probes_sent", 0) != 0:
            results.append(
                self.block_unsafe_action(
                    source_organ="NetworkCartographyOrgan",
                    condition="cartography.active_probes_sent",
                    requested_action="accept_cartography_probe_results",
                    reason="Build 0.8.0 must not send active probes.",
                    details={
                        "active_probes_sent": dry_run_plan.get("active_probes_sent"),
                        "context": context,
                    },
                )
            )

        policy = cartography_report.get("policy", {})

        self.checks_performed_this_run += 1

        if (
            policy.get("cartography_enabled") is True
            and policy.get("active_cartography_implemented") is not True
        ):
            results.append(
                self.raise_warning(
                    source_organ="NetworkCartographyOrgan",
                    condition="cartography.policy_enabled_but_not_implemented",
                    message="Cartography policy appears enabled, but active cartography is not implemented.",
                    details={
                        "cartography_enabled": policy.get("cartography_enabled"),
                        "active_cartography_implemented": policy.get("active_cartography_implemented"),
                        "context": context,
                    },
                    severity="warning",
                )
            )

        return copy.deepcopy(results)

    def evaluate_memory_reflexes(
        self,
        memory_summary: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluate Memory-derived reflex conditions.

        Current reflexes:
            - block if arbitrary file ingestion occurred
            - block if raw environment values were stored
            - block if secrets were stored
            - note topology changes
        """

        context = context or {}
        self.validate_details_safety(context)

        results = []

        safety = memory_summary.get("safety_summary", {})

        unsafe_memory_flags = [
            ("arbitrary_file_ingestion_performed", "Memory must not ingest arbitrary files."),
            ("raw_environment_values_stored", "Memory must not store raw environment values."),
            ("secrets_stored", "Memory must not store secrets."),
            ("network_access_performed", "Memory must not access the network."),
            ("commands_executed", "Memory must not execute commands."),
            ("historical_records_deleted", "Memory must not delete history in this build."),
        ]

        for flag, reason in unsafe_memory_flags:
            self.checks_performed_this_run += 1

            if safety.get(flag) is True:
                results.append(
                    self.block_unsafe_action(
                        source_organ="MemoryOrgan",
                        condition=f"memory.unsafe_flag.{flag}",
                        requested_action="accept_memory_summary",
                        reason=reason,
                        details={
                            "flag": flag,
                            "context": context,
                        },
                    )
                )

        change_markers = memory_summary.get("change_markers", {})

        self.checks_performed_this_run += 1

        if change_markers.get("topology_changed_since_previous") is True:
            results.append(
                self.record_reflex(
                    reflex_type="state.note",
                    severity="notice",
                    source_organ="MemoryOrgan",
                    condition="memory.topology_change_detected",
                    action_taken="recorded_note",
                    details={
                        "message": "Memory summary indicates topology changed since previous record.",
                        "context": context,
                    },
                )
            )

        return copy.deepcopy(results)

    # ========================================================
    # SAFE ACTIONS
    # ========================================================

    def ensure_directory(
        self,
        path_text: str,
        source_organ: str,
        condition: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Safely create an approved local directory if missing.

        This is one of the only write actions allowed in Build 0.8.0.
        """

        context = context or {}
        self.validate_details_safety(context)

        if not self.is_approved_directory_path(path_text):
            return self.block_unsafe_action(
                source_organ=source_organ,
                condition=condition,
                requested_action="ensure_directory",
                reason=f"Path is not approved for reflex directory creation: {path_text}",
                details={
                    "path": path_text,
                    "context": context,
                },
            )

        path = Path(path_text)

        try:
            path.mkdir(parents=True, exist_ok=True)

        except OSError as error:
            return self.raise_warning(
                source_organ=source_organ,
                condition=f"{condition}.directory_create_failed",
                message=f"Could not create approved directory: {path_text}",
                details={
                    "path": path_text,
                    "error": str(error),
                    "context": context,
                },
                severity="warning",
            )

        self.safe_actions_performed_this_run += 1

        return self.record_reflex(
            reflex_type="path.ensure_directory",
            severity="info",
            source_organ=source_organ,
            condition=condition,
            action_taken="ensured_directory_exists",
            details={
                "path": path_text,
                "context": context,
            },
        )

    def raise_warning(
        self,
        source_organ: str,
        condition: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        severity: str = "warning",
    ) -> Dict[str, Any]:
        """
        Raise and log a warning reflex.

        This does not throw an exception by default.
        It records a warning and publishes a warning event.
        """

        details = details or {}
        self.validate_details_safety(details)

        if severity not in self.VALID_SEVERITIES:
            raise ReflexValidationError(
                f"Invalid warning severity: {severity}"
            )

        self.warnings_raised_this_run += 1

        record = self.record_reflex(
            reflex_type="warning.raise",
            severity=severity,
            source_organ=source_organ,
            condition=condition,
            action_taken="warning_recorded",
            details={
                "message": message,
                **details,
            },
        )

        self.publish_reflex_event(
            event_type="reflex.warning.raised",
            payload={
                "reflex_id": record.get("reflex_id"),
                "condition": condition,
                "message": message,
                "severity": severity,
                "source_organ": source_organ,
            },
        )

        return copy.deepcopy(record)

    def block_unsafe_action(
        self,
        source_organ: str,
        condition: str,
        requested_action: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a blocked unsafe action.

        This is a reflex-level block marker.

        Later, the Immune Organ will become the formal policy decision
        layer. For now, Reflex can record obvious unsafe contradictions.
        """

        details = details or {}
        self.validate_details_safety(details)

        self.unsafe_actions_blocked_this_run += 1

        record = self.record_reflex(
            reflex_type="safety.block",
            severity="warning",
            source_organ=source_organ,
            condition=condition,
            action_taken="unsafe_action_blocked",
            details={
                "requested_action": requested_action,
                "reason": reason,
                **details,
            },
        )

        self.publish_reflex_event(
            event_type="reflex.warning.raised",
            payload={
                "reflex_id": record.get("reflex_id"),
                "condition": condition,
                "message": reason,
                "severity": "warning",
                "source_organ": source_organ,
                "requested_action": requested_action,
            },
        )

        return copy.deepcopy(record)

    # ========================================================
    # REFLEX RECORDING
    # ========================================================

    def record_reflex(
        self,
        reflex_type: str,
        severity: str,
        source_organ: str,
        condition: str,
        action_taken: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a reflex event to reflex_log.jsonl.
        """

        details = details or {}

        self.validate_reflex_type(reflex_type)
        self.validate_severity(severity)
        self.validate_details_safety(details)

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        record = {
            "schema_version": self.SCHEMA_VERSION,
            "reflex_id": self.generate_reflex_id(reflex_type),
            "timestamp_utc": self.utc_now_iso(),
            "reflex_mode": self.REFLEX_MODE,
            "reflex_type": reflex_type,
            "severity": severity,
            "source_organ": source_organ,
            "condition": condition,
            "action_taken": action_taken,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_build": persistent["current_build"],
            "details": copy.deepcopy(details),
            "safety": {
                "commands_executed": False,
                "network_access_performed": False,
                "private_files_scanned": False,
                "historical_records_deleted": False,
                "source_code_modified": False,
                "active_network_scanning_enabled": False,
                "cartography_policy_modified": False,
            },
        }

        self.validate_reflex_record(record)
        self.append_reflex_record(record)
        self.update_counters(record)

        return copy.deepcopy(record)

    def append_reflex_record(self, record: Dict[str, Any]) -> None:
        """
        Append a reflex record to reflex_log.jsonl.
        """

        try:
            self.reflex_log_path.parent.mkdir(parents=True, exist_ok=True)

            with self.reflex_log_path.open("a", encoding="utf-8") as file:
                json.dump(record, file, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ReflexLogError(
                f"Could not append reflex record: {error}"
            ) from error

    def update_counters(self, record: Dict[str, Any]) -> None:
        """
        Update in-memory reflex counters.
        """

        self.reflexes_triggered_this_run += 1

        reflex_type = record["reflex_type"]
        severity = record["severity"]

        self.reflex_types_seen_this_run[reflex_type] = (
            self.reflex_types_seen_this_run.get(reflex_type, 0) + 1
        )

        self.severities_seen_this_run[severity] = (
            self.severities_seen_this_run.get(severity, 0) + 1
        )

    # ========================================================
    # EVENT BUS INTEGRATION
    # ========================================================

    def publish_reflex_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Publish a reflex event to the Event Bus if available.
        """

        if self.event_bus is None:
            return

        self.event_bus.publish_event(
            event_type=event_type,
            source_organ="ReflexOrgan",
            payload=payload,
            priority="warning",
        )

    # ========================================================
    # STATE GENERATION
    # ========================================================

    def generate_latest_reflex_state(self) -> Dict[str, Any]:
        """
        Generate latest_reflex_state.json.
        """

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        state = {
            "schema_version": self.SCHEMA_VERSION,
            "state_timestamp_utc": self.utc_now_iso(),
            "organism_name": persistent["organism_name"],
            "lineage_id": persistent["lineage_id"],
            "runtime_instance_id": runtime["runtime_instance_id"],
            "reflex_root": str(self.reflex_root),
            "reflex_log_path": str(self.reflex_log_path),
            "latest_state_path": str(self.latest_state_path),
            "reflex_mode": self.REFLEX_MODE,
            "checks_performed_this_run": self.checks_performed_this_run,
            "reflexes_triggered_this_run": self.reflexes_triggered_this_run,
            "warnings_raised_this_run": self.warnings_raised_this_run,
            "safe_actions_performed_this_run": self.safe_actions_performed_this_run,
            "unsafe_actions_blocked_this_run": self.unsafe_actions_blocked_this_run,
            "reflex_types_seen_this_run": copy.deepcopy(self.reflex_types_seen_this_run),
            "severities_seen_this_run": copy.deepcopy(self.severities_seen_this_run),
            "safety_boundary": self.get_safety_boundary(),
            "safety_summary": {
                "commands_executed": False,
                "network_access_performed": False,
                "private_files_scanned": False,
                "historical_records_deleted": False,
                "source_code_modified": False,
                "active_network_scanning_enabled": False,
                "cartography_policy_modified": False,
            },
        }

        self.validate_reflex_state(state)
        self.save_latest_reflex_state(state)

        return copy.deepcopy(state)

    def save_latest_reflex_state(self, state: Dict[str, Any]) -> None:
        """
        Save latest_reflex_state.json.
        """

        try:
            self.latest_state_path.parent.mkdir(parents=True, exist_ok=True)

            with self.latest_state_path.open("w", encoding="utf-8") as file:
                json.dump(state, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ReflexStateError(
                f"Could not save latest reflex state: {error}"
            ) from error

    def get_reflex_report(self, latest_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return a short Reflex report for console output.
        """

        if latest_state is None:
            latest_state = self.generate_latest_reflex_state()

        return {
            "reflex_root": latest_state["reflex_root"],
            "reflex_mode": latest_state["reflex_mode"],
            "checks_performed_this_run": latest_state["checks_performed_this_run"],
            "reflexes_triggered_this_run": latest_state["reflexes_triggered_this_run"],
            "warnings_raised_this_run": latest_state["warnings_raised_this_run"],
            "safe_actions_performed_this_run": latest_state["safe_actions_performed_this_run"],
            "unsafe_actions_blocked_this_run": latest_state["unsafe_actions_blocked_this_run"],
            "reflex_types_seen_this_run": latest_state["reflex_types_seen_this_run"],
            "severities_seen_this_run": latest_state["severities_seen_this_run"],
            "safety_summary": latest_state["safety_summary"],
        }

    # ========================================================
    # VALIDATION AND SAFETY
    # ========================================================

    def validate_reflex_type(self, reflex_type: str) -> bool:
        """
        Validate reflex type.
        """

        if reflex_type not in self.VALID_REFLEX_TYPES:
            raise ReflexValidationError(
                f"Invalid reflex type: {reflex_type}"
            )

        return True

    def validate_severity(self, severity: str) -> bool:
        """
        Validate severity.
        """

        if severity not in self.VALID_SEVERITIES:
            raise ReflexValidationError(
                f"Invalid reflex severity: {severity}"
            )

        return True

    def validate_reflex_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate a reflex log record.
        """

        required_fields = [
            "schema_version",
            "reflex_id",
            "timestamp_utc",
            "reflex_mode",
            "reflex_type",
            "severity",
            "source_organ",
            "condition",
            "action_taken",
            "source_runtime_instance_id",
            "source_lineage_id",
            "source_organism_name",
            "source_build",
            "details",
            "safety",
        ]

        for field in required_fields:
            if field not in record:
                raise ReflexValidationError(
                    f"Missing required reflex record field: {field}"
                )

        safety = record["safety"]

        prohibited_true_flags = [
            "commands_executed",
            "network_access_performed",
            "private_files_scanned",
            "historical_records_deleted",
            "source_code_modified",
            "active_network_scanning_enabled",
            "cartography_policy_modified",
        ]

        for flag in prohibited_true_flags:
            if safety.get(flag) is True:
                raise ReflexSafetyError(
                    f"Reflex record safety violation. This flag must be false: {flag}"
                )

        return True

    def validate_reflex_state(self, state: Dict[str, Any]) -> bool:
        """
        Validate latest reflex state.
        """

        required_fields = [
            "schema_version",
            "state_timestamp_utc",
            "organism_name",
            "lineage_id",
            "runtime_instance_id",
            "reflex_root",
            "reflex_log_path",
            "latest_state_path",
            "reflex_mode",
            "checks_performed_this_run",
            "reflexes_triggered_this_run",
            "warnings_raised_this_run",
            "safe_actions_performed_this_run",
            "unsafe_actions_blocked_this_run",
            "reflex_types_seen_this_run",
            "severities_seen_this_run",
            "safety_boundary",
            "safety_summary",
        ]

        for field in required_fields:
            if field not in state:
                raise ReflexStateError(
                    f"Missing required reflex state field: {field}"
                )

        safety_summary = state["safety_summary"]

        prohibited_true_flags = [
            "commands_executed",
            "network_access_performed",
            "private_files_scanned",
            "historical_records_deleted",
            "source_code_modified",
            "active_network_scanning_enabled",
            "cartography_policy_modified",
        ]

        for flag in prohibited_true_flags:
            if safety_summary.get(flag) is True:
                raise ReflexSafetyError(
                    f"Reflex state safety violation. This flag must be false: {flag}"
                )

        return True

    def validate_details_safety(self, details: Dict[str, Any]) -> bool:
        """
        Validate details payloads.

        Reflex records should not carry secrets, raw environment values,
        or private key material.
        """

        prohibited_keys = self.find_prohibited_keys(details)

        if prohibited_keys:
            raise ReflexSafetyError(
                f"Reflex details contain prohibited key names: {prohibited_keys}"
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

    def is_approved_directory_path(self, path_text: str) -> bool:
        """
        Check whether a path is approved for Reflex directory creation.

        This intentionally allows only known data/ subpaths.
        """

        normalized = str(Path(path_text)).replace("\\", "/").rstrip("/")

        if normalized.startswith("../") or "/../" in normalized or normalized == "..":
            return False

        for prefix in self.APPROVED_DIRECTORY_PREFIXES:
            normalized_prefix = str(Path(prefix)).replace("\\", "/").rstrip("/")

            if normalized == normalized_prefix:
                return True

            if normalized.startswith(normalized_prefix + "/"):
                return True

        return False

    def get_safety_boundary(self) -> Dict[str, bool]:
        """
        Return the Reflex Organ safety boundary.
        """

        return {
            "may_log_warnings": True,
            "may_publish_warning_events": True,
            "may_create_approved_local_directories": True,
            "may_detect_policy_contradictions": True,
            "may_record_block_markers": True,
            "may_generate_reflex_state": True,

            "may_execute_commands": False,
            "may_access_network": False,
            "may_scan_private_files": False,
            "may_delete_historical_records": False,
            "may_modify_source_code": False,
            "may_modify_cartography_policy": False,
            "may_enable_active_network_scanning": False,
            "may_repair_arbitrary_system_state": False,
            "may_bypass_safety_boundaries": False,
        }
