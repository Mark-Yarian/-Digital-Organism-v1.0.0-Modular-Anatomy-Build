"""
Digital Organism Launcher — ContinuityNode
Build: 0.5.0

Organs loaded:
  1. Core Identity Organ
  2. Sensorium Organ
  3. Network Cartography Organ
  4. Memory Organ

Run:
  python organism.py
"""

from organs.core_identity import CoreIdentityOrgan, CoreIdentityError
from organs.sensorium import SensoriumOrgan, SensoriumError
from organs.network_cartography import NetworkCartographyOrgan, NetworkCartographyError
from organs.memory import MemoryOrgan, MemoryError

BUILD_VERSION = "0.5.0"


def print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_identity_report(report: dict) -> None:
    persistent = report["persistent"]
    runtime = report["runtime"]
    classification = report["classification"]

    print_header("CONTINUITYNODE IDENTITY REPORT")
    print("Persistent Identity")
    print("-------------------")
    print(f"Organism Name:       {persistent['organism_name']}")
    print(f"Lineage ID:          {persistent['lineage_id']}")
    print(f"Birth Timestamp UTC: {persistent['birth_timestamp_utc']}")
    print(f"First Build:         {persistent['first_build']}")
    print(f"Current Build:       {persistent['current_build']}")
    print()
    print("Runtime Identity")
    print("----------------")
    print(f"Runtime Instance ID: {runtime['runtime_instance_id']}")
    print(f"Runtime Started UTC: {runtime['runtime_started_utc']}")
    print(f"Active Mode:         {runtime['active_mode']}")
    print()
    print("Classification")
    print("--------------")
    print(f"Organism Type:       {classification['organism_type']}")


def print_sensorium_report(report: dict) -> None:
    print_header("CONTINUITYNODE SENSORIUM REPORT")
    print(f"Snapshot ID:                  {report['snapshot_id']}")
    print(f"Platform System:              {report['platform_system']}")
    print(f"Python Version:               {report['python_version']}")
    print(f"psutil Available:             {report['psutil_available']}")
    print(f"Network Interfaces Found:     {report['network_interface_count']}")
    print(f"IPv4 Address Count:           {report['ipv4_address_count']}")
    print(f"ARP / Neighbor Entries Found: {report['arp_entry_count']}")
    print(f"Topology Nodes:               {report['topology_node_count']}")
    print(f"Topology Edges:               {report['topology_edge_count']}")
    print(f"Active Network Scan:          {report['active_network_scan_performed']}")


def print_cartography_report(report: dict) -> None:
    print_header("CONTINUITYNODE NETWORK CARTOGRAPHY REPORT")
    print(f"Report ID:                  {report['report_id']}")
    print(f"Cartography Mode:           {report['cartography_mode']}")
    print(f"Active Discovery Performed: {report['active_discovery_performed']}")
    print(f"Approved Scopes Count:      {report['dry_run_plan']['approved_scopes_count']}")
    print(f"Candidate Hosts Count:      {report['dry_run_plan']['candidate_hosts_count']}")
    print(f"Planned Probe Count:        {report['dry_run_plan']['planned_probe_count']}")
    print("No active probes were sent.")


def print_memory_report(report: dict) -> None:
    print_header("CONTINUITYNODE MEMORY REPORT")
    print(f"Memory Root:                  {report['memory_root']}")
    print(f"Records Count:                {report['records_count']}")
    print(f"Identity Stored This Run:      {report['stored_this_run']['identity_snapshot']}")
    print(f"Sensorium Stored This Run:     {report['stored_this_run']['sensorium_snapshot']}")
    print(f"Cartography Stored This Run:   {report['stored_this_run']['cartography_report']}")
    print(f"Sensorium Changed:             {report['change_markers']['sensorium_changed_since_previous']}")
    print(f"Topology Changed:              {report['change_markers']['topology_changed_since_previous']}")
    print(f"Cartography Plan Changed:      {report['change_markers']['cartography_plan_changed_since_previous']}")


def main() -> None:
    try:
        core_identity = CoreIdentityOrgan(
            identity_path="data/identity.json",
            build_version=BUILD_VERSION,
            default_name="ContinuityNode",
            default_mode="OBSERVE",
        )
        identity_report = core_identity.get_identity_report()
        print_identity_report(identity_report)

        sensorium = SensoriumOrgan(
            core_identity=core_identity,
            snapshot_path="data/sensorium_snapshot.json",
            mode="READ_ONLY",
        )
        sensorium.create_and_save_snapshot()
        sensorium_snapshot = sensorium.get_snapshot()
        print_sensorium_report(sensorium.get_sensorium_report())

        cartography = NetworkCartographyOrgan(
            core_identity=core_identity,
            sensorium_snapshot=sensorium_snapshot,
            policy_path="data/network_cartography_policy.json",
            report_path="data/network_cartography_report.json",
            audit_log_path="data/network_cartography_audit_log.jsonl",
            enabled=False,
        )
        cartography_report = cartography.run_cartography()
        print_cartography_report(cartography_report)

        memory = MemoryOrgan(core_identity=core_identity, memory_root="data/memory")
        memory.store_identity_snapshot(identity_report)
        memory.store_sensorium_snapshot(sensorium_snapshot)
        memory.store_cartography_report(cartography_report)
        memory_summary = memory.generate_latest_memory_summary()
        print_memory_report(memory.get_memory_report(memory_summary))

    except (CoreIdentityError, SensoriumError, NetworkCartographyError, MemoryError) as error:
        print_header("DIGITAL ORGANISM STARTUP ERROR")
        print(str(error))


if __name__ == "__main__":
    main()
