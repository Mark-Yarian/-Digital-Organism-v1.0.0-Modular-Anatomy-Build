from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
class ReflexError(Exception): pass
class ReflexOrgan:
    def __init__(self, core_identity: Any, event_bus: Optional[Any]=None, reflex_root="data/reflex"):
        self.core_identity=core_identity; self.event_bus=event_bus; self.root=Path(reflex_root); self.root.mkdir(parents=True, exist_ok=True)
        self.log_path=self.root/"reflex_log.jsonl"; self.state_path=self.root/"latest_reflex_state.json"
        self.checks_performed_this_run=0; self.reflexes_triggered_this_run=0; self.warnings_raised_this_run=0; self.safe_actions_performed_this_run=0; self.unsafe_actions_blocked_this_run=0
        self.record_reflex("state.note","info","ReflexOrgan","reflex.initialized","recorded_initialization",{})
    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    def record_reflex(self, reflex_type, severity, source_organ, condition, action_taken, details=None):
        r={"schema_version":"1.0.0","reflex_id":f"reflex-{uuid.uuid4().hex[:8]}","timestamp_utc":self.utc_now_iso(),"reflex_mode":"SAFE_LOCAL_RESPONSES","reflex_type":reflex_type,"severity":severity,"source_organ":source_organ,"condition":condition,"action_taken":action_taken,"details":details or {},"safety":{"commands_executed":False,"network_access_performed":False,"source_code_modified":False,"active_network_scanning_enabled":False}}
        with self.log_path.open("a",encoding="utf-8") as f: f.write(json.dumps(r)+"\n")
        self.reflexes_triggered_this_run += 1
        return copy.deepcopy(r)
    def ensure_directory(self, path_text, source_organ="ReflexOrgan", condition="ensure_directory", context=None):
        if not str(path_text).replace("\\","/").startswith("data"):
            self.unsafe_actions_blocked_this_run += 1
            return self.record_reflex("safety.block","warning",source_organ,condition,"unsafe_action_blocked",{"path":path_text})
        Path(path_text).mkdir(parents=True, exist_ok=True); self.safe_actions_performed_this_run += 1
        return self.record_reflex("path.ensure_directory","info",source_organ,condition,"ensured_directory_exists",{"path":path_text})
    def raise_warning(self, source_organ, condition, message, details=None, severity="warning"):
        self.warnings_raised_this_run += 1
        if self.event_bus: self.event_bus.publish_event("reflex.warning.raised","ReflexOrgan",{"condition":condition,"message":message},priority="warning")
        return self.record_reflex("warning.raise",severity,source_organ,condition,"warning_recorded",{"message":message, **(details or {})})
    def run_boot_reflex_checks(self, expected_paths: List[str], context=None):
        out=[] 
        for p in expected_paths:
            self.checks_performed_this_run += 1; out.append(self.ensure_directory(p, context=context))
        return out
    def evaluate_sensorium_reflexes(self, sensorium_snapshot, context=None):
        self.checks_performed_this_run += 1
        if sensorium_snapshot.get("topology_seed_matrix",{}).get("active_scan_performed") is not False:
            self.unsafe_actions_blocked_this_run += 1
            return [self.raise_warning("SensoriumOrgan","sensorium.active_scan_marker_detected","Sensorium active scan marker was not false.")]
        return []
    def evaluate_cartography_reflexes(self, cartography_report, context=None):
        self.checks_performed_this_run += 1
        if cartography_report.get("active_discovery_performed") is not False:
            self.unsafe_actions_blocked_this_run += 1
            return [self.raise_warning("NetworkCartographyOrgan","cartography.active_discovery_detected","Cartography active discovery detected.")]
        return []
    def evaluate_memory_reflexes(self, memory_summary, context=None): self.checks_performed_this_run += 1; return []
    def generate_latest_reflex_state(self):
        s={"schema_version":"1.0.0","state_timestamp_utc":self.utc_now_iso(),"reflex_root":str(self.root),"reflex_mode":"SAFE_LOCAL_RESPONSES","checks_performed_this_run":self.checks_performed_this_run,"reflexes_triggered_this_run":self.reflexes_triggered_this_run,"warnings_raised_this_run":self.warnings_raised_this_run,"safe_actions_performed_this_run":self.safe_actions_performed_this_run,"unsafe_actions_blocked_this_run":self.unsafe_actions_blocked_this_run,"safety_summary":{"commands_executed":False,"network_access_performed":False,"source_code_modified":False,"active_network_scanning_enabled":False}}
        self.state_path.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8"); return copy.deepcopy(s)
    def get_reflex_report(self, latest_state=None): return copy.deepcopy(latest_state or self.generate_latest_reflex_state())
