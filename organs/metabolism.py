"""
============================================================
METABOLISM ORGAN
============================================================

Project:
    Digital Organism

Build:
    0.7.0

Organism Name:
    ContinuityNode

Organ:
    Metabolism Organ

File:
    organs/metabolism.py

Primary Function:
    Manage and record controlled runtime cycles, lifecycle phases,
    heartbeat records, and shutdown state.

Scientific / Clinical Description:
    The Metabolism Organ is a runtime-cycle and lifecycle-recording
    component.

    It does not create biological metabolism, life, consciousness,
    agency, or autonomous drive. The metabolism metaphor is used
    architecturally to describe controlled runtime rhythm, cycle
    progression, heartbeat records, and bounded execution flow.

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

    Metabolism Organ answers:
        What phase am I in?
        How many cycles have I run?
        Did I heartbeat?
        Did I shut down cleanly?

Important Safety Boundary:
    The Metabolism Organ does not create an infinite loop.

    It does not:
        - run forever
        - spawn background workers
        - execute commands
        - access the network
        - scan files
        - directly mutate unrelated organs
        - bypass safety boundaries
        - perform active network discovery

Storage Model:
    data/metabolism/
        metabolism_state.json
        metabolism_cycles.jsonl

Build 0.7.0 Behavior:
    - Create metabolism directory structure.
    - Create a run ID.
    - Record phases.
    - Record heartbeat events.
    - Record cycle start/end events.
    - Enforce max cycle count.
    - Generate metabolism_state.json.
    - Append cycle/phase records to metabolism_cycles.jsonl.
"""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================


class MetabolismError(Exception):
    """
    Base exception for all Metabolism Organ errors.
    """


class MetabolismStateError(MetabolismError):
    """
    Raised when metabolism state cannot be created, validated, or saved.
    """


class MetabolismCycleError(MetabolismError):
    """
    Raised when a cycle record cannot be written or a cycle rule is
    violated.
    """


class MetabolismSafetyError(MetabolismError):
    """
    Raised when a metabolism operation violates the safety boundary.
    """


# ============================================================
# METABOLISM ORGAN CLASS
# ============================================================


