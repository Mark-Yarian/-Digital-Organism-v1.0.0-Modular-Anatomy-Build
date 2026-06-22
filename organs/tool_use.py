from __future__ import annotations
import copy, json, platform, shutil, subprocess, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
class ToolUseError(Exception): pass
class ToolUseSafetyError(ToolUseError): pass
class ToolUseOrgan:
    TOOLS={"Windows":{"arp_table":["arp","-a"],"ip_config":["ipconfig","/all"]},"Linux":{"ip_addresses":["ip","addr"],"ip_routes":["ip","route"],"ip_neighbors":["ip","neigh"]},"Darwin":{"ifconfig":["ifconfig"],"arp_table":["arp","-a"]}}
    def __init__(self, core_identity: Any, event_bus: Optional[Any]=None, immune: Optional[Any]=None, tool_use_root="data/tool_use"):
        self.core_identity=core_identity; self.event_bus=event_bus; self.immune=immune; self.root=Path(tool_use_root); self.root.mkdir(parents=True,exist_ok=True)
        self.policy_path=self.root/"tool_use_policy.json"; self.audit_log_path=self.root/"tool_use_audit_log.jsonl"; self.report_path=self.root/"latest_tool_use_report.json"
        self.requests_this_run=0; self.allowed_requests_this_run=0; self.denied_requests_this_run=0; self.executions_this_run=0; self.successful_executions_this_run=0; self.failed_executions_this_run=0; self.timeouts_this_run=0; self.output_truncations_this_run=0
        self.policy=self.ensure_policy()
    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    def ensure_policy(self):
        if self.policy_path.exists(): return json.loads(self.policy_path.read_text(encoding="utf-8"))
        p={"schema_version":"1.0.0","tool_mode":"IMMUNE_GATED_READ_ONLY_LOCAL_TOOLS","enabled":True,"requires_immune_approval":True,"local_only":True,"read_only_only":True,"allow_shell":False,"allow_arbitrary_command_strings":False,"timeout_seconds":3,"output_limit_chars":25000,"allowed_tools_by_os":self.TOOLS}
        self.policy_path.write_text(json.dumps(p,indent=2)+"\n",encoding="utf-8"); return p
    def audit(self,event_type,tool_name,decision,status,details=None):
        r={"schema_version":"1.0.0","tool_use_event_id":f"tool-use-{uuid.uuid4().hex[:8]}","timestamp_utc":self.utc_now_iso(),"tool_mode":"IMMUNE_GATED_READ_ONLY_LOCAL_TOOLS","event_type":event_type,"tool_name":tool_name,"decision":decision,"result_status":status,"details":details or {},"safety":{"shell_used":False,"arbitrary_command_string_used":False,"user_supplied_executable_used":False,"network_scanner_used":False,"offensive_tool_used":False,"credential_tool_used":False,"filesystem_modified":False,"background_process_started":False,"immune_bypassed":False}}
        with self.audit_log_path.open("a",encoding="utf-8") as f: f.write(json.dumps(r)+"\n")
        return copy.deepcopy(r)
    def run_tool(self, tool_name, request_context=None):
        self.requests_this_run += 1
        cmd=self.policy["allowed_tools_by_os"].get(platform.system(),{}).get(tool_name)
        if not cmd or shutil.which(cmd[0]) is None:
            self.denied_requests_this_run += 1; return self.audit("tool_use.request.denied",tool_name,"deny","denied",{"reason":"not allowed or unavailable"})
        if self.immune:
            d=self.immune.review_action_request("tool_use.execute_approved_read_only_tool","ToolUseOrgan",{"tool_name":tool_name,"shell":False})
            if d.get("decision")!="allow":
                self.denied_requests_this_run += 1; return self.audit("tool_use.request.denied_by_immune",tool_name,"deny","denied_by_immune",{"reason":d.get("reason")})
        self.allowed_requests_this_run += 1; self.executions_this_run += 1
        try:
            c=subprocess.run(cmd,shell=False,capture_output=True,text=True,timeout=3,encoding="utf-8",errors="replace")
            self.successful_executions_this_run += 1
            return self.audit("tool_use.command.executed",tool_name,"allow","completed",{"return_code":c.returncode,"stdout":c.stdout[:25000],"stderr":c.stderr[:25000],"stdout_truncated":len(c.stdout)>25000,"stderr_truncated":len(c.stderr)>25000})
        except subprocess.TimeoutExpired:
            self.timeouts_this_run += 1; self.failed_executions_this_run += 1
            return self.audit("tool_use.command.timeout",tool_name,"allow","timeout",{})
    def generate_latest_tool_use_report(self):
        s={"schema_version":"1.0.0","report_timestamp_utc":self.utc_now_iso(),"tool_use_root":str(self.root),"tool_mode":"IMMUNE_GATED_READ_ONLY_LOCAL_TOOLS","enabled":self.policy["enabled"],"requires_immune_approval":self.policy["requires_immune_approval"],"requests_this_run":self.requests_this_run,"allowed_requests_this_run":self.allowed_requests_this_run,"denied_requests_this_run":self.denied_requests_this_run,"executions_this_run":self.executions_this_run,"successful_executions_this_run":self.successful_executions_this_run,"failed_executions_this_run":self.failed_executions_this_run,"timeouts_this_run":self.timeouts_this_run,"output_truncations_this_run":self.output_truncations_this_run,"current_os":platform.system(),"available_tools_for_current_os":sorted(self.policy["allowed_tools_by_os"].get(platform.system(),{}).keys()),"safety_summary":{"shell_used":False,"arbitrary_command_string_used":False,"filesystem_modified":False,"immune_bypassed":False}}
        self.report_path.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8"); return copy.deepcopy(s)
    def get_tool_use_report(self, latest_report=None): return copy.deepcopy(latest_report or self.generate_latest_tool_use_report())
