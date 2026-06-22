from __future__ import annotations
import copy, hashlib, ipaddress, json, os, platform, socket, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

try:
    import psutil
    PSUTIL_AVAILABLE = True
except Exception:
    psutil = None
    PSUTIL_AVAILABLE = False

class SensoriumError(Exception): pass
class SensoriumSnapshotError(SensoriumError): pass
class SensoriumSafetyError(SensoriumError): pass

class SensoriumOrgan:
    SCHEMA_VERSION = "1.1.0"
    def __init__(self, core_identity: Any, snapshot_path="data/sensorium_snapshot.json", mode="READ_ONLY"):
        self.core_identity = core_identity
        self.snapshot_path = Path(snapshot_path)
        self.mode = mode.upper()
        if self.mode != "READ_ONLY":
            raise SensoriumSafetyError("Sensorium supports READ_ONLY only.")
        self.snapshot = {}

    def utc_now_iso(self): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    def _id(self): return f"sensorium-{uuid.uuid4().hex[:8]}"

    def collect_network_interfaces(self):
        interfaces = []
        if PSUTIL_AVAILABLE:
            for name, addrs in psutil.net_if_addrs().items():
                ipv4 = []
                macs = []
                for a in addrs:
                    if getattr(a, "family", None) == socket.AF_INET:
                        cidr = None
                        try:
                            cidr = str(ipaddress.ip_interface(f"{a.address}/{a.netmask}").network) if a.netmask else None
                        except Exception:
                            pass
                        ip = ipaddress.ip_address(a.address)
                        ipv4.append({"ip_address": a.address, "netmask": a.netmask, "network_cidr": cidr,
                                     "is_private": ip.is_private, "is_loopback": ip.is_loopback,
                                     "is_link_local": ip.is_link_local, "is_multicast": ip.is_multicast})
                    elif isinstance(getattr(a, "address", None), str) and ":" in a.address and len(a.address) >= 11:
                        h = hashlib.sha256(a.address.lower().encode()).hexdigest()[:24]
                        macs.append({"mac_address_stored": "hashed", "mac_address_hash": f"sha256:{h}", "raw_mac_address_stored": False})
                interfaces.append({"interface_name": name, "mac_addresses": macs, "ipv4_addresses": ipv4, "ipv6_addresses": []})
        else:
            try:
                ips = socket.gethostbyname_ex(socket.gethostname())[2]
            except Exception:
                ips = []
            interfaces.append({"interface_name": "standard_library_hostname_resolution", "mac_addresses": [], "ipv4_addresses": [
                {"ip_address": ip, "network_cidr": None, "is_private": ipaddress.ip_address(ip).is_private,
                 "is_loopback": ipaddress.ip_address(ip).is_loopback, "is_link_local": ipaddress.ip_address(ip).is_link_local,
                 "is_multicast": ipaddress.ip_address(ip).is_multicast} for ip in ips
            ], "ipv6_addresses": []})
        return {"collection_attempted": True, "psutil_available": PSUTIL_AVAILABLE, "active_scan_performed": False,
                "interface_count": len(interfaces), "ipv4_address_count": sum(len(i["ipv4_addresses"]) for i in interfaces),
                "interfaces": interfaces}

    def build_topology(self, ni):
        nodes = [{"node_id": "local-host", "node_type": "self", "evidence": ["local_interface"]}]
        edges = []
        for iface in ni.get("interfaces", []):
            for ip in iface.get("ipv4_addresses", []):
                cidr = ip.get("network_cidr")
                if cidr:
                    nid = f"network-{cidr}"
                    nodes.append({"node_id": nid, "node_type": "derived_local_subnet", "network_cidr": cidr, "evidence": ["derived_subnet"]})
                    edges.append({"source": "local-host", "target": nid, "relationship": "attached_to_derived_subnet"})
        return {"matrix_id": f"topology-seed-{uuid.uuid4().hex[:8]}", "matrix_type": "passive_observation_seed",
                "active_scan_performed": False, "subnet_scan_performed": False, "port_scan_performed": False,
                "service_fingerprinting_performed": False, "nodes_count": len(nodes), "edges_count": len(edges),
                "nodes": nodes, "edges": edges}

    def create_snapshot(self):
        identity = self.core_identity.get_identity_report()
        ni = self.collect_network_interfaces()
        topo = self.build_topology(ni)
        env_keys = list(os.environ.keys())
        sensitive_markers = sorted({frag for frag in ["TOKEN","SECRET","KEY","PASSWORD","AUTH","CREDENTIAL","COOKIE"] for k in env_keys if frag in k.upper()})
        self.snapshot = {
            "schema_version": self.SCHEMA_VERSION,
            "snapshot_id": self._id(),
            "snapshot_timestamp_utc": self.utc_now_iso(),
            "source_runtime_instance_id": identity["runtime"]["runtime_instance_id"],
            "source_lineage_id": identity["persistent"]["lineage_id"],
            "source_organism_name": identity["persistent"]["organism_name"],
            "sensorium_mode": self.mode,
            "host": {"platform_system": platform.system(), "platform_release": platform.release(), "machine": platform.machine()},
            "python": {"python_version": platform.python_version(), "implementation": platform.python_implementation(), "psutil_available": PSUTIL_AVAILABLE},
            "environment": {"environment_variable_count": len(env_keys), "raw_environment_values_stored": False,
                            "sensitive_environment_keys_detected": bool(sensitive_markers),
                            "sensitive_environment_categories_detected": sensitive_markers},
            "network_interfaces": ni,
            "arp_table": {"collection_attempted": False, "active_scan_performed": False, "entries_count": 0, "entries": []},
            "network_connections": {"collection_attempted": False, "active_connections_initiated": False, "process_names_stored": False, "connections_count": 0, "connections": []},
            "topology_seed_matrix": topo,
            "safety_boundary": {"may_execute_active_network_scans": False, "may_store_raw_environment_values": False, "may_store_raw_username": False, "may_store_raw_mac_addresses": False},
        }
        return copy.deepcopy(self.snapshot)

    def create_and_save_snapshot(self):
        s = self.create_snapshot()
        self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self.snapshot_path.write_text(json.dumps(s, indent=2) + "\n", encoding="utf-8")
        return copy.deepcopy(s)

    def get_sensorium_report(self):
        if not self.snapshot: self.create_snapshot()
        s = self.snapshot
        return {
            "snapshot_id": s["snapshot_id"],
            "snapshot_timestamp_utc": s["snapshot_timestamp_utc"],
            "sensorium_mode": s["sensorium_mode"],
            "platform_system": s["host"]["platform_system"],
            "platform_release": s["host"]["platform_release"],
            "machine": s["host"]["machine"],
            "python_version": s["python"]["python_version"],
            "python_implementation": s["python"]["implementation"],
            "psutil_available": s["python"]["psutil_available"],
            "network_interface_count": s["network_interfaces"]["interface_count"],
            "ipv4_address_count": s["network_interfaces"]["ipv4_address_count"],
            "arp_entry_count": s["arp_table"]["entries_count"],
            "network_connection_count": s["network_connections"]["connections_count"],
            "topology_node_count": s["topology_seed_matrix"]["nodes_count"],
            "topology_edge_count": s["topology_seed_matrix"]["edges_count"],
            "active_network_scan_performed": False,
        }

    def get_snapshot(self): return copy.deepcopy(self.snapshot)
