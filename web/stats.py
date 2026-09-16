import os
import re
import subprocess
import time


CPU_RE = re.compile(
    r"CPU usage:\s*([\d.]+)%\s*user,\s*([\d.]+)%\s*sys,\s*([\d.]+)%\s*idle",
    re.I,
)
LOAD_RE = re.compile(
    r"Load Avg:\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)",
    re.I,
)
PHYSMEM_RE = re.compile(
    r"PhysMem:\s*([0-9.]+[KMGTP])\s*used.*?([0-9.]+[KMGTP])\s*unused",
    re.I,
)
SIZE_RE = re.compile(r"^([0-9.]+)([KMGTP])$", re.I)
BATTERY_TEMP_RE = re.compile(r'"Temperature"\s*=\s*(\d+)')

CACHE_SECONDS = 0.8
_cache = {"at": 0.0, "data": None}


def collect_stats():
    """Read local CPU, memory, and process use for the web widget."""
    now = time.monotonic()
    cached = _cache["data"]
    if cached is not None and now - _cache["at"] < CACHE_SECONDS:
        return cached

    data = {
        "cpu_percent": None,
        "memory_used_gb": None,
        "memory_total_gb": None,
        "memory_unused_gb": None,
        "load_1m": None,
        "cpu_count": os.cpu_count() or 0,
        "ollama": {"cpu_percent": 0.0, "memory_mb": 0.0, "running": False},
        "bchubot": {"cpu_percent": 0.0, "memory_mb": 0.0, "running": True},
        "battery_c": None,
    }

    top_text = _run(["top", "-l", "1", "-n", "0", "-s", "0"])
    parsed_top = parse_top(top_text)
    data.update(parsed_top)

    total_bytes = _sysctl_int("hw.memsize")
    if total_bytes:
        data["memory_total_gb"] = _bytes_to_gb(total_bytes)
        unused = data.get("memory_unused_gb")
        if unused is not None:
            data["memory_used_gb"] = round(data["memory_total_gb"] - unused, 2)

    if data["load_1m"] is None:
        try:
            data["load_1m"] = round(os.getloadavg()[0], 2)
        except OSError:
            pass

    processes = parse_ps(_run(["ps", "-axo", "pid=,ppid=,pcpu=,pmem=,rss=,command="]))
    data["ollama"] = _group_processes(processes, _is_ollama)
    data["bchubot"] = _group_processes(
        processes,
        _self_matcher(os.getpid(), processes),
    )
    data["battery_c"] = parse_battery_temp(
        _run(["ioreg", "-r", "-n", "AppleSmartBattery", "-k", "Temperature"])
    )

    _cache["at"] = now
    _cache["data"] = data
    return data


def parse_top(text):
    result = {}
    cpu = CPU_RE.search(text or "")
    if cpu:
        user = float(cpu.group(1))
        system = float(cpu.group(2))
        idle = float(cpu.group(3))
        result["cpu_percent"] = round(min(100.0, max(0.0, user + system, 100.0 - idle)), 1)

    load = LOAD_RE.search(text or "")
    if load:
        result["load_1m"] = round(float(load.group(1)), 2)

    mem = PHYSMEM_RE.search(text or "")
    if mem:
        unused = _size_to_bytes(mem.group(2))
        if unused is not None:
            result["memory_unused_gb"] = _bytes_to_gb(unused)
    return result


def parse_ps(text):
    rows = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        try:
            rows.append(
                {
                    "pid": int(parts[0]),
                    "ppid": int(parts[1]),
                    "cpu_percent": float(parts[2]),
                    "memory_mb": int(parts[4]) / 1024,
                    "command": parts[5],
                }
            )
        except ValueError:
            continue
    return rows


def parse_battery_temp(text):
    match = BATTERY_TEMP_RE.search(text or "")
    if not match:
        return None
    return round(int(match.group(1)) / 100, 1)


def _group_processes(processes, matches):
    cpu = 0.0
    memory = 0.0
    found = False
    for process in processes:
        if not matches(process):
            continue
        found = True
        cpu += process["cpu_percent"]
        memory += process["memory_mb"]
    return {
        "cpu_percent": round(cpu, 1),
        "memory_mb": round(memory, 1),
        "running": found,
    }


def _is_ollama(process):
    command = process["command"].lower()
    return "ollama" in command


def _self_matcher(root_pid, processes):
    children = {}
    for process in processes:
        children.setdefault(process["ppid"], set()).add(process["pid"])

    keep = {root_pid}
    stack = [root_pid]
    while stack:
        pid = stack.pop()
        for child in children.get(pid, ()):
            if child not in keep:
                keep.add(child)
                stack.append(child)

    return lambda process: process["pid"] in keep


def _sysctl_int(name):
    output = _run(["sysctl", "-n", name]).strip()
    if not output:
        return None
    try:
        return int(output)
    except ValueError:
        return None


def _size_to_bytes(text):
    match = SIZE_RE.match((text or "").strip())
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2).upper()
    multipliers = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4, "P": 1024**5}
    return int(amount * multipliers[unit])


def _bytes_to_gb(value):
    return round(value / (1024**3), 2)


def _run(command, timeout=1.5):
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return completed.stdout or ""
