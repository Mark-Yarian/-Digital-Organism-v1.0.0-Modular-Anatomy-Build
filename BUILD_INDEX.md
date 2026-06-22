# Digital Organism Build Index

Project: Digital Organism  
Organism: ContinuityNode  
Build: 0.5.0  
Mode: OBSERVE  
Cartography Mode: DRY_RUN_ONLY  
Memory Mode: LOCAL_STRUCTURED_ARCHIVE  

## File Index

| File | Purpose | Output |
|---|---|---|
| `organism.py` | Main launcher | Console reports |
| `organs/__init__.py` | Organ package index | None |
| `organs/core_identity.py` | Persistent identity + runtime identity | `data/identity.json` |
| `organs/sensorium.py` | Runtime/environment snapshot + passive topology seed | `data/sensorium_snapshot.json` |
| `organs/network_cartography.py` | Dry-run active-discovery planning | `data/network_cartography_policy.json`, `data/network_cartography_report.json`, `data/network_cartography_audit_log.jsonl` |
| `organs/memory.py` | Structured historical memory archive | `data/memory/memory_index.json`, `data/memory/event_log.jsonl`, `data/memory/summaries/latest_memory_summary.json` |

## Build History

### 0.1.0
Core Identity Organ

### 0.2.0
Sensorium Organ

### 0.3.0
Expanded Sensorium passive network awareness and topology seed matrix

### 0.4.0
Network Cartography Organ dry-run policy/report/audit system

### 0.5.0
Memory Organ structured archive, memory index, event log, latest summary, and lightweight change comparison
