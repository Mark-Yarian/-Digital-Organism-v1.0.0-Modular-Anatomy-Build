from __future__ import annotations
import copy, json, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List
class InterfaceError(Exception): pass
class InterfaceCommandError(InterfaceError): pass
class InterfaceReadError(InterfaceError): pass
class InterfaceOrgan:
    VALID_COMMANDS=["run","status","identity","sensorium","cartography","memory","events","metabolism","reflex","immune","safety","telemetry","tool-use","replication","help"]
    APPROVED_READ_PATHS={"identity":"data/identity.json","sensorium":"data/sensorium_snapshot.json","cartography":"data/network_cartography_report.json","memory":"data/memory/summaries/latest_memory_summary.json","events":"data/events/latest_event_bus_state.json","metabolism":"data/metabolism/metabolism_state.json","reflex":"data/reflex/latest_reflex_state.json","immune":"data/immune/latest_immune_state.json","telemetry":"data/telemetry/latest_observatory_report.json","tool_use":"data/tool_use/latest_tool_use_report.json","replication":"data/replication/latest_replication_report.json"}
    def __init__(self, core_identity: Any, event_bus: Optional[Any]=None, immune: Optional[Any]=None, interface_root="data/interface"):
        self.core_identity=core_identity; self.event_bus=event_bus; self.immune=immune; self.root=Path(interface_root); self.root.mkdir(parents=True,exist_ok=True)
        self.log_path=self.root/"interface_log.jsonl"; self.state_path=self.root/"latest_interface_state.json"; self.commands_handled_this_run=0; self.reads_performed_this_run=0; self.invalid_commands_this_run=0
    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    def parse_command(self, argv: Optional[List[str]]=None):
        argv=argv or sys.argv
        return "run" if len(argv)<2 else argv[1].strip().lower()
    def safe_read_json(self,key,missing_ok=False):
        if key not in self.APPROVED_READ_PATHS: raise InterfaceReadError(f"Unapproved read key: {key}")
        p=Path(self.APPROVED_READ_PATHS[key])
        if not p.exists():
            if missing_ok: return {}
            raise InterfaceReadError(f"Missing approved file: {p}")
        self.reads_performed_this_run += 1
        return json.loads(p.read_text(encoding="utf-8"))
    def handle_command(self, command, runtime_context=None):
        if command not in self.VALID_COMMANDS:
            self.invalid_commands_this_run+=1; raise InterfaceCommandError(f"Invalid command: {command}")
        self.commands_handled_this_run += 1
        if command=="help": return {"command":"help","valid_commands":self.VALID_COMMANDS}
        if command=="run": return {"command":"run","message":"Run handled by organism.py"}
        if command=="status":
            identity=self.safe_read_json("identity",True); return {"command":"status","organism_name":identity.get("organism_name"),"current_build":identity.get("current_build")}
        key = "tool_use" if command=="tool-use" else command
        return {"command":command, "summary": self.safe_read_json(key, True)}
    def print_command_result(self,result): print(json.dumps(result,indent=2))
    def generate_latest_interface_state(self):
        s={"schema_version":"1.0.0","state_timestamp_utc":self.utc_now_iso(),"interface_root":str(self.root),"interface_mode":"LOCAL_CLI_READ_ONLY","valid_commands":self.VALID_COMMANDS,"commands_handled_this_run":self.commands_handled_this_run,"reads_performed_this_run":self.reads_performed_this_run,"invalid_commands_this_run":self.invalid_commands_this_run,"safety_summary":{"commands_executed":False,"network_access_performed":False,"arbitrary_files_read":False,"source_code_modified":False,"memory_deleted":False,"active_cartography_enabled":False,"immune_bypassed":False}}
        self.state_path.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8"); return copy.deepcopy(s)
    def get_interface_report(self, latest_state=None): return copy.deepcopy(latest_state or self.generate_latest_interface_state())
