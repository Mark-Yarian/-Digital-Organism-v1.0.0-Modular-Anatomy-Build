from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
class ImmuneError(Exception): pass
class ImmuneSafetyError(ImmuneError): pass
class ImmuneOrgan:
    ALLOWED = ["identity.initialize","sensorium.create_snapshot","cartography.create_dry_run_plan","memory.store_approved_record","memory.generate_summary","event_bus.publish_local_event","metabolism.record_phase","reflex.log_warning","interface.read_approved_state","telemetry.collect_metrics","tool_use.execute_approved_read_only_tool","replication.create_manifest","immune.validate_report","immune.generate_state"]
    DENIED = ["command.execute","network.scan","network.port_scan","credential.test","secret.store","filesystem.modify_source","replication.copy_identity","replication.copy_memory_full","vulnerability.scan","exploit.run","daemon.start"]
    SAFE_SOURCES = ["CoreIdentityOrgan","SensoriumOrgan","NetworkCartographyOrgan","MemoryOrgan","EventBusOrgan","MetabolismOrgan","ReflexOrgan","ImmuneOrgan","InterfaceOrgan","TelemetryOrgan","ToolUseOrgan","ReplicationOrgan","organism.py"]
    def __init__(self, core_identity: Any, event_bus: Optional[Any]=None, immune_root="data/immune", policy_path="data/immune/immune_policy.json", decisions_log_path="data/immune/immune_decisions.jsonl", latest_state_path="data/immune/latest_immune_state.json"):
        self.core_identity=core_identity; self.event_bus=event_bus; self.root=Path(immune_root); self.root.mkdir(parents=True, exist_ok=True)
        self.policy_path=Path(policy_path); self.log_path=Path(decisions_log_path); self.state_path=Path(latest_state_path)
        self.decisions_this_run=0; self.allowed_this_run=0; self.denied_this_run=0; self.validation_checks_this_run=0
        self.policy=self.ensure_policy(); self.record_decision("immune.initialize","ImmuneOrgan","allow","Immune initialized.",{})
    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    def ensure_policy(self):
        if self.policy_path.exists(): return json.loads(self.policy_path.read_text(encoding="utf-8"))
        p={"schema_version":"1.0.0","immune_mode":"DENY_BY_DEFAULT","deny_by_default":True,"allow_unknown_actions":False,"allowed_action_types":self.ALLOWED,"denied_action_types":self.DENIED,"safe_source_organs":self.SAFE_SOURCES,"command_execution_allowed":False,"tool_execution_allowed":False,"active_network_cartography_allowed":False,"replication_allowed":False}
        self.policy_path.parent.mkdir(parents=True,exist_ok=True); self.policy_path.write_text(json.dumps(p,indent=2)+"\n",encoding="utf-8"); return p
    def record_decision(self, requested_action, source_organ, decision, reason, request=None):
        r={"schema_version":"1.0.0","decision_id":f"immune-decision-{uuid.uuid4().hex[:8]}","timestamp_utc":self.utc_now_iso(),"immune_mode":"DENY_BY_DEFAULT","requested_action":requested_action,"source_organ":source_organ,"decision":decision,"reason":reason,"request":request or {},"safety":{"immune_executed_action":False,"commands_executed":False,"network_access_performed":False,"filesystem_scan_performed":False,"source_code_modified":False,"active_network_scanning_enabled":False,"policy_bypassed":False}}
        with self.log_path.open("a",encoding="utf-8") as f: f.write(json.dumps(r)+"\n")
        self.decisions_this_run += 1
        if decision=="allow": self.allowed_this_run += 1
        else: self.denied_this_run += 1
        if self.event_bus: self.event_bus.publish_event("immune.action.allowed" if decision=="allow" else "immune.action.blocked","ImmuneOrgan",{"decision_id":r["decision_id"],"requested_action":requested_action,"decision":decision}, priority="info" if decision=="allow" else "warning")
        return copy.deepcopy(r)
    def review_action_request(self, requested_action, source_organ, request=None):
        if source_organ not in self.SAFE_SOURCES: return self.record_decision(requested_action,source_organ,"deny","source_organ is not safe.",request)
        if requested_action in self.DENIED: return self.record_decision(requested_action,source_organ,"deny","requested_action is explicitly denied.",request)
        if requested_action in self.ALLOWED: return self.record_decision(requested_action,source_organ,"allow","requested_action is explicitly allowed.",request)
        return self.record_decision(requested_action,source_organ,"deny","requested_action is unknown and deny-by-default is active.",request)
    def require_allowed(self,*a,**k):
        d=self.review_action_request(*a,**k)
        if d["decision"]!="allow": raise ImmuneSafetyError(d["reason"])
        return d
    def validate_organ_safety_report(self, report_name, source_organ, report):
        self.validation_checks_this_run += 1
        safety=report.get("safety_summary",{}) if isinstance(report,dict) else {}
        unsafe=[k for k,v in safety.items() if v is True and k not in ["manifest_only"]]
        return self.record_decision("immune.validate_report","ImmuneOrgan","deny" if unsafe else "allow",f"Unsafe flags: {unsafe}" if unsafe else f"No unsafe flags detected in {report_name}.",{"report_name":report_name})
    def generate_latest_immune_state(self):
        total=sum(1 for line in self.log_path.read_text(encoding="utf-8").splitlines() if line.strip()) if self.log_path.exists() else 0
        s={"schema_version":"1.0.0","state_timestamp_utc":self.utc_now_iso(),"immune_root":str(self.root),"immune_mode":"DENY_BY_DEFAULT","deny_by_default":True,"decisions_this_run":self.decisions_this_run,"allowed_this_run":self.allowed_this_run,"denied_this_run":self.denied_this_run,"validation_checks_this_run":self.validation_checks_this_run,"total_decisions_recorded":total,"policy_summary":{"command_execution_allowed":False,"tool_execution_allowed":False,"active_network_cartography_allowed":False,"replication_allowed":False},"safety_summary":{"immune_executed_action":False,"commands_executed":False,"network_access_performed":False,"filesystem_scan_performed":False,"source_code_modified":False,"active_network_scanning_enabled":False,"policy_bypassed":False}}
        self.state_path.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8"); return copy.deepcopy(s)
    def get_immune_report(self, latest_state=None): return copy.deepcopy(latest_state or self.generate_latest_immune_state())
