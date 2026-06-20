# Digital Organism Build Index

Project: Digital Organism  
Organism: ContinuityNode  
Build: 0.4.0  
Mode: OBSERVE  
Cartography Mode: DRY_RUN_ONLY  

---

## File Index

| File | Purpose | Output |
|---|---|---|
| `organism.py` | Main launcher | Console reports |
| `organs/__init__.py` | Organ package index | None |
| `organs/core_identity.py` | Persistent identity + runtime identity | `data/identity.json` |
| `organs/sensorium.py` | Runtime/environment snapshot + passive topology seed | `data/sensorium_snapshot.json` |
| `organs/network_cartography.py` | Dry-run active-discovery planning | `data/network_cartography_policy.json`, `data/network_cartography_report.json`, `data/network_cartography_audit_log.jsonl` |
| `README.md` | Base documentation | None |
| `BUILD_INDEX.md` | This index file | None |

---

## Organ Responsibility Index

### Core Identity Organ

Question answered:

```text
Who am I?
```

Key concepts:

```text
persistent identity
runtime identity
lineage ID
birth timestamp
locked fields
current build
first build
```

Locked fields:

```text
organism_name
birth_timestamp_utc
lineage_id
first_build
```

---

### Sensorium Organ

Question answered:

```text
Where am I running?
What can I safely observe?
```

Key concepts:

```text
read-only observation
local host context
Python runtime context
safe environment summary
passive network interfaces
passive ARP/neighbor cache
passive connection records
topology seed matrix
```

Active scan status:

```text
false
```

---

### Network Cartography Organ

Question answered:

```text
What would I be allowed to map if active discovery were later approved?
```

Key concepts:

```text
dry-run planning
approved scopes
private ranges only
policy validation
audit logging
future TCP connect probing
```

Active probe status:

```text
not implemented
not permitted
active_probes_sent = 0
```

---

## Build History

### Build 0.1.0

Added:

```text
Core Identity Organ
```

### Build 0.2.0

Added:

```text
Sensorium Organ
```

### Build 0.3.0

Expanded:

```text
Sensorium passive network awareness
topology seed matrix
```

### Build 0.4.0

Added:

```text
Network Cartography Organ
dry-run policy/report/audit system
```
