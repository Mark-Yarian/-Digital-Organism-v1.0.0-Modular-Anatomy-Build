"""
Network Cartography Organ — ContinuityNode
Build: 0.4.0/0.5.0

Purpose:
  Prepare controlled active discovery of approved local network ranges using
  strict scope, rate limits, timeout controls, and audit logs.

Build status:
  DRY-RUN ONLY. No active probes are sent.
"""

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
    DEFAULT_MODE = "DRY_RUN_ONLY"
    DEFAULT_ALLOWED_PROBE_TYPES = ["tcp_connect"]
    DEFAULT_ALLOWED_TCP_PORTS = [80, 443]
    DEFAULT_DISALLOWED_TCP_PORTS = [21, 23, 25, 110, 143, 3306, 5432, 6379, 9200]

    def __init__(
        self,
        core_identity: Any,
        sensorium_snapshot: Dict[str, Any],
        policy_path: str = "data/network_cartography_policy.json",
        report_path: str = "data/network_cartography_report.json",
        audit_log_path: str = "data/network_cartography_audit_log.jsonl",
        enabled: bool = False,
    ) -> None:
        self.core_identity = core_identity
        self.sensorium_snapshot = sensorium_snapshot
        self.policy_path = Path(policy_path)
        self.report_path = Path(report_path)
        self.audit_log_path = Path(audit_log_path)
        self.enabled = enabled
        self.policy_created_automatically = False
        self.policy = self.ensure_policy_file()
        self.validate_policy(self.policy)
        self.report: Dict[str, Any] = {}

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_report_id(self) -> str:
        ts = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        return f"cartography-{ts}-{uuid.uuid4().hex[:6]}"

    def ensure_policy_file(self) -> Dict[str, Any]:
        if self.policy_path.exists():
            return self.load_policy()
        policy = self.create_default_policy()
        self.policy_created_automatically = True
        self.save_policy(policy)
        return policy

    def create_default_policy(self) -> Dict[str, Any]:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "cartography_enabled": False,
            "requires_explicit_approval": True,
            "approved_scopes": self.derive_private_scopes_from_sensorium(),
            "scope_source": "sensorium_derived_private_ranges_pending_user_review",
            "allow_private_ranges_only": True,
            "max_hosts_per_run": 32,
            "max_ports_per_host": 4,
            "probe_timeout_seconds": 0.75,
            "delay_between_probes_seconds": 0.1,
            "allowed_probe_types": list(self.DEFAULT_ALLOWED_PROBE_TYPES),
            "allowed_tcp_ports": list(self.DEFAULT_ALLOWED_TCP_PORTS),
            "disallowed_tcp_ports": list(self.DEFAULT_DISALLOWED_TCP_PORTS),
            "audit_logging_enabled": True,
            "store_raw_banners": False,
            "service_fingerprinting_enabled": False,
            "credential_testing_enabled": False,
            "vulnerability_testing_enabled": False,
            "active_cartography_implemented": False,
            "notes": ["Build 0.5.0 still uses dry-run cartography only.", "No active network probes are sent."],
        }

    def load_policy(self) -> Dict[str, Any]:
        try:
            with self.policy_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise CartographyPolicyError(f"Policy could not be parsed: {error}") from error
        except OSError as error:
            raise CartographyPolicyError(f"Policy could not be read: {error}") from error
        if not isinstance(data, dict):
            raise CartographyPolicyError("Policy must contain a JSON object.")
        return data

    def save_policy(self, policy: Dict[str, Any]) -> None:
        try:
            self.policy_path.parent.mkdir(parents=True, exist_ok=True)
            with self.policy_path.open("w", encoding="utf-8") as file:
                json.dump(policy, file, indent=2, sort_keys=False)
                file.write("\n")
        except OSError as error:
            raise CartographyPolicyError(f"Could not save policy: {error}") from error

    def validate_policy(self, policy: Dict[str, Any]) -> bool:
        required = [
            "schema_version", "cartography_enabled", "requires_explicit_approval",
            "approved_scopes", "scope_source", "allow_private_ranges_only",
            "max_hosts_per_run", "max_ports_per_host", "probe_timeout_seconds",
            "delay_between_probes_seconds", "allowed_probe_types", "allowed_tcp_ports",
            "disallowed_tcp_ports", "audit_logging_enabled", "store_raw_banners",
            "service_fingerprinting_enabled", "credential_testing_enabled",
            "vulnerability_testing_enabled", "active_cartography_implemented",
        ]
        for field in required:
            if field not in policy:
                raise CartographyPolicyError(f"Missing policy field: {field}")
        if policy["requires_explicit_approval"] is not True:
            raise CartographyPolicyError("requires_explicit_approval must be true.")
        if policy["allow_private_ranges_only"] is not True:
            raise CartographyPolicyError("allow_private_ranges_only must be true.")
        for flag in ["store_raw_banners", "service_fingerprinting_enabled", "credential_testing_enabled", "vulnerability_testing_enabled", "active_cartography_implemented"]:
            if policy[flag] is not False:
                raise CartographyPolicyError(f"{flag} must be false in this build.")
        if int(policy["max_hosts_per_run"]) > 256:
            raise CartographyPolicyError("max_hosts_per_run cannot exceed 256.")
        if int(policy["max_ports_per_host"]) > 16:
            raise CartographyPolicyError("max_ports_per_host cannot exceed 16.")
        for p in policy["allowed_probe_types"]:
            if p not in self.DEFAULT_ALLOWED_PROBE_TYPES:
                raise CartographyPolicyError(f"Probe type not allowed: {p}")
        self.validate_tcp_ports(policy["allowed_tcp_ports"])
        self.validate_tcp_ports(policy["disallowed_tcp_ports"])
        self.validate_approved_scopes(policy["approved_scopes"])
        return True

    def validate_tcp_ports(self, ports: List[Any]) -> bool:
        for port in ports:
            if not isinstance(port, int) or port < 1 or port > 65535:
                raise CartographyPolicyError(f"Invalid TCP port: {port}")
        return True

    def derive_private_scopes_from_sensorium(self) -> List[str]:
        scopes = set()
        for interface in self.sensorium_snapshot.get("network_interfaces", {}).get("interfaces", []):
            for ipv4 in interface.get("ipv4_addresses", []):
                cidr = ipv4.get("network_cidr")
                if not cidr or not ipv4.get("is_private") or ipv4.get("is_loopback") or ipv4.get("is_link_local") or ipv4.get("is_multicast"):
                    continue
                try:
                    network = ipaddress.ip_network(cidr, strict=False)
                    if network.version == 4 and network.is_private:
                        scopes.add(str(network))
                except ValueError:
                    continue
        return sorted(scopes)

    def validate_approved_scopes(self, scopes: List[str]) -> bool:
        for scope in scopes:
            try:
                network = ipaddress.ip_network(scope, strict=False)
            except ValueError as error:
                raise CartographyScopeError(f"Invalid scope: {scope}") from error
            if network.version != 4 or not network.is_private or network.is_loopback or network.is_multicast or network.is_link_local:
                raise CartographyScopeError(f"Scope is not allowed: {scope}")
        return True

    def limit_scope_hosts(self, scope: str, max_hosts: int) -> List[str]:
        candidates = []
        for host in ipaddress.ip_network(scope, strict=False).hosts():
            candidates.append(str(host))
            if len(candidates) >= max_hosts:
                break
        return candidates

    def create_dry_run_plan(self) -> Dict[str, Any]:
        scopes = self.policy.get("approved_scopes", [])
        max_hosts = int(self.policy.get("max_hosts_per_run", 0))
        max_ports = int(self.policy.get("max_ports_per_host", 0))
        disallowed = set(self.policy.get("disallowed_tcp_ports", []))
        ports = [p for p in self.policy.get("allowed_tcp_ports", []) if p not in disallowed][:max_ports]
        all_hosts, scopes_plan = [], []
        for scope in scopes:
            hosts = self.limit_scope_hosts(scope, max_hosts)
            scopes_plan.append({"scope": scope, "candidate_hosts_limited_count": len(hosts), "candidate_hosts": hosts, "ports_considered": ports, "planned_probe_count": len(hosts) * len(ports), "active_probes_sent": 0})
            all_hosts.extend(hosts)
            if len(all_hosts) >= max_hosts:
                all_hosts = all_hosts[:max_hosts]
                break
        return {"plan_generated": True, "dry_run_only": True, "approved_scopes_count": len(scopes), "approved_scopes": scopes, "candidate_hosts_count": len(all_hosts), "candidate_hosts": all_hosts, "ports_considered": ports, "planned_probe_count": len(all_hosts) * len(ports), "active_probes_sent": 0}

    def run_cartography(self) -> Dict[str, Any]:
        self.validate_policy(self.policy)
        self.write_audit_event({"event_type": "cartography_run_started", "cartography_mode": self.DEFAULT_MODE, "enabled_runtime_flag": self.enabled})
        plan = self.create_dry_run_plan()
        self.write_audit_event({"event_type": "dry_run_plan_created", "candidate_hosts_count": plan["candidate_hosts_count"], "planned_probe_count": plan["planned_probe_count"], "active_probes_sent": 0})
        report = self.build_cartography_report(plan)
        self.save_report(report)
        self.write_audit_event({"event_type": "cartography_run_completed", "report_id": report["report_id"], "active_probes_sent": 0})
        self.report = report
        return copy.deepcopy(report)

    def probe_host_tcp(self, target_ip: str, target_port: int) -> Dict[str, Any]:
        raise CartographySafetyError("TCP probing is not implemented or permitted in Build 0.5.0.")

    def build_cartography_report(self, dry_run_plan: Dict[str, Any]) -> Dict[str, Any]:
        identity = self.core_identity.get_identity_report()
        persistent, runtime = identity["persistent"], identity["runtime"]
        topology_seed = self.sensorium_snapshot.get("topology_seed_matrix", {})
        report = {
            "schema_version": self.SCHEMA_VERSION,
            "report_id": self.generate_report_id(),
            "report_timestamp_utc": self.utc_now_iso(),
            "cartography_mode": self.DEFAULT_MODE,
            "active_discovery_performed": False,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_build": persistent["current_build"],
            "source_sensorium_snapshot_id": self.sensorium_snapshot.get("snapshot_id"),
            "source_topology_seed_matrix_id": topology_seed.get("matrix_id"),
            "policy_created_automatically": self.policy_created_automatically,
            "policy_path": str(self.policy_path),
            "report_path": str(self.report_path),
            "audit_log_path": str(self.audit_log_path),
            "policy": self.get_policy_summary(),
            "dry_run_plan": dry_run_plan,
            "topology_seed_summary": {"matrix_id": topology_seed.get("matrix_id"), "matrix_type": topology_seed.get("matrix_type"), "nodes_count": topology_seed.get("nodes_count", 0), "edges_count": topology_seed.get("edges_count", 0), "active_scan_performed": topology_seed.get("active_scan_performed", False)},
            "probe_summary": {"hosts_considered": dry_run_plan.get("candidate_hosts_count", 0), "hosts_probed": 0, "ports_considered": len(dry_run_plan.get("ports_considered", [])), "ports_probed": 0, "responsive_hosts": 0, "errors": 0},
            "safety_summary": {"public_ranges_excluded": True, "private_ranges_only": True, "scope_limit_enforced": True, "rate_limit_enforced": True, "active_cartography_implemented": False, "active_probes_sent": 0, "credential_testing_performed": False, "vulnerability_testing_performed": False, "service_fingerprinting_performed": False, "banner_grabbing_performed": False},
            "notes": ["Build 0.5.0 cartography remains dry-run only.", "No active probes were sent."],
        }
        self.validate_report(report)
        return report

    def get_policy_summary(self) -> Dict[str, Any]:
        fields = ["cartography_enabled", "requires_explicit_approval", "approved_scopes", "scope_source", "allow_private_ranges_only", "max_hosts_per_run", "max_ports_per_host", "probe_timeout_seconds", "delay_between_probes_seconds", "allowed_probe_types", "allowed_tcp_ports", "audit_logging_enabled", "store_raw_banners", "service_fingerprinting_enabled", "credential_testing_enabled", "vulnerability_testing_enabled", "active_cartography_implemented"]
        return {field: copy.deepcopy(self.policy.get(field)) for field in fields}

    def validate_report(self, report: Dict[str, Any]) -> bool:
        if report.get("active_discovery_performed") is not False:
            raise CartographySafetyError("Report cannot claim active discovery.")
        if report.get("safety_summary", {}).get("active_probes_sent") != 0:
            raise CartographySafetyError("Report cannot contain active probes.")
        return True

    def save_report(self, report: Dict[str, Any]) -> None:
        self.validate_report(report)
        try:
            self.report_path.parent.mkdir(parents=True, exist_ok=True)
            with self.report_path.open("w", encoding="utf-8") as file:
                json.dump(report, file, indent=2, sort_keys=False)
                file.write("\n")
        except OSError as error:
            raise CartographyReportError(f"Could not save report: {error}") from error

    def get_cartography_report(self) -> Dict[str, Any]:
        if not self.report:
            self.run_cartography()
        return copy.deepcopy(self.report)

    def write_audit_event(self, event: Dict[str, Any]) -> None:
        if self.policy and self.policy.get("audit_logging_enabled") is not True:
            return
        payload = {"timestamp_utc": self.utc_now_iso(), "organ": "NetworkCartographyOrgan", "build_behavior": "dry_run_only", "active_discovery_performed": False, "active_probes_sent": 0, **event}
        try:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_log_path.open("a", encoding="utf-8") as file:
                json.dump(payload, file, sort_keys=False)
                file.write("\n")
        except OSError as error:
            raise CartographyAuditError(f"Could not write audit event: {error}") from error
