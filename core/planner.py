"""Aodı-NexusZero — capability-aware shard planner (deterministic, zero LLM).

Goal → shards[] where every shard carries capability tags:
    heavy → prefers nodes tagged "gpu"/"strong" (tensor/model load)
    lite  → analysis / API-contract / test-harness shards (any fast node)
Node scoring: tag match + idle (inverse load) + battery penalty + latency.
"""
import re

HEAVY_HINTS = re.compile(
    r"(deep|large|multi|pipeline|train|tensor|embed|batch|parser|analy[sz]e|"
    r"architect|design|system|refactor|generation)", re.I)
MAX_SHARDS = 3


def decompose(goal):
    """Split a goal into at most MAX_SHARDS executable shards (deterministic)."""
    g = (goal or "").strip()
    parts = re.split(r"\s+(?:ثم|و-ثم|then|AND)\s+", g, flags=re.I)
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) == 1 and len(g) > 260:
        # long single goal → 1 analysis + 1 implement + 1 test
        parts = ["برسالة تحليل معماري واختصار سياق: " + g, g,
                 "برسالة اختبارات تأكدية بالبايثون لـ: " + g]
    shards = []
    for i, p in enumerate(parts[:MAX_SHARDS]):
        if i == 0 and len(parts) > 2:
            shards.append(_mk(i, "analyze", p, ["lite"]))
            continue
        kind = "test" if p.lower().startswith("برسالة اختبارات") \
            else "implement"
        tags = ["gpu"] if kind in ("implement",) and HEAVY_HINTS.search(g) else ["lite"]
        if kind == "test":
            tags = ["lite"]
        shards.append(_mk(i, kind, p, tags))
    if not shards:
        shards.append(_mk(0, "implement", g, ["lite"]))
    return shards


def _mk(idx, kind, prompt, tags):
    import uuid
    return {"sid": uuid.uuid4().hex[:10], "idx": idx, "kind": kind,
            "prompt": prompt, "tags": tags}


def score_node(node, shard):
    """Higher = better candidate. Deterministic, no LLM."""
    tags = set(node.get("tags") or [])
    want = set(shard.get("tags") or ["lite"])
    want |= {"gpu"} if shard.get("kind") == "implement" and "gpu" in tags else set()
    s = 0.0
    if tags & {"gpu", "strong"} and ("gpu" in want or shard["kind"] == "implement"):
        s += 2.5
    if tags & {"lite"} and shard["kind"] in ("analyze", "test"):
        s += 2.0
    load = max(0.0, min(float(node.get("load") or 0.0), 1.0))
    s += (1.0 - load)
    batt = node.get("battery")
    if isinstance(batt, (int, float)):
        if batt <= 20:
            s -= 3.0          # جهاز على وشك الموت → حذره قبل كل تفضيل قدرات
        elif batt <= 35:
            s -= 0.8
    lat = node.get("latency_ms")
    if isinstance(lat, (int, float)):
        s -= min(lat, 400) / 1000.0
    if not node.get("up", True):
        s -= 10.0
    return s


def pick(nodes, shard, exclude=()):
    # candidates must be alive AND have a generation engine to run shards
    cands = [n for n in nodes if n.get("up", True) and n.get("ollama_url")
             and n.get("name") not in exclude]
    if not cands:
        return None
    return sorted(cands, key=lambda n: score_node(n, shard), reverse=True)[0]
