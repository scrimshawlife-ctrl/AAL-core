"""
Process-based overlay runner using subprocess.

Executes local CLI overlays with JSON stdin/stdout protocol.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Dict, List


def canonical_json_str(obj: Any) -> str:
    """
    Produce canonical JSON string for deterministic process input.

    Args:
        obj: Any JSON-serializable object

    Returns:
        Canonical JSON string
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class ProcOverlayRunner:
    """
    Process-based overlay runner.

    Executes command with --stdin-json flag and passes request via stdin.
    Expects JSON response on stdout.
    """

    def __init__(
        self,
        command: List[str],
        timeout: float = 30.0,
    ):
        """
        Initialize process runner.

        Args:
            command: Base command to execute (e.g., ["python", "-m", "overlay_cli"])
            timeout: Process timeout in seconds
        """
        self.command = command
        self.timeout = timeout

    def call(
        self,
        path: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute overlay via subprocess.

        Args:
            path: Subcommand or path argument
            payload: Request payload dictionary

        Returns:
            Response dictionary with structure:
            {
                "ok": bool,
                "result": Any,  # Present if ok=True
                "error": str,   # Present if ok=False
            }
        """
        # Build command with path and stdin-json flag
        full_command = self.command + [path, "--stdin-json"]

        # Prepare deterministic request body
        request_json = canonical_json_str(payload)

        try:
            result = subprocess.run(
                full_command,
                input=request_json,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )

            # Check exit code
            if result.returncode != 0:
                # Try to parse stderr as JSON error
                try:
                    error_data = json.loads(result.stderr)
                    return {
                        "ok": False,
                        "error": error_data.get("error", "Process failed"),
                        "exit_code": result.returncode,
                    }
                except json.JSONDecodeError:
                    return {
                        "ok": False,
                        "error": f"Process exited with code {result.returncode}: {result.stderr}",
                        "exit_code": result.returncode,
                    }

            # Parse stdout as JSON
            try:
                response = json.loads(result.stdout)

                # Wrap in standard format if needed
                if "ok" not in response:
                    response = {
                        "ok": True,
                        "result": response,
                    }

                return response

            except json.JSONDecodeError as e:
                return {
                    "ok": False,
                    "error": f"Invalid JSON response: {e}",
                    "stdout": result.stdout[:200],  # Include snippet
                }

        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "error": f"Process timeout after {self.timeout}s",
            }

        except FileNotFoundError:
            return {
                "ok": False,
                "error": f"Command not found: {self.command[0]}",
            }

        except Exception as e:
            return {
                "ok": False,
                "error": f"Unexpected error: {type(e).__name__}: {e}",
            }
