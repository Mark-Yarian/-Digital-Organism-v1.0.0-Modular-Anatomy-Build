from __future__ import annotations
import copy, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
class TelemetryError(Exception): pass
class TelemetryOrgan:
    JSON_INPUTS={"identity":"data/identity.json","sensorium":"data/sensorium_snapshot.json","cartography":"data/network_cartography_report.json","memory":"data/memory/summaries/latest_memory_summary.json","events":"data/events/latest_event_bus_state.json","metabolism":"data/metabolism/metabolism_state.json","reflex":"data/reflex/latest_reflex_state.json","immune":"data/immune/latest_immune_state.json","interface":"data/interface/latest_interface_state.json","tool_use":"data/tool_use/latest_tool_use_report.json","replication":"data/replication/latest_replication_report.json"}
    JSONL_INPUTS={"events":"data/events/event_bus_log.jsonl","memory":"data/memory/event_log.jsonl","immune":"data/immune/immune_decisions.jsonl","reflex":"data/reflex/reflex_log.jsonl","tool_use":"data/tool_use/tool_use_audit_log.jsonl","clone_events":"data/replication/clone_events.jsonl","divergence":"data/replication/divergence_records.jsonl"}
    def __init__(self, core_identity: Any, event_bus: Optional[Any]=None, immune: Optional[Any]=None, telemetry_root="data/telemetry"):
        self.core_identity=core_identity; self.event_bus=event_bus; self.immune=immune; self.root=Path(telemetry_root); self.root.mkdir(parents=True,exist_ok=True)
        self.metrics_path=self.root/"telemetry_metrics.json"; self.timeseries_path=self.root/"telemetry_timeseries.jsonl"; self.report_path=self.root/"latest_observatory_report.json"
    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    def read(self,key):
        p=Path(self.JSON_INPUTS[key]); return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    def count(self,key):
        p=Path(self.JSONL_INPUTS[key]); return sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip()) if p.exists() else 0
    def collect_telemetry(self):
        inputs={k:self.read(k) for k in self.JSON_INPUTS}
        logs={k:self.count(k) for k in self.JSONL_INPUTS}
        metrics={"schema_version":"1.0.0","telemetry_id":f"telemetry-{uuid.uuid4().hex[:8]}","telemetry_timestamp_utc":self.utc_now_iso(),"telemetry_mode":"LOCAL_OBSERVABILITY","organism":{"current_build":inputs["identity"].get("current_build"),"organism_name":inputs["identity"].get("organism_name"),"lineage_id":inputs["identity"].get("lineage_id")},
                 "memory_metrics":{"records_count":inputs["memory"].get("records_count",0)},"event_metrics":{"total_events_recorded":inputs["events"].get("total_events_recorded",0)},"metabolism_metrics":{"heartbeat_count":inputs["metabolism"].get("heartbeat_count",0)},"reflex_metrics":{"warnings_raised_this_run":inputs["reflex"].get("warnings_raised_this_run",0)},"immune_metrics":{"denied_this_run":inputs["immune"].get("denied_this_run",0)},"sensorium_metrics":{"topology_nodes_count":inputs["sensorium"].get("topology_seed_matrix",{}).get("nodes_count",0),"topology_edges_count":inputs["sensorium"].get("topology_seed_matrix",{}).get("edges_count",0)},"cartography_metrics":{"active_probes_sent":inputs["cartography"].get("dry_run_plan",{}).get("active_probes_sent",0)},"tool_use_metrics":{"executions_this_run":inputs["tool_use"].get("executions_this_run",0)},"replication_metrics":{"clone_plans_created_this_run":inputs["replication"].get("clone_plans_created_this_run",0)},"log_counts":logs,"safety_summary":{"commands_executed":False,"network_access_performed":False,"arbitrary_files_read":False,"actions_triggered":False,"decisions_made":False,"immune_bypassed":False}}
        self.metrics_path.write_text(json.dumps(metrics,indent=2)+"\n",encoding="utf-8")
        with self.timeseries_path.open("a",encoding="utf-8") as f: f.write(json.dumps({"telemetry_id":metrics["telemetry_id"],"timestamp_utc":metrics["telemetry_timestamp_utc"],"memory_records_count":metrics["memory_metrics"]["records_count"],"total_events_recorded":metrics["event_metrics"]["total_events_recorded"]})+"\n")
        report={"schema_version":"1.0.0","report_timestamp_utc":self.utc_now_iso(),"telemetry_id":metrics["telemetry_id"],"telemetry_mode":"LOCAL_OBSERVABILITY","organism":metrics["organism"],"health_summary":{"overall_status":"ok","warnings_count":0,"warnings":[]},"key_metrics":{"current_build":metrics["organism"]["current_build"],"memory_records_count":metrics["memory_metrics"]["records_count"],"total_events_recorded":metrics["event_metrics"]["total_events_recorded"],"heartbeat_count":metrics["metabolism_metrics"]["heartbeat_count"],"reflex_warnings":metrics["reflex_metrics"]["warnings_raised_this_run"],"immune_denials":metrics["immune_metrics"]["denied_this_run"],"topology_nodes_count":metrics["sensorium_metrics"]["topology_nodes_count"],"topology_edges_count":metrics["sensorium_metrics"]["topology_edges_count"],"active_probes_sent":metrics["cartography_metrics"]["active_probes_sent"]},"safety_summary":metrics["safety_summary"]}
        self.report_path.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
        if self.event_bus: self.event_bus.publish_event("telemetry.metrics.collected","TelemetryOrgan",{"telemetry_id":metrics["telemetry_id"]})
        return copy.deepcopy(report)
    def get_telemetry_report(self, observatory_report=None): return copy.deepcopy(observatory_report or self.collect_telemetry()) | {"telemetry_root": str(self.root)}
