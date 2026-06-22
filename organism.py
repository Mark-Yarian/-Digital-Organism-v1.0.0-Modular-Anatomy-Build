"""
============================================================
DIGITAL ORGANISM LAUNCHER
============================================================

Project:
    Digital Organism

Build:
    0.6.0

Organism Name:
    ContinuityNode

Major Organs Loaded In This Build:
    1. Core Identity Organ
    2. Sensorium Organ
    3. Network Cartography Organ
    4. Memory Organ
    5. Event Bus / Nervous System Organ

Build 0.6.0 Expansion:
    Adds the Event Bus Organ.

    The Event Bus Organ provides local structured event routing.
    It allows organs to publish events without directly controlling
    each other.

Important Boundary:
    The Event Bus does not perform actions.

    It does not:
        - execute commands
        - access the network
        - scan files
        - mutate other organs
        - trigger active network discovery
        - make decisions
        - bypass safety boundaries

How To Run:
    From the digital_organism/ directory:

        python organism.py
"""

from organs.core_identity import CoreIdentityOrgan, CoreIdentityError
from organs.sensorium import SensoriumOrgan, SensoriumError
from organs.network_cartography import (
    NetworkCartographyOrgan,
    NetworkCartographyError,
)
from organs.memory import MemoryOrgan, MemoryError
from organs.event_bus import EventBusOrgan, EventBusError


BUILD_VERSION = "0.6.0"


def print_header(title: str) -> None:
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_identity_report(report: dict) -> None:
    persistent = report["persistent"]
    runtime = report["runtime"]

    print_header("CONTINUITYNODE IDENTITY REPORT")
    print(f"Organism Name:       {persistent['organism_name']}")
    print(f"Lineage ID:          {persistent['lineage_id']}")
    print(f"Birth Timestamp UTC: {persistent['birth_timestamp_utc']}")
    print(f"First Build:         {persistent['first_build']}")
    print(f"Current Build:       {persistent['current_build']}")
    print(f"Runtime Instance ID: {runtime['runtime_instance_id']}")
    print(f"Active Mode:         {runtime['active_mode']}")


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
    print(f"Memory Root:                {report['memory_root']}")
    print(f"Records Count:              {report['records_count']}")
    print(f"Identity Stored This Run:    {report['stored_this_run']['identity_snapshot']}")
    print(f"Sensorium Stored This Run:   {report['stored_this_run']['sensorium_snapshot']}")
    print(f"Cartography Stored This Run: {report['stored_this_run']['cartography_report']}")
    print(f"Sensorium Changed:           {report['change_markers']['sensorium_changed_since_previous']}")
    print(f"Topology Changed:            {report['change_markers']['topology_changed_since_previous']}")
    print(f"Cartography Plan Changed:    {report['change_markers']['cartography_plan_changed_since_previous']}")


def print_event_bus_report(report: dict) -> None:
    print_header("CONTINUITYNODE EVENT BUS REPORT")
    print(f"Event Root:                 {report['event_root']}")
    print(f"Events Published This Run:  {report['events_published_this_run']}")
    print(f"Total Events Recorded:      {report['total_events_recorded']}")
    print(f"Known Event Types:          {report['known_event_types_count']}")
    print(f"Subscribers Registered:     {report['subscribers_registered_count']}")
    print(f"Event Actions Performed:    {report['safety_summary']['actions_performed']}")
    print(f"Commands Executed:          {report['safety_summary']['commands_executed']}")
    print(f"Network Access Performed:   {report['safety_summary']['network_access_performed']}")


