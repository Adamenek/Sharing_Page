#!/usr/bin/env python3
"""
Publish a minimal BOINC status snapshot to the user's GitHub Pages repository.

Requirements:
  - Python 3 on Windows
  - GitHub CLI (`gh`) installed and authenticated (`gh auth login`)
  - BOINC running locally
  - Run this script from a trusted local machine only

This publishes task names/progress and optional temperatures publicly.
It does NOT send BOINC control commands or expose the BOINC RPC port to the internet.
"""
import base64
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

REPO = "Adamenek/Sharing_Page"
BRANCH = "main"
DESTINATION = "boinc-live.json"
PUBLISH_EVERY_SECONDS = 300  # 5 minutes: avoids excessive public Git commits
BOINC_HOST = "127.0.0.1"
BOINC_PORT = 31416

def rpc_get_results():
    request_xml = (
        "<boinc_gui_rpc_request><get_results><active_only>1</active_only>"
        "</get_results></boinc_gui_rpc_request>\x03"
    )
    with __import__("socket").create_connection((BOINC_HOST, BOINC_PORT), timeout=4) as sock:
        sock.sendall(request_xml.encode("utf-8"))
        sock.settimeout(4)
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            joined = b"".join(chunks)
            if b"\x03" in joined:
                break
    raw = b"".join(chunks).split(b"\x03", 1)[0].decode("utf-8", errors="replace")
    root = ET.fromstring(raw)
    tasks = []
    for result in root.findall(".//result"):
        active = result.find("active_task")
        if active is None:
            continue
        fraction = active.findtext("fraction_done")
        remaining = result.findtext("estimated_cpu_time_remaining")
        elapsed = active.findtext("elapsed_time")
        try:
            percent = max(0.0, min(100.0, float(fraction or 0) * 100))
        except ValueError:
            percent = 0.0
        try:
            seconds_remaining = max(0, int(float(remaining or 0)))
        except ValueError:
            seconds_remaining = None
        project_url = result.findtext("project_url") or ""
        project = project_url.rstrip("/").split("/")[-1] if project_url else "BOINC"
        tasks.append({
            "name": result.findtext("name") or "Unnamed task",
            "project": project,
            "progress_percent": round(percent, 2),
            "estimated_seconds_remaining": seconds_remaining,
            "elapsed_seconds": round(float(elapsed or 0), 1),
        })
    return tasks

def read_temperatures():
    # Optional: install and run LibreHardwareMonitor with its WMI interface enabled.
    # WMI support varies by version/configuration; missing sensors remain null.
    result = {"cpu_c": None, "gpu_c": None}
    try:
        command = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
            "$ErrorActionPreference='Stop'; "
            "$s=Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Sensor; "
            "$temps=$s | Where-Object { $_.SensorType -eq 'Temperature' }; "
            "$cpu=$temps | Where-Object { $_.Name -match 'CPU Package|CPU Core Max|Core \\(Tctl/Tdie\\)' } | Select-Object -First 1; "
            "$gpu=$temps | Where-Object { $_.Name -match 'GPU Core|GPU Temperature' } | Select-Object -First 1; "
            "[pscustomobject]@{cpu_c=$cpu.Value;gpu_c=$gpu.Value} | ConvertTo-Json -Compress"
        ]
        output = subprocess.run(command, capture_output=True, text=True, timeout=8, check=True).stdout.strip()
        if output:
            values = json.loads(output)
            for key in ("cpu_c", "gpu_c"):
                try:
                    result[key] = round(float(values[key]), 1) if values.get(key) is not None else None
                except (TypeError, ValueError):
                    pass
    except Exception:
        pass
    return result

def gh_api(path, method="GET", payload=None):
    command = ["gh", "api", path, "--method", method]
    if payload is not None:
        # Use a temporary JSON file? `--input -` accepts stdin through subprocess.run.
        command.extend(["--input", "-"])
        data = json.dumps(payload).encode("utf-8")
    else:
        data = None
    proc = subprocess.run(command, input=data, capture_output=True, check=True)
    if not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout.decode("utf-8"))

def publish(document):
    api_path = f"repos/{REPO}/contents/{DESTINATION}"
    try:
        current = gh_api(api_path)
        sha = current.get("sha")
    except subprocess.CalledProcessError:
        sha = None
    content = base64.b64encode((json.dumps(document, indent=2) + "\n").encode("utf-8")).decode("ascii")
    payload = {
        "message": "Update live BOINC status",
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha
    gh_api(api_path, method="PUT", payload=payload)

def main():
    print(f"Publishing BOINC status to {REPO}/{DESTINATION} every {PUBLISH_EVERY_SECONDS} seconds.")
    print("Stop with Ctrl+C. This makes task names/progress and sensor readings public.")
    while True:
        now = datetime.now(timezone.utc).isoformat()
        try:
            tasks = rpc_get_results()
            snapshot = {
                "updated_at": now,
                "boinc_running": True,
                "active_task_count": len(tasks),
                "tasks": tasks[:2],
                "temperatures": read_temperatures(),
            }
            publish(snapshot)
            print(f"[{now}] published {len(tasks)} active task(s)")
        except (OSError, ET.ParseError, subprocess.CalledProcessError, ValueError) as exc:
            snapshot = {
                "updated_at": now,
                "boinc_running": False,
                "active_task_count": 0,
                "tasks": [],
                "temperatures": {"cpu_c": None, "gpu_c": None},
                "note": "BOINC unavailable or publishing failed",
            }
            try:
                publish(snapshot)
                print(f"[{now}] BOINC unavailable; published offline status")
            except Exception as publish_exc:
                print(f"[{now}] Could not publish status: {publish_exc}")
            print(f"Status collection issue: {exc}")
        time.sleep(PUBLISH_EVERY_SECONDS)

if __name__ == "__main__":
    main()
