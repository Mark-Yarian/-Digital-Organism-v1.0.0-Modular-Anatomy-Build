"""
Sensorium Organ — ContinuityNode
Build compatibility: 0.2.0 through 0.5.0

Purpose:
  Collect a safe, read-only runtime/environment snapshot and passive
  network topology seed matrix.

Boundary:
  No active network scanning. No ping sweeps. No port scans.
"""

from __future__ import annotations
import copy, hashlib, ipaddress, json, os, platform, re, shutil, socket, subprocess, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil  # type: ignore
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore
    PSUTIL_AVAILABLE = False


class SensoriumError(Exception): pass
class SensoriumSnapshotError(SensoriumError): pass
class SensoriumSafetyError(SensoriumError): pass


class SensoriumOrgan:
    SCHEMA_VERSION = "1.1.0"
    ALLOWED_MODES = ["READ_ONLY"]
    COMMANDS_TO_CHECK = [
        "python", "python3", "pip", "pip3", "git", "where", "which",
        "ipconfig", "ifconfig", "tracert", "traceroute", "ping", "netstat",
        "nslookup", "powershell", "pwsh", "cmd", "bash", "sh", "arp", "ip", "route",
    ]
    SAFE_ENVIRONMENT_KEYS = [
        "OS", "PROCESSOR_ARCHITECTURE", "COMPUTERNAME", "USERDOMAIN",
        "USERNAME", "USER", "HOME", "SHELL", "PATH", "PYTHONPATH",
        "VIRTUAL_ENV", "TERM", "LANG",
    ]
    SENSITIVE_ENVIRONMENT_KEY_FRAGMENTS = [
        "TOKEN", "SECRET", "KEY", "PASSWORD", "PASS", "AUTH", "CREDENTIAL",
        "COOKIE", "SESSION", "PRIVATE", "CERT", "DATABASE_URL", "DB_URL",
        "CONNECTION_STRING", "ACCESS", "BEARER",
    ]
    READ_ONLY_NETWORK_COMMANDS_BY_OS = {
        "Windows": [["arp", "-a"]],
        "Linux": [["ip", "neigh"], ["arp", "-n"]],
        "Darwin": [["arp", "-a"]],
    }
    COMMAND_TIMEOUT_SECONDS = 3
    COMMAND_OUTPUT_LIMIT_CHARS = 25000

    def __init__(self, core_identity: Any, snapshot_path: str = "data/sensorium_snapshot.json", mode: str = "READ_ONLY") -> None:
        self.core_identity = core_identity
        self.snapshot_path = Path(snapshot_path)
        self.mode = mode.upper()
        self.snapshot: Dict[str, Any] = {}
        if self.mode not in self.ALLOWED_MODES:
            raise SensoriumSafetyError(f"Sensorium mode is not allowed: {self.mode}")

    def utc_now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_snapshot_id(self) -> str:
        ts = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        return f"sensorium-{ts}-{uuid.uuid4().hex[:6]}"

    def generate_topology_matrix_id(self) -> str:
        ts = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        return f"topology-seed-{ts}-{uuid.uuid4().hex[:6]}"

    def create_snapshot(self) -> Dict[str, Any]:
        if self.mode != "READ_ONLY":
            raise SensoriumSafetyError("Sensorium requires READ_ONLY mode.")
        identity = self.core_identity.get_identity_report()
        persistent, runtime = identity["persistent"], identity["runtime"]
        network_interfaces = self.collect_network_interfaces()
        arp_table = self.collect_arp_table()
        network_connections = self.collect_network_connections()
        topology_seed_matrix = self.build_topology_seed_matrix(network_interfaces, arp_table, network_connections)
        snapshot = {
            "schema_version": self.SCHEMA_VERSION,
            "snapshot_id": self.generate_snapshot_id(),
            "snapshot_timestamp_utc": self.utc_now_iso(),
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_active_mode": runtime["active_mode"],
            "source_build": persistent["current_build"],
            "sensorium_mode": self.mode,
            "host": self.collect_host_info(),
            "python": self.collect_python_info(),
            "filesystem": self.collect_filesystem_info(),
            "process": self.collect_process_info(),
            "user_context": self.collect_user_context(),
            "environment": self.collect_environment_summary(),
            "commands": self.check_command_availability(),
            "network_observation": self.collect_network_observation(),
            "network_interfaces": network_interfaces,
            "arp_table": arp_table,
            "network_connections": network_connections,
            "topology_seed_matrix": topology_seed_matrix,
            "safety_boundary": self.get_safety_boundary(),
        }
        self.validate_snapshot(snapshot)
        self.snapshot = snapshot
        return copy.deepcopy(snapshot)

    def create_and_save_snapshot(self) -> Dict[str, Any]:
        snapshot = self.create_snapshot()
        self.save_snapshot(snapshot)
        return copy.deepcopy(snapshot)

    def validate_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        for field in ["schema_version", "snapshot_id", "host", "python", "network_interfaces", "arp_table", "network_connections", "topology_seed_matrix", "safety_boundary"]:
            if field not in snapshot:
                raise SensoriumSnapshotError(f"Missing sensorium field: {field}")
        if snapshot["topology_seed_matrix"].get("active_scan_performed") is not False:
            raise SensoriumSafetyError("Sensorium topology must be passive only.")
        return True

    def save_snapshot(self, snapshot: Dict[str, Any]) -> None:
        self.validate_snapshot(snapshot)
        try:
            self.snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            with self.snapshot_path.open("w", encoding="utf-8") as file:
                json.dump(snapshot, file, indent=2, sort_keys=False)
                file.write("\n")
        except OSError as error:
            raise SensoriumSnapshotError(f"Could not save sensorium snapshot: {error}") from error

    def collect_host_info(self) -> Dict[str, Any]:
        try:
            hostname = socket.gethostname()
        except OSError:
            hostname = None
        return {
            "hostname": hostname,
            "platform_system": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "node": platform.node(),
        }

    def collect_python_info(self) -> Dict[str, Any]:
        return {
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "implementation": platform.python_implementation(),
            "compiler": platform.python_compiler(),
            "build": list(platform.python_build()),
            "sys_prefix": sys.prefix,
            "base_prefix": sys.base_prefix,
            "virtual_environment_detected": sys.prefix != sys.base_prefix,
            "psutil_available": PSUTIL_AVAILABLE,
        }

    def collect_filesystem_info(self) -> Dict[str, Any]:
        script_directory = Path(__file__).resolve().parent
        try:
            home_detected = bool(str(Path.home()))
        except RuntimeError:
            home_detected = False
        return {
            "current_working_directory": str(Path.cwd()),
            "script_directory": str(script_directory),
            "project_root_guess": str(script_directory.parent),
            "home_directory_detected": home_detected,
            "home_directory_label": "available" if home_detected else "unavailable",
            "data_directory": str(self.snapshot_path.parent),
            "snapshot_path": str(self.snapshot_path),
            "recursive_filesystem_scan_performed": False,
        }

    def collect_process_info(self) -> Dict[str, Any]:
        try:
            parent_process_id = os.getppid()
        except AttributeError:
            parent_process_id = None
        return {
            "process_id": os.getpid(),
            "parent_process_id": parent_process_id,
            "process_list_scan_performed": False,
            "process_modification_performed": False,
        }

    def collect_user_context(self) -> Dict[str, Any]:
        detected = any(os.environ.get(key) for key in ["USERNAME", "USER", "LOGNAME"])
        return {
            "user_name_detected": detected,
            "user_name_label": "available" if detected else "unavailable",
            "login_context_available": detected,
            "raw_user_name_stored": False,
        }

    def collect_environment_summary(self) -> Dict[str, Any]:
        env_keys = list(os.environ.keys())
        included = [key for key in self.SAFE_ENVIRONMENT_KEYS if key in os.environ]
        sensitive = self.detect_sensitive_environment_keys(env_keys)
        return {
            "environment_variable_count": len(env_keys),
            "included_environment_keys": included,
            "raw_environment_values_stored": False,
            "sensitive_environment_categories_detected": sensitive,
            "sensitive_environment_keys_detected": bool(sensitive),
        }

    def detect_sensitive_environment_keys(self, env_keys: List[str]) -> List[str]:
        detected = set()
        for key in [k.upper() for k in env_keys]:
            for fragment in self.SENSITIVE_ENVIRONMENT_KEY_FRAGMENTS:
                if fragment in key:
                    detected.add(fragment)
        return sorted(detected)

    def check_command_availability(self) -> Dict[str, bool]:
        return {cmd: shutil.which(cmd) is not None for cmd in self.COMMANDS_TO_CHECK}

    def collect_network_observation(self) -> Dict[str, Any]:
        success, count = False, 0
        try:
            _name, _aliases, addresses = socket.gethostbyname_ex(socket.gethostname())
            success, count = True, len(addresses)
        except OSError:
            pass
        return {
            "network_scan_performed": False,
            "active_network_scan_performed": False,
            "external_network_access_performed": False,
            "public_ip_lookup_performed": False,
            "ping_performed": False,
            "port_scan_performed": False,
            "traceroute_performed": False,
            "local_hostname_resolution_attempted": True,
            "local_hostname_resolution_success": success,
            "local_hostname_address_count": count,
        }

    def collect_network_interfaces(self) -> Dict[str, Any]:
        if PSUTIL_AVAILABLE:
            interfaces, method = self.collect_network_interfaces_psutil(), "psutil.net_if_addrs"
        else:
            interfaces, method = self.collect_network_interfaces_standard_library_fallback(), "standard_library_fallback"
        ipv4_count = sum(len(i.get("ipv4_addresses", [])) for i in interfaces)
        return {
            "collection_attempted": True,
            "collection_method": method,
            "psutil_available": PSUTIL_AVAILABLE,
            "active_scan_performed": False,
            "interface_count": len(interfaces),
            "ipv4_address_count": ipv4_count,
            "interfaces": interfaces,
        }

    def collect_network_interfaces_psutil(self) -> List[Dict[str, Any]]:
        records = []
        addrs_by_interface = psutil.net_if_addrs()  # type: ignore[union-attr]
        try:
            stats_by_interface = psutil.net_if_stats()  # type: ignore[union-attr]
        except Exception:
            stats_by_interface = {}
        for name, addresses in addrs_by_interface.items():
            ipv4, ipv6, macs = [], [], []
            for addr in addresses:
                address = getattr(addr, "address", None)
                if not address:
                    continue
                if addr.family == socket.AF_INET:
                    ipv4.append(self.build_ipv4_record(address, getattr(addr, "netmask", None), getattr(addr, "broadcast", None)))
                elif addr.family == socket.AF_INET6:
                    ipv6.append({"ip_address": address, "is_loopback": address == "::1", "is_link_local": address.lower().startswith("fe80"), "raw_scope_id_may_be_present": "%" in address})
                elif self.looks_like_mac_address(address):
                    macs.append({"mac_address_stored": "hashed", "mac_address_hash": self.hash_mac_address(address), "raw_mac_address_stored": False})
            stats = stats_by_interface.get(name)
            records.append({
                "interface_name": name,
                "interface_status_available": stats is not None,
                "is_up": getattr(stats, "isup", None) if stats else None,
                "speed_mbps": getattr(stats, "speed", None) if stats else None,
                "mtu": getattr(stats, "mtu", None) if stats else None,
                "mac_addresses": macs,
                "ipv4_addresses": ipv4,
                "ipv6_addresses": ipv6,
            })
        return records

    def collect_network_interfaces_standard_library_fallback(self) -> List[Dict[str, Any]]:
        try:
            _name, _aliases, addresses = socket.gethostbyname_ex(socket.gethostname())
            ipv4 = [self.build_ipv4_record(ip, None, None) for ip in addresses]
        except OSError:
            ipv4 = []
        return [{
            "interface_name": "standard_library_hostname_resolution",
            "interface_status_available": False,
            "is_up": None,
            "speed_mbps": None,
            "mtu": None,
            "mac_addresses": [],
            "ipv4_addresses": ipv4,
            "ipv6_addresses": [],
        }]

    def build_ipv4_record(self, ip_address: str, netmask: Optional[str], broadcast: Optional[str]) -> Dict[str, Any]:
        prefix_length, network_cidr = None, None
        try:
            ip_obj = ipaddress.ip_address(ip_address)
            if netmask:
                interface = ipaddress.ip_interface(f"{ip_address}/{netmask}")
                prefix_length = interface.network.prefixlen
                network_cidr = str(interface.network)
            return {
                "ip_address": ip_address,
                "netmask": netmask,
                "prefix_length": prefix_length,
                "network_cidr": network_cidr,
                "broadcast": broadcast,
                "is_private": ip_obj.is_private,
                "is_loopback": ip_obj.is_loopback,
                "is_link_local": ip_obj.is_link_local,
                "is_multicast": ip_obj.is_multicast,
                "ip_version": ip_obj.version,
            }
        except ValueError:
            return {"ip_address": ip_address, "netmask": netmask, "prefix_length": None, "network_cidr": None, "broadcast": broadcast, "is_private": None, "is_loopback": None, "is_link_local": None, "is_multicast": None, "ip_version": None, "parse_error": True}

    def collect_arp_table(self) -> Dict[str, Any]:
        system_name = platform.system()
        commands = self.READ_ONLY_NETWORK_COMMANDS_BY_OS.get(system_name, [])
        command_results, entries = [], []
        for command in commands:
            result = self.run_read_only_observation_command(command)
            command_results.append(result)
            if not result["executed"] or result["return_code"] != 0:
                continue
            output = result.get("stdout", "")
            if system_name == "Windows":
                entries.extend(self.parse_arp_output_windows(output))
            elif system_name == "Linux" and command[:2] == ["ip", "neigh"]:
                entries.extend(self.parse_ip_neigh_output_linux(output))
            else:
                entries.extend(self.parse_arp_output_linux_mac(output))
        entries = self.dedupe_arp_entries(entries)
        return {
            "collection_attempted": bool(commands),
            "collection_method": "strict_read_only_command_allowlist",
            "platform_system": system_name,
            "allowed_commands_considered": commands,
            "read_only_commands_executed": sum(1 for r in command_results if r["executed"]),
            "active_scan_performed": False,
            "entries_count": len(entries),
            "entries": entries,
            "command_results_summary": [{k: r.get(k) for k in ["command", "executed", "return_code", "stdout_truncated", "stderr_truncated", "error"]} for r in command_results],
        }

    def run_read_only_observation_command(self, command: List[str]) -> Dict[str, Any]:
        if command not in self.READ_ONLY_NETWORK_COMMANDS_BY_OS.get(platform.system(), []):
            raise SensoriumSafetyError(f"Command is not allowlisted: {command}")
        if shutil.which(command[0]) is None:
            return {"command": command, "executed": False, "return_code": None, "stdout": "", "stderr": "", "stdout_truncated": False, "stderr_truncated": False, "error": f"Executable not found: {command[0]}"}
        try:
            completed = subprocess.run(command, shell=False, capture_output=True, text=True, timeout=self.COMMAND_TIMEOUT_SECONDS, encoding="utf-8", errors="replace")
            stdout, stdout_t = self.truncate_text(completed.stdout)
            stderr, stderr_t = self.truncate_text(completed.stderr)
            return {"command": command, "executed": True, "return_code": completed.returncode, "stdout": stdout, "stderr": stderr, "stdout_truncated": stdout_t, "stderr_truncated": stderr_t, "error": None}
        except subprocess.TimeoutExpired:
            return {"command": command, "executed": True, "return_code": None, "stdout": "", "stderr": "", "stdout_truncated": False, "stderr_truncated": False, "error": "Command timed out."}
        except OSError as error:
            return {"command": command, "executed": False, "return_code": None, "stdout": "", "stderr": "", "stdout_truncated": False, "stderr_truncated": False, "error": str(error)}

    def truncate_text(self, text: str) -> Tuple[str, bool]:
        return (text, False) if len(text) <= self.COMMAND_OUTPUT_LIMIT_CHARS else (text[:self.COMMAND_OUTPUT_LIMIT_CHARS], True)

    def parse_arp_output_windows(self, output: str) -> List[Dict[str, Any]]:
        entries, current_interface = [], None
        interface_pattern = re.compile(r"Interface:\s+([\d\.]+)\s+---")
        entry_pattern = re.compile(r"^\s*([\d\.]+)\s+([0-9a-fA-F\-]{17})\s+(\w+)\s*$")
        for line in output.splitlines():
            m = interface_pattern.search(line)
            if m:
                current_interface = m.group(1)
                continue
            m = entry_pattern.match(line)
            if m:
                entries.append(self.build_arp_entry(m.group(1), m.group(2).replace("-", ":").lower(), current_interface, m.group(3).lower(), "windows_arp_a"))
        return entries

    def parse_arp_output_linux_mac(self, output: str) -> List[Dict[str, Any]]:
        entries = []
        mac_pattern = r"([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})"
        ip_pattern = r"(\d{1,3}(?:\.\d{1,3}){3})"
        for line in output.splitlines():
            ip_m, mac_m = re.search(ip_pattern, line), re.search(mac_pattern, line)
            if ip_m and mac_m:
                on_m = re.search(r"\bon\s+([A-Za-z0-9_\-\.]+)", line)
                entries.append(self.build_arp_entry(ip_m.group(1), mac_m.group(1).lower(), on_m.group(1) if on_m else None, "observed", "arp_output"))
        return entries

    def parse_ip_neigh_output_linux(self, output: str) -> List[Dict[str, Any]]:
        entries = []
        pattern = re.compile(r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+dev\s+(?P<iface>[^\s]+).*?(?:lladdr\s+(?P<mac>[0-9a-fA-F:]{17}))?.*?(?P<state>REACHABLE|STALE|DELAY|PROBE|FAILED|INCOMPLETE|PERMANENT|NOARP)?$")
        for line in output.splitlines():
            m = pattern.search(line)
            if m:
                entries.append(self.build_arp_entry(m.group("ip"), m.group("mac"), m.group("iface"), (m.group("state") or "unknown").lower(), "linux_ip_neigh"))
        return entries

    def build_arp_entry(self, ip_address: str, mac_address: Optional[str], interface: Optional[str], entry_type: str, source: str) -> Dict[str, Any]:
        parsed = self.safe_parse_ip(ip_address)
        return {
            "ip_address": ip_address,
            "ip_version": parsed.get("ip_version"),
            "is_private": parsed.get("is_private"),
            "is_loopback": parsed.get("is_loopback"),
            "is_link_local": parsed.get("is_link_local"),
            "mac_address_stored": "hashed" if mac_address else "unavailable",
            "mac_address_hash": self.hash_mac_address(mac_address) if mac_address else None,
            "raw_mac_address_stored": False,
            "interface": interface,
            "entry_type": entry_type,
            "source": source,
            "confidence": 0.7,
        }

    def dedupe_arp_entries(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen, out = set(), []
        for e in entries:
            key = (e.get("ip_address"), e.get("mac_address_hash"), e.get("interface"))
            if key not in seen:
                seen.add(key)
                out.append(e)
        return out

    def collect_network_connections(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"collection_attempted": False, "collection_method": "psutil_unavailable", "psutil_available": False, "active_connections_initiated": False, "process_names_stored": False, "connections_count": 0, "connections": []}
        try:
            raw_connections = psutil.net_connections(kind="inet")  # type: ignore[union-attr]
        except Exception as error:
            return {"collection_attempted": True, "collection_method": "psutil.net_connections", "psutil_available": True, "active_connections_initiated": False, "process_names_stored": False, "error": str(error), "connections_count": 0, "connections": []}
        connections = []
        for c in raw_connections:
            connections.append({
                "family": str(c.family),
                "type": str(c.type),
                "status": c.status,
                "local_address": getattr(c.laddr, "ip", None) if c.laddr else None,
                "local_port": getattr(c.laddr, "port", None) if c.laddr else None,
                "remote_address": getattr(c.raddr, "ip", None) if c.raddr else None,
                "remote_port": getattr(c.raddr, "port", None) if c.raddr else None,
                "pid_available": c.pid is not None,
                "pid": c.pid,
                "process_name_stored": False,
                "connection_initiated_by_sensorium": False,
            })
        return {"collection_attempted": True, "collection_method": "psutil.net_connections", "psutil_available": True, "active_connections_initiated": False, "process_names_stored": False, "connections_count": len(connections), "connections": connections}

    def build_topology_seed_matrix(self, network_interfaces: Dict[str, Any], arp_table: Dict[str, Any], network_connections: Dict[str, Any]) -> Dict[str, Any]:
        nodes, edges = {}, []
        local = "local-host"
        nodes[local] = {"node_id": local, "node_type": "self", "ip_addresses": [], "network_cidrs": [], "mac_address_hashes": [], "confidence": 1.0, "evidence": ["local_interface"]}
        for interface in network_interfaces.get("interfaces", []):
            name = interface.get("interface_name")
            for mac in interface.get("mac_addresses", []):
                h = mac.get("mac_address_hash")
                if h and h not in nodes[local]["mac_address_hashes"]:
                    nodes[local]["mac_address_hashes"].append(h)
            for ipv4 in interface.get("ipv4_addresses", []):
                ip, cidr = ipv4.get("ip_address"), ipv4.get("network_cidr")
                if ip and ip not in nodes[local]["ip_addresses"]:
                    nodes[local]["ip_addresses"].append(ip)
                if cidr:
                    if cidr not in nodes[local]["network_cidrs"]:
                        nodes[local]["network_cidrs"].append(cidr)
                    network_id = f"network-{cidr}"
                    nodes.setdefault(network_id, {"node_id": network_id, "node_type": "derived_local_subnet", "network_cidr": cidr, "confidence": 0.85, "evidence": ["derived_subnet", "local_interface"]})
                    edges.append({"source": local, "target": network_id, "relationship": "attached_to_derived_subnet", "interface": name, "confidence": 0.85, "evidence": ["local_interface"]})
        for entry in arp_table.get("entries", []):
            ip = entry.get("ip_address")
            if ip:
                node_id = f"neighbor-{ip}"
                nodes.setdefault(node_id, {"node_id": node_id, "node_type": "neighbor_observed", "ip_addresses": [ip], "mac_address_hash": entry.get("mac_address_hash"), "confidence": entry.get("confidence", 0.7), "evidence": ["arp_table"]})
                edges.append({"source": local, "target": node_id, "relationship": "same_l2_neighbor_cache", "interface": entry.get("interface"), "confidence": entry.get("confidence", 0.7), "evidence": ["arp_table"]})
        for c in network_connections.get("connections", []):
            remote = c.get("remote_address")
            if remote:
                rid = f"remote-{remote}"
                nodes.setdefault(rid, {"node_id": rid, "node_type": "remote_endpoint_observed", "ip_addresses": [remote], **self.safe_parse_ip(remote), "confidence": 0.55, "evidence": ["passive_connection"]})
                edges.append({"source": local, "target": rid, "relationship": "has_passive_connection_record", "local_port": c.get("local_port"), "remote_port": c.get("remote_port"), "status": c.get("status"), "confidence": 0.55, "evidence": ["passive_connection"]})
        return {"matrix_id": self.generate_topology_matrix_id(), "matrix_type": "passive_observation_seed", "active_scan_performed": False, "subnet_scan_performed": False, "port_scan_performed": False, "service_fingerprinting_performed": False, "nodes_count": len(nodes), "edges_count": len(edges), "nodes": list(nodes.values()), "edges": edges}

    def get_safety_boundary(self) -> Dict[str, bool]:
        return {"read_only_observation": True, "may_write_snapshot_file": True, "may_check_command_availability": True, "may_execute_general_shell_commands": False, "may_execute_read_only_network_observation_commands": True, "may_execute_active_network_scans": False, "may_probe_remote_hosts": False, "may_scan_ports": False, "may_perform_ping_sweep": False, "may_perform_traceroute": False, "may_fingerprint_services": False, "may_access_external_network": False, "may_lookup_public_ip": False, "may_modify_system": False, "may_scan_private_documents": False, "may_store_raw_environment_values": False, "may_store_raw_username": False, "may_store_raw_mac_addresses": False, "may_store_process_names": False}

    def get_sensorium_report(self) -> Dict[str, Any]:
        if not self.snapshot:
            self.create_snapshot()
        commands, ni, arp, nc, topo = self.snapshot["commands"], self.snapshot["network_interfaces"], self.snapshot["arp_table"], self.snapshot["network_connections"], self.snapshot["topology_seed_matrix"]
        return {
            "snapshot_id": self.snapshot["snapshot_id"],
            "snapshot_timestamp_utc": self.snapshot["snapshot_timestamp_utc"],
            "sensorium_mode": self.snapshot["sensorium_mode"],
            "platform_system": self.snapshot["host"]["platform_system"],
            "platform_release": self.snapshot["host"]["platform_release"],
            "machine": self.snapshot["host"]["machine"],
            "python_version": self.snapshot["python"]["python_version"],
            "python_implementation": self.snapshot["python"]["implementation"],
            "psutil_available": self.snapshot["python"]["psutil_available"],
            "current_working_directory": self.snapshot["filesystem"]["current_working_directory"],
            "snapshot_path": self.snapshot["filesystem"]["snapshot_path"],
            "environment_variable_count": self.snapshot["environment"]["environment_variable_count"],
            "sensitive_environment_keys_detected": self.snapshot["environment"]["sensitive_environment_keys_detected"],
            "commands_checked_count": len(commands),
            "commands_available_count": sum(1 for v in commands.values() if v),
            "general_shell_commands_executed": False,
            "read_only_network_commands_executed": arp.get("read_only_commands_executed", 0),
            "network_interface_count": ni.get("interface_count", 0),
            "ipv4_address_count": ni.get("ipv4_address_count", 0),
            "arp_entry_count": arp.get("entries_count", 0),
            "network_connection_count": nc.get("connections_count", 0),
            "topology_node_count": topo.get("nodes_count", 0),
            "topology_edge_count": topo.get("edges_count", 0),
            "active_network_scan_performed": topo.get("active_scan_performed", False),
        }

    def get_snapshot(self) -> Dict[str, Any]:
        return copy.deepcopy(self.snapshot)

    def safe_parse_ip(self, ip_address: str) -> Dict[str, Any]:
        try:
            obj = ipaddress.ip_address(ip_address)
            return {"ip_version": obj.version, "is_private": obj.is_private, "is_loopback": obj.is_loopback, "is_link_local": obj.is_link_local, "is_multicast": obj.is_multicast, "parse_error": False}
        except ValueError:
            return {"ip_version": None, "is_private": None, "is_loopback": None, "is_link_local": None, "is_multicast": None, "parse_error": True}

    def looks_like_mac_address(self, value: str) -> bool:
        return bool(value and (re.match(r"^[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}$", value) or re.match(r"^[0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5}$", value)))

    def hash_mac_address(self, mac_address: Optional[str]) -> Optional[str]:
        if not mac_address:
            return None
        digest = hashlib.sha256(mac_address.strip().lower().replace("-", ":").encode("utf-8")).hexdigest()
        return f"sha256:{digest[:24]}"
