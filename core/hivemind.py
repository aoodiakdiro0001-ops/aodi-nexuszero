"""Aodı-NexusZero hivemind — the distributed brain.

Flow: goal → deterministic shard plan → capability-scored node pick per shard
→ bounded generation → local sentinel self-audit → sha256 seal entry →
artifacts on disk. Devices dropping get re-shuffled to next best candidate.
"""
import hashlib, json, os, sys, threading, time, uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
import planner
import peers
import sentinel
import seal
import storage
import telemetry

TASKS = {}
_TLOCK = threading.Lock()

SYSTEM_HEAVY = ("أنت وكيل تنفيذ عالي القدرة في خلية NexusZero. أخرج بايثون قابلة "
                "للتشغيل فقط، بلا شرح، بلا زخرفة. لا تلمس الشبكة، ولا ملفات "
                "خارجية، ولا حلقات بلا نهاية.")
SYSTEM_LITE = ("أنت محلل سريع في خلية NexusZero. المطلوب نص تحليل مضغوط (أقل "
               "من 12 سطراً) يحدد الواجهة والسلوك المطلوب.")
SYSTEM_TEST = ("أنت مولد اختبارات في خلية NexusZero. أخرج أسطر assert بايثون "
               "فحسب ضد الدالة المطلوبة، بدون تعريفها وبدون شرح.")


def new_task(goal):
    info = planner.decompose(goal)
    tid = uuid.uuid4().hex[:10]
    rec = {"id": tid, "goal": goal, "status": "queued",
           "shards": [dict(s, status="planned", node=None, ms=None,
                           error=None, output=None) for s in info],
           "created": time.strftime("%H:%M:%S"), "artifact": None,
           "seal": None, "duration_ms": 0, "findings": []}
    TASKS[tid] = rec
    storage.new_task(tid, goal, len(info))
    telemetry.emit(tid, "info",
                   f"هدف جديد → خطة {len(info)} شظايا موزعة حسب القدرات")
    threading.Thread(target=_run, args=(tid,), daemon=True).start()
    return _public(rec)


def get(tid):
    with _TLOCK:
        r = TASKS.get(tid)
        return _public(r) if r else None


def all_tasks(limit=30):
    with _TLOCK:
        items = list(TASKS.values())[::-1][:limit]
    return [_public(r) for r in items]


def _public(rec):
    out = {k: rec.get(k) for k in ("id", "goal", "status", "created",
                                   "artifact", "seal", "duration_ms",
                                   "findings")}
    out["shards"] = [
        {k: s[k] for k in ("sid", "idx", "kind", "tags", "status", "node",
                           "ms", "error")}
        for s in rec.get("shards", [])]
    return out


# ---------------- core loop ----------------
def _run(tid):
    rec = TASKS[tid]
    try:
        rec["status"] = "running"
        storage.update_task(tid, status="running")
        t0 = time.time()
        nodes = peers.topology()
        down = set()
        produced = []
        for shard in rec["shards"]:
            spec = _spec(shard)
            for attempt in range(1, config.MAX_ATTEMPTS + 1):
                node = planner.pick(nodes, shard, exclude=down)
                if not node:
                    shard["status"] = "failed"
                    shard["error"] = "لا عقدة حية متاحة للشظية"
                    break
                shard["node"] = node.get("name")
                storage.update_shard(shard["sid"], node=node.get("name"),
                                     status="running")
                telemetry.emit(tid, "info",
                               f"شظية {shard['idx']} ({shard['kind']}) → "
                               f"{node.get('name')} ({','.join(node.get('tags') or [])})")
                gen = peers.generate(node, spec["system"], spec["prompt"],
                                     expect_code=(shard["kind"] == "implement"))
                if not gen["ok"]:
                    shard["error"] = f"توليد فاشل: {gen.get('error')}"
                    down.add(node.get("name"))   # لا تُكرر نفس العقدة الميتة
                    telemetry.emit(tid, "warn", f"شظية {shard['idx']} برفض "
                                   f"توليد من {node.get('name')} — نقل الحمل")
                    continue
                produced.append({"kind": shard["kind"],
                                 "node": gen.get("node"),
                                 "text": gen["text"]})
                shard["status"] = "done"
                shard["ms"] = gen.get("latency_ms")
                storage.update_shard(shard["sid"], status="done",
                                     ms=gen.get("latency_ms"))
                break
            else:
                if shard["status"] != "done":
                    shard["status"] = "failed"
            storage.update_shard(shard["sid"], status=shard["status"],
                                 error=(shard.get("error") or "")[:300])
        done_n = sum(1 for s in rec["shards"] if s["status"] == "done")
        storage.update_task(tid, shards_done=done_n)
        # sentinel self-audit on the bundle
        bundle_text = "\n\n# --- shard ---\n".join(
            p["text"] for p in produced if p["kind"] == "implement")
        findings = sentinel.scan_text(bundle_text, "bundle")
        rec["findings"] = findings
        for fnd in findings:
            storage.add_finding(fnd["path"], fnd["line"], fnd["rule"],
                                fnd["severity"], fnd["message"])
        # artifacts on disk + seal chain
        art_dir = config.ARTIFACTS / tid
        art_dir.mkdir(parents=True, exist_ok=True)
        for i, piece in enumerate(produced):
            ext = ".py" if piece["kind"] == "implement" else ".txt"
            fpath = art_dir / f"shard-{piece['kind']}-{i}{ext}"
            fpath.write_text(piece["text"], encoding="utf-8")
        manifest = json.dumps({
            "id": tid, "goal": rec["goal"], "shards": rec["shards"],
            "sentinel": sentinel.summary(findings)}, ensure_ascii=False,
            indent=1)
        manifest_path = art_dir / "manifest.json"
        manifest_path.write_text(manifest, encoding="utf-8")
        rec["seal"] = seal.seal_file(manifest_path, "hivemind-manifest")
        rec["artifact"] = str(art_dir)
        okb = sentinel.summary(findings)
        status = "done" if okb["by_severity"].get("high", 0) == 0 else "done-with-findings"
        if not produced:
            status = "failed"
        rec["status"] = status
        rec["duration_ms"] = int((time.time() - t0) * 1000)
        storage.update_task(tid, status=status, artifact=rec["artifact"],
                            finished=time.time())
        telemetry.emit(tid, "ok" if status == "done" else "warn",
                       f"اكتملت المهمة {status}: {done_n}/{len(rec['shards'])} "
                       f"شظايا · sentinel {okb['total']} · ختم سلسلة رقم "
                       f"{(rec['seal'] or {}).get('idx')}")
    except Exception as e:
        rec["status"] = "failed"
        storage.update_task(tid, status="failed", finished=time.time())
        telemetry.emit(tid, "error", f"استثناء: {type(e).__name__}: {e}"[:200])


def _spec(shard):
    if shard["kind"] == "analyze":
        return {"system": SYSTEM_LITE, "prompt": shard["prompt"]}
    if shard["kind"] == "test":
        return {"system": SYSTEM_TEST, "prompt": shard["prompt"]}
    return {"system": SYSTEM_HEAVY, "prompt": shard["prompt"]}


def re_shuffle_demo(tid, drop_node):
    """Mark a node down to demonstrate dynamic re-shuffling (bounded, logged)."""
    telemetry.emit(tid, "warn", f"جهاز توقف: {drop_node} — إعادة توزيع الشظايا")
    storage.log_event(tid, "warn", f"re-shuffle trigger: {drop_node}")
