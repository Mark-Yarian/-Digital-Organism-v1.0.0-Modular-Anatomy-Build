# Digital Organism — ContinuityNode

Build: **0.4.0**

ContinuityNode is an experimental software system and digital organism research model designed to study persistent identity, runtime instancing, continuity tracking, controlled environmental observation, passive network mapping, and dry-run network cartography planning.

This project uses “organ” terminology as a modular software architecture model. It does **not** claim biological life, sentience, consciousness, agency, or autonomy.

---

## Current Organs

### 1. Core Identity Organ

File:

```text
organs/core_identity.py
```

Purpose:

```text
Who am I?
Which lineage do I belong to?
Which runtime instance is currently active?
```

Creates and maintains:

```text
data/identity.json
```

Important behavior:

```text
- creates persistent identity on first run
- preserves birth timestamp
- preserves lineage ID
- preserves first_build
- generates a new runtime instance ID on each launch
- never overwrites locked fields unless a future reset_identity() method is explicitly added
```

---

### 2. Sensorium Organ

File:

```text
organs/sensorium.py
```

Purpose:

```text
Where am I running?
What can I safely observe?
What does the host already know?
```

Creates:

```text
data/sensorium_snapshot.json
```

Collects:

```text
- host information
- Python runtime information
- filesystem context
- process context
- non-sensitive user-context hints
- safe environment variable summary
- command availability checks
- local network interfaces
- local IPv4/subnet/CIDR data
- passive ARP / neighbor cache data
- passive connection records if psutil is available
- passive topology seed matrix
```

Important boundary:

```text
Sensorium does not actively scan the network.
```

It does **not** perform:

```text
- ping sweeps
- port scans
- traceroute mapping
- subnet crawling
- service fingerprinting
- external IP lookup
```

---

### 3. Network Cartography Organ

File:

```text
organs/network_cartography.py
```

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

Build `0.4.0` behavior:

```text
DRY-RUN ONLY
```

It:

```text
- creates a safe default policy file
- derives candidate private scopes from Sensorium
- validates approved scopes
- creates a dry-run discovery plan
- writes a JSON report
- appends JSONL audit events
```

It does **not**:

```text
- ping hosts
- open TCP sockets
- scan ports
- run traceroute
- fingerprint services
- test credentials
- test vulnerabilities
```

---

## How To Run

From the project root:

```bash
python organism.py
```

Optional, for richer passive network detail:

```bash
pip install psutil
```

The organism does **not** auto-install packages.

---

## Generated Data Files

These files are created automatically under `data/`:

```text
identity.json
sensorium_snapshot.json
network_cartography_policy.json
network_cartography_report.json
network_cartography_audit_log.jsonl
```

---

## Safety Model

Current safety posture:

```text
Core Identity:
  persistent identity only

Sensorium:
  read-only observation with passive network awareness

Network Cartography:
  dry-run planning only
```

Active network discovery is intentionally not implemented in this build.

---

## Suggested Next Build

Build `0.5.0` could add carefully bounded TCP connect probing, but only after explicit enablement, strict policy validation, scope limits, timeout controls, rate limits, and audit logs.

Recommended future rule:

```text
No active probing unless:
  - cartography_enabled is true
  - active_cartography_implemented is true
  - approved scopes are private RFC1918/local ranges
  - user has explicitly reviewed the policy
  - all probes are logged
```
