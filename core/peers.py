"""Aodı-NexusZero — distributed inference peer client (stdlib urllib).

Every registered device exposes Ollama at ollama_url; capability tags steer
which peer is picked upstream (planner). Generation failures are bounded
and honest — a dead peer never silently degrades a shard.
"""
import json, time, urllib.request

import config
import storage


def _req(method, url, payload=None, timeout=60):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def probe(node):
    t0 = time.time()
    entry = {"up": False, "latency_ms": None, "models": [], "load": _load_hint(), "battery": _battery_hint()}
    try:
        tags = _req("GET", node["ollama_url"].rstrip("/") + "/api/tags", timeout=6)
        entry["up"] = True
        entry["latency_ms"] = int((time.time() - t0) * 1000)
        entry["models"] = [m.get("name", "?").split(":")[0] for m in tags.get("models", [])]
    except Exception as e:
        entry["error"] = f"{type(e).__name__}: {e}"[:120]
    return entry


def generate(node, system, prompt, expect_code=True, timeout=None, temperature=0.15):
    url = (node.get("ollama_url") or "").rstrip("/")
    if not url:
        return {"ok": False, "text": "", "node": node.get("name"),
                "model": None, "latency_ms": None,
                "error": "العقدة بلا محرك توليد (ollama_url فارغ)"}
    model = node.get("model") or "qwen2.5-coder"
    payload = {"model": model, "prompt": prompt, "system": system,
               "stream": False, "options": {"temperature": temperature,
                                            "num_ctx": 8192}}
    t0 = time.time()
    try:
        out = _req("POST", url + "/api/generate", payload,
                   timeout=timeout or config.GEN_TIMEOUT)
        text = (out.get("response") or "").strip()
        if expect_code:
            text = _strip_fences(text)
        return {"ok": True, "text": text, "node": node.get("name"),
                "model": model, "latency_ms": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {"ok": False, "text": "", "node": node.get("name"),
                "model": model, "latency_ms": int((time.time() - t0) * 1000),
                "error": f"{type(e).__name__}: {e}"[:160]}


def _strip_fences(s):
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()


# ---- local device hints (best-effort, optional fields) ----
def _load_hint():
    try:
        la = os_loadavg()
        n = os_cpu() or 1
        return round(min(la[0] / max(n, 1), 1.0), 2)
    except Exception:
        return 0.0


def os_loadavg():
    import os
    if hasattr(os, "getloadavg"):
        return os.getloadavg()
    return (0.0, 0.0, 0.0)


def os_cpu():
    import os
    return os.cpu_count() or 1


def _battery_hint():
    """mac: pmset; best-effort elsewhere → None (field stays optional)."""
    try:
        import subprocess
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True,
                             text=True, timeout=3).stdout
        for line in out.splitlines():
            if "%" in line:
                import re
                m = re.search(r"(\d{1,3})%", line)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return None


def topology():
    """Registry nodes + computed health, plus optional atlas feed."""
    nodes = []
    seen = set()
    for n in config.load_nodes():
        if n.get("name") in seen:
            continue
        pr = probe(n)
        nodes.append({"name": n.get("name"), "ollama_url": n.get("ollama_url"),
                      "tags": n.get("tags", []), **pr})
        seen.add(n.get("name"))
    atlas_nodes = _atlas_feed()
    for n in atlas_nodes:
        if n.get("name") in seen:
            continue
        nodes.append(n)
        seen.add(n.get("name"))
    return nodes


def _atlas_feed():
    try:
        data = _req("GET", config.ATLAS_URL.rstrip("/") + "/atlas/nodes", timeout=4)
        out = []
        for n in data.get("nodes", []):
            out.append({"name": n.get("name"), "ollama_url": n.get("ollama_url"),
                        "tags": n.get("tags", []), "up": n.get("up", False),
                        "load": n.get("load"), "battery": n.get("battery"),
                        "latency_ms": n.get("latency_ms"),
                        "source": "atlas"})
        return out
    except Exception:
        return []
