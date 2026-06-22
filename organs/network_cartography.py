from __future__ import annotations
import copy, ipaddress, json, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

class NetworkCartographyError(Exception): pass
class CartographyPolicyError(NetworkCartographyError): pass
class CartographyScopeError(NetworkCartographyError): pass
class CartographyAuditError(NetworkCartographyError): pass
class CartographyReportError(NetworkCartographyError): pass
class CartographySafetyError(NetworkCartographyError): pass

class NetworkCartographyOrgan:
    SCHEMA_VERSION = "1.0.0"
    def __init__(self, core_identity: Any, sensorium_snapshot: Dict[str, Any],
                 policy_path="data/network_cartography_policy.json",
                 report_path="data/network_cartography_report.json",
                 audit_log_path="data/network_cartography_audit_log.jsonl",
                 enabled=False):
        self.core_identity = core_identity
        self.sensorium_snapshot = sensorium_snapshot
        self.policy_path = Path(policy_path)
        self.report_path = Path(report_path)
        self.audit_log_path = Path(audit_log_path)
        self.enabled = enabled
        self.policy_created_automatically = False
        self.policy = self.ensure_policy_file()
        self.report = {}

    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    def _id(self): return f"cartography-{uuid.uuid4().hex[:8]}"

    def derive_private_scopes_from_sensorium(self):
        scopes = set()
        for iface in self.sensorium_snapshot.get("network_interfaces", {}).get("interfaces", []):
            for item in iface.get("ipv4_addresses", []):
                cidr = item.get("network_cidr")
                if cidr and item.get("is_private") and not item.get("is_loopback"):
                    try:
                        network = ipaddress.ip_network(cidr, strict=False)
                        if network.is_private:
                            scopes.add(str(network))
                    except Exception:
                        pass
        return sorted(scopes)

    def create_default_policy(self):
        return {
            "schema_version": self.SCHEMA_VERSION,
            "cartography_enabled": False,
            "requires_explicit_approval": True,
            "approved_scopes": self.derive_private_scopes_from_sensorium(),
            "allow_private_ranges_only": True,
            "max_hosts_per_run": 32,
            "max_ports_per_host": 4,
            "probe_timeout_seconds": 0.75,
            "delay_between_probes_seconds": 0.1,
            "allowed_probe_types": ["tcp_connect"],
            "allowed_tcp_ports": [80, 443],
            "disallowed_tcp_ports": [21, 23, 25, 110, 143, 3306, 5432, 6379, 9200],
            "audit_logging_enabled": True,
            "store_raw_banners": False,
            "service_fingerprinting_enabled": False,
            "credential_testing_enabled": False,
            "vulnerability_testing_enabled": False,
            "active_cartography_implemented": False,
        }

    def ensure_policy_file(self):
        if self.policy_path.exists():
            return json.loads(self.policy_path.read_text(encoding="utf-8"))
        self.policy_created_automatically = True
        policy = self.create_default_policy()
        self.policy_path.parent.mkdir(parents=True, exist_ok=True)
        self.policy_path.write_text(json.dumps(policy, indent=2) + "\n", encoding="utf-8")
        return policy

    def create_dry_run_plan(self):
        hosts = []
        for scope in self.policy.get("approved_scopes", []):
            try:
                for h in ipaddress.ip_network(scope, strict=False).hosts():
                    hosts.append(str(h))
                    if len(hosts) >= self.policy["max_hosts_per_run"]:
                        break
            except Exception:
                pass
            if len(hosts) >= self.policy["max_hosts_per_run"]:
                break
        ports = self.policy.get("allowed_tcp_ports", [])[: self.policy.get("max_ports_per_host", 4)]
        return {"plan_generated": True, "dry_run_only": True, "approved_scopes_count": len(self.policy.get("approved_scopes", [])),
                "approved_scopes": self.policy.get("approved_scopes", []), "candidate_hosts_count": len(hosts), "candidate_hosts": hosts,
                "ports_considered": ports, "planned_probe_count": len(hosts) * len(ports), "active_probes_sent": 0}

    def write_audit_event(self, event):
        if not self.policy.get("audit_logging_enabled", True): return
        payload = {"timestamp_utc": self.utc_now_iso(), "organ": "NetworkCartographyOrgan", "active_discovery_performed": False, "active_probes_sent": 0, **event}
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

    def run_cartography(self):
        self.write_audit_event({"event_type": "cartography_run_started"})
        plan = self.create_dry_run_plan()
        identity = self.core_identity.get_identity_report()
        topo = self.sensorium_snapshot.get("topology_seed_matrix", {})
        self.report = {
            "schema_version": self.SCHEMA_VERSION,
            "report_id": self._id(),
            "report_timestamp_utc": self.utc_now_iso(),
            "cartography_mode": "DRY_RUN_ONLY",
            "active_discovery_performed": False,
            "source_runtime_instance_id": identity["runtime"]["runtime_instance_id"],
            "source_lineage_id": identity["persistent"]["lineage_id"],
            "source_organism_name": identity["persistent"]["organism_name"],
            "policy_created_automatically": self.policy_created_automatically,
            "policy": copy.deepcopy(self.policy),
            "dry_run_plan": plan,
            "topology_seed_summary": {"matrix_id": topo.get("matrix_id"), "nodes_count": topo.get("nodes_count", 0), "edges_count": topo.get("edges_count", 0), "active_scan_performed": False},
            "safety_summary": {"public_ranges_excluded": True, "private_ranges_only": True, "active_cartography_implemented": False,
                               "active_probes_sent": 0, "credential_testing_performed": False, "vulnerability_testing_performed": False,
                               "service_fingerprinting_performed": False, "banner_grabbing_performed": False},
        }
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(json.dumps(self.report, indent=2) + "\n", encoding="utf-8")
        self.write_audit_event({"event_type": "cartography_run_completed", "report_id": self.report["report_id"]})
        return copy.deepcopy(self.report)

    def get_cartography_report(self):
        return copy.deepcopy(self.report or self.run_cartography())
