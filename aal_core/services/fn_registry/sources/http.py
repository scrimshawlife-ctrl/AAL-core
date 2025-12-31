"""
AAL-core Function Registry: HTTP Source
Discovers functions from remote overlay HTTP endpoints.
"""

import json
import urllib.request
from typing import Any, Dict, List


def _fetch_json(url: str, timeout_s: float = 1.5) -> Any:
    """
    Fetch JSON from HTTP endpoint.

    Args:
        url: HTTP(S) URL to fetch
        timeout_s: Request timeout in seconds

    Returns:
        Parsed JSON response

    Raises:
        urllib.error.URLError: On network failure
        json.JSONDecodeError: On invalid JSON
    """
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_remote_functions(manifests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fetch function descriptors from remote overlay services.

    Manifests may include:
      "service_url": "http://127.0.0.1:8088"

    We will call:
      GET {service_url}/abx/functions

    Expected response format:
      {
        "functions": [<FunctionDescriptor>, ...]
      }

    Args:
        manifests: List of overlay manifests

    Returns:
        List of FunctionDescriptor dicts from all remote services

    Note:
        Failures are silent by design - the registry must survive partial outages.
        Remote services are optional discovery sources.
    """
    descriptors: List[Dict[str, Any]] = []

    for manifest in manifests:
        service_url = (manifest.get("service_url") or "").rstrip("/")

        if not service_url:
            continue

        overlay_name = manifest.get("_overlay", "unknown")
        endpoint = f"{service_url}/abx/functions"

        try:
            payload = _fetch_json(endpoint)

            # Validate response structure
            if not isinstance(payload, dict):
                print(f"Warning: {overlay_name} {endpoint} returned non-dict response")
                continue

            functions = payload.get("functions")

            if not isinstance(functions, list):
                print(f"Warning: {overlay_name} {endpoint} 'functions' must be a list")
                continue

            descriptors.extend(functions)

        except urllib.error.URLError as e:
            # Network failure - silent skip
            print(f"Info: Could not reach {overlay_name} at {endpoint}: {e.reason}")
            continue

        except json.JSONDecodeError as e:
            print(f"Warning: {overlay_name} {endpoint} returned invalid JSON: {e}")
            continue

        except Exception as e:
            print(f"Warning: Error fetching from {overlay_name} {endpoint}: {e}")
            continue

    return descriptors
