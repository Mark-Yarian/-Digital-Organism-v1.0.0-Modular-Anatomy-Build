"""
============================================================
DIGITAL ORGANISM LAUNCHER
============================================================

Project:
    Digital Organism

Build:
    0.4.0

Organism Name:
    ContinuityNode

Major Organs Loaded In This Build:
    1. Core Identity Organ
    2. Sensorium Organ
    3. Network Cartography Organ

Build 0.4.0 Expansion:
    Adds the Network Cartography Organ.

    This organ is introduced as a dry-run-only skeleton.

    It creates and validates a cartography policy file, reads the
    passive topology seed matrix from Sensorium, creates a dry-run
    discovery plan, writes an audit log, and writes a report.

Important Boundary:
    Build 0.4.0 does not actively scan the network.

    It does not:
        - ping sweep
        - port scan
        - TCP connect probe
        - traceroute
        - crawl subnets
        - fingerprint services
        - perform credential testing
        - perform vulnerability testing

    Actual active discovery will be added later under strict policy
    controls.

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


BUILD_VERSION = "0.4.0"


def print_identity_report(report: dict) -> None:
    """Print a human-readable identity report."""

    persistent = report["persistent"]
    runtime = report["runtime"]
    classification = report["classification"]

    print()
    print("============================================================")
    print("CONTINUITYNODE IDENTITY REPORT")
    print("============================================================")
    print()
    print("Persistent Identity")
    print("-------------------")
    print(f"Organism Name:          {persistent['organism_name']}")
    print(f"Lineage ID:             {persistent['lineage_id']}")
    print(f"Birth Timestamp UTC:    {persistent['birth_timestamp_utc']}")
    print(f"First Build:            {persistent['first_build']}")
    print(f"Current Build:          {persistent['current_build']}")
    print()
    print("Runtime Identity")
    print("----------------")
    print(f"Runtime Instance ID:    {runtime['runtime_instance_id']}")
    print(f"Runtime Started UTC:    {runtime['runtime_started_utc']}")
    print(f"Active Mode:            {runtime['active_mode']}")
    print()
    print("Classification")
    print("--------------")
    print(f"Organism Type:          {classification['organism_type']}")
    print(f"Description:            {classification['description']}")
    print()
    print("Safety Boundary")
    print("---------------")

    for key, value in report["safety_boundary"].items():
        print(f"{key}: {value}")

    print()
    print("============================================================")
    print("Identity initialization complete.")
    print("============================================================")
    print()


def print_sensorium_report(report: dict) -> None:
    """Print a short human-readable Sensorium report."""

    print()
    print("============================================================")
    print("CONTINUITYNODE SENSORIUM REPORT")
    print("============================================================")
    print()
    print("Snapshot")
    print("--------")
    print(f"Snapshot ID:                         {report['snapshot_id']}")
    print(f"Snapshot Timestamp UTC:              {report['snapshot_timestamp_utc']}")
    print(f"Sensorium Mode:                      {report['sensorium_mode']}")
    print()
    print("Host")
    print("----")
    print(f"Platform System:                     {report['platform_system']}")
    print(f"Platform Release:                    {report['platform_release']}")
    print(f"Machine Architecture:                {report['machine']}")
    print()
    print("Python")
    print("------")
    print(f"Python Version:                      {report['python_version']}")
    print(f"Python Implementation:               {report['python_implementation']}")
    print(f"psutil Available:                    {report['psutil_available']}")
    print()
    print("Filesystem")
    print("----------")
    print(f"Current Working Directory:           {report['current_working_directory']}")
    print(f"Snapshot Path:                       {report['snapshot_path']}")
    print()
    print("Passive Network Mapping")
    print("-----------------------")
    print(f"Network Interfaces Found:            {report['network_interface_count']}")
    print(f"IPv4 Address Count:                  {report['ipv4_address_count']}")
    print(f"ARP / Neighbor Entries Found:        {report['arp_entry_count']}")
    print(f"Network Connections Found:           {report['network_connection_count']}")
    print(f"Topology Nodes:                      {report['topology_node_count']}")
    print(f"Topology Edges:                      {report['topology_edge_count']}")
    print(f"Active Network Scan Performed:       {report['active_network_scan_performed']}")
    print()
    print("============================================================")
    print("Sensorium observation complete.")
    print("============================================================")
    print()


def print_cartography_report(report: dict) -> None:
    """
    Print a short Network Cartography report.

    The full report is saved to:
        data/network_cartography_report.json

    The audit trail is appended to:
        data/network_cartography_audit_log.jsonl
    """

    print()
    print("============================================================")
    print("CONTINUITYNODE NETWORK CARTOGRAPHY REPORT")
    print("============================================================")
    print()
    print("Report")
    print("------")
    print(f"Report ID:                         {report['report_id']}")
    print(f"Report Timestamp UTC:              {report['report_timestamp_utc']}")
    print(f"Cartography Mode:                  {report['cartography_mode']}")
    print(f"Active Discovery Performed:        {report['active_discovery_performed']}")
    print()
    print("Policy")
    print("------")
    print(f"Policy Created Automatically:      {report['policy_created_automatically']}")
    print(f"Cartography Enabled:               {report['policy']['cartography_enabled']}")
    print(f"Requires Explicit Approval:        {report['policy']['requires_explicit_approval']}")
    print(f"Private Ranges Only:               {report['policy']['allow_private_ranges_only']}")
    print(f"Max Hosts Per Run:                 {report['policy']['max_hosts_per_run']}")
    print(f"Allowed Probe Types:               {report['policy']['allowed_probe_types']}")
    print()
    print("Dry-Run Plan")
    print("------------")
    print(f"Approved Scopes Count:             {report['dry_run_plan']['approved_scopes_count']}")
    print(f"Candidate Hosts Count:             {report['dry_run_plan']['candidate_hosts_count']}")
    print(f"Planned Probe Count:               {report['dry_run_plan']['planned_probe_count']}")
    print(f"Plan Generated:                    {report['dry_run_plan']['plan_generated']}")
    print()
    print("Safety Summary")
    print("--------------")
    print(f"Public Ranges Excluded:            {report['safety_summary']['public_ranges_excluded']}")
    print(f"Scope Limit Enforced:              {report['safety_summary']['scope_limit_enforced']}")
    print(f"Rate Limit Enforced:               {report['safety_summary']['rate_limit_enforced']}")
    print(f"Credential Testing Performed:      {report['safety_summary']['credential_testing_performed']}")
    print(f"Vulnerability Testing Performed:   {report['safety_summary']['vulnerability_testing_performed']}")
    print(f"Service Fingerprinting Performed:  {report['safety_summary']['service_fingerprinting_performed']}")
    print()
    print("============================================================")
    print("Network Cartography dry-run complete. No active probes were sent.")
    print("============================================================")
    print()


def main() -> None:
    """
    Main program entry point.

    Build 0.4.0 startup sequence:
        1. Initialize Core Identity Organ.
        2. Print identity report.
        3. Initialize Sensorium Organ.
        4. Create and save Sensorium snapshot.
        5. Print short Sensorium report.
        6. Initialize Network Cartography Organ.
        7. Create policy file if missing.
        8. Build dry-run cartography plan.
        9. Save report and audit entry.
       10. Print short Cartography report.

    No active network discovery is performed in this build.
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

        sensorium = SensoriumOrgan(
            core_identity=core_identity,
            snapshot_path="data/sensorium_snapshot.json",
            mode="READ_ONLY",
        )

        sensorium.create_and_save_snapshot()

        sensorium_report = sensorium.get_sensorium_report()
        print_sensorium_report(sensorium_report)

        sensorium_snapshot = sensorium.get_snapshot()

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

    except CoreIdentityError as error:
        print()
        print("============================================================")
        print("CORE IDENTITY ORGAN ERROR")
        print("============================================================")
        print(str(error))
        print()
        print("The organism did not complete startup.")
        print("============================================================")
        print()

    except SensoriumError as error:
        print()
        print("============================================================")
        print("SENSORIUM ORGAN ERROR")
        print("============================================================")
        print(str(error))
        print()
        print("The organism did not complete sensorium observation.")
        print("============================================================")
        print()

    except NetworkCartographyError as error:
        print()
        print("============================================================")
        print("NETWORK CARTOGRAPHY ORGAN ERROR")
        print("============================================================")
        print(str(error))
        print()
        print("The organism did not complete network cartography planning.")
        print("============================================================")
        print()


if __name__ == "__main__":
    main()
