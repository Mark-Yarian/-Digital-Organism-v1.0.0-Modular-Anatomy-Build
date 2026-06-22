"""
============================================================
TOOL USE ORGAN
============================================================

Project:
    Digital Organism

Build:
    1.2.0

Organism Name:
    ContinuityNode

Organ:
    Tool Use Organ

File:
    organs/tool_use.py

Primary Function:
    Execute approved local read-only tools safely through Immune-gated,
    allowlisted, timeout-limited, output-limited, audited tool calls.

Scientific / Clinical Description:
    The Tool Use Organ is a controlled execution boundary.

    It does not create agency, autonomy, intent, self-directed behavior,
    or unrestricted tool access. The "tool use" metaphor is used
    architecturally to describe limited interaction with approved local
    diagnostic tools.

Relationship To Existing Organs:
    Immune Organ:
        Formally allows or denies tool-use requests.

    Event Bus Organ:
        Receives tool-use events.

    Telemetry Organ:
        Can later measure tool-use count and safety posture.

    Sensorium Organ:
        Previously performed passive observation directly. Future builds
        may move command-based passive observation behind Tool Use.

Important Safety Boundary:
    The Tool Use Organ is local, read-only, allowlisted, and Immune-gated.

    It may:
        - execute approved read-only local commands
        - use shell=False only
        - enforce timeout limits
        - enforce output size limits
        - write audit logs
        - generate latest tool-use report
        - publish tool-use events

    It may not:
        - execute arbitrary commands
        - use shell=True
        - run user-supplied command strings
        - access external network intentionally
        - run scanners such as nmap
        - run offensive tools
        - perform exploitation
        - test credentials
        - modify files
        - delete files
        - install persistence
        - spawn background daemons
        - bypass Immune

Storage Model:
    data/tool_use/
        tool_use_policy.json
        tool_use_audit_log.jsonl
        latest_tool_use_report.json

Build 1.2.0 Behavior:
    - Create default policy.
    - Validate tool-use policy.
    - Review tool requests with Immune.
    - Execute only approved read-only local commands.
    - Record all requests and results.
    - Enforce timeout and output limits.
    - Generate latest_tool_use_report.json.
"""

from __future__ import annotations

import copy
import json
import platform
import shutil
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================


class ToolUseError(Exception):
    """
    Base exception for all Tool Use Organ errors.
    """


class ToolUsePolicyError(ToolUseError):
    """
    Raised when tool-use policy is missing, malformed, or unsafe.
    """


class ToolUseAuditError(ToolUseError):
    """
    Raised when tool-use audit logging fails.
    """


class ToolUseExecutionError(ToolUseError):
    """
    Raised when approved tool execution fails unexpectedly.
    """


class ToolUseSafetyError(ToolUseError):
    """
    Raised when a tool-use request violates safety boundaries.
    """


class ToolUseReportError(ToolUseError):
    """
    Raised when latest tool-use report cannot be generated or saved.
    """


# ============================================================
# TOOL USE ORGAN CLASS
# ============================================================