class MetabolismOrgan:
    """
    Records controlled runtime lifecycle and cycle state.

    Build 0.7.0 is single-cycle by default.

    The organ is not a scheduler, daemon, or autonomous loop.

    It records:
        - run identity
        - current phase
        - phase history
        - heartbeat count
        - cycle count
        - cycle start/end records
        - shutdown state
    """

    SCHEMA_VERSION = "1.0.0"

    VALID_RUNTIME_MODES = [
        "SINGLE_CYCLE",
    ]

    VALID_PHASES = [
        "INITIALIZED",
        "BOOT",
        "OBSERVE",
        "CARTOGRAPHY_DRY_RUN",
        "MEMORY_COMMIT",
        "EVENT_STATE",
        "IDLE",
        "SHUTDOWN",
        "ERROR",
    ]

    VALID_CYCLE_EVENTS = [
        "metabolism.initialized",
        "metabolism.phase.recorded",
        "metabolism.heartbeat",
        "metabolism.cycle.started",
        "metabolism.cycle.ended",
        "metabolism.run.finalized",
    ]

    def __init__(
        self,
        core_identity: Any,
        event_bus: Optional[Any] = None,
        metabolism_root: str = "data/metabolism",
        runtime_mode: str = "SINGLE_CYCLE",
        max_cycles: int = 1,
    ) -> None:
        """
        Initialize the Metabolism Organ.

        Parameters:
            core_identity:
                Initialized CoreIdentityOrgan instance.

            event_bus:
                Optional EventBusOrgan instance.

            metabolism_root:
                Root directory for metabolism output.

            runtime_mode:
                Build 0.7.0 supports SINGLE_CYCLE only.

            max_cycles:
                Maximum permitted cycles for this run.

                Build 0.7.0 default:
                    1
        """

        self.core_identity = core_identity
        self.event_bus = event_bus
        self.metabolism_root = Path(metabolism_root)

        self.state_path = self.metabolism_root / "metabolism_state.json"
        self.cycles_log_path = self.metabolism_root / "metabolism_cycles.jsonl"

        self.runtime_mode = runtime_mode.upper()
        self.max_cycles = int(max_cycles)

        self.run_id = self.generate_run_id()

        self.current_phase = "INITIALIZED"
        self.cycle_count = 0
        self.heartbeat_count = 0
        self.shutdown_recorded = False
        self.finalized = False

        self.phase_history = []

        self.validate_runtime_configuration()
        self.ensure_metabolism_structure()

        self.record_internal_event(
            event_type="metabolism.initialized",
            phase_name="INITIALIZED",
            source_organ="MetabolismOrgan",
            details={
                "runtime_mode": self.runtime_mode,
                "max_cycles": self.max_cycles,
                "continuous_mode_enabled": False,
            },
        )

        self.save_state()

    # ========================================================
    # TIME AND ID HELPERS
    # ========================================================

    def utc_now_iso(self) -> str:
        """
        Return the current UTC timestamp in ISO-8601 Z format.
        """

        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def generate_run_id(self) -> str:
        """
        Generate a unique metabolism run ID.
        """

        timestamp = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        short_id = uuid.uuid4().hex[:6]

        return f"metabolism-run-{timestamp}-{short_id}"

    def generate_cycle_record_id(self, event_type: str) -> str:
        """
        Generate a unique cycle/phase record ID.
        """

        safe_type = event_type.replace(".", "-").replace("_", "-")
        timestamp = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        short_id = uuid.uuid4().hex[:6]

        return f"metabolism-{safe_type}-{timestamp}-{short_id}"

    # ========================================================
    # STRUCTURE AND CONFIGURATION
    # ========================================================

    def ensure_metabolism_structure(self) -> None:
        """
        Create the controlled metabolism directory structure.
        """

        try:
            self.metabolism_root.mkdir(parents=True, exist_ok=True)

        except OSError as error:
            raise MetabolismStateError(
                f"Could not create metabolism directory structure: {error}"
            ) from error

    def validate_runtime_configuration(self) -> bool:
        """
        Validate runtime mode and cycle limits.

        Build 0.7.0 only allows SINGLE_CYCLE.
        """

        if self.runtime_mode not in self.VALID_RUNTIME_MODES:
            raise MetabolismSafetyError(
                f"Runtime mode is not allowed in Build 0.7.0: {self.runtime_mode}"
            )

        if self.max_cycles < 1:
            raise MetabolismSafetyError(
                "max_cycles must be at least 1."
            )

        if self.max_cycles > 1:
            raise MetabolismSafetyError(
                "Build 0.7.0 does not allow max_cycles greater than 1."
            )

        return True

    # ========================================================
    # PHASE AND CYCLE RECORDING
    # ========================================================

    def record_phase(
        self,
        phase_name: str,
        source_organ: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a lifecycle phase.

        Phase recording is observational. It does not cause the phase's
        work to happen. The caller performs work explicitly.
        """

        normalized_phase = phase_name.upper()

        if normalized_phase not in self.VALID_PHASES:
            raise MetabolismCycleError(
                f"Invalid metabolism phase: {phase_name}"
            )

        self.current_phase = normalized_phase

        event = self.record_internal_event(
            event_type="metabolism.phase.recorded",
            phase_name=normalized_phase,
            source_organ=source_organ,
            details=details or {},
        )

        self.phase_history.append(
            {
                "phase_name": normalized_phase,
                "timestamp_utc": event["timestamp_utc"],
                "source_organ": source_organ,
            }
        )

        self.publish_to_event_bus(
            event_type="metabolism.phase.recorded",
            payload={
                "phase_name": normalized_phase,
                "source_organ": source_organ,
                "record_id": event["record_id"],
            },
        )

        self.save_state()

        return copy.deepcopy(event)

    def heartbeat(
        self,
        phase_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Record a heartbeat.

        A heartbeat is a small structured runtime-alive marker.

        It does not create a loop.
        It does not schedule future work.
        """

        self.heartbeat_count += 1

        phase = (phase_name or self.current_phase).upper()

        event = self.record_internal_event(
            event_type="metabolism.heartbeat",
            phase_name=phase,
            source_organ="MetabolismOrgan",
            details=details or {},
        )

        self.publish_to_event_bus(
            event_type="metabolism.heartbeat",
            payload={
                "heartbeat_count": self.heartbeat_count,
                "phase_name": phase,
                "record_id": event["record_id"],
            },
        )

        self.save_state()

        return copy.deepcopy(event)

    def start_cycle(
        self,
        cycle_name: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Start a controlled cycle.

        Build 0.7.0 allows exactly one cycle.
        """

        if self.cycle_count >= self.max_cycles:
            raise MetabolismSafetyError(
                "Maximum cycle count reached. Refusing to start another cycle."
            )

        self.cycle_count += 1

        event = self.record_internal_event(
            event_type="metabolism.cycle.started",
            phase_name=self.current_phase,
            source_organ="MetabolismOrgan",
            details={
                "cycle_name": cycle_name,
                "cycle_count": self.cycle_count,
                **(details or {}),
            },
        )

        self.publish_to_event_bus(
            event_type="metabolism.cycle.started",
            payload={
                "cycle_name": cycle_name,
                "cycle_count": self.cycle_count,
                "record_id": event["record_id"],
            },
        )

        self.save_state()

        return copy.deepcopy(event)

    def end_cycle(
        self,
        cycle_name: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        End a controlled cycle.
        """

        event = self.record_internal_event(
            event_type="metabolism.cycle.ended",
            phase_name=self.current_phase,
            source_organ="MetabolismOrgan",
            details={
                "cycle_name": cycle_name,
                "cycle_count": self.cycle_count,
                **(details or {}),
            },
        )

        self.publish_to_event_bus(
            event_type="metabolism.cycle.ended",
            payload={
                "cycle_name": cycle_name,
                "cycle_count": self.cycle_count,
                "record_id": event["record_id"],
            },
        )

        self.save_state()

        return copy.deepcopy(event)

    def finalize_run(
        self,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Finalize the metabolism run.

        This records normal shutdown/finalization state.

        It does not terminate the Python process.
        """

        self.shutdown_recorded = True
        self.finalized = True
        self.current_phase = "SHUTDOWN"

        event = self.record_internal_event(
            event_type="metabolism.run.finalized",
            phase_name="SHUTDOWN",
            source_organ="MetabolismOrgan",
            details=details or {},
        )

        self.publish_to_event_bus(
            event_type="metabolism.run.finalized",
            payload={
                "run_id": self.run_id,
                "cycle_count": self.cycle_count,
                "heartbeat_count": self.heartbeat_count,
                "record_id": event["record_id"],
            },
        )

        self.save_state()

        return copy.deepcopy(event)

    # ========================================================
    # INTERNAL RECORDING
    # ========================================================

    def record_internal_event(
        self,
        event_type: str,
        phase_name: str,
        source_organ: str,
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Record a metabolism event to metabolism_cycles.jsonl.

        This is the append-only lifecycle/cycle log.
        """

        if event_type not in self.VALID_CYCLE_EVENTS:
            raise MetabolismCycleError(
                f"Invalid metabolism event type: {event_type}"
            )

        self.validate_details_safety(details)

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        record = {
            "schema_version": self.SCHEMA_VERSION,
            "record_id": self.generate_cycle_record_id(event_type),
            "event_type": event_type,
            "timestamp_utc": self.utc_now_iso(),
            "run_id": self.run_id,
            "phase_name": phase_name,
            "source_organ": source_organ,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_build": persistent["current_build"],
            "cycle_count": self.cycle_count,
            "heartbeat_count": self.heartbeat_count,
            "details": copy.deepcopy(details),
            "safety": {
                "commands_executed": False,
                "network_access_performed": False,
                "filesystem_scan_performed": False,
                "background_workers_started": False,
                "active_network_discovery_triggered": False,
            },
        }

        self.validate_record(record)
        self.append_cycle_record(record)

        return copy.deepcopy(record)

    def append_cycle_record(self, record: Dict[str, Any]) -> None:
        """
        Append a cycle/phase record to metabolism_cycles.jsonl.
        """

        try:
            self.cycles_log_path.parent.mkdir(parents=True, exist_ok=True)

            with self.cycles_log_path.open("a", encoding="utf-8") as file:
                json.dump(record, file, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise MetabolismCycleError(
                f"Could not append metabolism cycle record: {error}"
            ) from error

    # ========================================================
    # EVENT BUS INTEGRATION
    # ========================================================

    def publish_to_event_bus(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """
        Publish a metabolism event to the Event Bus if available.

        The Metabolism Organ does not require Event Bus to function.

        If no Event Bus exists, this method does nothing.
        """

        if self.event_bus is None:
            return

        self.event_bus.publish_event(
            event_type=event_type,
            source_organ="MetabolismOrgan",
            payload=payload,
        )

    # ========================================================
    # STATE GENERATION
    # ========================================================

    def build_state(self) -> Dict[str, Any]:
        """
        Build the current metabolism_state.json payload.
        """

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        state = {
            "schema_version": self.SCHEMA_VERSION,
            "state_timestamp_utc": self.utc_now_iso(),
            "run_id": self.run_id,
            "organism_name": persistent["organism_name"],
            "lineage_id": persistent["lineage_id"],
            "runtime_instance_id": runtime["runtime_instance_id"],
            "runtime_mode": self.runtime_mode,
            "current_phase": self.current_phase,
            "cycle_count": self.cycle_count,
            "max_cycles": self.max_cycles,
            "heartbeat_count": self.heartbeat_count,
            "shutdown_recorded": self.shutdown_recorded,
            "finalized": self.finalized,
            "continuous_mode_enabled": False,
            "phase_history": copy.deepcopy(self.phase_history),
            "metabolism_root": str(self.metabolism_root),
            "state_path": str(self.state_path),
            "cycles_log_path": str(self.cycles_log_path),
            "safety_boundary": self.get_safety_boundary(),
            "safety_summary": {
                "commands_executed": False,
                "network_access_performed": False,
                "filesystem_scan_performed": False,
                "background_workers_started": False,
                "active_network_discovery_triggered": False,
                "infinite_loop_created": False,
            },
        }

        self.validate_state(state)

        return state

    def save_state(self) -> Dict[str, Any]:
        """
        Save metabolism_state.json.
        """

        state = self.build_state()

        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)

            with self.state_path.open("w", encoding="utf-8") as file:
                json.dump(state, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise MetabolismStateError(
                f"Could not save metabolism state: {error}"
            ) from error

        return copy.deepcopy(state)

    def get_metabolism_report(self) -> Dict[str, Any]:
        """
        Return a short metabolism report for console output.
        """

        state = self.build_state()

        return {
            "metabolism_root": state["metabolism_root"],
            "run_id": state["run_id"],
            "runtime_mode": state["runtime_mode"],
            "current_phase": state["current_phase"],
            "cycle_count": state["cycle_count"],
            "max_cycles": state["max_cycles"],
            "heartbeat_count": state["heartbeat_count"],
            "continuous_mode_enabled": state["continuous_mode_enabled"],
            "shutdown_recorded": state["shutdown_recorded"],
            "finalized": state["finalized"],
            "safety_summary": state["safety_summary"],
        }

    # ========================================================
    # VALIDATION AND SAFETY
    # ========================================================

    def validate_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate a metabolism cycle/phase record.
        """

        required_fields = [
            "schema_version",
            "record_id",
            "event_type",
            "timestamp_utc",
            "run_id",
            "phase_name",
            "source_organ",
            "source_runtime_instance_id",
            "source_lineage_id",
            "source_organism_name",
            "source_build",
            "cycle_count",
            "heartbeat_count",
            "details",
            "safety",
        ]

        for field in required_fields:
            if field not in record:
                raise MetabolismCycleError(
                    f"Missing required metabolism record field: {field}"
                )

        safety = record["safety"]

        prohibited_true_flags = [
            "commands_executed",
            "network_access_performed",
            "filesystem_scan_performed",
            "background_workers_started",
            "active_network_discovery_triggered",
        ]

        for flag in prohibited_true_flags:
            if safety.get(flag) is True:
                raise MetabolismSafetyError(
                    f"Metabolism record safety violation. This flag must be false: {flag}"
                )

        return True

    def validate_state(self, state: Dict[str, Any]) -> bool:
        """
        Validate metabolism state.
        """

        required_fields = [
            "schema_version",
            "state_timestamp_utc",
            "run_id",
            "organism_name",
            "lineage_id",
            "runtime_instance_id",
            "runtime_mode",
            "current_phase",
            "cycle_count",
            "max_cycles",
            "heartbeat_count",
            "shutdown_recorded",
            "finalized",
            "continuous_mode_enabled",
            "phase_history",
            "safety_boundary",
            "safety_summary",
        ]

        for field in required_fields:
            if field not in state:
                raise MetabolismStateError(
                    f"Missing required metabolism state field: {field}"
                )

        if state["continuous_mode_enabled"] is not False:
            raise MetabolismSafetyError(
                "Build 0.7.0 does not allow continuous mode."
            )

        if state["cycle_count"] > state["max_cycles"]:
            raise MetabolismSafetyError(
                "cycle_count cannot exceed max_cycles."
            )

        if state["max_cycles"] > 1:
            raise MetabolismSafetyError(
                "Build 0.7.0 does not allow max_cycles greater than 1."
            )

        safety_summary = state["safety_summary"]

        for flag in [
            "commands_executed",
            "network_access_performed",
            "filesystem_scan_performed",
            "background_workers_started",
            "active_network_discovery_triggered",
            "infinite_loop_created",
        ]:
            if safety_summary.get(flag) is True:
                raise MetabolismSafetyError(
                    f"Metabolism state safety violation. This flag must be false: {flag}"
                )

        return True

    def validate_details_safety(self, details: Dict[str, Any]) -> bool:
        """
        Validate detail payloads.

        Metabolism details should be lightweight structured metadata,
        not secret dumps or raw environment payloads.
        """

        prohibited_keys = self.find_prohibited_keys(details)

        if prohibited_keys:
            raise MetabolismSafetyError(
                f"Metabolism details contain prohibited key names: {prohibited_keys}"
            )

        return True

    def find_prohibited_keys(self, value: Any, path: str = "") -> list[str]:
        """
        Recursively find prohibited key names.
        """

        prohibited = [
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

        found = []

        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                child_path = f"{path}.{key_text}" if path else key_text

                if key_text in prohibited:
                    found.append(child_path)

                found.extend(self.find_prohibited_keys(child, child_path))

        elif isinstance(value, list):
            for index, item in enumerate(value):
                child_path = f"{path}[{index}]"
                found.extend(self.find_prohibited_keys(item, child_path))

        return found

    def get_safety_boundary(self) -> Dict[str, bool]:
        """
        Return the Metabolism Organ safety boundary.
        """

        return {
            "may_record_runtime_phases": True,
            "may_record_heartbeats": True,
            "may_record_cycle_start": True,
            "may_record_cycle_end": True,
            "may_save_metabolism_state": True,
            "may_append_metabolism_cycle_log": True,
            "may_publish_metabolism_events": True,

            "may_run_continuously": False,
            "may_create_infinite_loop": False,
            "may_spawn_background_workers": False,
            "may_execute_commands": False,
            "may_access_network": False,
            "may_scan_filesystem": False,
            "may_mutate_other_organs": False,
            "may_trigger_active_network_discovery": False,
            "may_bypass_safety_boundaries": False,
        }
