"""
============================================================
INTERFACE ORGAN
============================================================

Project:
    Digital Organism

Build:
    1.0.0

Organism Name:
    ContinuityNode

Organ:
    Interface Organ

File:
    organs/interface.py

Primary Function:
    Provide a controlled local command-line inspection interface for
    ContinuityNode.

Scientific / Clinical Description:
    The Interface Organ is a local presentation and inspection component.

    It does not create consciousness, agency, autonomy, or independent
    intent. It gives a human operator a controlled way to inspect the
    organism's current state and saved reports.

Relationship To Existing Organs:
    Core Identity Organ:
        Provides identity state.

    Sensorium Organ:
        Provides passive observation snapshots.

    Network Cartography Organ:
        Provides dry-run cartography reports.

    Memory Organ:
        Provides structured memory summaries.

    Event Bus Organ:
        Provides local event state.

    Metabolism Organ:
        Provides lifecycle and heartbeat state.

    Reflex Organ:
        Provides warning and reflex state.

    Immune Organ:
        Provides formal allow/deny safety decisions.

    Interface Organ:
        Presents controlled local summaries to a human operator.

Important Safety Boundary:
    The Interface Organ is read-only in Build 1.0.0.

    It may:
        - print local status
        - read approved JSON report files
        - summarize approved state files
        - write interface logs
        - write latest interface state

    It may not:
        - execute commands
        - access the network
        - scan arbitrary files
        - modify source code
        - delete memory
        - enable active cartography
        - change immune policy
        - run as a web server
        - start a background daemon
        - bypass Immune decisions

Storage Model:
    data/interface/
        interface_log.jsonl
        latest_interface_state.json

Supported CLI Commands:
    run
    status
    identity
    sensorium
    cartography
    memory
    events
    metabolism
    reflex
    immune
    safety
    help

Build 1.0.0 Behavior:
    - Parse local CLI command.
    - Read approved state/report files only.
    - Print readable summaries.
    - Log interface command usage.
    - Generate latest_interface_state.json.
"""

from __future__ import annotations

import copy
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================


class InterfaceError(Exception):
    """
    Base exception for all Interface Organ errors.
    """


class InterfaceCommandError(InterfaceError):
    """
    Raised when a CLI command is invalid.
    """


class InterfaceReadError(InterfaceError):
    """
    Raised when an approved report file cannot be read.
    """


class InterfaceLogError(InterfaceError):
    """
    Raised when interface log cannot be written.
    """


class InterfaceStateError(InterfaceError):
    """
    Raised when interface state cannot be generated or saved.
    """


class InterfaceSafetyError(InterfaceError):
    """
    Raised when an interface request violates safety boundaries.
    """


# ============================================================
# INTERFACE ORGAN CLASS
# ============================================================


