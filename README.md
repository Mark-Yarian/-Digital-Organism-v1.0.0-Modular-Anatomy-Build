# Digital Organism — ContinuityNode

Build: **0.5.0**

ContinuityNode is an experimental software system and digital organism research model designed to study persistent identity, runtime instancing, continuity tracking, controlled environmental observation, passive network mapping, dry-run network cartography planning, and structured memory across executions.

This project uses “organ” terminology as a modular software architecture model. It does **not** claim biological life, sentience, consciousness, agency, or autonomy.

## Current Organs

### 1. Core Identity Organ

File: `organs/core_identity.py`

Purpose:

```text
Who am I?
Which lineage do I belong to?
Which runtime instance is currently active?
```

Creates: `data/identity.json`

### 2. Sensorium Organ

File: `organs/sensorium.py`

Purpose:

```text
Where am I running?
What can I safely observe?
What does the host already know?
```

Creates: `data/sensorium_snapshot.json`

Boundary: passive observation only; no active network scanning.

### 3. Network Cartography Organ

File: `organs/network_cartography.py`

Purpose:

```text
What would I be allowed to map if active discovery were later approved?
```

Creates:

```text
data/network_cartography_policy.json
data/network_cartography_report.json
data/network_cartography_audit_log.jsonl
```

Status: dry-run only; no active probes.

### 4. Memory Organ

File: `organs/memory.py`

Purpose:

```text
What have I observed before?
What changed across executions?
What should persist?
```

Creates:

```text
data/memory/memory_index.json
data/memory/event_log.jsonl
data/memory/snapshots/
data/memory/summaries/latest_memory_summary.json
```

Boundary: no arbitrary file ingestion, no raw environment values, no secrets, no commands, no network access, no deletion.

## How To Run

```bash
python organism.py
```

Optional richer passive network detail:

```bash
pip install psutil
```

The organism does not auto-install packages.

## Suggested Next Build

Build `0.6.0` should add the Event Bus / Nervous System Organ.