def main() -> None:
    """
    Main program entry point.

    Build 0.6.0 startup sequence:
        1. Initialize Core Identity.
        2. Initialize Event Bus.
        3. Publish identity initialized event.
        4. Run Sensorium.
        5. Publish sensorium snapshot event.
        6. Run Network Cartography dry-run.
        7. Publish cartography plan event.
        8. Run Memory.
        9. Store approved records.
       10. Publish memory events.
       11. Generate latest Event Bus state.
    """

    try:
        core_identity = CoreIdentityOrgan(
            identity_path="data/identity.json",
            build_version=BUILD_VERSION,
            default_name="ContinuityNode",
            default_mode="OBSERVE",
        )

        identity_report = core_identity.get_identity_report()
        print_identity_report(identity_report)

        event_bus = EventBusOrgan(
            core_identity=core_identity,
            event_root="data/events",
        )

        event_bus.publish_event(
            event_type="identity.initialized",
            source_organ="CoreIdentityOrgan",
            payload={
                "organism_name": identity_report["persistent"]["organism_name"],
                "lineage_id": identity_report["persistent"]["lineage_id"],
                "runtime_instance_id": identity_report["runtime"]["runtime_instance_id"],
                "current_build": identity_report["persistent"]["current_build"],
            },
        )

        sensorium = SensoriumOrgan(
            core_identity=core_identity,
            snapshot_path="data/sensorium_snapshot.json",
            mode="READ_ONLY",
        )

        sensorium.create_and_save_snapshot()
        sensorium_snapshot = sensorium.get_snapshot()
        sensorium_report = sensorium.get_sensorium_report()
        print_sensorium_report(sensorium_report)

        event_bus.publish_event(
            event_type="sensorium.snapshot.created",
            source_organ="SensoriumOrgan",
            payload={
                "snapshot_id": sensorium_snapshot.get("snapshot_id"),
                "topology_matrix_id": sensorium_snapshot.get("topology_seed_matrix", {}).get("matrix_id"),
                "topology_nodes_count": sensorium_snapshot.get("topology_seed_matrix", {}).get("nodes_count", 0),
                "topology_edges_count": sensorium_snapshot.get("topology_seed_matrix", {}).get("edges_count", 0),
                "active_scan_performed": sensorium_snapshot.get("topology_seed_matrix", {}).get("active_scan_performed", False),
            },
        )

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

        event_bus.publish_event(
            event_type="cartography.plan.created",
            source_organ="NetworkCartographyOrgan",
            payload={
                "report_id": cartography_report.get("report_id"),
                "cartography_mode": cartography_report.get("cartography_mode"),
                "active_discovery_performed": cartography_report.get("active_discovery_performed"),
                "planned_probe_count": cartography_report.get("dry_run_plan", {}).get("planned_probe_count", 0),
                "active_probes_sent": 0,
            },
        )

        memory = MemoryOrgan(
            core_identity=core_identity,
            memory_root="data/memory",
        )

        identity_memory = memory.store_identity_snapshot(identity_report)
        sensorium_memory = memory.store_sensorium_snapshot(sensorium_snapshot)
        cartography_memory = memory.store_cartography_report(cartography_report)

        event_bus.publish_event(
            event_type="memory.records.stored",
            source_organ="MemoryOrgan",
            payload={
                "identity_memory_id": identity_memory.get("memory_id"),
                "sensorium_memory_id": sensorium_memory.get("memory_id"),
                "cartography_memory_id": cartography_memory.get("memory_id"),
            },
        )

        memory_summary = memory.generate_latest_memory_summary()
        memory_report = memory.get_memory_report(memory_summary)
        print_memory_report(memory_report)

        event_bus.publish_event(
            event_type="memory.summary.generated",
            source_organ="MemoryOrgan",
            payload={
                "records_count": memory_summary.get("records_count"),
                "latest_records": memory_summary.get("latest_records"),
                "change_markers": memory_summary.get("change_markers"),
            },
        )

        event_bus_state = event_bus.generate_latest_event_bus_state()
        event_bus_report = event_bus.get_event_bus_report(event_bus_state)
        print_event_bus_report(event_bus_report)

    except CoreIdentityError as error:
        print_header("CORE IDENTITY ORGAN ERROR")
        print(str(error))

    except SensoriumError as error:
        print_header("SENSORIUM ORGAN ERROR")
        print(str(error))

    except NetworkCartographyError as error:
        print_header("NETWORK CARTOGRAPHY ORGAN ERROR")
        print(str(error))

    except MemoryError as error:
        print_header("MEMORY ORGAN ERROR")
        print(str(error))

    except EventBusError as error:
        print_header("EVENT BUS ORGAN ERROR")
        print(str(error))


if __name__ == "__main__":
    main()