class ToolUseOrgan:
    """
    Controlled local tool-use boundary.

    Build 1.2.0 only allows named tools defined in policy.

    No arbitrary command strings are accepted.
    No shell=True is used.
    """

    SCHEMA_VERSION = "1.0.0"
    TOOL_MODE = "IMMUNE_GATED_READ_ONLY_LOCAL_TOOLS"

    DEFAULT_TIMEOUT_SECONDS = 3
    DEFAULT_OUTPUT_LIMIT_CHARS = 25000

    # --------------------------------------------------------
    # These tool names are logical names, not free command text.
    # The command arrays are selected internally from policy.
    # --------------------------------------------------------
    DEFAULT_TOOLS_BY_OS = {
        "Windows": {
            "arp_table": ["arp", "-a"],
            "ip_config": ["ipconfig", "/all"],
            "route_table": ["route", "print"],
            "network_stats": ["netstat", "-ano"],
        },
        "Linux": {
            "ip_addresses": ["ip", "addr"],
            "ip_routes": ["ip", "route"],
            "ip_neighbors": ["ip", "neigh"],
            "socket_summary": ["ss", "-tunap"],
        },
        "Darwin": {
            "ifconfig": ["ifconfig"],
            "route_table": ["netstat", "-rn"],
            "arp_table": ["arp", "-a"],
            "socket_summary": ["netstat", "-an"],
        },
    }

    # Explicitly disallowed executable names.
    DENIED_EXECUTABLES = [
        "nmap",
        "nc",
        "netcat",
        "telnet",
        "ssh",
        "scp",
        "curl",
        "wget",
        "powershell",
        "pwsh",
        "cmd",
        "bash",
        "sh",
        "python",
        "python3",
        "pip",
        "pip3",
        "rm",
        "del",
        "erase",
        "format",
        "shutdown",
        "reboot",
    ]

    PROHIBITED_REQUEST_KEYS = [
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
        tool_use_root: str = "data/tool_use",
        policy_path: str = "data/tool_use/tool_use_policy.json",
        audit_log_path: str = "data/tool_use/tool_use_audit_log.jsonl",
        latest_report_path: str = "data/tool_use/latest_tool_use_report.json",
    ) -> None:
        """
        Initialize Tool Use Organ.
        """

        self.core_identity = core_identity
        self.event_bus = event_bus
        self.immune = immune

        self.tool_use_root = Path(tool_use_root)
        self.policy_path = Path(policy_path)
        self.audit_log_path = Path(audit_log_path)
        self.latest_report_path = Path(latest_report_path)

        self.requests_this_run = 0
        self.allowed_requests_this_run = 0
        self.denied_requests_this_run = 0
        self.executions_this_run = 0
        self.successful_executions_this_run = 0
        self.failed_executions_this_run = 0
        self.timeouts_this_run = 0
        self.output_truncations_this_run = 0

        self.tools_requested_this_run: Dict[str, int] = {}
        self.results_by_status_this_run: Dict[str, int] = {}

        self.ensure_tool_use_structure()
        self.policy = self.ensure_policy_file()
        self.validate_policy(self.policy)

        self.write_audit_event(
            event_type="tool_use.initialized",
            tool_name=None,
            decision="allow",
            result_status="initialized",
            details={
                "tool_mode": self.TOOL_MODE,
                "policy_path": str(self.policy_path),
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

    def generate_request_id(self, tool_name: Optional[str]) -> str:
        """
        Generate unique tool-use request ID.
        """

        safe_tool = (tool_name or "none").replace(".", "-").replace("_", "-")
        timestamp = self.utc_now_iso().replace("-", "").replace(":", "").replace("Z", "Z")
        short_id = uuid.uuid4().hex[:6]

        return f"tool-use-{safe_tool}-{timestamp}-{short_id}"

    # ========================================================
    # STRUCTURE AND POLICY
    # ========================================================

    def ensure_tool_use_structure(self) -> None:
        """
        Create tool-use output directory.
        """

        try:
            self.tool_use_root.mkdir(parents=True, exist_ok=True)

        except OSError as error:
            raise ToolUseReportError(
                f"Could not create tool-use directory: {error}"
            ) from error

    def ensure_policy_file(self) -> Dict[str, Any]:
        """
        Load or create tool-use policy.
        """

        if self.policy_path.exists():
            return self.load_policy()

        policy = self.create_default_policy()
        self.save_policy(policy)

        return policy

    def create_default_policy(self) -> Dict[str, Any]:
        """
        Create default Tool Use policy.

        This policy is intentionally conservative.
        """

        return {
            "schema_version": self.SCHEMA_VERSION,
            "tool_mode": self.TOOL_MODE,
            "enabled": True,
            "requires_immune_approval": True,
            "local_only": True,
            "read_only_only": True,
            "allow_shell": False,
            "allow_arbitrary_command_strings": False,
            "allow_user_supplied_executables": False,
            "allow_network_scanners": False,
            "allow_offensive_tools": False,
            "allow_credential_tools": False,
            "allow_file_modification": False,
            "allow_background_processes": False,
            "timeout_seconds": self.DEFAULT_TIMEOUT_SECONDS,
            "output_limit_chars": self.DEFAULT_OUTPUT_LIMIT_CHARS,
            "allowed_tools_by_os": copy.deepcopy(self.DEFAULT_TOOLS_BY_OS),
            "denied_executables": list(self.DENIED_EXECUTABLES),
            "audit_logging_enabled": True,
            "store_stdout": True,
            "store_stderr": True,
            "notes": [
                "Build 1.2.0 allows approved read-only local tools only.",
                "No arbitrary command strings are accepted.",
                "shell=True is prohibited.",
                "Tool execution should be Immune-gated.",
            ],
        }

    def load_policy(self) -> Dict[str, Any]:
        """
        Load tool-use policy.
        """

        try:
            with self.policy_path.open("r", encoding="utf-8") as file:
                data = json.load(file)

        except json.JSONDecodeError as error:
            raise ToolUsePolicyError(
                f"tool_use_policy.json could not be parsed: {error}"
            ) from error

        except OSError as error:
            raise ToolUsePolicyError(
                f"tool_use_policy.json could not be read: {error}"
            ) from error

        if not isinstance(data, dict):
            raise ToolUsePolicyError(
                "tool_use_policy.json must contain a JSON object."
            )

        return data

    def save_policy(self, policy: Dict[str, Any]) -> None:
        """
        Save tool-use policy.
        """

        self.validate_policy(policy)

        try:
            self.policy_path.parent.mkdir(parents=True, exist_ok=True)

            with self.policy_path.open("w", encoding="utf-8") as file:
                json.dump(policy, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ToolUsePolicyError(
                f"Could not save tool-use policy: {error}"
            ) from error

    def validate_policy(self, policy: Dict[str, Any]) -> bool:
        """
        Validate policy and enforce conservative safety posture.
        """

        required_fields = [
            "schema_version",
            "tool_mode",
            "enabled",
            "requires_immune_approval",
            "local_only",
            "read_only_only",
            "allow_shell",
            "allow_arbitrary_command_strings",
            "allow_user_supplied_executables",
            "allow_network_scanners",
            "allow_offensive_tools",
            "allow_credential_tools",
            "allow_file_modification",
            "allow_background_processes",
            "timeout_seconds",
            "output_limit_chars",
            "allowed_tools_by_os",
            "denied_executables",
            "audit_logging_enabled",
            "store_stdout",
            "store_stderr",
        ]

        for field in required_fields:
            if field not in policy:
                raise ToolUsePolicyError(
                    f"Missing required tool-use policy field: {field}"
                )

        required_true_flags = [
            "requires_immune_approval",
            "local_only",
            "read_only_only",
            "audit_logging_enabled",
        ]

        required_false_flags = [
            "allow_shell",
            "allow_arbitrary_command_strings",
            "allow_user_supplied_executables",
            "allow_network_scanners",
            "allow_offensive_tools",
            "allow_credential_tools",
            "allow_file_modification",
            "allow_background_processes",
        ]

        for flag in required_true_flags:
            if policy.get(flag) is not True:
                raise ToolUseSafetyError(
                    f"Tool-use policy safety violation. This flag must be true: {flag}"
                )

        for flag in required_false_flags:
            if policy.get(flag) is not False:
                raise ToolUseSafetyError(
                    f"Tool-use policy safety violation. This flag must be false: {flag}"
                )

        timeout = policy.get("timeout_seconds")
        output_limit = policy.get("output_limit_chars")

        if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 10:
            raise ToolUsePolicyError(
                "timeout_seconds must be greater than 0 and no more than 10."
            )

        if not isinstance(output_limit, int) or output_limit < 1000 or output_limit > 100000:
            raise ToolUsePolicyError(
                "output_limit_chars must be between 1000 and 100000."
            )

        allowed_tools_by_os = policy.get("allowed_tools_by_os")

        if not isinstance(allowed_tools_by_os, dict):
            raise ToolUsePolicyError("allowed_tools_by_os must be a dictionary.")

        denied_executables = {
            str(item).lower()
            for item in policy.get("denied_executables", [])
        }

        for os_name, tools in allowed_tools_by_os.items():
            if not isinstance(tools, dict):
                raise ToolUsePolicyError(
                    f"allowed tools for OS must be a dictionary: {os_name}"
                )

            for tool_name, command in tools.items():
                if not isinstance(tool_name, str) or not tool_name.strip():
                    raise ToolUsePolicyError("tool name must be a non-empty string.")

                if not isinstance(command, list) or not command:
                    raise ToolUsePolicyError(
                        f"command for tool {tool_name} must be a non-empty list."
                    )

                executable = str(command[0]).lower()

                if executable in denied_executables:
                    raise ToolUseSafetyError(
                        f"Allowed tool uses denied executable: {tool_name} -> {executable}"
                    )

                for part in command:
                    if not isinstance(part, str):
                        raise ToolUsePolicyError(
                            f"command part for tool {tool_name} must be string."
                        )

        return True

    # ========================================================
    # TOOL REQUEST / EXECUTION
    # ========================================================

    def run_tool(
        self,
        tool_name: str,
        request_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run an approved local read-only tool by logical name.

        No arbitrary command string is accepted.
        """

        request_context = request_context or {}
        self.validate_request_context(request_context)

        self.requests_this_run += 1
        self.tools_requested_this_run[tool_name] = (
            self.tools_requested_this_run.get(tool_name, 0) + 1
        )

        request_id = self.generate_request_id(tool_name)

        allowed, reason, command = self.evaluate_tool_request(tool_name)

        if not allowed:
            self.denied_requests_this_run += 1

            record = self.write_audit_event(
                event_type="tool_use.request.denied",
                tool_name=tool_name,
                decision="deny",
                result_status="denied",
                details={
                    "request_id": request_id,
                    "reason": reason,
                    "request_context": request_context,
                },
            )

            self.publish_tool_event(
                event_type="tool_use.command.denied",
                payload={
                    "request_id": request_id,
                    "tool_name": tool_name,
                    "reason": reason,
                },
                priority="warning",
            )

            return copy.deepcopy(record)

        immune_decision = None

        if self.immune is not None:
            immune_decision = self.immune.review_action_request(
                requested_action="tool_use.execute_approved_read_only_tool",
                source_organ="ToolUseOrgan",
                request={
                    "tool_name": tool_name,
                    "command": command,
                    "read_only": True,
                    "local_only": True,
                    "shell": False,
                    "request_context": request_context,
                },
            )

            if immune_decision.get("decision") != "allow":
                self.denied_requests_this_run += 1

                record = self.write_audit_event(
                    event_type="tool_use.request.denied_by_immune",
                    tool_name=tool_name,
                    decision="deny",
                    result_status="denied_by_immune",
                    details={
                        "request_id": request_id,
                        "reason": immune_decision.get("reason"),
                        "immune_decision_id": immune_decision.get("decision_id"),
                    },
                )

                self.publish_tool_event(
                    event_type="tool_use.command.denied",
                    payload={
                        "request_id": request_id,
                        "tool_name": tool_name,
                        "reason": immune_decision.get("reason"),
                        "immune_decision_id": immune_decision.get("decision_id"),
                    },
                    priority="warning",
                )

                return copy.deepcopy(record)

        self.allowed_requests_this_run += 1

        self.write_audit_event(
            event_type="tool_use.request.allowed",
            tool_name=tool_name,
            decision="allow",
            result_status="allowed",
            details={
                "request_id": request_id,
                "command": command,
                "immune_decision_id": immune_decision.get("decision_id") if immune_decision else None,
            },
        )

        result = self.execute_command(
            request_id=request_id,
            tool_name=tool_name,
            command=command,
        )

        self.publish_tool_event(
            event_type="tool_use.command.executed",
            payload={
                "request_id": request_id,
                "tool_name": tool_name,
                "result_status": result.get("result_status"),
                "return_code": result.get("return_code"),
                "stdout_truncated": result.get("stdout_truncated"),
                "stderr_truncated": result.get("stderr_truncated"),
            },
            priority="info",
        )

        self.generate_latest_tool_use_report()

        return copy.deepcopy(result)

    def evaluate_tool_request(self, tool_name: str) -> tuple[bool, str, Optional[List[str]]]:
        """
        Evaluate local policy before Immune review.
        """

        if not self.policy.get("enabled"):
            return False, "Tool Use Organ is disabled by policy.", None

        if not isinstance(tool_name, str) or not tool_name.strip():
            return False, "tool_name must be a non-empty string.", None

        system_name = platform.system()
        tools_for_os = self.policy.get("allowed_tools_by_os", {}).get(system_name, {})

        if tool_name not in tools_for_os:
            return False, f"Tool is not allowed for this OS: {tool_name}", None

        command = tools_for_os[tool_name]

        if not isinstance(command, list) or not command:
            return False, "Configured command is malformed.", None

        executable = str(command[0]).lower()

        if executable in {str(item).lower() for item in self.policy.get("denied_executables", [])}:
            return False, f"Executable is denied: {executable}", None

        if shutil.which(command[0]) is None:
            return False, f"Executable not found locally: {command[0]}", None

        return True, "Tool request is locally allowed by policy.", copy.deepcopy(command)

    def execute_command(
        self,
        request_id: str,
        tool_name: str,
        command: List[str],
    ) -> Dict[str, Any]:
        """
        Execute an already-approved command.

        shell=False always.
        timeout enforced.
        output size limit enforced.
        """

        self.executions_this_run += 1

        timeout = float(self.policy.get("timeout_seconds", self.DEFAULT_TIMEOUT_SECONDS))

        try:
            completed = subprocess.run(
                command,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )

            stdout, stdout_truncated = self.truncate_output(completed.stdout)
            stderr, stderr_truncated = self.truncate_output(completed.stderr)

            if stdout_truncated or stderr_truncated:
                self.output_truncations_this_run += 1

            result_status = "completed"
            self.successful_executions_this_run += 1

            record = self.write_audit_event(
                event_type="tool_use.command.executed",
                tool_name=tool_name,
                decision="allow",
                result_status=result_status,
                details={
                    "request_id": request_id,
                    "command": command,
                    "return_code": completed.returncode,
                    "stdout": stdout if self.policy.get("store_stdout") else None,
                    "stderr": stderr if self.policy.get("store_stderr") else None,
                    "stdout_truncated": stdout_truncated,
                    "stderr_truncated": stderr_truncated,
                },
            )

            record["return_code"] = completed.returncode
            record["stdout_truncated"] = stdout_truncated
            record["stderr_truncated"] = stderr_truncated

            return copy.deepcopy(record)

        except subprocess.TimeoutExpired:
            self.timeouts_this_run += 1
            self.failed_executions_this_run += 1

            return self.write_audit_event(
                event_type="tool_use.command.timeout",
                tool_name=tool_name,
                decision="allow",
                result_status="timeout",
                details={
                    "request_id": request_id,
                    "command": command,
                    "timeout_seconds": timeout,
                },
            )

        except OSError as error:
            self.failed_executions_this_run += 1

            return self.write_audit_event(
                event_type="tool_use.command.error",
                tool_name=tool_name,
                decision="allow",
                result_status="error",
                details={
                    "request_id": request_id,
                    "command": command,
                    "error": str(error),
                },
            )

    # ========================================================
    # AUDIT LOGGING
    # ========================================================

    def write_audit_event(
        self,
        event_type: str,
        tool_name: Optional[str],
        decision: str,
        result_status: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Write a tool-use audit event.
        """

        details = details or {}
        self.validate_request_context(details)

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        record = {
            "schema_version": self.SCHEMA_VERSION,
            "tool_use_event_id": self.generate_request_id(tool_name),
            "timestamp_utc": self.utc_now_iso(),
            "tool_mode": self.TOOL_MODE,
            "event_type": event_type,
            "tool_name": tool_name,
            "decision": decision,
            "result_status": result_status,
            "source_runtime_instance_id": runtime["runtime_instance_id"],
            "source_lineage_id": persistent["lineage_id"],
            "source_organism_name": persistent["organism_name"],
            "source_build": persistent["current_build"],
            "details": copy.deepcopy(details),
            "safety": {
                "shell_used": False,
                "arbitrary_command_string_used": False,
                "user_supplied_executable_used": False,
                "network_scanner_used": False,
                "offensive_tool_used": False,
                "credential_tool_used": False,
                "filesystem_modified": False,
                "background_process_started": False,
                "immune_bypassed": False,
            },
        }

        self.validate_audit_record(record)

        try:
            self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

            with self.audit_log_path.open("a", encoding="utf-8") as file:
                json.dump(record, file, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ToolUseAuditError(
                f"Could not write tool-use audit event: {error}"
            ) from error

        self.results_by_status_this_run[result_status] = (
            self.results_by_status_this_run.get(result_status, 0) + 1
        )

        return copy.deepcopy(record)

    # ========================================================
    # STATE / REPORT
    # ========================================================

    def generate_latest_tool_use_report(self) -> Dict[str, Any]:
        """
        Generate latest_tool_use_report.json.
        """

        identity_report = self.core_identity.get_identity_report()
        persistent = identity_report["persistent"]
        runtime = identity_report["runtime"]

        report = {
            "schema_version": self.SCHEMA_VERSION,
            "report_timestamp_utc": self.utc_now_iso(),
            "organism_name": persistent["organism_name"],
            "lineage_id": persistent["lineage_id"],
            "runtime_instance_id": runtime["runtime_instance_id"],
            "tool_use_root": str(self.tool_use_root),
            "policy_path": str(self.policy_path),
            "audit_log_path": str(self.audit_log_path),
            "latest_report_path": str(self.latest_report_path),
            "tool_mode": self.TOOL_MODE,
            "enabled": self.policy.get("enabled"),
            "requires_immune_approval": self.policy.get("requires_immune_approval"),
            "requests_this_run": self.requests_this_run,
            "allowed_requests_this_run": self.allowed_requests_this_run,
            "denied_requests_this_run": self.denied_requests_this_run,
            "executions_this_run": self.executions_this_run,
            "successful_executions_this_run": self.successful_executions_this_run,
            "failed_executions_this_run": self.failed_executions_this_run,
            "timeouts_this_run": self.timeouts_this_run,
            "output_truncations_this_run": self.output_truncations_this_run,
            "tools_requested_this_run": copy.deepcopy(self.tools_requested_this_run),
            "results_by_status_this_run": copy.deepcopy(self.results_by_status_this_run),
            "current_os": platform.system(),
            "available_tools_for_current_os": sorted(
                self.policy.get("allowed_tools_by_os", {}).get(platform.system(), {}).keys()
            ),
            "safety_boundary": self.get_safety_boundary(),
            "safety_summary": {
                "shell_used": False,
                "arbitrary_command_string_used": False,
                "user_supplied_executable_used": False,
                "network_scanner_used": False,
                "offensive_tool_used": False,
                "credential_tool_used": False,
                "filesystem_modified": False,
                "background_process_started": False,
                "immune_bypassed": False,
            },
        }

        self.validate_report(report)
        self.save_latest_tool_use_report(report)

        return copy.deepcopy(report)

    def save_latest_tool_use_report(self, report: Dict[str, Any]) -> None:
        """
        Save latest_tool_use_report.json.
        """

        try:
            self.latest_report_path.parent.mkdir(parents=True, exist_ok=True)

            with self.latest_report_path.open("w", encoding="utf-8") as file:
                json.dump(report, file, indent=2, sort_keys=False)
                file.write("\n")

        except OSError as error:
            raise ToolUseReportError(
                f"Could not save latest tool-use report: {error}"
            ) from error

    def get_tool_use_report(self, latest_report: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Return short report for console output.
        """

        if latest_report is None:
            latest_report = self.generate_latest_tool_use_report()

        return {
            "tool_use_root": latest_report["tool_use_root"],
            "tool_mode": latest_report["tool_mode"],
            "enabled": latest_report["enabled"],
            "requires_immune_approval": latest_report["requires_immune_approval"],
            "requests_this_run": latest_report["requests_this_run"],
            "allowed_requests_this_run": latest_report["allowed_requests_this_run"],
            "denied_requests_this_run": latest_report["denied_requests_this_run"],
            "executions_this_run": latest_report["executions_this_run"],
            "successful_executions_this_run": latest_report["successful_executions_this_run"],
            "failed_executions_this_run": latest_report["failed_executions_this_run"],
            "timeouts_this_run": latest_report["timeouts_this_run"],
            "output_truncations_this_run": latest_report["output_truncations_this_run"],
            "current_os": latest_report["current_os"],
            "available_tools_for_current_os": latest_report["available_tools_for_current_os"],
            "safety_summary": latest_report["safety_summary"],
        }

    # ========================================================
    # EVENT BUS
    # ========================================================

    def publish_tool_event(
        self,
        event_type: str,
        payload: Dict[str, Any],
        priority: str = "info",
    ) -> None:
        """
        Publish tool-use event through Event Bus if available.
        """

        if self.event_bus is None:
            return

        self.event_bus.publish_event(
            event_type=event_type,
            source_organ="ToolUseOrgan",
            payload=payload,
            priority=priority,
        )

    # ========================================================
    # VALIDATION / SAFETY
    # ========================================================

    def truncate_output(self, text: str) -> tuple[str, bool]:
        """
        Truncate command output according to policy.
        """

        limit = int(self.policy.get("output_limit_chars", self.DEFAULT_OUTPUT_LIMIT_CHARS))

        if len(text) <= limit:
            return text, False

        return text[:limit], True

    def validate_request_context(self, context: Dict[str, Any]) -> bool:
        """
        Validate context/details for prohibited key names.
        """

        if not isinstance(context, dict):
            raise ToolUseSafetyError("Tool-use context must be a dictionary.")

        prohibited = self.find_prohibited_keys(context)

        if prohibited:
            raise ToolUseSafetyError(
                f"Tool-use context contains prohibited key names: {prohibited}"
            )

        return True

    def validate_audit_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate audit record safety flags.
        """

        required_fields = [
            "schema_version",
            "tool_use_event_id",
            "timestamp_utc",
            "tool_mode",
            "event_type",
            "tool_name",
            "decision",
            "result_status",
            "source_runtime_instance_id",
            "source_lineage_id",
            "source_organism_name",
            "source_build",
            "details",
            "safety",
        ]

        for field in required_fields:
            if field not in record:
                raise ToolUseAuditError(
                    f"Missing required tool-use audit field: {field}"
                )

        return self.validate_safety_flags(record["safety"])

    def validate_report(self, report: Dict[str, Any]) -> bool:
        """
        Validate latest tool-use report.
        """

        required_fields = [
            "schema_version",
            "report_timestamp_utc",
            "organism_name",
            "lineage_id",
            "runtime_instance_id",
            "tool_use_root",
            "policy_path",
            "audit_log_path",
            "latest_report_path",
            "tool_mode",
            "enabled",
            "requires_immune_approval",
            "requests_this_run",
            "allowed_requests_this_run",
            "denied_requests_this_run",
            "executions_this_run",
            "successful_executions_this_run",
            "failed_executions_this_run",
            "timeouts_this_run",
            "output_truncations_this_run",
            "current_os",
            "available_tools_for_current_os",
            "safety_boundary",
            "safety_summary",
        ]

        for field in required_fields:
            if field not in report:
                raise ToolUseReportError(
                    f"Missing required tool-use report field: {field}"
                )

        return self.validate_safety_flags(report["safety_summary"])

    def validate_safety_flags(self, safety: Dict[str, Any]) -> bool:
        """
        Validate safety flags remain false.
        """

        prohibited_true_flags = [
            "shell_used",
            "arbitrary_command_string_used",
            "user_supplied_executable_used",
            "network_scanner_used",
            "offensive_tool_used",
            "credential_tool_used",
            "filesystem_modified",
            "background_process_started",
            "immune_bypassed",
        ]

        for flag in prohibited_true_flags:
            if safety.get(flag) is True:
                raise ToolUseSafetyError(
                    f"Tool-use safety violation. This flag must be false: {flag}"
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

                if key_text in self.PROHIBITED_REQUEST_KEYS:
                    found.append(child_path)

                found.extend(self.find_prohibited_keys(child, child_path))

        elif isinstance(value, list):
            for index, item in enumerate(value):
                child_path = f"{path}[{index}]"
                found.extend(self.find_prohibited_keys(item, child_path))

        return found

    def get_safety_boundary(self) -> Dict[str, bool]:
        """
        Return Tool Use Organ safety boundary.
        """

        return {
            "may_execute_approved_local_read_only_tools": True,
            "may_use_shell_false": True,
            "may_enforce_timeout": True,
            "may_enforce_output_limit": True,
            "may_write_tool_use_audit_log": True,
            "may_generate_tool_use_report": True,
            "may_publish_tool_use_events": True,

            "may_execute_arbitrary_commands": False,
            "may_use_shell_true": False,
            "may_accept_user_supplied_command_strings": False,
            "may_accept_user_supplied_executables": False,
            "may_run_network_scanners": False,
            "may_run_offensive_tools": False,
            "may_test_credentials": False,
            "may_modify_filesystem": False,
            "may_delete_files": False,
            "may_install_persistence": False,
            "may_spawn_background_processes": False,
            "may_bypass_immune": False,
        }
