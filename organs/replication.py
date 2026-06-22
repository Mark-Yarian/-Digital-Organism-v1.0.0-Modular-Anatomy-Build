from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, List
class ReplicationError(Exception): pass
class ReplicationSafetyError(ReplicationError): pass
class ReplicationOrgan:
    def __init__(self, core_identity: Any, event_bus: Optional[Any]=None, immune: Optional[Any]=None, replication_root="data/replication"):
        self.core_identity=core_identity; self.event_bus=event_bus; self.immune=immune; self.root=Path(replication_root); self.root.mkdir(parents=True,exist_ok=True)
        self.manifest_path=self.root/"lineage_manifest.json"; self.clone_events_path=self.root/"clone_events.jsonl"; self.divergence_path=self.root/"divergence_records.jsonl"; self.report_path=self.root/"latest_replication_report.json"
        self.clone_plans_created_this_run=0; self.clone_events_written_this_run=0; self.divergence_records_written_this_run=0; self.allowed_replication_requests_this_run=0; self.denied_replication_requests_this_run=0
        self.manifest=self.ensure_manifest()
    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    def ensure_manifest(self):
        if self.manifest_path.exists(): return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        i=self.core_identity.get_identity_report()["persistent"]
        m={"schema_version":"1.0.0","manifest_created_utc":self.utc_now_iso(),"last_updated_utc":self.utc_now_iso(),"organism_name":i["organism_name"],"lineage_id":i["lineage_id"],"birth_timestamp_utc":i["birth_timestamp_utc"],"first_build":i["first_build"],"current_build":i["current_build"],"replication_mode":"MANIFEST_ONLY_SAFE_EXPORT","default_clone_mode":"CLONE_WITH_PARENT_REFERENCE","clone_plans_count":0,"divergence_records_count":0,"memory_transfer_policy":{"default_memory_transfer_mode":"SUMMARY_ONLY","copy_full_memory_snapshots":False,"copy_secrets":False},"source_file_policy":{"copy_source_code":True,"copy_identity":False,"copy_full_memory":False,"copy_secrets":False}}
        self.manifest_path.write_text(json.dumps(m,indent=2)+"\n",encoding="utf-8"); return m
    def log(self,path,event):
        with path.open("a",encoding="utf-8") as f: f.write(json.dumps(event)+"\n")
    def create_clone_manifest(self, clone_mode="CLONE_WITH_PARENT_REFERENCE", memory_transfer_mode="SUMMARY_ONLY", clone_label=None, notes: Optional[List[str]]=None):
        if self.immune:
            d=self.immune.review_action_request("replication.create_manifest","ReplicationOrgan",{"manifest_only":True,"copy_files":False,"copy_identity":False,"copy_full_memory":False,"copy_secrets":False})
            if d.get("decision")!="allow":
                self.denied_replication_requests_this_run += 1
                return {"decision":"deny","reason":d.get("reason")}
        i=self.core_identity.get_identity_report()["persistent"]
        child=f"cn-child-lineage-{uuid.uuid4().hex[:12]}"
        cm={"schema_version":"1.0.0","clone_manifest_id":f"clone-manifest-{uuid.uuid4().hex[:8]}","created_utc":self.utc_now_iso(),"replication_mode":"MANIFEST_ONLY_SAFE_EXPORT","clone_mode":clone_mode,"clone_label":clone_label,"source_organism":i,"child_candidate":{"child_lineage_candidate_id":child,"child_identity_created":False,"child_files_copied":False},"lineage_relationship":{"relationship_type":"parent_referenced_child_lineage","parent_lineage_id":i["lineage_id"],"child_lineage_candidate_id":child,"continuity_claim":"derived_from_parent_not_same_identity"},"memory_transfer_policy":{"selected_memory_transfer_mode":memory_transfer_mode,"copy_full_memory_snapshots":False,"copy_secrets":False},"notes":notes or [],"safety_summary":{"manifest_only":True,"files_copied":False,"identity_copied":False,"full_memory_copied":False,"secrets_copied":False,"raw_environment_values_copied":False,"credentials_copied":False,"commands_executed":False,"network_access_performed":False,"files_uploaded":False,"persistence_installed":False,"self_propagation_performed":False,"immune_bypassed":False}}
        self.clone_plans_created_this_run += 1; self.allowed_replication_requests_this_run += 1
        self.log(self.clone_events_path,{"timestamp_utc":self.utc_now_iso(),"event_type":"replication.clone_manifest.created","clone_manifest_id":cm["clone_manifest_id"],"safety":cm["safety_summary"]}); self.clone_events_written_this_run += 1
        self.log(self.divergence_path,{"timestamp_utc":self.utc_now_iso(),"divergence_type":"clone_candidate_created","parent_lineage_id":i["lineage_id"],"child_lineage_candidate_id":child,"safety":{"manifest_only":True,"child_created":False,"files_copied":False}}); self.divergence_records_written_this_run += 1
        self.manifest["clone_plans_count"]=self.manifest.get("clone_plans_count",0)+1; self.manifest["divergence_records_count"]=self.manifest.get("divergence_records_count",0)+1; self.manifest["last_updated_utc"]=self.utc_now_iso(); self.manifest_path.write_text(json.dumps(self.manifest,indent=2)+"\n",encoding="utf-8")
        if self.event_bus: self.event_bus.publish_event("replication.lineage.created","ReplicationOrgan",{"clone_manifest_id":cm["clone_manifest_id"],"child_lineage_candidate_id":child})
        return copy.deepcopy(cm)
    def generate_latest_replication_report(self):
        s={"schema_version":"1.0.0","report_timestamp_utc":self.utc_now_iso(),"replication_root":str(self.root),"replication_mode":"MANIFEST_ONLY_SAFE_EXPORT","default_clone_mode":"CLONE_WITH_PARENT_REFERENCE","clone_plans_created_this_run":self.clone_plans_created_this_run,"clone_events_written_this_run":self.clone_events_written_this_run,"divergence_records_written_this_run":self.divergence_records_written_this_run,"allowed_replication_requests_this_run":self.allowed_replication_requests_this_run,"denied_replication_requests_this_run":self.denied_replication_requests_this_run,"manifest_summary":{"clone_plans_count":self.manifest.get("clone_plans_count"),"divergence_records_count":self.manifest.get("divergence_records_count"),"default_memory_transfer_mode":"SUMMARY_ONLY"},"safety_summary":{"manifest_only":True,"files_copied":False,"identity_copied":False,"full_memory_copied":False,"secrets_copied":False,"raw_environment_values_copied":False,"credentials_copied":False,"commands_executed":False,"network_access_performed":False,"files_uploaded":False,"persistence_installed":False,"self_propagation_performed":False,"immune_bypassed":False}}
        self.report_path.write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8"); return copy.deepcopy(s)
    def get_replication_report(self, latest_report=None): return copy.deepcopy(latest_report or self.generate_latest_replication_report())