class InterfaceOrgan:
    """
    Controlled local CLI inspection interface.

    Build 1.0.0 is intentionally read-only.

    This organ does not execute commands.
    It only interprets the CLI argument that started the Python process.
    """

    SCHEMA_VERSION = "1.0.0"
    INTERFACE_MODE = "LOCAL_CLI_READ_ONLY"

    VALID_COMMANDS = [
        "run",
        "status",
        "identity",
        "sensorium",
        "cartography",
        "memory",
        "events",
        "metabolism",
        "reflex",
        "immune",
        "safety",
        "help",
    ]

    APPROVED_READ_PATHS = {
        "identity": "data/identity.json",
        "sensorium": "data/sensorium_snapshot.json",
        "cartography": "data/network_cartography_report.json",
        "cartography_policy": "data/network_cartography_policy.json",
        "memory": "data/memory/summaries/latest_memory_summary.json",
        "memory_index": "data/memory/memory_index.json",
        "events": "data/events/latest_event_bus_state.json",
        "metabolism": "data/metabolism/metabolism_state.json",
        "reflex": "data/reflex/latest_reflex_state.json",
        "immune": "data/immune/latest_immune_state.json",
    }

    PROHIBITED_DETAIL_KEYS = [
        "raw_environment_values",
        "environment_values",
        "secret_values",
        "token_values",
        "password_values",
        "credential_values",
        "cookie_values",
        "raw_private_key",
        "private_key",
    ]

    def __init__(
        self,
        core_identity: Any,
        event_bus: Optional[Any] = None,
        immune: Optional[Any] = None,
        interface_root: str = "data/interface",
    ) -> None:
        """
        Initialize the Interface Organ.
        """

        self.core_identity = core_identity
        self.event_bus = event_bus
        self.immune = immune

        self.interface_root = Path(interface_root)
        self.interface_log_path = self.interface_root / "interface_log.jsonl"
        self.latest_state_path = self.interface_root / "latest_interface_state.json"

        self.commands_handled_this_run = 0
        self.reads_performed_this_run = 0
        self.invalid_commands_this_run = 0
        self.interface_events_written_this_run = 0

        self.ensure_interface_structure()

        self.log_interface_event(
            event_type="interface.initialized",
            command="init",
            result="ok",
            details={
                "interface_mode": self.INTERFACE_MODE,
                "interface_root": str(self.interface_root),
            },
        )

    # ========================================================
    # TIME AND ID HELPERS
    # ========================================================

    def utc_now_iso(self) -> str:
        """
        Return current UTC timestamp.
        """

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_interface_event_id(self, event_type: str) -> str:
        """
        Generate a unique interface event ID.
        """

        safe_type = event_type.replace(".", "-").replace("_", "-")
        timestamp = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        short_id = uuid.uuid4().hex[:6]

        return f"interface-{safe_type}-{timestamp}-{short_id}"

    # ========================================================
    # STRUCTURE
    # ========================================================

    def ensure_interface_structure(self) -> None:
        """
        Create interface output directory.
        """

        try:
            self.interface_root.mkdir(parents=True, exist_ok=True)

        except OSError as error:
            raise InterfaceStateError(
                f"Could not create interface directory: {error}"
            ) from error

    # ========================================================
    # CLI COMMAND HANDLING
    # ========================================================

    def parse_command(self, argv: Optional[List[str]] = None) -> str:
        """
        Parse command from argv.

        Defaults:
            no command -> run

        Examples:
            python organism.py
            python organism.py run
            python organism.py status
            python organism.py memory
        """

        argv = argv if argv is not None else sys.argv

        if len(argv) < 2:
            return "run"

        command = str(argv[1]).strip().lower()

        if not command:
            return "run"

        if command not in self.VALID_COMMANDS:
            self.invalid_commands_this_run += 1

            self.log_interface_event(
                event_type="interface.invalid_command",
                command=command,
                result="denied",
                details={
                    "valid_commands": self.VALID_COMMANDS,
                },
            )

            raise InterfaceCommandError(
                f"Invalid interface command: {command}. Use 'help' for valid commands."
            )

        return command

    def handle_command(
        self,
        command: str,
        runtime_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle a validated command.

        This does not execute system commands.

        It only performs approved local read/report behavior.
        """

        runtime_context = runtime_context or {}
        self.validate_details_safety(runtime_context)

        if command not in self.VALID_COMMANDS:
            raise InterfaceCommandError(f"Invalid interface command: {command}")

        self.commands_handled_this_run += 1

        # Immune gate for interface read/presentation action.
        if self.immune is not None:
            self.immune.review_action_request(
                requested_action="interface.read_approved_state",
                source_organ="InterfaceOrgan",
                request={
                    "command": command,
                    "read_only": True,
                    "approved_paths_only": True,
                },
            )

        if command == "help":
            result = self.command_help()

        elif command == "status":
            result = self.command_status()

        elif command == "identity":
            result = self.command_identity()

        elif command == "sensorium":
            result = self.command_sensorium()

        elif command == "cartography":
            result = self.command_cartography()

        elif command == "memory":
            result = self.command_memory()

        elif command == "events":
            result = self.command_events()

        elif command == "metabolism":
            result = self.command_metabolism()

        elif command == "reflex":
            result = self.command_reflex()

        elif command == "immune":
            result = self.command_immune()

        elif command == "safety":
            result = self.command_safety()

        elif command == "run":
            result = {
                "command": "run",
                "message": "Full organism run should be handled by organism.py startup sequence.",
                "interface_action": "no_direct_run_performed",
            }

        else:
            raise InterfaceCommandError(f"Unhandled interface command: {command}")

        self.log_interface_event(
            event_type="interface.command.handled",
            command=command,
            result="ok",
            details={
                "runtime_context": runtime_context,
                "result_keys": list(result.keys()),
            },
        )

        self.publish_interface_event(
            event_type="interface.command.handled",
            payload={
                "command": command,
                "result": "ok",
            },
        )

        self.generate_latest_interface_state()

        return copy.deepcopy(result)

    # ========================================================
    # COMMAND IMPLEMENTATIONS
    # ========================================================

    def command_help(self) -> Dict[str, Any]:
        """
        Return help text.
        """

        return {
            "command": "help",
            "valid_commands": list(self.VALID_COMMANDS),
            "usage": {
                "run": "Run the normal single-cycle organism startup sequence.",
                "status": "Show high-level organism status.",
                "identity": "Show identity summary.",
                "sensorium": "Show latest sensorium snapshot summary.",
                "cartography": "Show latest dry-run cartography summary.",
                "memory": "Show latest memory summary.",
                "events": "Show latest event bus state.",
                "metabolism": "Show latest metabolism state.",
                "reflex": "Show latest reflex state.",
                "immune": "Show latest immune state.",
                "safety": "Show combined safety posture.",
                "help": "Show this help output.",
            },
        }

    def command_status(self) -> Dict[str, Any]:
        """
        Return combined high-level status from approved files.
        """

        identity = self.safe_read_json("identity")
        memory = self.safe_read_json("memory", missing_ok=True)
        events = self.safe_read_json("events", missing_ok=True)
        metabolism = self.safe_read_json("metabolism", missing_ok=True)
        immune = self.safe_read_json("immune", missing_ok=True)

        return {
            "command": "status",
            "organism_name": identity.get("organism_name"),
            "lineage_id": identity.get("lineage_id"),
            "current_build": identity.get("current_build"),
            "memory_records_count": memory.get("records_count") if memory else None,
            "events_published_this_run": events.get("events_published_this_run") if events else None,
            "metabolism_phase": metabolism.get("current_phase") if metabolism else None,
            "immune_mode": immune.get("immune_mode") if immune else None,
            "deny_by_default": immune.get("deny_by_default") if immune else None,
        }

    def command_identity(self) -> Dict[str, Any]:
        """
        Return identity summary.
        """

        identity = self.safe_read_json("identity")

        return {
            "command": "identity",
            "organism_name": identity.get("organism_name"),
            "lineage_id": identity.get("lineage_id"),
            "birth_timestamp_utc": identity.get("birth_timestamp_utc"),
            "first_build": identity.get("first_build"),
            "current_build": identity.get("current_build"),
            "default_runtime_mode": identity.get("default_runtime_mode"),
            "locked_fields": identity.get("identity_locked_fields"),
        }

    def command_sensorium(self) -> Dict[str, Any]:
        """
        Return latest sensorium summary.
        """

        sensorium = self.safe_read_json("sensorium")

        topology = sensorium.get("topology_seed_matrix", {})
        network_interfaces = sensorium.get("network_interfaces", {})
        arp_table = sensorium.get("arp_table", {})
        python_info = sensorium.get("python", {})
        host = sensorium.get("host", {})

        return {
            "command": "sensorium",
            "snapshot_id": sensorium.get("snapshot_id"),
            "platform_system": host.get("platform_system"),
            "platform_release": host.get("platform_release"),
            "python_version": python_info.get("python_version"),
            "psutil_available": python_info.get("psutil_available"),
            "network_interface_count": network_interfaces.get("interface_count"),
            "ipv4_address_count": network_interfaces.get("ipv4_address_count"),
            "arp_entry_count": arp_table.get("entries_count"),
            "topology_nodes_count": topology.get("nodes_count"),
            "topology_edges_count": topology.get("edges_count"),
            "active_scan_performed": topology.get("active_scan_performed"),
        }

    def command_cartography(self) -> Dict[str, Any]:
        """
        Return latest cartography dry-run summary.
        """

        report = self.safe_read_json("cartography")
        plan = report.get("dry_run_plan", {})
        policy = report.get("policy", {})

        return {
            "command": "cartography",
            "report_id": report.get("report_id"),
            "cartography_mode": report.get("cartography_mode"),
            "active_discovery_performed": report.get("active_discovery_performed"),
            "cartography_enabled": policy.get("cartography_enabled"),
            "approved_scopes_count": plan.get("approved_scopes_count"),
            "candidate_hosts_count": plan.get("candidate_hosts_count"),
            "planned_probe_count": plan.get("planned_probe_count"),
            "active_probes_sent": plan.get("active_probes_sent"),
        }

    def command_memory(self) -> Dict[str, Any]:
        """
        Return latest memory summary.
        """

        memory = self.safe_read_json("memory")

        return {
            "command": "memory",
            "records_count": memory.get("records_count"),
            "latest_records": memory.get("latest_records"),
            "change_markers": memory.get("change_markers"),
            "stored_this_run": memory.get("stored_this_run"),
            "safety_summary": memory.get("safety_summary"),
        }

    def command_events(self) -> Dict[str, Any]:
        """
        Return latest event bus summary.
        """

        events = self.safe_read_json("events")

        return {
            "command": "events",
            "events_published_this_run": events.get("events_published_this_run"),
            "total_events_recorded": events.get("total_events_recorded"),
            "known_event_types_count": events.get("known_event_types_count"),
            "event_types_seen_this_run": events.get("event_types_seen_this_run"),
            "source_organs_seen_this_run": events.get("source_organs_seen_this_run"),
            "safety_summary": events.get("safety_summary"),
        }

    def command_metabolism(self) -> Dict[str, Any]:
        """
        Return latest metabolism summary.
        """

        metabolism = self.safe_read_json("metabolism")

        return {
            "command": "metabolism",
            "run_id": metabolism.get("run_id"),
            "runtime_mode": metabolism.get("runtime_mode"),
            "current_phase": metabolism.get("current_phase"),
            "cycle_count": metabolism.get("cycle_count"),
            "max_cycles": metabolism.get("max_cycles"),
            "heartbeat_count": metabolism.get("heartbeat_count"),
            "shutdown_recorded": metabolism.get("shutdown_recorded"),
            "finalized": metabolism.get("finalized"),
            "safety_summary": metabolism.get("safety_summary"),
        }

    def command_reflex(self) -> Dict[str, Any]:
        """
        Return latest reflex summary.
        """

        reflex = self.safe_read_json("reflex")

        return {
            "command": "reflex",
            "reflex_mode": reflex.get("reflex_mode"),
            "checks_performed_this_run": reflex.get("checks_performed_this_run"),
            "reflexes_triggered_this_run": reflex.get("reflexes_triggered_this_run"),
            "warnings_raised_this_run": reflex.get("warnings_raised_this_run"),
            "safe_actions_performed_this_run": reflex.get("safe_actions_performed_this_run"),
            "unsafe_actions_blocked_this_run": reflex.get("unsafe_actions_blocked_this_run"),
            "safety_summary": reflex.get("safety_summary"),
        }

    def command_immune(self) -> Dict[str, Any]:
        """
        Return latest immune summary.
        """

        immune = self.safe_read_json("immune")

        return {
            "command": "immune",
            "immune_mode": immune.get("immune_mode"),
            "deny_by_default": immune.get("deny_by_default"),
            "decisions_this_run": immune.get("decisions_this_run"),
            "allowed_this_run": immune.get("allowed_this_run"),
            "denied_this_run": immune.get("denied_this_run"),
            "validation_checks_this_run": immune.get("validation_checks_this_run"),
            "policy_summary": immune.get("policy_summary"),
            "safety_summary": immune.get("safety_summary"),
        }

    def command_safety(self) -> Dict[str, Any]:
        """
        Return combined safety posture.
        """

        immune = self.safe_read_json("immune", missing_ok=True)
        reflex = self.safe_read_json("reflex", missing_ok=True)
        cartography = self.safe_read_json("cartography", missing_ok=True)
        memory = self.safe_read_json("memory", missing_ok=True)
        events = self.safe_read_json("events", missing_ok=True)
        metabolism = self.safe_read_json("metabolism", missing_ok=True)

        return {
            "command": "safety",
            "immune": {
                "immune_mode": immune.get("immune_mode") if immune else None,
                "deny_by_default": immune.get("deny_by_default") if immune else None,
                "command_execution_allowed": immune.get("policy_summary", {}).get("command_execution_allowed") if immune else None,
                "tool_execution_allowed": immune.get("policy_summary", {}).get("tool_execution_allowed") if immune else None,
                "active_network_cartography_allowed": immune.get("policy_summary", {}).get("active_network_cartography_allowed") if immune else None,
            },
            "reflex": {
                "unsafe_actions_blocked_this_run": reflex.get("unsafe_actions_blocked_this_run") if reflex else None,
                "active_network_scanning_enabled": reflex.get("safety_summary", {}).get("active_network_scanning_enabled") if reflex else None,
            },
            "cartography": {
                "active_discovery_performed": cartography.get("active_discovery_performed") if cartography else None,
                "active_probes_sent": cartography.get("dry_run_plan", {}).get("active_probes_sent") if cartography else None,
            },
            "memory": {
                "raw_environment_values_stored": memory.get("safety_summary", {}).get("raw_environment_values_stored") if memory else None,
                "secrets_stored": memory.get("safety_summary", {}).get("secrets_stored") if memory else None,
            },
            "events": {
                "network_access_performed": events.get("safety_summary", {}).get("network_access_performed") if events else None,
                "commands_executed": events.get("safety_summary", {}).get("commands_executed") if events else None,
            },
            "metabolism": {
                "continuous_mode_enabled": metabolism.get("continuous_mode_enabled") if metabolism else None,
                "background_workers_started": metabolism.get("safety_summary", {}).get("background_workers_started") if metabolism else None,
            },
        }

    # ========================================================
    # APPROVED FILE READING
    # ========================================================

    def safe_read_json(
        self,
        key: str,
        missing_ok: bool = False,
    ) -> Dict[str, Any]:
        """
        Read an approved JSON file by key.

        This method does not accept arbitrary paths.
        """

        if key not in self.APPROVED_READ_PATHS:
            raise InterfaceSafetyError(
                f"Interface read key is not approved: {key}"
            )

        path = Path(self.APPROVED_READ_PATHS[key])

        if not self.is_approved_read_path(path):
            raise InterfaceSafetyError(
                f"Resolved path is not approved for interface read: {path}"
            )

        if not path.exists():
            if missing_ok:
                return {}

            raise InterfaceReadError(
                f"Approved report file does not exist yet: {path}"
            )

        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)

        except json.JSONDecodeError as error:
            raise InterfaceReadError(
                f"Approved report file could not be parsed: {path}: {error}"
            ) from error

        except OSError as error:
            raise InterfaceReadError(
                f"Approved report file could not be read: {path}: {error}"
            ) from error

        if not isinstance(data, dict):
            raise InterfaceReadError(
                f"Approved report file must contain a JSON object: {path}"
            )

        self.reads_performed_this_run += 1

        return data

    def is_approved_read_path(self, path: Path) -> bool:
        """
        Confirm that a path is exactly one of the approved read paths.
        """

        normalized = str(path).replace("\\", "/")

        approved = {
            str(Path(value)).replace("\\", "/")
            for value in self.APPROVED_READ_PATHS.values()
        }

        return normalized in approved

    # ========================================================
    # OUTPUT / PRESENTATION HELPERS
    # ========================================================

    def print_command_result(self, result: Dict[str, Any]) -> None:
        """
        Print command result in readable JSON.

        This keeps CLI output consistent.
        """

        print(json.dumps(result, indent=2, sort_keys=False))

    # ========================================================
    # LOGGING AND STATE
    # ========================================================

    def log_interface_event(
        self,
        event_type: str,
        command: str,
        result: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Append interface event to interface_log.jsonl.
        """

        details = details or {}
        self.validate_details_safety(details)

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        record = {
            "schema_version": self.SCHEMA_VERSION,
            "interface_event_id": self.generate_interface_event_id(event_type),
            "timestamp_utc": self.utc_now_iso(),
            "interface_mode": self.INTERFACE_MODE,
            "event_type": event_type,
            "command": command,
            "result": result,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_build": persistent["current_build"],
            "details": copy.deepcopy(details),
            "safety": {
                "commands_executed": False,
                "network_access_performed": False,
                "arbitrary_files_read": False,
                "source_code_modified": False,
                "memory_deleted": False,
                "active_cartography_enabled": False,
                "web_server_started": False,
                "background_daemon_started": False,
                "immune_bypassed": False,
            },
        }

        self.validate_interface_record(record)

        try:
            self.interface_log_path.parent.mkdir(parents=True, exist_ok=True)

            with self.interface_log_path.open("a", encoding="utf-8") as file:
                json.dump(record, file, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise InterfaceLogError(
                f"Could not append interface event: {error}"
            ) from error

        self.interface_events_written_this_run += 1

        return copy.deepcopy(record)

    def publish_interface_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Publish an interface event through Event Bus if available.
        """

        if self.event_bus is None:
            return

        self.event_bus.publish_event(
            event_type=event_type,
            source_organ="InterfaceOrgan",
            payload=payload,
            priority="info",
        )

    def generate_latest_interface_state(self) -> Dict[str, Any]:
        """
        Generate latest_interface_state.json.
        """

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        state = {
            "schema_version": self.SCHEMA_VERSION,
            "state_timestamp_utc": self.utc_now_iso(),
            "organism_name": persistent["organism_name"],
            "lineage_id": persistent["lineage_id"],
            "runtime_instance_id": runtime["runtime_instance_id"],
            "interface_root": str(self.interface_root),
            "interface_log_path": str(self.interface_log_path),
            "latest_state_path": str(self.latest_state_path),
            "interface_mode": self.INTERFACE_MODE,
            "valid_commands": list(self.VALID_COMMANDS),
            "approved_read_keys": sorted(self.APPROVED_READ_PATHS.keys()),
            "commands_handled_this_run": self.commands_handled_this_run,
            "reads_performed_this_run": self.reads_performed_this_run,
            "invalid_commands_this_run": self.invalid_commands_this_run,
            "interface_events_written_this_run": self.interface_events_written_this_run,
            "safety_boundary": self.get_safety_boundary(),
            "safety_summary": {
                "commands_executed": False,
                "network_access_performed": False,
                "arbitrary_files_read": False,
                "source_code_modified": False,
                "memory_deleted": False,
                "active_cartography_enabled": False,
                "web_server_started": False,
                "background_daemon_started": False,
                "immune_bypassed": False,
            },
        }

        self.validate_interface_state(state)
        self.save_latest_interface_state(state)

        return copy.deepcopy(state)

    def save_latest_interface_state(self, state: Dict[str, Any]) -> None:
        """
        Save latest_interface_state.json.
        """

        try:
            self.latest_state_path.parent.mkdir(parents=True, exist_ok=True)

            with self.latest_state_path.open("w", encoding="utf-8") as file:
                json.dump(state, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise InterfaceStateError(
                f"Could not save latest interface state: {error}"
            ) from error

    def get_interface_report(self, latest_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return a short interface report.
        """

        if latest_state is None:
            latest_state = self.generate_latest_interface_state()

        return {
            "interface_root": latest_state["interface_root"],
            "interface_mode": latest_state["interface_mode"],
            "valid_commands_count": len(latest_state["valid_commands"]),
            "approved_read_keys_count": len(latest_state["approved_read_keys"]),
            "commands_handled_this_run": latest_state["commands_handled_this_run"],
            "reads_performed_this_run": latest_state["reads_performed_this_run"],
            "invalid_commands_this_run": latest_state["invalid_commands_this_run"],
            "interface_events_written_this_run": latest_state["interface_events_written_this_run"],
            "safety_summary": latest_state["safety_summary"],
        }

    # ========================================================
    # VALIDATION AND SAFETY
    # ========================================================

    def validate_interface_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate interface log record.
        """

        required_fields = [
            "schema_version",
            "interface_event_id",
            "timestamp_utc",
            "interface_mode",
            "event_type",
            "command",
            "result",
            "source_runtime_instance_id",
            "source_lineage_id",
            "source_organism_name",
            "source_build",
            "details",
            "safety",
        ]

        for field in required_fields:
            if field not in record:
                raise InterfaceLogError(
                    f"Missing required interface record field: {field}"
                )

        return self.validate_safety_flags(record["safety"])

    def validate_interface_state(self, state: Dict[str, Any]) -> bool:
        """
        Validate latest interface state.
        """

        required_fields = [
            "schema_version",
            "state_timestamp_utc",
            "organism_name",
            "lineage_id",
            "runtime_instance_id",
            "interface_root",
            "interface_log_path",
            "latest_state_path",
            "interface_mode",
            "valid_commands",
            "approved_read_keys",
            "commands_handled_this_run",
            "reads_performed_this_run",
            "invalid_commands_this_run",
            "interface_events_written_this_run",
            "safety_boundary",
            "safety_summary",
        ]

        for field in required_fields:
            if field not in state:
                raise InterfaceStateError(
                    f"Missing required interface state field: {field}"
                )

        return self.validate_safety_flags(state["safety_summary"])

    def validate_safety_flags(self, safety: Dict[str, Any]) -> bool:
        """
        Validate safety flags remain false.
        """

        prohibited_true_flags = [
            "commands_executed",
            "network_access_performed",
            "arbitrary_files_read",
            "source_code_modified",
            "memory_deleted",
            "active_cartography_enabled",
            "web_server_started",
            "background_daemon_started",
            "immune_bypassed",
        ]

        for flag in prohibited_true_flags:
            if safety.get(flag) is True:
                raise InterfaceSafetyError(
                    f"Interface safety violation. This flag must be false: {flag}"
                )

        return True

    def validate_details_safety(self, details: Dict[str, Any]) -> bool:
        """
        Validate detail payloads for prohibited key names.
        """

        prohibited = self.find_prohibited_keys(details)

        if prohibited:
            raise InterfaceSafetyError(
                f"Interface details contain prohibited key names: {prohibited}"
            )

        return True

    def find_prohibited_keys(self, value: Any, path: str = "") -> List[str]:
        """
        Recursively find prohibited key names.
        """

        found = []

        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text

                if key_text in self.PROHIBITED_DETAIL_KEYS:
                    found.append(child_path)

                found.extend(self.find_prohibited_keys(child, child_path))

        elif isinstance(value, list):
            for index, item in enumerate(value):
                child_path = f"{path}[{index}]"
                found.extend(self.find_prohibited_keys(item, child_path))

        return found

    def get_safety_boundary(self) -> Dict[str, bool]:
        """
        Return Interface Organ safety boundary.
        """

        return {
            "may_parse_local_cli_args": True,
            "may_read_approved_json_reports": True,
            "may_print_local_status": True,
            "may_write_interface_log": True,
            "may_generate_interface_state": True,
            "may_publish_interface_events": True,

            "may_execute_commands": False,
            "may_access_network": False,
            "may_read_arbitrary_files": False,
            "may_modify_source_code": False,
            "may_delete_memory": False,
            "may_enable_active_cartography": False,
            "may_modify_immune_policy": False,
            "may_start_web_server": False,
            "may_start_background_daemon": False,
            "may_bypass_immune": False,
        }
