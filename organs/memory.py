"""
Memory Organ — ContinuityNode
Build: 0.5.0

Purpose:
  Store structured records from approved organs across executions,
  maintain a memory index, append memory events, generate summaries,
  and detect lightweight changes between newest and previous records.

Boundary:
  No arbitrary file ingestion. No command execution. No network access.
  No raw environment value storage. No deletion/pruning in this build.
"""

from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class MemoryError(Exception): pass
class MemoryIndexError(MemoryError): pass
class MemoryStorageError(MemoryError): pass
class MemoryEventLogError(MemoryError): pass
class MemorySummaryError(MemoryError): pass
class MemorySafetyError(MemoryError): pass


class MemoryOrgan:
    SCHEMA_VERSION = "1.0.0"
    VALID_RECORD_TYPES = ["identity_snapshot", "sensorium_snapshot", "cartography_report", "cartography_policy_snapshot", "runtime_event", "change_summary"]
    PROHIBITED_PAYLOAD_KEYS = ["raw_environment_values", "environment_values", "secret_values", "token_values", "password_values", "credential_values", "cookie_values", "raw_username"]

    def __init__(self, core_identity: Any, memory_root: str = "data/memory") -> None:
        self.core_identity = core_identity
        self.memory_root = Path(memory_root)
        self.index_path = self.memory_root / "memory_index.json"
        self.event_log_path = self.memory_root / "event_log.jsonl"
        self.snapshots_root = self.memory_root / "snapshots"
        self.identity_snapshots_dir = self.snapshots_root / "identity"
        self.sensorium_snapshots_dir = self.snapshots_root / "sensorium"
        self.cartography_snapshots_dir = self.snapshots_root / "cartography"
        self.summaries_dir = self.memory_root / "summaries"
        self.latest_summary_path = self.summaries_dir / "latest_memory_summary.json"
        self.stored_this_run = {record_type: 0 for record_type in self.VALID_RECORD_TYPES}
        self.ensure_memory_structure()
        self.memory_index = self.ensure_memory_index()
        self.validate_memory_index(self.memory_index)

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_memory_id(self, record_type: str) -> str:
        ts = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        return f"mem-{record_type.replace('_', '-')}-{ts}-{uuid.uuid4().hex[:6]}"

    def ensure_memory_structure(self) -> None:
        for directory in [self.memory_root, self.snapshots_root, self.identity_snapshots_dir, self.sensorium_snapshots_dir, self.cartography_snapshots_dir, self.summaries_dir]:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as error:
                raise MemoryStorageError(f"Could not create memory directory: {error}") from error

    def ensure_memory_index(self) -> Dict[str, Any]:
        if self.index_path.exists():
            return self.load_memory_index()
        index = self.create_default_memory_index()
        self.save_memory_index(index)
        self.append_event({"event_type": "memory_index_created", "memory_index_path": str(self.index_path)})
        return index

    def create_default_memory_index(self) -> Dict[str, Any]:
        identity = self.core_identity.get_identity_report()
        persistent = identity["persistent"]
        now = self.utc_now_iso()
        return {"schema_version": self.SCHEMA_VERSION, "memory_created_utc": now, "last_updated_utc": now, "organism_name": persistent["organism_name"], "lineage_id": persistent["lineage_id"], "records_count": 0, "records": [], "safety_boundary": self.get_safety_boundary()}

    def load_memory_index(self) -> Dict[str, Any]:
        try:
            with self.index_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise MemoryIndexError(f"memory_index.json could not be parsed: {error}") from error
        except OSError as error:
            raise MemoryIndexError(f"memory_index.json could not be read: {error}") from error
        if not isinstance(data, dict):
            raise MemoryIndexError("memory_index.json must contain a JSON object.")
        return data

    def save_memory_index(self, index: Dict[str, Any]) -> None:
        self.validate_memory_index(index)
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            with self.index_path.open("w", encoding="utf-8") as file:
                json.dump(index, file, indent=2, sort_keys=False)
                file.write("\n")
        except OSError as error:
            raise MemoryIndexError(f"Could not save memory_index.json: {error}") from error

    def validate_memory_index(self, index: Dict[str, Any]) -> bool:
        for field in ["schema_version", "memory_created_utc", "last_updated_utc", "organism_name", "lineage_id", "records_count", "records", "safety_boundary"]:
            if field not in index:
                raise MemoryIndexError(f"Missing memory index field: {field}")
        if not isinstance(index["records"], list):
            raise MemoryIndexError("memory_index records must be a list.")
        if index["records_count"] != len(index["records"]):
            raise MemoryIndexError("records_count does not match records length.")
        for flag in ["may_scan_arbitrary_folders", "may_ingest_private_documents_automatically", "may_store_raw_environment_values", "may_store_secrets", "may_execute_commands", "may_access_network", "may_delete_historical_records", "may_modify_source_organ_outputs"]:
            if index["safety_boundary"].get(flag) is True:
                raise MemorySafetyError(f"Memory safety flag must be false: {flag}")
        return True

    def append_event(self, event: Dict[str, Any]) -> None:
        payload = {"timestamp_utc": self.utc_now_iso(), "organ": "MemoryOrgan", **event}
        try:
            self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.event_log_path.open("a", encoding="utf-8") as file:
                json.dump(payload, file, sort_keys=False)
                file.write("\n")
        except OSError as error:
            raise MemoryEventLogError(f"Could not append memory event: {error}") from error

    def store_identity_snapshot(self, identity_report: Dict[str, Any]) -> Dict[str, Any]:
        return self.store_json_record("identity_snapshot", "CoreIdentityOrgan", "data/identity.json", identity_report)

    def store_sensorium_snapshot(self, sensorium_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        return self.store_json_record("sensorium_snapshot", "SensoriumOrgan", "data/sensorium_snapshot.json", sensorium_snapshot)

    def store_cartography_report(self, cartography_report: Dict[str, Any]) -> Dict[str, Any]:
        return self.store_json_record("cartography_report", "NetworkCartographyOrgan", "data/network_cartography_report.json", cartography_report)

    def store_json_record(self, record_type: str, source_organ: str, source_file: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if record_type not in self.VALID_RECORD_TYPES:
            raise MemoryStorageError(f"Unsupported memory record type: {record_type}")
        if not isinstance(payload, dict):
            raise MemoryStorageError("Memory payload must be a dictionary.")
        self.validate_payload_safety(payload)
        previous = self.get_latest_record(record_type)
        memory_id = self.generate_memory_id(record_type)
        created = self.utc_now_iso()
        target_dir = self.get_storage_directory_for_record_type(record_type)
        stored_file = target_dir / f"{memory_id}.json"
        identity = self.core_identity.get_identity_report()
        runtime, persistent = identity["runtime"], identity["persistent"]
        summary = self.summarize_record(record_type, payload)
        wrapper = {
            "schema_version": self.SCHEMA_VERSION,
            "memory_id": memory_id,
            "record_type": record_type,
            "source_organ": source_organ,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_file": source_file,
            "stored_file": str(stored_file),
            "created_utc": created,
            "payload": copy.deepcopy(payload),
            "summary": summary,
            "previous_record_memory_id": previous.get("memory_id") if previous else None,
            "lightweight_diff_from_previous": self.compare_record_summaries(previous.get("summary") if previous else None, summary),
        }
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            with stored_file.open("w", encoding="utf-8") as file:
                json.dump(wrapper, file, indent=2, sort_keys=False)
                file.write("\n")
        except OSError as error:
            raise MemoryStorageError(f"Could not store memory record: {error}") from error
        metadata = {k: wrapper[k] for k in ["memory_id", "record_type", "source_organ", "source_runtime_instance_id", "source_lineage_id", "source_file", "stored_file", "created_utc", "summary"]}
        self.update_memory_index(metadata)
        self.stored_this_run[record_type] = self.stored_this_run.get(record_type, 0) + 1
        self.append_event({"event_type": "memory_record_stored", "memory_id": memory_id, "record_type": record_type, "source_organ": source_organ, "stored_file": str(stored_file)})
        return copy.deepcopy(metadata)

    def summarize_record(self, record_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if record_type == "identity_snapshot":
            p, r = payload.get("persistent", {}), payload.get("runtime", {})
            return {"organism_name": p.get("organism_name"), "lineage_id": p.get("lineage_id"), "birth_timestamp_utc": p.get("birth_timestamp_utc"), "first_build": p.get("first_build"), "current_build": p.get("current_build"), "runtime_instance_id": r.get("runtime_instance_id"), "active_mode": r.get("active_mode")}
        if record_type == "sensorium_snapshot":
            host, py = payload.get("host", {}), payload.get("python", {})
            topo, ni, arp, nc = payload.get("topology_seed_matrix", {}), payload.get("network_interfaces", {}), payload.get("arp_table", {}), payload.get("network_connections", {})
            return {"snapshot_id": payload.get("snapshot_id"), "platform_system": host.get("platform_system"), "platform_release": host.get("platform_release"), "machine": host.get("machine"), "python_version": py.get("python_version"), "psutil_available": py.get("psutil_available"), "network_interface_count": ni.get("interface_count", 0), "ipv4_address_count": ni.get("ipv4_address_count", 0), "arp_entry_count": arp.get("entries_count", 0), "network_connection_count": nc.get("connections_count", 0), "topology_matrix_id": topo.get("matrix_id"), "topology_nodes_count": topo.get("nodes_count", 0), "topology_edges_count": topo.get("edges_count", 0), "active_scan_performed": topo.get("active_scan_performed", False)}
        if record_type == "cartography_report":
            policy, plan, topo = payload.get("policy", {}), payload.get("dry_run_plan", {}), payload.get("topology_seed_summary", {})
            return {"report_id": payload.get("report_id"), "cartography_mode": payload.get("cartography_mode"), "active_discovery_performed": payload.get("active_discovery_performed"), "cartography_enabled": policy.get("cartography_enabled"), "approved_scopes_count": plan.get("approved_scopes_count", 0), "candidate_hosts_count": plan.get("candidate_hosts_count", 0), "planned_probe_count": plan.get("planned_probe_count", 0), "topology_seed_nodes_count": topo.get("nodes_count", 0), "topology_seed_edges_count": topo.get("edges_count", 0)}
        return {"summary_available": False, "record_type": record_type}

    def update_memory_index(self, metadata: Dict[str, Any]) -> None:
        self.memory_index["records"].append(copy.deepcopy(metadata))
        self.memory_index["records_count"] = len(self.memory_index["records"])
        self.memory_index["last_updated_utc"] = self.utc_now_iso()
        self.save_memory_index(self.memory_index)

    def get_latest_record(self, record_type: str) -> Optional[Dict[str, Any]]:
        records = [r for r in self.memory_index.get("records", []) if r.get("record_type") == record_type]
        return copy.deepcopy(records[-1]) if records else None

    def get_previous_record_before_latest(self, record_type: str) -> Optional[Dict[str, Any]]:
        records = [r for r in self.memory_index.get("records", []) if r.get("record_type") == record_type]
        return copy.deepcopy(records[-2]) if len(records) >= 2 else None

    def get_latest_records_by_type(self) -> Dict[str, Optional[str]]:
        output = {}
        for record_type in self.VALID_RECORD_TYPES:
            record = self.get_latest_record(record_type)
            output[record_type] = record.get("memory_id") if record else None
        return output

    def compare_record_summaries(self, previous_summary: Optional[Dict[str, Any]], current_summary: Dict[str, Any]) -> Dict[str, Any]:
        if previous_summary is None:
            return {"previous_record_exists": False, "changed": None, "changed_keys": [], "notes": ["No previous record of this type exists."]}
        keys = set(previous_summary.keys()) | set(current_summary.keys())
        changed = [k for k in sorted(keys) if previous_summary.get(k) != current_summary.get(k)]
        return {"previous_record_exists": True, "changed": bool(changed), "changed_keys": changed}

    def summary_changed(self, previous_record: Optional[Dict[str, Any]], latest_record: Optional[Dict[str, Any]]) -> Optional[bool]:
        if previous_record is None or latest_record is None:
            return None
        return previous_record.get("summary") != latest_record.get("summary")

    def topology_summary_changed(self, previous_sensorium: Optional[Dict[str, Any]], latest_sensorium: Optional[Dict[str, Any]]) -> Optional[bool]:
        if previous_sensorium is None or latest_sensorium is None:
            return None
        prev, latest = previous_sensorium.get("summary", {}), latest_sensorium.get("summary", {})
        keys = ["topology_nodes_count", "topology_edges_count", "network_interface_count", "ipv4_address_count", "arp_entry_count", "network_connection_count"]
        return any(prev.get(k) != latest.get(k) for k in keys)

    def generate_change_markers(self) -> Dict[str, Any]:
        latest_s = self.get_latest_record("sensorium_snapshot")
        prev_s = self.get_previous_record_before_latest("sensorium_snapshot")
        latest_c = self.get_latest_record("cartography_report")
        prev_c = self.get_previous_record_before_latest("cartography_report")
        return {"sensorium_changed_since_previous": self.summary_changed(prev_s, latest_s), "topology_changed_since_previous": self.topology_summary_changed(prev_s, latest_s), "cartography_plan_changed_since_previous": self.summary_changed(prev_c, latest_c)}

    def generate_latest_memory_summary(self) -> Dict[str, Any]:
        identity = self.core_identity.get_identity_report()
        persistent = identity["persistent"]
        summary = {"schema_version": self.SCHEMA_VERSION, "summary_timestamp_utc": self.utc_now_iso(), "organism_name": persistent["organism_name"], "lineage_id": persistent["lineage_id"], "records_count": self.memory_index["records_count"], "latest_records": self.get_latest_records_by_type(), "change_markers": self.generate_change_markers(), "stored_this_run": copy.deepcopy(self.stored_this_run), "safety_summary": {"arbitrary_file_ingestion_performed": False, "raw_environment_values_stored": False, "secrets_stored": False, "network_access_performed": False, "commands_executed": False, "historical_records_deleted": False}, "notes": ["Memory Organ stores approved structured organ outputs only.", "No arbitrary file ingestion is performed.", "No pruning or deletion is performed in Build 0.5.0."]}
        self.save_latest_memory_summary(summary)
        self.append_event({"event_type": "latest_memory_summary_generated", "records_count": summary["records_count"], "latest_memory_summary_path": str(self.latest_summary_path)})
        return copy.deepcopy(summary)

    def save_latest_memory_summary(self, summary: Dict[str, Any]) -> None:
        try:
            self.summaries_dir.mkdir(parents=True, exist_ok=True)
            with self.latest_summary_path.open("w", encoding="utf-8") as file:
                json.dump(summary, file, indent=2, sort_keys=False)
                file.write("\n")
        except OSError as error:
            raise MemorySummaryError(f"Could not save latest memory summary: {error}") from error

    def get_memory_report(self, latest_summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if latest_summary is None:
            latest_summary = self.generate_latest_memory_summary()
        return {"memory_root": str(self.memory_root), "memory_created_utc": self.memory_index["memory_created_utc"], "last_updated_utc": self.memory_index["last_updated_utc"], "records_count": self.memory_index["records_count"], "stored_this_run": copy.deepcopy(self.stored_this_run), "latest_records": latest_summary["latest_records"], "change_markers": latest_summary["change_markers"], "safety_summary": latest_summary["safety_summary"]}

    def validate_payload_safety(self, payload: Dict[str, Any]) -> bool:
        found = self.find_prohibited_keys(payload)
        if found:
            raise MemorySafetyError(f"Memory payload contains prohibited key names: {found}")
        return True

    def find_prohibited_keys(self, value: Any, path: str = "") -> List[str]:
        found = []
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                if str(key) in self.PROHIBITED_PAYLOAD_KEYS:
                    found.append(child_path)
                found.extend(self.find_prohibited_keys(child, child_path))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                found.extend(self.find_prohibited_keys(item, f"{path}[{i}]"))
        return found

    def get_storage_directory_for_record_type(self, record_type: str) -> Path:
        if record_type == "identity_snapshot":
            return self.identity_snapshots_dir
        if record_type == "sensorium_snapshot":
            return self.sensorium_snapshots_dir
        if record_type in ["cartography_report", "cartography_policy_snapshot"]:
            return self.cartography_snapshots_dir
        if record_type == "change_summary":
            return self.summaries_dir
        raise MemoryStorageError(f"No storage directory configured for record type: {record_type}")

    def get_safety_boundary(self) -> Dict[str, bool]:
        return {"may_store_approved_organ_outputs": True, "may_create_memory_directories": True, "may_write_memory_index": True, "may_append_event_log": True, "may_generate_summaries": True, "may_compare_structured_records": True, "may_scan_arbitrary_folders": False, "may_ingest_private_documents_automatically": False, "may_store_raw_environment_values": False, "may_store_secrets": False, "may_execute_commands": False, "may_access_network": False, "may_delete_historical_records": False, "may_modify_source_organ_outputs": False}
