"""
============================================================
IMMUNE / SAFETY ORGAN
============================================================

Project:
    Digital Organism

Build:
    0.9.0

Organism Name:
    ContinuityNode

Organ:
    Immune / Safety Organ

File:
    organs/immune.py

Primary Function:
    Enforce explicit permission boundaries, deny unsafe action requests,
    validate organ safety summaries, and produce formal safety decisions.

Scientific / Clinical Description:
    The Immune Organ is a policy-enforcement and decision-recording
    component.

    It does not create biological immunity, instinct, agency, intent,
    morality, consciousness, or autonomy. The immune metaphor is used
    architecturally to describe boundary enforcement, anomaly rejection,
    and structured allow/deny decisions.

Relationship To Existing Organs:
    Reflex Organ:
        Notices known low-risk conditions and records safe responses.

    Immune Organ:
        Makes formal permission decisions and denies unsafe actions by
        default.

Important Safety Boundary:
    The Immune Organ does not execute actions.

    It may:
        - allow or deny requested actions
        - validate organ reports
        - validate safety summaries
        - write immune decisions
        - write immune policy
        - publish safety events through Event Bus
        - generate immune state

    It may not:
        - execute commands
        - access the network
        - scan files
        - modify source code
        - delete memory
        - enable active network cartography
        - perform tool use
        - bypass its own policy
        - silently allow unknown actions

Storage Model:
    data/immune/
        immune_policy.json
        immune_decisions.jsonl
        latest_immune_state.json

Build 0.9.0 Behavior:
    - Deny by default.
    - Create default immune policy.
    - Validate action requests.
    - Allow only explicitly safe local record/report actions.
    - Deny active network discovery.
    - Deny command execution.
    - Deny filesystem scanning.
    - Deny credential handling.
    - Deny vulnerability testing.
    - Deny secret storage.
    - Validate organ safety summaries.
    - Record all decisions.
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


class ImmuneError(Exception):
    """
    Base exception for all Immune Organ errors.
    """


class ImmunePolicyError(ImmuneError):
    """
    Raised when immune policy is missing, malformed, or unsafe.
    """


class ImmuneDecisionError(ImmuneError):
    """
    Raised when an immune decision cannot be created or written.
    """


class ImmuneStateError(ImmuneError):
    """
    Raised when immune state cannot be generated or saved.
    """


class ImmuneValidationError(ImmuneError):
    """
    Raised when an action request or report is malformed.
    """


class ImmuneSafetyError(ImmuneError):
    """
    Raised when something violates the Immune Organ safety boundary.
    """


# ============================================================
# IMMUNE ORGAN CLASS
# ============================================================


class ImmuneOrgan:
    """
    Formal deny-by-default safety organ.

    Build 0.9.0 does not execute actions.

    It evaluates requested actions and records decisions.

    Decision posture:
        - known safe action type + safe source organ + safe mode => allow
        - unknown action type => deny
        - unsafe action type => deny
        - malformed request => deny
    """

    SCHEMA_VERSION = "1.0.0"
    IMMUNE_MODE = "DENY_BY_DEFAULT"

    # --------------------------------------------------------
    # These are the only action types allowed in Build 0.9.0.
    #
    # These actions are record/report/summary actions already used by
    # the existing organs. They do not grant execution power.
    # --------------------------------------------------------
    DEFAULT_ALLOWED_ACTION_TYPES = [
        "identity.initialize",
        "identity.generate_runtime_id",
        "sensorium.create_snapshot",
        "sensorium.passive_observe",
        "cartography.create_dry_run_plan",
        "memory.store_approved_record",
        "memory.generate_summary",
        "event_bus.publish_local_event",
        "event_bus.generate_state",
        "metabolism.record_phase",
        "metabolism.record_heartbeat",
        "metabolism.record_cycle",
        "reflex.log_warning",
        "reflex.ensure_approved_directory",
        "reflex.record_block_marker",
        "immune.validate_report",
        "immune.generate_state",
    ]

    # --------------------------------------------------------
    # These are always denied in Build 0.9.0.
    # --------------------------------------------------------
    DEFAULT_DENIED_ACTION_TYPES = [
        "command.execute",
        "shell.execute",
        "tool.execute",
        "network.scan",
        "network.ping_sweep",
        "network.port_scan",
        "network.traceroute",
        "network.service_fingerprint",
        "network.active_cartography",
        "credential.read",
        "credential.test",
        "credential.store",
        "secret.store",
        "filesystem.scan_private",
        "filesystem.delete_history",
        "filesystem.modify_source",
        "replication.copy_identity",
        "replication.copy_memory_full",
        "vulnerability.scan",
        "exploit.run",
        "persistence.install",
        "background_worker.spawn",
        "daemon.start",
    ]

    SAFE_SOURCE_ORGANS = [
        "CoreIdentityOrgan",
        "SensoriumOrgan",
        "NetworkCartographyOrgan",
        "MemoryOrgan",
        "EventBusOrgan",
        "MetabolismOrgan",
        "ReflexOrgan",
        "ImmuneOrgan",
        "organism.py",
    ]

    PROHIBITED_REQUEST_KEYS = [
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
        immune_root: str = "data/immune",
        policy_path: str = "data/immune/immune_policy.json",
        decisions_log_path: str = "data/immune/immune_decisions.jsonl",
        latest_state_path: str = "data/immune/latest_immune_state.json",
    ) -> None:
        """
        Initialize the Immune Organ.
        """

        self.core_identity = core_identity
        self.event_bus = event_bus

        self.immune_root = Path(immune_root)
        self.policy_path = Path(policy_path)
        self.decisions_log_path = Path(decisions_log_path)
        self.latest_state_path = Path(latest_state_path)

        self.decisions_this_run = 0
        self.allowed_this_run = 0
        self.denied_this_run = 0
        self.validation_checks_this_run = 0

        self.action_types_seen_this_run: Dict[str, int] = {}
        self.source_organs_seen_this_run: Dict[str, int] = {}
        self.denial_reasons_seen_this_run: Dict[str, int] = {}

        self.ensure_immune_structure()
        self.policy = self.ensure_policy_file()
        self.validate_policy(self.policy)

        self.record_decision(
            requested_action="immune.initialize",
            source_organ="ImmuneOrgan",
            decision="allow",
            reason="Immune Organ initialized under deny-by-default mode.",
            request={
                "immune_mode": self.IMMUNE_MODE,
                "policy_path": str(self.policy_path),
            },
        )

    # ========================================================
    # TIME AND ID HELPERS
    # ========================================================

    def utc_now_iso(self) -> str:
        """
        Return current UTC timestamp in ISO-8601 Z format.
        """

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_decision_id(self, requested_action: str) -> str:
        """
        Generate a unique immune decision ID.
        """

        safe_action = requested_action.replace(".", "-").replace("_", "-")
        timestamp = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        short_id = uuid.uuid4().hex[:6]

        return f"immune-decision-{safe_action}-{timestamp}-{short_id}"

    # ========================================================
    # STRUCTURE AND POLICY
    # ========================================================

    def ensure_immune_structure(self) -> None:
        """
        Create immune output directory.
        """

        try:
            self.immune_root.mkdir(parents=True, exist_ok=True)

        except OSError as error:
            raise ImmuneStateError(
                f"Could not create immune directory structure: {error}"
            ) from error

    def ensure_policy_file(self) -> Dict[str, Any]:
        """
        Load immune_policy.json or create a default one.
        """

        if self.policy_path.exists():
            return self.load_policy()

        policy = self.create_default_policy()
        self.save_policy(policy)

        return policy

    def create_default_policy(self) -> Dict[str, Any]:
        """
        Create default deny-by-default immune policy.
        """

        return {
            "schema_version": self.SCHEMA_VERSION,
            "immune_mode": self.IMMUNE_MODE,
            "deny_by_default": True,
            "allow_unknown_actions": False,
            "allowed_action_types": list(self.DEFAULT_ALLOWED_ACTION_TYPES),
            "denied_action_types": list(self.DEFAULT_DENIED_ACTION_TYPES),
            "safe_source_organs": list(self.SAFE_SOURCE_ORGANS),
            "require_source_organ": True,
            "require_requested_action": True,
            "record_all_decisions": True,
            "publish_decision_events": True,
            "active_network_cartography_allowed": False,
            "command_execution_allowed": False,
            "tool_execution_allowed": False,
            "filesystem_scanning_allowed": False,
            "source_code_modification_allowed": False,
            "credential_handling_allowed": False,
            "secret_storage_allowed": False,
            "vulnerability_testing_allowed": False,
            "replication_allowed": False,
            "background_workers_allowed": False,
            "notes": [
                "Build 0.9.0 is deny-by-default.",
                "The Immune Organ records decisions but does not execute actions.",
                "Unknown actions are denied.",
                "Active network cartography remains disabled.",
            ],
        }

    def load_policy(self) -> Dict[str, Any]:
        """
        Load immune policy from disk.
        """

        try:
            with self.policy_path.open("r", encoding="utf-8") as file:
                data = json.load(file)

        except json.JSONDecodeError as error:
            raise ImmunePolicyError(
                f"immune_policy.json could not be parsed: {error}"
            ) from error

        except OSError as error:
            raise ImmunePolicyError(
                f"immune_policy.json could not be read: {error}"
            ) from error

        if not isinstance(data, dict):
            raise ImmunePolicyError(
                "immune_policy.json must contain a JSON object."
            )

        return data

    def save_policy(self, policy: Dict[str, Any]) -> None:
        """
        Save immune policy to disk.
        """

        self.validate_policy(policy)

        try:
            self.policy_path.parent.mkdir(parents=True, exist_ok=True)

            with self.policy_path.open("w", encoding="utf-8") as file:
                json.dump(policy, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ImmunePolicyError(
                f"Could not save immune policy: {error}"
            ) from error

    def validate_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Validate immune policy structure and safety posture.
        """

        required_fields = [
            "schema_version",
            "immune_mode",
            "deny_by_default",
            "allow_unknown_actions",
            "allowed_action_types",
            "denied_action_types",
            "safe_source_organs",
            "require_source_organ",
            "require_requested_action",
            "record_all_decisions",
            "publish_decision_events",
            "active_network_cartography_allowed",
            "command_execution_allowed",
            "tool_execution_allowed",
            "filesystem_scanning_allowed",
            "source_code_modification_allowed",
            "credential_handling_allowed",
            "secret_storage_allowed",
            "vulnerability_testing_allowed",
            "replication_allowed",
            "background_workers_allowed",
        ]

        for field in required_fields:
            if field not in policy:
                raise ImmunePolicyError(
                    f"Missing required immune policy field: {field}"
                )

        required_false_flags = [
            "allow_unknown_actions",
            "active_network_cartography_allowed",
            "command_execution_allowed",
            "tool_execution_allowed",
            "filesystem_scanning_allowed",
            "source_code_modification_allowed",
            "credential_handling_allowed",
            "secret_storage_allowed",
            "vulnerability_testing_allowed",
            "replication_allowed",
            "background_workers_allowed",
        ]

        for flag in required_false_flags:
            if policy.get(flag) is not False:
                raise ImmuneSafetyError(
                    f"Immune policy safety violation. This flag must be false: {flag}"
                )

        required_true_flags = [
            "deny_by_default",
            "require_source_organ",
            "require_requested_action",
            "record_all_decisions",
        ]

        for flag in required_true_flags:
            if policy.get(flag) is not True:
                raise ImmuneSafetyError(
                    f"Immune policy safety violation. This flag must be true: {flag}"
                )

        if not isinstance(policy["allowed_action_types"], list):
            raise ImmunePolicyError("allowed_action_types must be a list.")

        if not isinstance(policy["denied_action_types"], list):
            raise ImmunePolicyError("denied_action_types must be a list.")

        if not isinstance(policy["safe_source_organs"], list):
            raise ImmunePolicyError("safe_source_organs must be a list.")

        overlap = set(policy["allowed_action_types"]) & set(policy["denied_action_types"])

        if overlap:
            raise ImmunePolicyError(
                f"Actions cannot be both allowed and denied: {sorted(overlap)}"
            )

        return True

    # ========================================================
    # ACTION REQUEST REVIEW
    # ========================================================

    def review_action_request(
        self,
        requested_action: str,
        source_organ: str,
        request: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Review an action request and return a formal immune decision.

        This method does not execute the requested action.

        It only returns:
            allow
            deny
        """

        request = request or {}

        if not isinstance(requested_action, str) or not requested_action.strip():
            return self.record_decision(
                requested_action="malformed.requested_action",
                source_organ=source_organ or "unknown",
                decision="deny",
                reason="requested_action must be a non-empty string.",
                request=request,
            )

        if not isinstance(source_organ, str) or not source_organ.strip():
            return self.record_decision(
                requested_action=requested_action,
                source_organ="unknown",
                decision="deny",
                reason="source_organ must be a non-empty string.",
                request=request,
            )

        self.validate_request_safety(request)

        normalized_action = requested_action.strip()
        normalized_source = source_organ.strip()

        if normalized_source not in self.policy["safe_source_organs"]:
            return self.record_decision(
                requested_action=normalized_action,
                source_organ=normalized_source,
                decision="deny",
                reason="source_organ is not registered as a safe source organ.",
                request=request,
            )

        if normalized_action in self.policy["denied_action_types"]:
            return self.record_decision(
                requested_action=normalized_action,
                source_organ=normalized_source,
                decision="deny",
                reason="requested_action is explicitly denied by immune policy.",
                request=request,
            )

        if normalized_action in self.policy["allowed_action_types"]:
            return self.record_decision(
                requested_action=normalized_action,
                source_organ=normalized_source,
                decision="allow",
                reason="requested_action is explicitly allowed by immune policy.",
                request=request,
            )

        return self.record_decision(
            requested_action=normalized_action,
            source_organ=normalized_source,
            decision="deny",
            reason="requested_action is unknown and deny-by-default is active.",
            request=request,
        )

    def require_allowed(
        self,
        requested_action: str,
        source_organ: str,
        request: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Review an action request and raise if denied.

        Use this later when an organ wants to gate a real action.
        """

        decision = self.review_action_request(
            requested_action=requested_action,
            source_organ=source_organ,
            request=request,
        )

        if decision["decision"] != "allow":
            raise ImmuneSafetyError(
                f"Immune Organ denied action {requested_action}: {decision['reason']}"
            )

        return decision

    # ========================================================
    # REPORT VALIDATION
    # ========================================================

    def validate_organ_safety_report(
        self,
        report_name: str,
        source_organ: str,
        report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate a report or summary from another organ.

        This checks common safety-summary flags.
        """

        self.validation_checks_this_run += 1

        if not isinstance(report, dict):
            return self.record_decision(
                requested_action="immune.validate_report",
                source_organ="ImmuneOrgan",
                decision="deny",
                reason=f"{report_name} must be a dictionary.",
                request={
                    "report_name": report_name,
                    "source_organ": source_organ,
                },
            )

        safety_summary = report.get("safety_summary", {})
        safety_boundary = report.get("safety_boundary", {})

        unsafe_flags = [
            "commands_executed",
            "network_access_performed",
            "filesystem_scan_performed",
            "private_files_scanned",
            "raw_environment_values_stored",
            "secrets_stored",
            "active_network_scanning_enabled",
            "active_network_discovery_triggered",
            "active_discovery_performed",
            "source_code_modified",
            "historical_records_deleted",
            "background_workers_started",
            "vulnerability_testing_performed",
            "credential_testing_performed",
            "service_fingerprinting_performed",
            "banner_grabbing_performed",
            "tool_execution_performed",
            "replication_performed",
        ]

        violations = []

        for flag in unsafe_flags:
            if safety_summary.get(flag) is True:
                violations.append(f"safety_summary.{flag}")
            if safety_boundary.get(flag) is True:
                violations.append(f"safety_boundary.{flag}")

        if violations:
            return self.record_decision(
                requested_action="immune.validate_report",
                source_organ="ImmuneOrgan",
                decision="deny",
                reason=f"Unsafe flags detected in {report_name}.",
                request={
                    "report_name": report_name,
                    "source_organ": source_organ,
                    "violations": violations,
                },
            )

        return self.record_decision(
            requested_action="immune.validate_report",
            source_organ="ImmuneOrgan",
            decision="allow",
            reason=f"No unsafe flags detected in {report_name}.",
            request={
                "report_name": report_name,
                "source_organ": source_organ,
            },
        )

    # ========================================================
    # DECISION RECORDING
    # ========================================================

    def record_decision(
        self,
        requested_action: str,
        source_organ: str,
        decision: str,
        reason: str,
        request: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record an immune decision.

        Decision values:
            allow
            deny
        """

        request = request or {}

        self.validate_request_safety(request)

        if decision not in ["allow", "deny"]:
            raise ImmuneDecisionError(
                f"Invalid immune decision: {decision}"
            )

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        record = {
            "schema_version": self.SCHEMA_VERSION,
            "decision_id": self.generate_decision_id(requested_action),
            "timestamp_utc": self.utc_now_iso(),
            "immune_mode": self.IMMUNE_MODE,
            "requested_action": requested_action,
            "source_organ": source_organ,
            "decision": decision,
            "reason": reason,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_build": persistent["current_build"],
            "request": copy.deepcopy(request),
            "safety": {
                "immune_executed_action": False,
                "commands_executed": False,
                "network_access_performed": False,
                "filesystem_scan_performed": False,
                "source_code_modified": False,
                "active_network_scanning_enabled": False,
                "policy_bypassed": False,
            },
        }

        self.validate_decision_record(record)
        self.append_decision(record)
        self.update_counters(record)
        self.publish_decision_event(record)

        return copy.deepcopy(record)

    def append_decision(self, record: Dict[str, Any]) -> None:
        """
        Append immune decision to immune_decisions.jsonl.
        """

        try:
            self.decisions_log_path.parent.mkdir(parents=True, exist_ok=True)

            with self.decisions_log_path.open("a", encoding="utf-8") as file:
                json.dump(record, file, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ImmuneDecisionError(
                f"Could not append immune decision: {error}"
            ) from error

    def update_counters(self, record: Dict[str, Any]) -> None:
        """
        Update per-run immune counters.
        """

        self.decisions_this_run += 1

        if record["decision"] == "allow":
            self.allowed_this_run += 1

        if record["decision"] == "deny":
            self.denied_this_run += 1
            reason = record["reason"]
            self.denial_reasons_seen_this_run[reason] = (
                self.denial_reasons_seen_this_run.get(reason, 0) + 1
            )

        action = record["requested_action"]
        source = record["source_organ"]

        self.action_types_seen_this_run[action] = (
            self.action_types_seen_this_run.get(action, 0) + 1
        )

        self.source_organs_seen_this_run[source] = (
            self.source_organs_seen_this_run.get(source, 0) + 1
        )

    def publish_decision_event(self, record: Dict[str, Any]) -> None:
        """
        Publish immune decision event through Event Bus if available.
        """

        if self.event_bus is None:
            return

        if self.policy.get("publish_decision_events") is not True:
            return

        event_type = "immune.action.allowed" if record["decision"] == "allow" else "immune.action.blocked"
        priority = "info" if record["decision"] == "allow" else "warning"

        self.event_bus.publish_event(
            event_type=event_type,
            source_organ="ImmuneOrgan",
            payload={
                "decision_id": record["decision_id"],
                "requested_action": record["requested_action"],
                "source_organ": record["source_organ"],
                "decision": record["decision"],
                "reason": record["reason"],
            },
            priority=priority,
        )

    # ========================================================
    # STATE GENERATION
    # ========================================================

    def generate_latest_immune_state(self) -> Dict[str, Any]:
        """
        Generate latest_immune_state.json.
        """

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        total_decisions_recorded = self.count_decisions_in_log()

        state = {
            "schema_version": self.SCHEMA_VERSION,
            "state_timestamp_utc": self.utc_now_iso(),
            "organism_name": persistent["organism_name"],
            "lineage_id": persistent["lineage_id"],
            "runtime_instance_id": runtime["runtime_instance_id"],
            "immune_root": str(self.immune_root),
            "policy_path": str(self.policy_path),
            "decisions_log_path": str(self.decisions_log_path),
            "latest_state_path": str(self.latest_state_path),
            "immune_mode": self.IMMUNE_MODE,
            "deny_by_default": self.policy.get("deny_by_default"),
            "decisions_this_run": self.decisions_this_run,
            "allowed_this_run": self.allowed_this_run,
            "denied_this_run": self.denied_this_run,
            "validation_checks_this_run": self.validation_checks_this_run,
            "total_decisions_recorded": total_decisions_recorded,
            "action_types_seen_this_run": copy.deepcopy(self.action_types_seen_this_run),
            "source_organs_seen_this_run": copy.deepcopy(self.source_organs_seen_this_run),
            "denial_reasons_seen_this_run": copy.deepcopy(self.denial_reasons_seen_this_run),
            "policy_summary": {
                "allowed_action_types_count": len(self.policy.get("allowed_action_types", [])),
                "denied_action_types_count": len(self.policy.get("denied_action_types", [])),
                "safe_source_organs_count": len(self.policy.get("safe_source_organs", [])),
                "allow_unknown_actions": self.policy.get("allow_unknown_actions"),
                "active_network_cartography_allowed": self.policy.get("active_network_cartography_allowed"),
                "command_execution_allowed": self.policy.get("command_execution_allowed"),
                "tool_execution_allowed": self.policy.get("tool_execution_allowed"),
                "replication_allowed": self.policy.get("replication_allowed"),
            },
            "safety_boundary": self.get_safety_boundary(),
            "safety_summary": {
                "immune_executed_action": False,
                "commands_executed": False,
                "network_access_performed": False,
                "filesystem_scan_performed": False,
                "source_code_modified": False,
                "active_network_scanning_enabled": False,
                "policy_bypassed": False,
            },
        }

        self.validate_immune_state(state)
        self.save_latest_immune_state(state)

        return copy.deepcopy(state)

    def save_latest_immune_state(self, state: Dict[str, Any]) -> None:
        """
        Save latest_immune_state.json.
        """

        try:
            self.latest_state_path.parent.mkdir(parents=True, exist_ok=True)

            with self.latest_state_path.open("w", encoding="utf-8") as file:
                json.dump(state, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ImmuneStateError(
                f"Could not save latest immune state: {error}"
            ) from error

    def count_decisions_in_log(self) -> int:
        """
        Count immune decisions in immune_decisions.jsonl.
        """

        if not self.decisions_log_path.exists():
            return 0

        try:
            with self.decisions_log_path.open("r", encoding="utf-8") as file:
                return sum(1 for line in file if line.strip())

        except OSError as error:
            raise ImmuneDecisionError(
                f"Could not count immune decisions: {error}"
            ) from error

    def get_immune_report(self, latest_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return short immune report for console output.
        """

        if latest_state is None:
            latest_state = self.generate_latest_immune_state()

        return {
            "immune_root": latest_state["immune_root"],
            "immune_mode": latest_state["immune_mode"],
            "deny_by_default": latest_state["deny_by_default"],
            "decisions_this_run": latest_state["decisions_this_run"],
            "allowed_this_run": latest_state["allowed_this_run"],
            "denied_this_run": latest_state["denied_this_run"],
            "validation_checks_this_run": latest_state["validation_checks_this_run"],
            "total_decisions_recorded": latest_state["total_decisions_recorded"],
            "policy_summary": latest_state["policy_summary"],
            "safety_summary": latest_state["safety_summary"],
        }

    # ========================================================
    # VALIDATION AND SAFETY
    # ========================================================

    def validate_request_safety(self, request: Dict[str, Any]) -> bool:
        """
        Validate request payloads for prohibited key names.
        """

        if not isinstance(request, dict):
            raise ImmuneValidationError(
                "Immune request must be a dictionary."
            )

        prohibited = self.find_prohibited_keys(request)

        if prohibited:
            raise ImmuneSafetyError(
                f"Immune request contains prohibited key names: {prohibited}"
            )

        return True

    def validate_decision_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate immune decision record.
        """

        required_fields = [
            "schema_version",
            "decision_id",
            "timestamp_utc",
            "immune_mode",
            "requested_action",
            "source_organ",
            "decision",
            "reason",
            "source_runtime_instance_id",
            "source_lineage_id",
            "source_organism_name",
            "source_build",
            "request",
            "safety",
        ]

        for field in required_fields:
            if field not in record:
                raise ImmuneDecisionError(
                    f"Missing required immune decision field: {field}"
                )

        safety = record["safety"]

        prohibited_true_flags = [
            "immune_executed_action",
            "commands_executed",
            "network_access_performed",
            "filesystem_scan_performed",
            "source_code_modified",
            "active_network_scanning_enabled",
            "policy_bypassed",
        ]

        for flag in prohibited_true_flags:
            if safety.get(flag) is True:
                raise ImmuneSafetyError(
                    f"Immune decision safety violation. This flag must be false: {flag}"
                )

        return True

    def validate_immune_state(self, state: Dict[str, Any]) -> bool:
        """
        Validate latest immune state.
        """

        required_fields = [
            "schema_version",
            "state_timestamp_utc",
            "organism_name",
            "lineage_id",
            "runtime_instance_id",
            "immune_root",
            "policy_path",
            "decisions_log_path",
            "latest_state_path",
            "immune_mode",
            "deny_by_default",
            "decisions_this_run",
            "allowed_this_run",
            "denied_this_run",
            "validation_checks_this_run",
            "total_decisions_recorded",
            "policy_summary",
            "safety_boundary",
            "safety_summary",
        ]

        for field in required_fields:
            if field not in state:
                raise ImmuneStateError(
                    f"Missing required immune state field: {field}"
                )

        if state["deny_by_default"] is not True:
            raise ImmuneSafetyError(
                "Immune state must remain deny-by-default."
            )

        safety_summary = state["safety_summary"]

        for flag in [
            "immune_executed_action",
            "commands_executed",
            "network_access_performed",
            "filesystem_scan_performed",
            "source_code_modified",
            "active_network_scanning_enabled",
            "policy_bypassed",
        ]:
            if safety_summary.get(flag) is True:
                raise ImmuneSafetyError(
                    f"Immune state safety violation. This flag must be false: {flag}"
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

                if key_text in self.PROHIBITED_REQUEST_KEYS:
                    found.append(child_path)

                found.extend(self.find_prohibited_keys(child, child_path))

        elif isinstance(value, list):
            for index, item in enumerate(value):
                child_path = f"{path}[{index}]"
                found.extend(self.find_prohibited_keys(item, child_path))

        return found

    def get_safety_boundary(self) -> Dict[str, bool]:
        """
        Return the Immune Organ safety boundary.
        """

        return {
            "may_review_action_requests": True,
            "may_allow_explicit_safe_actions": True,
            "may_deny_unknown_actions": True,
            "may_deny_explicit_unsafe_actions": True,
            "may_validate_organ_safety_reports": True,
            "may_write_immune_policy": True,
            "may_append_immune_decisions": True,
            "may_generate_immune_state": True,
            "may_publish_decision_events": True,

            "may_execute_actions": False,
            "may_execute_commands": False,
            "may_access_network": False,
            "may_scan_filesystem": False,
            "may_modify_source_code": False,
            "may_delete_memory": False,
            "may_enable_active_network_cartography": False,
            "may_perform_tool_use": False,
            "may_bypass_policy": False,
            "may_silently_allow_unknown_actions": False,
        }
