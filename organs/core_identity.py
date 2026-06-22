"""
Core Identity Organ — ContinuityNode
Build compatibility: 0.1.0 through 0.5.0

Purpose:
  Maintain stable organism-level identity across executions while generating
  a unique runtime identity for each launch.

Locked-field rule:
  The identity organ should never overwrite locked fields unless a future
  reset_identity() method is explicitly added. No reset_identity() exists here.
"""

from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class CoreIdentityError(Exception): pass
class IdentityLoadError(CoreIdentityError): pass
class IdentityValidationError(CoreIdentityError): pass
class IdentityUpdateError(CoreIdentityError): pass


class CoreIdentityOrgan:
    SCHEMA_VERSION = "1.0.0"
    ORGANISM_TYPE = "experimental_software_and_digital_organism_research_model"
    DEFAULT_DESCRIPTION = (
        "ContinuityNode is an experimental software system and digital organism "
        "research model designed to study persistent identity, runtime instancing, "
        "continuity tracking, and controlled divergence across executions."
    )
    REQUIRED_TOP_LEVEL_FIELDS = [
        "schema_version", "organism_name", "organism_type", "description",
        "birth_timestamp_utc", "lineage_id", "first_build", "current_build",
        "default_runtime_mode", "created_by", "created_with",
        "identity_locked_fields", "allowed_runtime_modes", "safety_boundary",
        "last_identity_validation_utc",
    ]
    REQUIRED_SAFETY_FLAGS = [
        "may_create_identity_file", "may_update_current_build",
        "may_update_description", "may_generate_runtime_instance_id",
        "may_execute_shell_commands", "may_access_network",
        "may_modify_unrelated_files", "may_scan_environment",
    ]
    RUNTIME_ONLY_FIELDS = [
        "runtime_instance_id", "runtime_started_utc", "active_mode",
        "runtime", "session", "events", "logs", "machine_state",
        "command_results",
    ]
    DEFAULT_LOCKED_FIELDS = [
        "organism_name", "birth_timestamp_utc", "lineage_id", "first_build",
    ]
    DEFAULT_ALLOWED_RUNTIME_MODES = [
        "OBSERVE", "DIAGNOSTIC", "EXPERIMENTAL", "MAINTENANCE", "REPLICATION_TEST",
    ]

    def __init__(
        self,
        identity_path: str = "data/identity.json",
        build_version: str = "0.5.0",
        default_name: str = "ContinuityNode",
        default_mode: str = "OBSERVE",
    ) -> None:
        self.identity_path = Path(identity_path)
        self.build_version = build_version
        self.default_name = default_name
        self.default_mode = default_mode.upper()
        self.identity: Dict[str, Any] = {}
        self.runtime: Dict[str, Any] = {}
        self.identity = self.ensure_identity_file()
        self.validate_identity(self.identity)
        if self.identity.get("current_build") != self.build_version:
            self.update_current_build(self.build_version)
        self.update_validation_timestamp()
        self.runtime = self.create_runtime_identity(self.default_mode)

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_lineage_id(self) -> str:
        return f"cn-lineage-{uuid.uuid4().hex[:12]}"

    def generate_runtime_instance_id(self) -> str:
        if not self.identity.get("safety_boundary", {}).get("may_generate_runtime_instance_id", False):
            raise IdentityUpdateError("Runtime instance ID generation is not permitted.")
        ts = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        return f"cn-run-{ts}-{uuid.uuid4().hex[:6]}"

    def ensure_identity_file(self) -> Dict[str, Any]:
        if self.identity_path.exists():
            return self.load_identity()
        identity = self.create_default_identity()
        if not identity["safety_boundary"].get("may_create_identity_file", False):
            raise IdentityUpdateError("Identity file creation is not permitted.")
        self.save_identity(identity)
        return identity

    def create_default_identity(self) -> Dict[str, Any]:
        now = self.utc_now_iso()
        return {
            "schema_version": self.SCHEMA_VERSION,
            "organism_name": self.default_name,
            "organism_type": self.ORGANISM_TYPE,
            "description": self.DEFAULT_DESCRIPTION,
            "birth_timestamp_utc": now,
            "lineage_id": self.generate_lineage_id(),
            "first_build": self.build_version,
            "current_build": self.build_version,
            "default_runtime_mode": self.default_mode,
            "created_by": "User",
            "created_with": "Python",
            "identity_locked_fields": list(self.DEFAULT_LOCKED_FIELDS),
            "allowed_runtime_modes": list(self.DEFAULT_ALLOWED_RUNTIME_MODES),
            "safety_boundary": {
                "may_create_identity_file": True,
                "may_update_current_build": True,
                "may_update_description": True,
                "may_generate_runtime_instance_id": True,
                "may_execute_shell_commands": False,
                "may_access_network": False,
                "may_modify_unrelated_files": False,
                "may_scan_environment": False,
            },
            "last_identity_validation_utc": None,
        }

    def load_identity(self) -> Dict[str, Any]:
        try:
            with self.identity_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise IdentityLoadError(f"identity.json could not be parsed: {error}") from error
        except OSError as error:
            raise IdentityLoadError(f"identity.json could not be read: {error}") from error
        if not isinstance(data, dict):
            raise IdentityLoadError("identity.json must contain a JSON object.")
        return data

    def save_identity(self, identity: Dict[str, Any]) -> None:
        self.reject_runtime_fields(identity)
        try:
            self.identity_path.parent.mkdir(parents=True, exist_ok=True)
            with self.identity_path.open("w", encoding="utf-8") as file:
                json.dump(identity, file, indent=2, sort_keys=False)
                file.write("\n")
        except OSError as error:
            raise IdentityUpdateError(f"Could not save identity file: {error}") from error

    def reject_runtime_fields(self, identity: Dict[str, Any]) -> None:
        for field in self.RUNTIME_ONLY_FIELDS:
            if field in identity:
                raise IdentityUpdateError(f"Refusing to save runtime-only field: {field}")

    def validate_identity(self, identity: Dict[str, Any]) -> bool:
        for field in self.REQUIRED_TOP_LEVEL_FIELDS:
            if field not in identity:
                raise IdentityValidationError(f"Missing required identity field: {field}")
        for field in self.RUNTIME_ONLY_FIELDS:
            if field in identity:
                raise IdentityValidationError(f"Runtime-only field in persistent identity: {field}")
        locked = identity.get("identity_locked_fields")
        if not isinstance(locked, list):
            raise IdentityValidationError("identity_locked_fields must be a list.")
        for field in self.DEFAULT_LOCKED_FIELDS:
            if field not in locked:
                raise IdentityValidationError(f"Continuity-critical field missing from locks: {field}")
        for field in locked:
            if field not in identity:
                raise IdentityValidationError(f"Locked field missing from identity: {field}")
        allowed = identity.get("allowed_runtime_modes")
        if not isinstance(allowed, list) or not allowed:
            raise IdentityValidationError("allowed_runtime_modes must be non-empty list.")
        if str(identity.get("default_runtime_mode")).upper() not in [str(m).upper() for m in allowed]:
            raise IdentityValidationError("default_runtime_mode is not allowed.")
        safety = identity.get("safety_boundary")
        if not isinstance(safety, dict):
            raise IdentityValidationError("safety_boundary must be a dictionary.")
        for flag in self.REQUIRED_SAFETY_FLAGS:
            if flag not in safety:
                raise IdentityValidationError(f"Missing safety flag: {flag}")
            if not isinstance(safety[flag], bool):
                raise IdentityValidationError(f"Safety flag must be boolean: {flag}")
        for flag in ["may_execute_shell_commands", "may_access_network", "may_modify_unrelated_files", "may_scan_environment"]:
            if safety.get(flag) is True:
                raise IdentityValidationError(f"Core Identity flag must be false: {flag}")
        return True

    def update_validation_timestamp(self) -> None:
        self.identity["last_identity_validation_utc"] = self.utc_now_iso()
        self.save_identity(self.identity)

    def create_runtime_identity(self, mode: Optional[str] = None) -> Dict[str, Any]:
        requested = (mode or self.identity["default_runtime_mode"]).upper()
        if requested not in self.get_allowed_modes_upper():
            raise IdentityValidationError(f"Requested runtime mode is not allowed: {requested}")
        return {
            "runtime_instance_id": self.generate_runtime_instance_id(),
            "runtime_started_utc": self.utc_now_iso(),
            "active_mode": requested,
            "source_lineage_id": self.identity["lineage_id"],
            "source_organism_name": self.identity["organism_name"],
            "build": self.identity["current_build"],
        }

    def get_allowed_modes_upper(self) -> list[str]:
        return [str(m).upper() for m in self.identity["allowed_runtime_modes"]]

    def get_persistent_identity(self) -> Dict[str, Any]:
        return copy.deepcopy(self.identity)

    def get_runtime_identity(self) -> Dict[str, Any]:
        return copy.deepcopy(self.runtime)

    def get_identity_report(self) -> Dict[str, Any]:
        return {
            "persistent": {
                "organism_name": self.identity["organism_name"],
                "lineage_id": self.identity["lineage_id"],
                "birth_timestamp_utc": self.identity["birth_timestamp_utc"],
                "first_build": self.identity["first_build"],
                "current_build": self.identity["current_build"],
            },
            "runtime": {
                "runtime_instance_id": self.runtime["runtime_instance_id"],
                "runtime_started_utc": self.runtime["runtime_started_utc"],
                "active_mode": self.runtime["active_mode"],
            },
            "classification": {
                "organism_type": self.identity["organism_type"],
                "description": self.identity["description"],
            },
            "safety_boundary": copy.deepcopy(self.identity["safety_boundary"]),
        }

    def update_current_build(self, new_build: str) -> None:
        if not self.identity["safety_boundary"].get("may_update_current_build", False):
            raise IdentityUpdateError("Updating current_build is not permitted.")
        if self.is_locked_field("current_build"):
            raise IdentityUpdateError("current_build is locked.")
        self.identity["current_build"] = new_build
        self.validate_identity(self.identity)
        self.save_identity(self.identity)

    def is_locked_field(self, field_name: str) -> bool:
        return field_name in self.identity.get("identity_locked_fields", [])
