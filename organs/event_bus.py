"""
============================================================
EVENT BUS / NERVOUS SYSTEM ORGAN
============================================================

Project:
    Digital Organism

Build:
    0.6.0

Organism Name:
    ContinuityNode

Organ:
    Event Bus / Nervous System Organ

File:
    organs/event_bus.py

Primary Function:
    Route internal organism events between organs using a controlled
    local structured event system.

Scientific / Clinical Description:
    The Event Bus Organ is a local message-routing and event-recording
    component.

    It does not create consciousness, agency, intent, autonomy, or
    biological nervous activity. The nervous-system metaphor is used
    architecturally to describe event transmission between modular
    software organs.

Relationship To Existing Organs:
    Core Identity Organ answers:
        Who am I?

    Sensorium Organ answers:
        Where am I running?
        What does the host already know?

    Network Cartography Organ answers:
        What would I be allowed to map if active discovery were later
        approved?

    Memory Organ answers:
        What have I observed before?

    Event Bus Organ answers:
        What happened internally, and which organs should know?

Important Safety Boundary:
    The Event Bus does not perform actions.

    It does not:
        - execute commands
        - access the network
        - scan files
        - modify other organs
        - trigger active discovery
        - make decisions
        - bypass immune/safety boundaries
        - mutate event payloads after publication

Storage Model:
    data/events/
        event_bus_log.jsonl
        latest_event_bus_state.json

Build 0.6.0 Behavior:
    - Create event directory structure.
    - Publish structured events.
    - Append event records to JSONL log.
    - Track event counts by type/source.
    - Maintain in-memory subscriber registry.
    - Support safe local handler callbacks.
    - Generate latest_event_bus_state.json.
"""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================


class EventBusError(Exception):
    """
    Base exception for all Event Bus Organ errors.
    """


class EventValidationError(EventBusError):
    """
    Raised when an event is malformed or unsafe.
    """


class EventLogError(EventBusError):
    """
    Raised when the event bus log cannot be written.
    """


class EventStateError(EventBusError):
    """
    Raised when the latest event bus state cannot be generated or saved.
    """


class EventSubscriptionError(EventBusError):
    """
    Raised when subscription registration is invalid.
    """


class EventSafetyError(EventBusError):
    """
    Raised when an event bus operation violates the safety boundary.
    """


# ============================================================
# EVENT BUS ORGAN CLASS
# ============================================================


