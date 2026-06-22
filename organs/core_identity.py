from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

class CoreIdentityError(Exception): pass
class IdentityLoadError(CoreIdentityError): pass
class IdentityValidationError(CoreIdentityError): pass
class IdentityUpdateError(CoreIdentityError): pass

class CoreIdentityOrgan:
    SCHEMA_VERSION = "1.0.0"
    ORGANISM_TYPE = "experimental_software_and_digital_organism_research_model"
    DESCRIPTION = ("ContinuityNode is an experimental software system and digital organism "
                   "research model designed to study persistent identity, runtime instancing, "
                   "continuity tracking, and controlled divergence across executions.")
    LOCKED_FIELDS = ["organism_name", "birth_timestamp_utc", "lineage_id", "first_build"]
    ALLOWED_MODES = ["OBSERVE", "DIAGNOSTIC", "EXPERIMENTAL", "MAINTENANCE", "REPLICATION_TEST"]

    def __init__(self, identity_path="data/identity.json", build_version="1.3.0",
                 default_name="ContinuityNode", default_mode="OBSERVE"):
        self.identity_path = Path(identity_path)
        self.build_version = build_version
        self.default_name = default_name
        self.default_mode = default_mode.upper()
        self.identity = self.ensure_identity_file()
        self.validate_identity(self.identity)
        if self.identity.get("current_build") != self.build_version:
            self.identity["current_build"] = self.build_version
            self.save_identity(self.identity)
        self.identity["last_identity_validation_utc"] = self.utc_now_iso()
        self.save_identity(self.identity)
        self.runtime = self.create_runtime_identity(self.default_mode)

    def utc_now_iso(self):
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def ensure_identity_file(self):
        if self.identity_path.exists():
            try:
                return json.loads(self.identity_path.read_text(encoding="utf-8"))
            except Exception as e:
                raise IdentityLoadError(str(e)) from e
        identity = {
            "schema_version": self.SCHEMA_VERSION,
            "organism_name": self.default_name,
            "organism_type": self.ORGANISM_TYPE,
            "description": self.DESCRIPTION,
            "birth_timestamp_utc": self.utc_now_iso(),
            "lineage_id": f"cn-lineage-{uuid.uuid4().hex[:12]}",
            "first_build": self.build_version,
            "current_build": self.build_version,
            "default_runtime_mode": self.default_mode,
            "created_by": "User",
            "created_with": "Python",
            "identity_locked_fields": list(self.LOCKED_FIELDS),
            "allowed_runtime_modes": list(self.ALLOWED_MODES),
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
        self.save_identity(identity)
        return identity

    def save_identity(self, identity: Dict[str, Any]):
        self.identity_path.parent.mkdir(parents=True, exist_ok=True)
        self.identity_path.write_text(json.dumps(identity, indent=2) + "\n", encoding="utf-8")

    def validate_identity(self, identity):
        for field in ["schema_version", "organism_name", "birth_timestamp_utc", "lineage_id", "first_build",
                      "current_build", "default_runtime_mode", "identity_locked_fields", "allowed_runtime_modes",
                      "safety_boundary"]:
            if field not in identity:
                raise IdentityValidationError(f"Missing identity field: {field}")
        for field in self.LOCKED_FIELDS:
            if field not in identity.get("identity_locked_fields", []):
                raise IdentityValidationError(f"Locked field missing: {field}")
        return True

    def create_runtime_identity(self, mode):
        mode = mode.upper()
        if mode not in [m.upper() for m in self.identity["allowed_runtime_modes"]]:
            raise IdentityValidationError(f"Mode not allowed: {mode}")
        ts = self.utc_now_iso().replace("-", "").replace(":", "")
        return {
            "runtime_instance_id": f"cn-run-{ts}-{uuid.uuid4().hex[:6]}",
            "runtime_started_utc": self.utc_now_iso(),
            "active_mode": mode,
            "source_lineage_id": self.identity["lineage_id"],
            "source_organism_name": self.identity["organism_name"],
            "build": self.identity["current_build"],
        }

    def get_identity_report(self):
        return {
            "persistent": {
                "organism_name": self.identity["organism_name"],
                "lineage_id": self.identity["lineage_id"],
                "birth_timestamp_utc": self.identity["birth_timestamp_utc"],
                "first_build": self.identity["first_build"],
                "current_build": self.identity["current_build"],
            },
            "runtime": copy.deepcopy(self.runtime),
            "classification": {
                "organism_type": self.identity["organism_type"],
                "description": self.identity["description"],
            },
            "safety_boundary": copy.deepcopy(self.identity["safety_boundary"]),
        }

    def get_persistent_identity(self): return copy.deepcopy(self.identity)
    def get_runtime_identity(self): return copy.deepcopy(self.runtime)
