# Alignment API

**HTTP Endpoints for Alignment Queries and Logging**

## Overview

The Alignment API exposes AAC functionality via HTTP endpoints, enabling:
1. Pre-flight alignment checks
2. Real-time tension scoring
3. Audit event submission
4. Compliance reporting

## Endpoints

### POST /alignment/score
**Compute tension scores for a proposed action**

Request:
```json
{
  "agent_id": "abraxas_001",
  "regime": "boxed",
  "request_summary": "User asks for help with X",
  "proposed_output": "Agent plans to respond with Y",
  "valueframes": ["safety_global", "legal_us", "org_ethics_aal"],
  "context": {
    "session_id": "...",
    "user_id_hash": "..."
  }
}
```

Response:
```json
{
  "alignment_id": "uuid",
  "timestamp": "2025-12-08T12:34:56Z",
  "tension_scores": {
    "harm": 0.0,
    "legal": 0.0,
    "psych": 0.0,
    "capability": 0.0,
    "semantic": 0.0,
    "procedural": 0.0
  },
  "alignment_score": 0.0,
  "recommendation": "PASS",
  "explanation": "All tension axes within acceptable range"
}
```

### POST /alignment/gate
**Run full alignment gate decision**

Request:
```json
{
  "agent_id": "abraxas_001",
  "regime": "boxed",
  "request": {
    "text": "Full user request",
    "hash": "sha256..."
  },
  "proposed_action": {
    "type": "generate_text",
    "output_summary": "...",
    "capabilities_required": ["read", "analyze"]
  },
  "valueframes": ["safety_global", "legal_us"]
}
```

Response:
```json
{
  "decision_id": "uuid",
  "timestamp": "2025-12-08T12:34:56Z",
  "decision": "PASS",
  "tension_scores": {...},
  "alignment_score": 0.15,
  "tripwires_triggered": [],
  "transformation_applied": null,
  "explanation": null,
  "logged_to_echo": true
}
```

Possible `decision` values:
- `PASS` - Proceed without modification
- `TRANSFORM` - Modification required (see `transformation_applied`)
- `REFUSE` - Cannot proceed (see `explanation`)
- `ESCALATE` - Human review required

### POST /alignment/log
**Submit audit event to Echo Engine**

Request:
```json
{
  "event_type": "alignment_decision",
  "agent_id": "abraxas_001",
  "regime": "boxed",
  "timestamp": "2025-12-08T12:34:56Z",
  "event_data": {
    "request_summary": "...",
    "decision": "PASS",
    "tension_scores": {...},
    "valueframes_active": [...]
  }
}
```

Response:
```json
{
  "event_id": "uuid",
  "logged": true,
  "echo_engine_ack": "stored"
}
```

### GET /alignment/status/:agent_id
**Get current alignment status for an agent**

Response:
```json
{
  "agent_id": "abraxas_001",
  "regime": "boxed",
  "version": "1.2.3",
  "active_valueframes": [
    "safety_global_v1.0.0",
    "legal_us_v1.2.0",
    "org_ethics_aal_v1.0.0"
  ],
  "capability_graph_version": "1.1.0",
  "recent_metrics": {
    "pass_rate": 0.87,
    "transform_rate": 0.08,
    "refuse_rate": 0.04,
    "escalate_rate": 0.01
  },
  "tripwire_status": "nominal",
  "drift_alert_level": 0
}
```

### GET /alignment/drift/:agent_id
**Get drift analysis for an agent**

Query params:
- `days`: Number of days to analyze (default: 7)

Response:
```json
{
  "agent_id": "abraxas_001",
  "analysis_period": {
    "start": "2025-12-01T00:00:00Z",
    "end": "2025-12-08T23:59:59Z"
  },
  "drift_level": 1,
  "drift_indicators": {
    "tension_trend": 0.02,
    "decision_distribution_shift": 0.01,
    "novel_pattern_rate": 0.03
  },
  "recommendation": "Enhanced monitoring, no intervention required",
  "incident_clusters": [...]
}
```

## Authentication

All endpoints require:
- **API Key** - Service authentication
- **Agent ID** - Which agent is making request
- **Signature** - Request signing for non-repudiation

Example header:
```
Authorization: Bearer <api_key>
X-Agent-ID: abraxas_001
X-Signature: <hmac_sha256_of_request>
```

## Rate Limits

- `/alignment/score`: 1000 requests/min
- `/alignment/gate`: 500 requests/min
- `/alignment/log`: 10000 requests/min
- `/alignment/status/*`: 100 requests/min
- `/alignment/drift/*`: 10 requests/min

## Error Responses

```json
{
  "error": "invalid_request",
  "message": "Missing required field: agent_id",
  "code": 400
}
```

Common errors:
- `400`: Invalid request
- `401`: Authentication failed
- `403`: Agent not authorized for this operation
- `429`: Rate limit exceeded
- `500`: Internal server error

## Integration

Example (Python):
```python
import requests

def check_alignment(agent_id, request_text, proposed_output):
    response = requests.post(
        "https://api.aal.internal/alignment/gate",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "X-Agent-ID": agent_id
        },
        json={
            "agent_id": agent_id,
            "regime": "boxed",
            "request": {"text": request_text},
            "proposed_action": {"output_summary": proposed_output}
        }
    )

    result = response.json()

    if result["decision"] == "PASS":
        return True, proposed_output
    elif result["decision"] == "TRANSFORM":
        return True, result["transformation_applied"]
    else:  # REFUSE or ESCALATE
        return False, result["explanation"]
```

See JSON specification files for full OpenAPI schema.

---

**The Alignment API makes AAC accessible to any system that can speak HTTP.**
