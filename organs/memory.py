from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

class MemoryError(Exception): pass
class MemoryIndexError(MemoryError): pass
class MemoryStorageError(MemoryError): pass
class MemorySafetyError(MemoryError): pass

class MemoryOrgan:
    SCHEMA_VERSION = "1.0.0"
    def __init__(self, core_identity: Any, memory_root="data/memory"):
        self.core_identity = core_identity
        self.memory_root = Path(memory_root)
        self.index_path = self.memory_root / "memory_index.json"
        self.event_log_path = self.memory_root / "event_log.jsonl"
        self.summary_path = self.memory_root / "summaries" / "latest_memory_summary.json"
        self.memory_root.mkdir(parents=True, exist_ok=True)
        (self.memory_root / "snapshots" / "identity").mkdir(parents=True, exist_ok=True)
        (self.memory_root / "snapshots" / "sensorium").mkdir(parents=True, exist_ok=True)
        (self.memory_root / "snapshots" / "cartography").mkdir(parents=True, exist_ok=True)
        (self.memory_root / "summaries").mkdir(parents=True, exist_ok=True)
        self.stored_this_run = {"identity_snapshot":0,"sensorium_snapshot":0,"cartography_report":0}
        self.index = self.ensure_index()

    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    def _id(self, t): return f"mem-{t.replace('_','-')}-{uuid.uuid4().hex[:8]}"

    def ensure_index(self):
        if self.index_path.exists():
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        identity = self.core_identity.get_identity_report()
        idx = {"schema_version": self.SCHEMA_VERSION, "memory_created_utc": self.utc_now_iso(), "last_updated_utc": self.utc_now_iso(),
               "organism_name": identity["persistent"]["organism_name"], "lineage_id": identity["persistent"]["lineage_id"],
               "records_count": 0, "records": [], "safety_boundary": {"may_store_approved_organ_outputs": True, "may_scan_arbitrary_folders": False, "may_store_secrets": False}}
        self.index_path.write_text(json.dumps(idx, indent=2) + "\n", encoding="utf-8")
        return idx

    def append_event(self, event):
        with self.event_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"timestamp_utc": self.utc_now_iso(), "organ":"MemoryOrgan", **event}) + "\n")

    def store_json_record(self, record_type, source_organ, source_file, payload):
        mem_id = self._id(record_type)
        sub = {"identity_snapshot":"identity","sensorium_snapshot":"sensorium","cartography_report":"cartography"}[record_type]
        path = self.memory_root / "snapshots" / sub / f"{mem_id}.json"
        summary = self.summarize_record(record_type, payload)
        wrapper = {"schema_version": self.SCHEMA_VERSION, "memory_id": mem_id, "record_type": record_type, "source_organ": source_organ,
                   "source_file": source_file, "stored_file": str(path), "created_utc": self.utc_now_iso(), "payload": copy.deepcopy(payload), "summary": summary}
        path.write_text(json.dumps(wrapper, indent=2) + "\n", encoding="utf-8")
        meta = {k: wrapper[k] for k in ["memory_id","record_type","source_organ","source_file","stored_file","created_utc","summary"]}
        self.index["records"].append(meta); self.index["records_count"] = len(self.index["records"]); self.index["last_updated_utc"] = self.utc_now_iso()
        self.index_path.write_text(json.dumps(self.index, indent=2) + "\n", encoding="utf-8")
        self.stored_this_run[record_type] += 1
        self.append_event({"event_type":"memory_record_stored","memory_id":mem_id,"record_type":record_type})
        return copy.deepcopy(meta)

    def store_identity_snapshot(self, r): return self.store_json_record("identity_snapshot","CoreIdentityOrgan","data/identity.json",r)
    def store_sensorium_snapshot(self, r): return self.store_json_record("sensorium_snapshot","SensoriumOrgan","data/sensorium_snapshot.json",r)
    def store_cartography_report(self, r): return self.store_json_record("cartography_report","NetworkCartographyOrgan","data/network_cartography_report.json",r)

    def summarize_record(self, record_type, payload):
        if record_type == "identity_snapshot":
            return payload.get("persistent", {})
        if record_type == "sensorium_snapshot":
            t = payload.get("topology_seed_matrix", {})
            return {"snapshot_id": payload.get("snapshot_id"), "topology_nodes_count": t.get("nodes_count",0), "topology_edges_count": t.get("edges_count",0), "active_scan_performed": t.get("active_scan_performed", False)}
        if record_type == "cartography_report":
            p = payload.get("dry_run_plan", {})
            return {"report_id": payload.get("report_id"), "planned_probe_count": p.get("planned_probe_count",0), "active_probes_sent": p.get("active_probes_sent",0)}
        return {}

    def get_latest_record(self, record_type):
        matches = [r for r in self.index["records"] if r.get("record_type") == record_type]
        return matches[-1] if matches else None

    def generate_latest_memory_summary(self):
        latest = {t: (self.get_latest_record(t) or {}).get("memory_id") for t in self.stored_this_run}
        summary = {"schema_version": self.SCHEMA_VERSION, "summary_timestamp_utc": self.utc_now_iso(),
                   "records_count": self.index["records_count"], "latest_records": latest,
                   "change_markers": {"sensorium_changed_since_previous": None, "topology_changed_since_previous": None, "cartography_plan_changed_since_previous": None},
                   "stored_this_run": copy.deepcopy(self.stored_this_run),
                   "safety_summary": {"arbitrary_file_ingestion_performed": False, "raw_environment_values_stored": False, "secrets_stored": False, "network_access_performed": False, "commands_executed": False, "historical_records_deleted": False}}
        self.summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        self.append_event({"event_type":"latest_memory_summary_generated","records_count":summary["records_count"]})
        return copy.deepcopy(summary)

    def get_memory_report(self, latest_summary=None):
        return copy.deepcopy(latest_summary or self.generate_latest_memory_summary()) | {"memory_root": str(self.memory_root)}
