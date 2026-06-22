from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
class MetabolismError(Exception): pass
class MetabolismSafetyError(MetabolismError): pass
class MetabolismOrgan:
    def __init__(self, core_identity: Any, event_bus: Optional[Any]=None, metabolism_root="data/metabolism", runtime_mode="SINGLE_CYCLE", max_cycles=1):
        self.core_identity=core_identity; self.event_bus=event_bus; self.root=Path(metabolism_root); self.root.mkdir(parents=True, exist_ok=True)
        self.state_path=self.root/"metabolism_state.json"; self.log_path=self.root/"metabolism_cycles.jsonl"
        self.run_id=f"metabolism-run-{uuid.uuid4().hex[:8]}"; self.runtime_mode=runtime_mode; self.max_cycles=max_cycles
        if runtime_mode!="SINGLE_CYCLE" or max_cycles>1: raise MetabolismSafetyError("Build supports SINGLE_CYCLE only.")
        self.current_phase="INITIALIZED"; self.cycle_count=0; self.heartbeat_count=0; self.shutdown_recorded=False; self.finalized=False; self.phase_history=[]
        self.record_phase("BOOT","MetabolismOrgan",{"initialized":True})
    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    def _rec(self,event_type,phase,source,details):
        r={"schema_version":"1.0.0","record_id":f"metabolism-{uuid.uuid4().hex[:8]}","event_type":event_type,"timestamp_utc":self.utc_now_iso(),"run_id":self.run_id,"phase_name":phase,"source_organ":source,"cycle_count":self.cycle_count,"heartbeat_count":self.heartbeat_count,"details":details,"safety":{"commands_executed":False,"network_access_performed":False,"background_workers_started":False,"active_network_discovery_triggered":False}}
        with self.log_path.open("a",encoding="utf-8") as f: f.write(json.dumps(r)+"\n")
        if self.event_bus: self.event_bus.publish_event(event_type, "MetabolismOrgan", {"phase_name":phase})
        self.save_state(); return copy.deepcopy(r)
    def record_phase(self, phase_name, source_organ, details=None):
        self.current_phase=phase_name; self.phase_history.append({"phase_name":phase_name,"timestamp_utc":self.utc_now_iso(),"source_organ":source_organ})
        return self._rec("metabolism.phase.recorded",phase_name,source_organ,details or {})
    def heartbeat(self, phase_name=None, details=None): self.heartbeat_count+=1; return self._rec("metabolism.heartbeat",phase_name or self.current_phase,"MetabolismOrgan",details or {})
    def start_cycle(self, cycle_name, details=None):
        if self.cycle_count>=self.max_cycles: raise MetabolismSafetyError("Max cycles reached.")
        self.cycle_count+=1; return self._rec("metabolism.cycle.started",self.current_phase,"MetabolismOrgan",{"cycle_name":cycle_name, **(details or {})})
    def end_cycle(self, cycle_name, details=None): return self._rec("metabolism.cycle.ended",self.current_phase,"MetabolismOrgan",{"cycle_name":cycle_name, **(details or {})})
    def finalize_run(self, details=None): self.shutdown_recorded=True; self.finalized=True; self.current_phase="SHUTDOWN"; return self._rec("metabolism.run.finalized","SHUTDOWN","MetabolismOrgan",details or {})
    def build_state(self):
        return {"schema_version":"1.0.0","state_timestamp_utc":self.utc_now_iso(),"run_id":self.run_id,"runtime_mode":self.runtime_mode,"current_phase":self.current_phase,"cycle_count":self.cycle_count,"max_cycles":self.max_cycles,"heartbeat_count":self.heartbeat_count,"shutdown_recorded":self.shutdown_recorded,"finalized":self.finalized,"continuous_mode_enabled":False,"phase_history":self.phase_history,"metabolism_root":str(self.root),"safety_summary":{"commands_executed":False,"network_access_performed":False,"background_workers_started":False,"active_network_discovery_triggered":False,"infinite_loop_created":False}}
    def save_state(self): s=self.build_state(); self.state_path.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8"); return copy.deepcopy(s)
    def get_metabolism_report(self): return self.save_state()
