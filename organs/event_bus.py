from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

class EventBusError(Exception): pass
class EventValidationError(EventBusError): pass
class EventLogError(EventBusError): pass
class EventStateError(EventBusError): pass

class EventBusOrgan:
    SCHEMA_VERSION = "1.0.0"
    def __init__(self, core_identity: Any, event_root="data/events"):
        self.core_identity = core_identity
        self.event_root = Path(event_root)
        self.event_log_path = self.event_root / "event_bus_log.jsonl"
        self.latest_state_path = self.event_root / "latest_event_bus_state.json"
        self.event_root.mkdir(parents=True, exist_ok=True)
        self.events_published_this_run = 0
        self.event_types_seen_this_run = {}
        self.source_organs_seen_this_run = {}
        self.publish_event("event_bus.initialized", "EventBusOrgan", {"event_root": str(self.event_root)})

    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    def _id(self, event_type): return f"evt-{event_type.replace('.', '-')}-{uuid.uuid4().hex[:8]}"

    def publish_event(self, event_type: str, source_organ: str, payload: Optional[Dict[str, Any]]=None, priority="info"):
        payload = payload or {}
        identity = self.core_identity.get_identity_report()
        event = {
            "schema_version": self.SCHEMA_VERSION,
            "event_id": self._id(event_type),
            "event_type": event_type,
            "priority": priority,
            "timestamp_utc": self.utc_now_iso(),
            "source_organ": source_organ,
            "source_runtime_instance_id": identity["runtime"]["runtime_instance_id"],
            "source_lineage_id": identity["persistent"]["lineage_id"],
            "source_organism_name": identity["persistent"]["organism_name"],
            "source_build": identity["persistent"]["current_build"],
            "payload": copy.deepcopy(payload),
            "safety": {
                "event_bus_performed_action": False,
                "commands_executed": False,
                "network_access_performed": False,
                "filesystem_scan_performed": False,
                "other_organs_mutated": False,
            },
        }
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.event_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        self.events_published_this_run += 1
        self.event_types_seen_this_run[event_type] = self.event_types_seen_this_run.get(event_type, 0) + 1
        self.source_organs_seen_this_run[source_organ] = self.source_organs_seen_this_run.get(source_organ, 0) + 1
        return copy.deepcopy(event)

    def count_events_in_log(self):
        if not self.event_log_path.exists(): return 0
        return sum(1 for line in self.event_log_path.read_text(encoding="utf-8").splitlines() if line.strip())

    def generate_latest_event_bus_state(self):
        identity = self.core_identity.get_identity_report()
        state = {
            "schema_version": self.SCHEMA_VERSION,
            "state_timestamp_utc": self.utc_now_iso(),
            "organism_name": identity["persistent"]["organism_name"],
            "lineage_id": identity["persistent"]["lineage_id"],
            "runtime_instance_id": identity["runtime"]["runtime_instance_id"],
            "event_root": str(self.event_root),
            "events_published_this_run": self.events_published_this_run,
            "total_events_recorded": self.count_events_in_log(),
            "known_event_types_count": len(self.event_types_seen_this_run),
            "event_types_seen_this_run": copy.deepcopy(self.event_types_seen_this_run),
            "source_organs_seen_this_run": copy.deepcopy(self.source_organs_seen_this_run),
            "subscribers_registered_count": 0,
            "safety_summary": {"actions_performed": False, "commands_executed": False, "network_access_performed": False},
        }
        self.latest_state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        return copy.deepcopy(state)

    def get_event_bus_report(self, latest_state=None):
        s = latest_state or self.generate_latest_event_bus_state()
        return copy.deepcopy(s)
