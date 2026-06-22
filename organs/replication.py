"""
============================================================
REPLICATION / LINEAGE ORGAN
============================================================

Project:
    Digital Organism

Build:
    1.3.0

Organism Name:
    ContinuityNode

Organ:
    Replication / Lineage Organ

File:
    organs/replication.py

Primary Function:
    Create controlled clone/export manifests, preserve lineage references,
    define memory transfer policy, and record safe source-only or
    parent-referenced replication plans.

Scientific / Clinical Description:
    The Replication Organ is a lineage and export-planning component.

    It does not create biological reproduction, autonomous propagation,
    uncontrolled self-copying, malware behavior, persistence, or
    self-spreading capability.

    The replication metaphor is used architecturally to describe
    controlled source packaging, lineage records, divergence records,
    clone manifests, and memory transfer policies.

Relationship To Existing Organs:
    Core Identity Organ:
        Provides organism identity and lineage ID.

    Memory Organ:
        Provides memory summaries that may be referenced, not blindly copied.

    Immune Organ:
        Reviews and denies/permits replication-related requests.

    Event Bus Organ:
        Receives replication events.

    Telemetry Organ:
        Can measure replication planning and lineage records.

Important Safety Boundary:
    Build 1.3.0 is manifest-only.

    It may:
        - create lineage manifest files
        - create clone/export plans
        - record divergence events
        - reference parent lineage
        - define memory transfer policy
        - generate latest replication report
        - publish replication events

    It may not:
        - copy secrets
        - copy raw environment values
        - copy full memory by default
        - overwrite identity
        - create a live child automatically
        - install persistence
        - execute commands
        - access the network
        - upload files
        - self-propagate
        - bypass Immune

Storage Model:
    data/replication/
        lineage_manifest.json
        clone_events.jsonl
        divergence_records.jsonl
        latest_replication_report.json

Build 1.3.0 Behavior:
    - Create replication directory.
    - Create or load lineage_manifest.json.
    - Generate source-only export manifests.
    - Generate parent-referenced clone manifests.
    - Record clone planning events.
    - Record divergence events.
    - Generate latest_replication_report.json.
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


class ReplicationError(Exception):
    """
    Base exception for all Replication Organ errors.
    """


class ReplicationManifestError(ReplicationError):
    """
    Raised when lineage manifest cannot be created, loaded, saved, or validated.
    """


class ReplicationEventError(ReplicationError):
    """
    Raised when clone/divergence event logging fails.
    """


class ReplicationPolicyError(ReplicationError):
    """
    Raised when clone/export policy is malformed or unsafe.
    """


class ReplicationSafetyError(ReplicationError):
    """
    Raised when a replication operation violates safety boundaries.
    """


class ReplicationReportError(ReplicationError):
    """
    Raised when latest replication report cannot be generated or saved.
    """


# ============================================================
# REPLICATION ORGAN CLASS
# ============================================================


class ReplicationOrgan:
    """
    Controlled lineage and replication planning organ.

    Build 1.3.0 does not perform actual filesystem copying.

    It creates manifests and records.
    Actual packaging/export can be added later through a dedicated,
    Immune-gated export operation.
    """

    SCHEMA_VERSION = "1.0.0"
    REPLICATION_MODE = "MANIFEST_ONLY_SAFE_EXPORT"

    VALID_REPLICATION_MODES = [
        "EXPORT_SOURCE_ONLY",
        "CLONE_WITH_NEW_LINEAGE",
        "CLONE_WITH_PARENT_REFERENCE",
        "CONTINUITY_COPY_DISABLED",
    ]

    DEFAULT_REPLICATION_MODE = "CLONE_WITH_PARENT_REFERENCE"

    DEFAULT_SOURCE_FILES = [
        "organism.py",
        "README.md",
        "BUILD_INDEX.md",
        "organs/__init__.py",
        "organs/core_identity.py",
        "organs/sensorium.py",
        "organs/network_cartography.py",
        "organs/memory.py",
        "organs/event_bus.py",
        "organs/metabolism.py",
        "organs/reflex.py",
        "organs/immune.py",
        "organs/interface.py",
        "organs/telemetry.py",
        "organs/tool_use.py",
        "organs/replication.py",
    ]

    DEFAULT_EXCLUDED_PATHS = [
        ".git/",
        "__pycache__/",
        ".venv/",
        "venv/",
        "env/",
        ".env",
        ".env.local",
        "secrets/",
        "credentials/",
        "private/",
        "data/identity.json",
        "data/sensorium_snapshot.json",
        "data/memory/snapshots/",
        "data/memory/event_log.jsonl",
        "data/tool_use/tool_use_audit_log.jsonl",
        "data/immune/immune_decisions.jsonl",
    ]

    PROHIBITED_MEMORY_TRANSFER_MODES = [
        "FULL_MEMORY_COPY",
        "COPY_SECRETS",
        "COPY_RAW_ENVIRONMENT",
        "COPY_CREDENTIALS",
    ]

    ALLOWED_MEMORY_TRANSFER_MODES = [
        "NONE",
        "SUMMARY_ONLY",
        "PARENT_REFERENCE_ONLY",
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
        immune: Optional[Any] = None,
        replication_root: str = "data/replication",
        lineage_manifest_path: str = "data/replication/lineage_manifest.json",
        clone_events_path: str = "data/replication/clone_events.jsonl",
        divergence_records_path: str = "data/replication/divergence_records.jsonl",
        latest_report_path: str = "data/replication/latest_replication_report.json",
    ) -> None:
        """
        Initialize Replication Organ.
        """

        self.core_identity = core_identity
        self.event_bus = event_bus
        self.immune = immune

        self.replication_root = Path(replication_root)
        self.lineage_manifest_path = Path(lineage_manifest_path)
        self.clone_events_path = Path(clone_events_path)
        self.divergence_records_path = Path(divergence_records_path)
        self.latest_report_path = Path(latest_report_path)

        self.clone_plans_created_this_run = 0
        self.clone_events_written_this_run = 0
        self.divergence_records_written_this_run = 0
        self.reports_written_this_run = 0
        self.denied_replication_requests_this_run = 0
        self.allowed_replication_requests_this_run = 0

        self.replication_modes_seen_this_run: Dict[str, int] = {}
        self.memory_transfer_modes_seen_this_run: Dict[str, int] = {}

        self.ensure_replication_structure()
        self.lineage_manifest = self.ensure_lineage_manifest()
        self.validate_lineage_manifest(self.lineage_manifest)

        self.record_clone_event(
            event_type="replication.initialized",
            replication_mode=self.REPLICATION_MODE,
            decision="allow",
            details={
                "replication_root": str(self.replication_root),
                "lineage_manifest_path": str(self.lineage_manifest_path),
                "manifest_only": True,
            },
        )

    # ========================================================
    # TIME AND ID HELPERS
    # ========================================================

    def utc_now_iso(self) -> str:
        """
        Return current UTC timestamp.
        """

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_record_id(self, prefix: str) -> str:
        """
        Generate unique replication record ID.
        """

        timestamp = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        short_id = uuid.uuid4().hex[:6]
        safe_prefix = prefix.replace(".", "-").replace("_", "-")

        return f"{safe_prefix}-{timestamp}-{short_id}"

    def generate_child_lineage_candidate_id(self) -> str:
        """
        Generate candidate child lineage ID.

        This is only a proposed lineage ID in Build 1.3.0.
        No child organism is created automatically.
        """

        return f"cn-child-lineage-{uuid.uuid4().hex[:12]}"

    # ========================================================
    # STRUCTURE AND MANIFEST
    # ========================================================

    def ensure_replication_structure(self) -> None:
        """
        Create replication output directory.
        """

        try:
            self.replication_root.mkdir(parents=True, exist_ok=True)

        except OSError as error:
            raise ReplicationReportError(
                f"Could not create replication directory: {error}"
            ) from error

    def ensure_lineage_manifest(self) -> Dict[str, Any]:
        """
        Load or create lineage_manifest.json.
        """

        if self.lineage_manifest_path.exists():
            return self.load_lineage_manifest()

        manifest = self.create_default_lineage_manifest()
        self.save_lineage_manifest(manifest)

        return manifest

    def create_default_lineage_manifest(self) -> Dict[str, Any]:
        """
        Create default lineage manifest for the current organism.
        """

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        return {
            "schema_version": self.SCHEMA_VERSION,
            "manifest_created_utc": self.utc_now_iso(),
            "last_updated_utc": self.utc_now_iso(),
            "organism_name": persistent["organism_name"],
            "lineage_id": persistent["lineage_id"],
            "birth_timestamp_utc": persistent["birth_timestamp_utc"],
            "first_build": persistent["first_build"],
            "current_build": persistent["current_build"],
            "created_by_runtime_instance_id": runtime["runtime_instance_id"],
            "replication_mode": self.REPLICATION_MODE,
            "default_clone_mode": self.DEFAULT_REPLICATION_MODE,
            "parent_lineage_id": None,
            "ancestor_lineage_ids": [],
            "clone_plans_count": 0,
            "divergence_records_count": 0,
            "memory_transfer_policy": self.get_default_memory_transfer_policy(),
            "source_file_policy": self.get_default_source_file_policy(),
            "safety_boundary": self.get_safety_boundary(),
        }

    def load_lineage_manifest(self) -> Dict[str, Any]:
        """
        Load lineage manifest from disk.
        """

        try:
            with self.lineage_manifest_path.open("r", encoding="utf-8") as file:
                data = json.load(file)

        except json.JSONDecodeError as error:
            raise ReplicationManifestError(
                f"lineage_manifest.json could not be parsed: {error}"
            ) from error

        except OSError as error:
            raise ReplicationManifestError(
                f"lineage_manifest.json could not be read: {error}"
            ) from error

        if not isinstance(data, dict):
            raise ReplicationManifestError(
                "lineage_manifest.json must contain a JSON object."
            )

        return data

    def save_lineage_manifest(self, manifest: Dict[str, Any]) -> None:
        """
        Save lineage manifest.
        """

        self.validate_lineage_manifest(manifest)

        try:
            self.lineage_manifest_path.parent.mkdir(parents=True, exist_ok=True)

            with self.lineage_manifest_path.open("w", encoding="utf-8") as file:
                json.dump(manifest, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ReplicationManifestError(
                f"Could not save lineage manifest: {error}"
            ) from error

    def validate_lineage_manifest(self, manifest: Dict[str, Any]) -> bool:
        """
        Validate lineage manifest.
        """

        required_fields = [
            "schema_version",
            "manifest_created_utc",
            "last_updated_utc",
            "organism_name",
            "lineage_id",
            "birth_timestamp_utc",
            "first_build",
            "current_build",
            "replication_mode",
            "default_clone_mode",
            "memory_transfer_policy",
            "source_file_policy",
            "safety_boundary",
        ]

        for field in required_fields:
            if field not in manifest:
                raise ReplicationManifestError(
                    f"Missing required lineage manifest field: {field}"
                )

        memory_policy = manifest["memory_transfer_policy"]

        if memory_policy.get("default_memory_transfer_mode") not in self.ALLOWED_MEMORY_TRANSFER_MODES:
            raise ReplicationPolicyError(
                "Default memory transfer mode is not allowed."
            )

        for mode in self.PROHIBITED_MEMORY_TRANSFER_MODES:
            if memory_policy.get(mode) is True:
                raise ReplicationSafetyError(
                    f"Prohibited memory transfer mode is enabled: {mode}"
                )

        safety = manifest["safety_boundary"]

        prohibited_true_flags = [
            "may_copy_secrets",
            "may_copy_raw_environment_values",
            "may_copy_credentials",
            "may_copy_full_memory_by_default",
            "may_overwrite_identity",
            "may_create_live_child_automatically",
            "may_install_persistence",
            "may_execute_commands",
            "may_access_network",
            "may_upload_files",
            "may_self_propagate",
            "may_bypass_immune",
        ]

        for flag in prohibited_true_flags:
            if safety.get(flag) is True:
                raise ReplicationSafetyError(
                    f"Replication safety boundary violation. This flag must be false: {flag}"
                )

        return True

    # ========================================================
    # POLICY HELPERS
    # ========================================================

    def get_default_memory_transfer_policy(self) -> Dict[str, Any]:
        """
        Return default memory transfer policy.

        This is intentionally conservative.
        """

        return {
            "default_memory_transfer_mode": "SUMMARY_ONLY",
            "allowed_memory_transfer_modes": list(self.ALLOWED_MEMORY_TRANSFER_MODES),
            "prohibited_memory_transfer_modes": list(self.PROHIBITED_MEMORY_TRANSFER_MODES),
            "copy_memory_summary": True,
            "copy_memory_index_metadata": False,
            "copy_full_memory_snapshots": False,
            "copy_event_logs": False,
            "copy_tool_use_logs": False,
            "copy_immune_decision_logs": False,
            "copy_raw_environment_values": False,
            "copy_credentials": False,
            "copy_secrets": False,
            "FULL_MEMORY_COPY": False,
            "COPY_SECRETS": False,
            "COPY_RAW_ENVIRONMENT": False,
            "COPY_CREDENTIALS": False,
        }

    def get_default_source_file_policy(self) -> Dict[str, Any]:
        """
        Return default source file inclusion/exclusion policy.
        """

        return {
            "copy_source_code": True,
            "copy_documentation": True,
            "copy_runtime_data": False,
            "copy_identity": False,
            "copy_full_memory": False,
            "copy_generated_reports": False,
            "copy_secrets": False,
            "included_source_files": list(self.DEFAULT_SOURCE_FILES),
            "excluded_paths": list(self.DEFAULT_EXCLUDED_PATHS),
        }

    # ========================================================
    # CLONE / EXPORT PLAN GENERATION
    # ========================================================

    def create_clone_manifest(
        self,
        clone_mode: str = DEFAULT_REPLICATION_MODE,
        memory_transfer_mode: str = "SUMMARY_ONLY",
        clone_label: Optional[str] = None,
        notes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Create a controlled clone/export manifest.

        This method does not copy files.

        It creates a plan describing what could be exported later.
        """

        clone_mode = clone_mode.upper()
        memory_transfer_mode = memory_transfer_mode.upper()
        notes = notes or []

        self.validate_details_safety(
            {
                "clone_label": clone_label,
                "notes": notes,
            }
        )

        if clone_mode not in self.VALID_REPLICATION_MODES:
            return self.deny_replication_request(
                requested_operation="create_clone_manifest",
                reason=f"Invalid clone mode: {clone_mode}",
                details={
                    "clone_mode": clone_mode,
                    "memory_transfer_mode": memory_transfer_mode,
                },
            )

        if clone_mode == "CONTINUITY_COPY_DISABLED":
            return self.deny_replication_request(
                requested_operation="create_clone_manifest",
                reason="Continuity copy is disabled in Build 1.3.0.",
                details={
                    "clone_mode": clone_mode,
                    "memory_transfer_mode": memory_transfer_mode,
                },
            )

        if memory_transfer_mode not in self.ALLOWED_MEMORY_TRANSFER_MODES:
            return self.deny_replication_request(
                requested_operation="create_clone_manifest",
                reason=f"Memory transfer mode is not allowed: {memory_transfer_mode}",
                details={
                    "clone_mode": clone_mode,
                    "memory_transfer_mode": memory_transfer_mode,
                },
            )

        if self.immune is not None:
            decision = self.immune.review_action_request(
                requested_action="replication.create_manifest",
                source_organ="ReplicationOrgan",
                request={
                    "clone_mode": clone_mode,
                    "memory_transfer_mode": memory_transfer_mode,
                    "manifest_only": True,
                    "copy_secrets": False,
                    "copy_full_memory": False,
                    "copy_identity": False,
                },
            )

            if decision.get("decision") != "allow":
                return self.deny_replication_request(
                    requested_operation="create_clone_manifest",
                    reason=decision.get("reason", "Immune denied replication manifest request."),
                    details={
                        "clone_mode": clone_mode,
                        "memory_transfer_mode": memory_transfer_mode,
                        "immune_decision_id": decision.get("decision_id"),
                    },
                )

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        child_lineage_candidate_id = self.generate_child_lineage_candidate_id()

        clone_manifest = {
            "schema_version": self.SCHEMA_VERSION,
            "clone_manifest_id": self.generate_record_id("clone-manifest"),
            "created_utc": self.utc_now_iso(),
            "replication_mode": self.REPLICATION_MODE,
            "clone_mode": clone_mode,
            "clone_label": clone_label,
            "source_organism": {
                "organism_name": persistent["organism_name"],
                "lineage_id": persistent["lineage_id"],
                "birth_timestamp_utc": persistent["birth_timestamp_utc"],
                "first_build": persistent["first_build"],
                "current_build": persistent["current_build"],
                "runtime_instance_id": runtime["runtime_instance_id"],
            },
            "child_candidate": {
                "child_lineage_candidate_id": child_lineage_candidate_id,
                "child_identity_created": False,
                "child_runtime_created": False,
                "child_files_copied": False,
                "child_memory_copied": False,
            },
            "lineage_relationship": self.build_lineage_relationship(
                clone_mode=clone_mode,
                parent_lineage_id=persistent["lineage_id"],
                child_lineage_candidate_id=child_lineage_candidate_id,
            ),
            "source_file_policy": self.get_default_source_file_policy(),
            "memory_transfer_policy": {
                **self.get_default_memory_transfer_policy(),
                "selected_memory_transfer_mode": memory_transfer_mode,
            },
            "included_files_planned": list(self.DEFAULT_SOURCE_FILES),
            "excluded_paths": list(self.DEFAULT_EXCLUDED_PATHS),
            "notes": notes,
            "safety_summary": {
                "manifest_only": True,
                "files_copied": False,
                "identity_copied": False,
                "full_memory_copied": False,
                "secrets_copied": False,
                "raw_environment_values_copied": False,
                "credentials_copied": False,
                "commands_executed": False,
                "network_access_performed": False,
                "files_uploaded": False,
                "persistence_installed": False,
                "self_propagation_performed": False,
                "immune_bypassed": False,
            },
        }

        self.validate_clone_manifest(clone_manifest)

        self.clone_plans_created_this_run += 1
        self.allowed_replication_requests_this_run += 1

        self.replication_modes_seen_this_run[clone_mode] = (
            self.replication_modes_seen_this_run.get(clone_mode, 0) + 1
        )

        self.memory_transfer_modes_seen_this_run[memory_transfer_mode] = (
            self.memory_transfer_modes_seen_this_run.get(memory_transfer_mode, 0) + 1
        )

        self.record_clone_event(
            event_type="replication.clone_manifest.created",
            replication_mode=clone_mode,
            decision="allow",
            details={
                "clone_manifest_id": clone_manifest["clone_manifest_id"],
                "child_lineage_candidate_id": child_lineage_candidate_id,
                "memory_transfer_mode": memory_transfer_mode,
                "manifest_only": True,
            },
        )

        self.record_divergence_record(
            divergence_type="clone_candidate_created",
            parent_lineage_id=persistent["lineage_id"],
            child_lineage_candidate_id=child_lineage_candidate_id,
            details={
                "clone_manifest_id": clone_manifest["clone_manifest_id"],
                "clone_mode": clone_mode,
                "memory_transfer_mode": memory_transfer_mode,
            },
        )

        self.update_lineage_manifest_after_clone_plan(clone_manifest)

        self.publish_replication_event(
            event_type="replication.lineage.created",
            payload={
                "clone_manifest_id": clone_manifest["clone_manifest_id"],
                "clone_mode": clone_mode,
                "parent_lineage_id": persistent["lineage_id"],
                "child_lineage_candidate_id": child_lineage_candidate_id,
                "manifest_only": True,
            },
        )

        self.generate_latest_replication_report()

        return copy.deepcopy(clone_manifest)

    def build_lineage_relationship(
        self,
        clone_mode: str,
        parent_lineage_id: str,
        child_lineage_candidate_id: str,
    ) -> Dict[str, Any]:
        """
        Build lineage relationship description.
        """

        if clone_mode == "EXPORT_SOURCE_ONLY":
            return {
                "relationship_type": "source_export",
                "parent_lineage_reference_included": False,
                "child_lineage_candidate_id": None,
                "continuity_claim": "none",
                "description": "Source-only export without child continuity claim.",
            }

        if clone_mode == "CLONE_WITH_NEW_LINEAGE":
            return {
                "relationship_type": "new_lineage_candidate",
                "parent_lineage_reference_included": False,
                "child_lineage_candidate_id": child_lineage_candidate_id,
                "continuity_claim": "new_lineage",
                "description": "Child would initialize as a new lineage.",
            }

        if clone_mode == "CLONE_WITH_PARENT_REFERENCE":
            return {
                "relationship_type": "parent_referenced_child_lineage",
                "parent_lineage_reference_included": True,
                "parent_lineage_id": parent_lineage_id,
                "child_lineage_candidate_id": child_lineage_candidate_id,
                "continuity_claim": "derived_from_parent_not_same_identity",
                "description": "Child would know parent lineage but would not be the same runtime identity.",
            }

        return {
            "relationship_type": "unsupported",
            "continuity_claim": "none",
        }

    def update_lineage_manifest_after_clone_plan(self, clone_manifest: Dict[str, Any]) -> None:
        """
        Update lineage manifest after a clone plan is created.
        """

        self.lineage_manifest["last_updated_utc"] = self.utc_now_iso()
        self.lineage_manifest["clone_plans_count"] = int(
            self.lineage_manifest.get("clone_plans_count", 0)
        ) + 1

        self.save_lineage_manifest(self.lineage_manifest)

    # ========================================================
    # DENIALS
    # ========================================================

    def deny_replication_request(
        self,
        requested_operation: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record denied replication request.
        """

        details = details or {}
        self.validate_details_safety(details)

        self.denied_replication_requests_this_run += 1

        record = self.record_clone_event(
            event_type="replication.request.denied",
            replication_mode=self.REPLICATION_MODE,
            decision="deny",
            details={
                "requested_operation": requested_operation,
                "reason": reason,
                **details,
            },
        )

        self.publish_replication_event(
            event_type="replication.request.denied",
            payload={
                "requested_operation": requested_operation,
                "reason": reason,
            },
            priority="warning",
        )

        return copy.deepcopy(record)

    # ========================================================
    # EVENT RECORDING
    # ========================================================

    def record_clone_event(
        self,
        event_type: str,
        replication_mode: str,
        decision: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Append clone event to clone_events.jsonl.
        """

        details = details or {}
        self.validate_details_safety(details)

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        record = {
            "schema_version": self.SCHEMA_VERSION,
            "clone_event_id": self.generate_record_id("clone-event"),
            "timestamp_utc": self.utc_now_iso(),
            "event_type": event_type,
            "replication_mode": replication_mode,
            "decision": decision,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_build": persistent["current_build"],
            "details": copy.deepcopy(details),
            "safety": {
                "manifest_only": True,
                "files_copied": False,
                "identity_copied": False,
                "full_memory_copied": False,
                "secrets_copied": False,
                "raw_environment_values_copied": False,
                "credentials_copied": False,
                "commands_executed": False,
                "network_access_performed": False,
                "files_uploaded": False,
                "persistence_installed": False,
                "self_propagation_performed": False,
                "immune_bypassed": False,
            },
        }

        self.validate_event_record(record)

        try:
            self.clone_events_path.parent.mkdir(parents=True, exist_ok=True)

            with self.clone_events_path.open("a", encoding="utf-8") as file:
                json.dump(record, file, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ReplicationEventError(
                f"Could not append clone event: {error}"
            ) from error

        self.clone_events_written_this_run += 1

        return copy.deepcopy(record)

    def record_divergence_record(
        self,
        divergence_type: str,
        parent_lineage_id: str,
        child_lineage_candidate_id: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Append divergence record to divergence_records.jsonl.
        """

        details = details or {}
        self.validate_details_safety(details)

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        record = {
            "schema_version": self.SCHEMA_VERSION,
            "divergence_record_id": self.generate_record_id("divergence"),
            "timestamp_utc": self.utc_now_iso(),
            "divergence_type": divergence_type,
            "parent_lineage_id": parent_lineage_id,
            "child_lineage_candidate_id": child_lineage_candidate_id,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_build": persistent["current_build"],
            "details": copy.deepcopy(details),
            "safety": {
                "manifest_only": True,
                "child_created": False,
                "files_copied": False,
                "identity_copied": False,
                "full_memory_copied": False,
                "secrets_copied": False,
                "commands_executed": False,
                "network_access_performed": False,
                "self_propagation_performed": False,
            },
        }

        self.validate_divergence_record(record)

        try:
            self.divergence_records_path.parent.mkdir(parents=True, exist_ok=True)

            with self.divergence_records_path.open("a", encoding="utf-8") as file:
                json.dump(record, file, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ReplicationEventError(
                f"Could not append divergence record: {error}"
            ) from error

        self.divergence_records_written_this_run += 1

        self.lineage_manifest["last_updated_utc"] = self.utc_now_iso()
        self.lineage_manifest["divergence_records_count"] = int(
            self.lineage_manifest.get("divergence_records_count", 0)
        ) + 1
        self.save_lineage_manifest(self.lineage_manifest)

        return copy.deepcopy(record)

    # ========================================================
    # REPORTING
    # ========================================================

    def generate_latest_replication_report(self) -> Dict[str, Any]:
        """
        Generate latest_replication_report.json.
        """

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        report = {
            "schema_version": self.SCHEMA_VERSION,
            "report_timestamp_utc": self.utc_now_iso(),
            "organism_name": persistent["organism_name"],
            "lineage_id": persistent["lineage_id"],
            "runtime_instance_id": runtime["runtime_instance_id"],
            "current_build": persistent["current_build"],
            "replication_root": str(self.replication_root),
            "lineage_manifest_path": str(self.lineage_manifest_path),
            "clone_events_path": str(self.clone_events_path),
            "divergence_records_path": str(self.divergence_records_path),
            "latest_report_path": str(self.latest_report_path),
            "replication_mode": self.REPLICATION_MODE,
            "default_clone_mode": self.DEFAULT_REPLICATION_MODE,
            "clone_plans_created_this_run": self.clone_plans_created_this_run,
            "clone_events_written_this_run": self.clone_events_written_this_run,
            "divergence_records_written_this_run": self.divergence_records_written_this_run,
            "reports_written_this_run": self.reports_written_this_run,
            "allowed_replication_requests_this_run": self.allowed_replication_requests_this_run,
            "denied_replication_requests_this_run": self.denied_replication_requests_this_run,
            "replication_modes_seen_this_run": copy.deepcopy(self.replication_modes_seen_this_run),
            "memory_transfer_modes_seen_this_run": copy.deepcopy(self.memory_transfer_modes_seen_this_run),
            "manifest_summary": {
                "clone_plans_count": self.lineage_manifest.get("clone_plans_count"),
                "divergence_records_count": self.lineage_manifest.get("divergence_records_count"),
                "parent_lineage_id": self.lineage_manifest.get("parent_lineage_id"),
                "ancestor_lineage_ids_count": len(self.lineage_manifest.get("ancestor_lineage_ids", [])),
                "default_memory_transfer_mode": self.lineage_manifest.get("memory_transfer_policy", {}).get("default_memory_transfer_mode"),
            },
            "safety_boundary": self.get_safety_boundary(),
            "safety_summary": {
                "manifest_only": True,
                "files_copied": False,
                "identity_copied": False,
                "full_memory_copied": False,
                "secrets_copied": False,
                "raw_environment_values_copied": False,
                "credentials_copied": False,
                "commands_executed": False,
                "network_access_performed": False,
                "files_uploaded": False,
                "persistence_installed": False,
                "self_propagation_performed": False,
                "immune_bypassed": False,
            },
        }

        self.validate_replication_report(report)
        self.save_latest_replication_report(report)

        return copy.deepcopy(report)

    def save_latest_replication_report(self, report: Dict[str, Any]) -> None:
        """
        Save latest_replication_report.json.
        """

        try:
            self.latest_report_path.parent.mkdir(parents=True, exist_ok=True)

            with self.latest_report_path.open("w", encoding="utf-8") as file:
                json.dump(report, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ReplicationReportError(
                f"Could not save latest replication report: {error}"
            ) from error

        self.reports_written_this_run += 1

    def get_replication_report(self, latest_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return short replication report for console output.
        """

        if latest_report is None:
            latest_report = self.generate_latest_replication_report()

        return {
            "replication_root": latest_report["replication_root"],
            "replication_mode": latest_report["replication_mode"],
            "default_clone_mode": latest_report["default_clone_mode"],
            "clone_plans_created_this_run": latest_report["clone_plans_created_this_run"],
            "clone_events_written_this_run": latest_report["clone_events_written_this_run"],
            "divergence_records_written_this_run": latest_report["divergence_records_written_this_run"],
            "allowed_replication_requests_this_run": latest_report["allowed_replication_requests_this_run"],
            "denied_replication_requests_this_run": latest_report["denied_replication_requests_this_run"],
            "manifest_summary": latest_report["manifest_summary"],
            "safety_summary": latest_report["safety_summary"],
        }

    # ========================================================
    # EVENT BUS
    # ========================================================

    def publish_replication_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: str = "info",
    ) -> None:
        """
        Publish replication event through Event Bus if available.
        """

        if self.event_bus is None:
            return

        self.event_bus.publish_event(
            event_type=event_type,
            source_organ="ReplicationOrgan",
            payload=payload,
            priority=priority,
        )

    # ========================================================
    # VALIDATION AND SAFETY
    # ========================================================

    def validate_clone_manifest(self, manifest: Dict[str, Any]) -> bool:
        """
        Validate clone manifest.
        """

        required_fields = [
            "schema_version",
            "clone_manifest_id",
            "created_utc",
            "replication_mode",
            "clone_mode",
            "source_organism",
            "child_candidate",
            "lineage_relationship",
            "source_file_policy",
            "memory_transfer_policy",
            "included_files_planned",
            "excluded_paths",
            "safety_summary",
        ]

        for field in required_fields:
            if field not in manifest:
                raise ReplicationManifestError(
                    f"Missing required clone manifest field: {field}"
                )

        if manifest["memory_transfer_policy"].get("selected_memory_transfer_mode") not in self.ALLOWED_MEMORY_TRANSFER_MODES:
            raise ReplicationPolicyError(
                "Selected memory transfer mode is not allowed."
            )

        return self.validate_safety_summary(manifest["safety_summary"])

    def validate_event_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate clone event record.
        """

        required_fields = [
            "schema_version",
            "clone_event_id",
            "timestamp_utc",
            "event_type",
            "replication_mode",
            "decision",
            "source_runtime_instance_id",
            "source_lineage_id",
            "source_organism_name",
            "source_build",
            "details",
            "safety",
        ]

        for field in required_fields:
            if field not in record:
                raise ReplicationEventError(
                    f"Missing required clone event field: {field}"
                )

        return self.validate_safety_summary(record["safety"])

    def validate_divergence_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate divergence record.
        """

        required_fields = [
            "schema_version",
            "divergence_record_id",
            "timestamp_utc",
            "divergence_type",
            "parent_lineage_id",
            "child_lineage_candidate_id",
            "source_runtime_instance_id",
            "source_lineage_id",
            "source_organism_name",
            "source_build",
            "details",
            "safety",
        ]

        for field in required_fields:
            if field not in record:
                raise ReplicationEventError(
                    f"Missing required divergence record field: {field}"
                )

        return self.validate_safety_summary(record["safety"])

    def validate_replication_report(self, report: Dict[str, Any]) -> bool:
        """
        Validate latest replication report.
        """

        required_fields = [
            "schema_version",
            "report_timestamp_utc",
            "organism_name",
            "lineage_id",
            "runtime_instance_id",
            "current_build",
            "replication_root",
            "lineage_manifest_path",
            "clone_events_path",
            "divergence_records_path",
            "latest_report_path",
            "replication_mode",
            "default_clone_mode",
            "clone_plans_created_this_run",
            "clone_events_written_this_run",
            "divergence_records_written_this_run",
            "manifest_summary",
            "safety_boundary",
            "safety_summary",
        ]

        for field in required_fields:
            if field not in report:
                raise ReplicationReportError(
                    f"Missing required replication report field: {field}"
                )

        return self.validate_safety_summary(report["safety_summary"])

    def validate_safety_summary(self, safety: Dict[str, Any]) -> bool:
        """
        Validate safety summary flags.
        """

        prohibited_true_flags = [
            "files_copied",
            "identity_copied",
            "full_memory_copied",
            "secrets_copied",
            "raw_environment_values_copied",
            "credentials_copied",
            "commands_executed",
            "network_access_performed",
            "files_uploaded",
            "persistence_installed",
            "self_propagation_performed",
            "immune_bypassed",
        ]

        for flag in prohibited_true_flags:
            if safety.get(flag) is True:
                raise ReplicationSafetyError(
                    f"Replication safety violation. This flag must be false: {flag}"
                )

        return True

    def validate_details_safety(self, details: Dict[str, Any]) -> bool:
        """
        Validate detail payloads for prohibited keys.
        """

        if not isinstance(details, dict):
            raise ReplicationSafetyError("Replication details must be a dictionary.")

        prohibited = self.find_prohibited_keys(details)

        if prohibited:
            raise ReplicationSafetyError(
                f"Replication details contain prohibited key names: {prohibited}"
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
        Return Replication Organ safety boundary.
        """

        return {
            "may_create_lineage_manifest": True,
            "may_create_clone_manifest": True,
            "may_record_clone_events": True,
            "may_record_divergence_records": True,
            "may_reference_parent_lineage": True,
            "may_define_memory_transfer_policy": True,
            "may_generate_replication_report": True,
            "may_publish_replication_events": True,

            "may_copy_files_in_this_build": False,
            "may_copy_identity": False,
            "may_copy_full_memory_by_default": False,
            "may_copy_secrets": False,
            "may_copy_raw_environment_values": False,
            "may_copy_credentials": False,
            "may_overwrite_identity": False,
            "may_create_live_child_automatically": False,
            "may_install_persistence": False,
            "may_execute_commands": False,
            "may_access_network": False,
            "may_upload_files": False,
            "may_self_propagate": False,
            "may_bypass_immune": False,
        }