class EventBusOrgan:
    """
    Local structured event router for ContinuityNode.

    The Event Bus records and routes events.

    It does not perform actions.

    It is intentionally simple in Build 0.6.0:
        - local-only
        - in-process only
        - append-only JSONL event log
        - no network transport
        - no background daemon
        - no async queue
        - no external broker
    """

    SCHEMA_VERSION = "1.0.0"

    VALID_EVENT_PRIORITIES = [
        "debug",
        "info",
        "notice",
        "warning",
        "error",
        "critical",
    ]

    DEFAULT_PRIORITY = "info"

    # --------------------------------------------------------
    # These event types are not an allowlist.
    #
    # They are the known event types introduced so far.
    #
    # Future organs may publish additional event types as long as
    # those events validate against the general event schema.
    # --------------------------------------------------------
    KNOWN_EVENT_TYPES = [
        "identity.initialized",
        "sensorium.snapshot.created",
        "cartography.plan.created",
        "memory.record.stored",
        "memory.records.stored",
        "memory.summary.generated",
        "event_bus.initialized",
        "event_bus.state.generated",
        "reflex.warning.raised",
        "immune.action.blocked",
        "metabolism.heartbeat",
        "tool_use.command.requested",
        "tool_use.command.denied",
        "replication.lineage.created",
    ]

    # --------------------------------------------------------
    # Obvious unsafe payload keys.
    #
    # Events should be summaries and references, not secret dumps.
    # --------------------------------------------------------
    PROHIBITED_PAYLOAD_KEYS = [
        "raw_environment_values",
        "environment_values",
        "secret_values",
        "token_values",
        "password_values",
        "credential_values",
        "cookie_values",
        "private_key",
        "raw_private_key",
    ]

    def __init__(
        self,
        core_identity: Any,
        event_root: str = "data/events",
    ) -> None:
        """
        Initialize the Event Bus Organ.

        Startup sequence:
            1. Store Core Identity reference.
            2. Store event paths.
            3. Create event directory.
            4. Initialize in-memory subscriber registry.
            5. Initialize per-run event counters.
            6. Publish event_bus.initialized event.

        The Event Bus does not automatically call other organs.
        """

        self.core_identity = core_identity
        self.event_root = Path(event_root)
        self.event_log_path = self.event_root / "event_bus_log.jsonl"
        self.latest_state_path = self.event_root / "latest_event_bus_state.json"

        self.subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}

        self.events_published_this_run = 0
        self.event_types_seen_this_run: Dict[str, int] = {}
        self.source_organs_seen_this_run: Dict[str, int] = {}

        self.ensure_event_structure()

        # Publish initialization event after the structure exists.
        self.publish_event(
            event_type="event_bus.initialized",
            source_organ="EventBusOrgan",
            payload={
                "event_root": str(self.event_root),
                "event_log_path": str(self.event_log_path),
                "latest_state_path": str(self.latest_state_path),
            },
        )

    # ========================================================
    # TIME AND ID HELPERS
    # ========================================================

    def utc_now_iso(self) -> str:
        """
        Return the current UTC timestamp in ISO-8601 Z format.
        """

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_event_id(self, event_type: str) -> str:
        """
        Generate a unique event ID.

        Example:
            evt-sensorium-snapshot-created-20260620T120000Z-a91f2c
        """

        safe_type = event_type.replace(".", "-").replace("_", "-")
        timestamp = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        short_id = uuid.uuid4().hex[:6]

        return f"evt-{safe_type}-{timestamp}-{short_id}"

    # ========================================================
    # STRUCTURE
    # ========================================================

    def ensure_event_structure(self) -> None:
        """
        Create the controlled event directory structure.

        This method only creates directories under event_root.
        """

        try:
            self.event_root.mkdir(parents=True, exist_ok=True)

        except OSError as error:
            raise EventStateError(
                f"Could not create event directory structure: {error}"
            ) from error

    # ========================================================
    # SUBSCRIPTION MANAGEMENT
    # ========================================================

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[Dict[str, Any]], None],
    ) -> None:
        """
        Subscribe a local handler to an event type.

        Build 0.6.0 subscription model:
            - in-process only
            - local function callbacks only
            - no network transport
            - no external webhooks
            - no background dispatch worker

        Important:
            Handlers should remain safe.

            The Event Bus itself does not grant permissions. A future
            Immune Organ should validate action requests made as a
            result of event handling.
        """

        if not isinstance(event_type, str) or not event_type.strip():
            raise EventSubscriptionError(
                "event_type must be a non-empty string."
            )

        if not callable(handler):
            raise EventSubscriptionError(
                "handler must be callable."
            )

        normalized_type = event_type.strip()

        self.subscribers.setdefault(normalized_type, []).append(handler)

    def get_subscribers_for_event(self, event_type: str) -> List[Callable[[Dict[str, Any]], None]]:
        """
        Return local handlers subscribed to an event type.

        Also supports wildcard subscriber:

            "*"

        Wildcard subscribers receive all events.
        """

        direct = self.subscribers.get(event_type, [])
        wildcard = self.subscribers.get("*", [])

        return list(direct) + list(wildcard)

    # ========================================================
    # EVENT PUBLICATION
    # ========================================================

    def publish_event(
        self,
        event_type: str,
        source_organ: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: str = DEFAULT_PRIORITY,
    ) -> Dict[str, Any]:
        """
        Publish a structured event.

        Event publication steps:
            1. Build event object.
            2. Validate event object.
            3. Append event to event_bus_log.jsonl.
            4. Update in-memory counters.
            5. Dispatch event to local subscribers.
            6. Return a copy of the event.

        Safety:
            Publishing an event is not the same as performing an action.

            Events may describe what happened, but they do not directly
            grant permission to execute commands, scan networks, delete
            files, or modify systems.
        """

        if payload is None:
            payload = {}

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        event = {
            "schema_version": self.SCHEMA_VERSION,
            "event_id": self.generate_event_id(event_type),
            "event_type": event_type,
            "priority": priority,
            "timestamp_utc": self.utc_now_iso(),
            "source_organ": source_organ,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_build": persistent["current_build"],
            "payload": copy.deepcopy(payload),
            "safety": {
                "event_bus_performed_action": False,
                "commands_executed": False,
                "network_access_performed": False,
                "filesystem_scan_performed": False,
                "other_organs_mutated": False,
            },
        }

        self.validate_event(event)
        self.append_event_to_log(event)
        self.update_counters(event)
        self.dispatch_event(event)

        return copy.deepcopy(event)

    def validate_event(self, event: Dict[str, Any]) -> bool:
        """
        Validate event structure and safety claims.
        """

        required_fields = [
            "schema_version",
            "event_id",
            "event_type",
            "priority",
            "timestamp_utc",
            "source_organ",
            "source_runtime_instance_id",
            "source_lineage_id",
            "source_organism_name",
            "source_build",
            "payload",
            "safety",
        ]

        for field in required_fields:
            if field not in event:
                raise EventValidationError(
                    f"Missing required event field: {field}"
                )

        if not isinstance(event["event_type"], str) or not event["event_type"].strip():
            raise EventValidationError(
                "event_type must be a non-empty string."
            )

        if event["priority"] not in self.VALID_EVENT_PRIORITIES:
            raise EventValidationError(
                f"Invalid event priority: {event['priority']}"
            )

        if not isinstance(event["payload"], dict):
            raise EventValidationError(
                "event payload must be a dictionary."
            )

        prohibited_keys = self.find_prohibited_payload_keys(event["payload"])

        if prohibited_keys:
            raise EventSafetyError(
                f"Event payload contains prohibited key names: {prohibited_keys}"
            )

        safety = event["safety"]

        if not isinstance(safety, dict):
            raise EventValidationError(
                "event safety field must be a dictionary."
            )

        prohibited_true_flags = [
            "event_bus_performed_action",
            "commands_executed",
            "network_access_performed",
            "filesystem_scan_performed",
            "other_organs_mutated",
        ]

        for flag in prohibited_true_flags:
            if safety.get(flag) is True:
                raise EventSafetyError(
                    f"Event Bus safety violation. This flag must be false: {flag}"
                )

        return True

    def append_event_to_log(self, event: Dict[str, Any]) -> None:
        """
        Append event to event_bus_log.jsonl.

        The event log is append-only in this build.
        """

        try:
            self.event_log_path.parent.mkdir(parents=True, exist_ok=True)

            with self.event_log_path.open("a", encoding="utf-8") as file:
                json.dump(event, file, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise EventLogError(
                f"Could not append event to event bus log: {error}"
            ) from error

    def update_counters(self, event: Dict[str, Any]) -> None:
        """
        Update in-memory event counters for this run.
        """

        self.events_published_this_run += 1

        event_type = event["event_type"]
        source_organ = event["source_organ"]

        self.event_types_seen_this_run[event_type] = (
            self.event_types_seen_this_run.get(event_type, 0) + 1
        )

        self.source_organs_seen_this_run[source_organ] = (
            self.source_organs_seen_this_run.get(source_organ, 0) + 1
        )

    def dispatch_event(self, event: Dict[str, Any]) -> None:
        """
        Dispatch an event to local in-process subscribers.

        If a subscriber raises an exception, the Event Bus records a
        warning event but does not re-raise the subscriber exception.

        This prevents one handler from breaking the full organism run.

        Important:
            Dispatch is local only.

            No external network callbacks.
            No webhooks.
            No background queue.
        """

        handlers = self.get_subscribers_for_event(event["event_type"])

        for handler in handlers:
            try:
                handler(copy.deepcopy(event))

            except Exception as error:
                # Avoid infinite recursion if handler failure occurs
                # while publishing a handler failure event.
                if event["event_type"] == "event_bus.subscriber_error":
                    continue

                self.publish_event(
                    event_type="event_bus.subscriber_error",
                    source_organ="EventBusOrgan",
                    payload={
                        "failed_event_id": event.get("event_id"),
                        "failed_event_type": event.get("event_type"),
                        "handler_repr": repr(handler),
                        "error": str(error),
                    },
                    priority="warning",
                )

    # ========================================================
    # STATE GENERATION
    # ========================================================

    def generate_latest_event_bus_state(self) -> Dict[str, Any]:
        """
        Generate latest_event_bus_state.json.

        This summarizes event bus activity for the current run.
        """

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        total_events_recorded = self.count_events_in_log()

        state = {
            "schema_version": self.SCHEMA_VERSION,
            "state_timestamp_utc": self.utc_now_iso(),
            "organism_name": persistent["organism_name"],
            "lineage_id": persistent["lineage_id"],
            "runtime_instance_id": runtime["runtime_instance_id"],
            "event_root": str(self.event_root),
            "event_log_path": str(self.event_log_path),
            "latest_state_path": str(self.latest_state_path),
            "events_published_this_run": self.events_published_this_run,
            "total_events_recorded": total_events_recorded,
            "known_event_types": list(self.KNOWN_EVENT_TYPES),
            "known_event_types_count": len(self.KNOWN_EVENT_TYPES),
            "event_types_seen_this_run": copy.deepcopy(self.event_types_seen_this_run),
            "source_organs_seen_this_run": copy.deepcopy(self.source_organs_seen_this_run),
            "subscribers_registered_count": self.count_registered_subscribers(),
            "safety_boundary": self.get_safety_boundary(),
            "safety_summary": {
                "actions_performed": False,
                "commands_executed": False,
                "network_access_performed": False,
                "filesystem_scan_performed": False,
                "other_organs_mutated": False,
            },
        }

        self.save_latest_event_bus_state(state)

        # Avoid generating this state event before state writing succeeds.
        self.publish_event(
            event_type="event_bus.state.generated",
            source_organ="EventBusOrgan",
            payload={
                "latest_state_path": str(self.latest_state_path),
                "events_published_this_run": self.events_published_this_run,
                "total_events_recorded": total_events_recorded,
            },
        )

        return copy.deepcopy(state)

    def save_latest_event_bus_state(self, state: Dict[str, Any]) -> None:
        """
        Save latest_event_bus_state.json.
        """

        try:
            self.latest_state_path.parent.mkdir(parents=True, exist_ok=True)

            with self.latest_state_path.open("w", encoding="utf-8") as file:
                json.dump(state, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise EventStateError(
                f"Could not save latest event bus state: {error}"
            ) from error

    def count_events_in_log(self) -> int:
        """
        Count events currently recorded in event_bus_log.jsonl.

        This is a lightweight line count.
        """

        if not self.event_log_path.exists():
            return 0

        try:
            with self.event_log_path.open("r", encoding="utf-8") as file:
                return sum(1 for line in file if line.strip())

        except OSError as error:
            raise EventLogError(
                f"Could not count event bus log entries: {error}"
            ) from error

    def count_registered_subscribers(self) -> int:
        """
        Count registered local subscribers.
        """

        return sum(len(handlers) for handlers in self.subscribers.values())

    def get_event_bus_report(self, latest_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return a short Event Bus report for console output.
        """

        if latest_state is None:
            latest_state = self.generate_latest_event_bus_state()

        return {
            "event_root": latest_state["event_root"],
            "events_published_this_run": latest_state["events_published_this_run"],
            "total_events_recorded": latest_state["total_events_recorded"],
            "known_event_types_count": latest_state["known_event_types_count"],
            "subscribers_registered_count": latest_state["subscribers_registered_count"],
            "event_types_seen_this_run": latest_state["event_types_seen_this_run"],
            "source_organs_seen_this_run": latest_state["source_organs_seen_this_run"],
            "safety_summary": latest_state["safety_summary"],
        }

    # ========================================================
    # SAFETY AND UTILITY METHODS
    # ========================================================

    def find_prohibited_payload_keys(self, value: Any, path: str = "") -> List[str]:
        """
        Recursively find prohibited key names in event payloads.
        """

        found = []

        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text

                if key_text in self.PROHIBITED_PAYLOAD_KEYS:
                    found.append(child_path)

                found.extend(self.find_prohibited_payload_keys(child, child_path))

        elif isinstance(value, list):
            for index, item in enumerate(value):
                child_path = f"{path}[{index}]"
                found.extend(self.find_prohibited_payload_keys(item, child_path))

        return found

    def get_safety_boundary(self) -> Dict[str, bool]:
        """
        Return the Event Bus safety boundary.
        """

        return {
            "may_publish_local_events": True,
            "may_append_event_log": True,
            "may_generate_event_bus_state": True,
            "may_register_local_subscribers": True,
            "may_dispatch_to_local_in_process_handlers": True,

            "may_execute_commands": False,
            "may_access_network": False,
            "may_scan_filesystem": False,
            "may_mutate_other_organs": False,
            "may_trigger_active_network_discovery": False,
            "may_bypass_immune_or_safety_boundaries": False,
            "may_send_external_webhooks": False,
            "may_run_background_daemon": False,
        }
