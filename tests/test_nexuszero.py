"""Aodı-NexusZero — no-network tests: planner · sentinel · fuzzer · seal."""
import os, sys, tempfile, unittest
from pathlib import Path

# كل اختبار يعزل حالته في دليل مؤقت — لا يلمس قاعدة ~/.nzx الحقيقية أبداً
os.environ["NZX_HOME"] = tempfile.mkdtemp(prefix="nzx_test_")

CORE = Path(__file__).resolve().parent.parent / "core"
sys.path.insert(0, str(CORE))

import planner    # noqa: E402
import sentinel   # noqa: E402
import fuzzer     # noqa: E402
import seal       # noqa: E402
import storage    # noqa: E402
import config     # noqa: E402


class PlannerTests(unittest.TestCase):
    def test_single_goal_two_shards(self):
        s = planner.decompose("write a tensor batch pipeline for text embedding")
        self.assertTrue(any(sh["kind"] == "implement" for sh in s))
        self.assertTrue(len(s) <= planner.MAX_SHARDS)

    def test_multi_part_goal_sets_kinds(self):
        g = "اَلتحليل في المعطيات ثم التوليد ثم اختبارات"
        s = planner.decompose(g)
        kinds = [sh["kind"] for sh in s]
        self.assertIn("implement", kinds)
        self.assertTrue(len(s) >= 2)

    def test_heavy_goal_prefers_gpu_tags(self):
        s = planner.decompose("large multi pipeline system analyze data")
        impl = [sh for sh in s if sh["kind"] == "implement"]
        self.assertTrue(impl and "gpu" in impl[0]["tags"], impl)

    def test_pick_prefers_gpu_node_for_heavy(self):
        nodes = [
            {"name": "mac-lite", "tags": ["lite"], "load": 0.1,
             "latency_ms": 4, "up": True, "ollama_url": "http://a:11434"},
            {"name": "win-gpu", "tags": ["gpu"], "load": 0.3,
             "latency_ms": 20, "up": True, "ollama_url": "http://b:11434"},
        ]
        shard = {"kind": "implement", "tags": ["gpu"]}
        self.assertEqual(planner.pick(nodes, shard)["name"], "win-gpu")
        # battery penalty shuffles away a nearly dead node
        nodes[1]["battery"] = 12
        self.assertEqual(planner.pick(nodes, shard)["name"], "mac-lite")

    def test_skips_down_node(self):
        nodes = [{"name": "a", "tags": ["gpu"], "up": False,
                  "ollama_url": "http://a:11434"},
                 {"name": "b", "tags": ["lite"], "up": True, "load": 0,
                  "ollama_url": "http://b:11434"}]
        shard = {"kind": "implement", "tags": ["gpu"]}
        self.assertEqual(planner.pick(nodes, shard)["name"], "b")


class SentinelTests(unittest.TestCase):
    FIXTURE = Path(__file__).resolve().parent.parent / "examples" / "vuln_fixture.py"

    def test_fixture_hits(self):
        hits = sentinel.scan_path(str(self.FIXTURE))
        rules = {h["rule"] for h in hits}
        for rid in ("NZ-X01", "NZ-X02", "NZ-X03", "NZ-X04", "NZ-X05",
                    "NZ-X06", "NZ-X07", "NZ-X08", "NZ-X09", "NZ-X10"):
            self.assertIn(rid, rules, f"missing {rid} in {sorted(rules)}")
        self.assertGreaterEqual(len(hits), 10)

    def test_clean_code(self):
        code = "def add(a, b):\n    return a + b\n"
        self.assertEqual(sentinel.scan_text(code, "clean"), [])

    def test_summary_shape(self):
        s = sentinel.scan_text("AKIAABCDEFGHIJKLMNOP\neval('1')\n", "t")
        sm = sentinel.summary(s)
        self.assertEqual(sm["by_severity"].get("high"), 2)


class FuzzerTests(unittest.TestCase):
    def test_buggy_function_crashes_found(self):
        code = "def risky(a, b=1):\n    return a / b\n"
        rep = fuzzer.fuzz_code(code, "risky")
        self.assertFalse(rep["ok"])
        self.assertTrue(any(c["type"] in ("ZeroDivisionError", "TypeError")
                            for c in rep["crashes"]), rep)

    def test_safe_function_clean(self):
        code = ("def safe(a, b=1):\n"
                "    try:\n"
                "        return a / b\n"
                "    except Exception:\n"
                "        return -1\n")
        rep = fuzzer.fuzz_code(code, "safe")
        self.assertTrue(rep["ok"], rep)


class SealTests(unittest.TestCase):
    def test_chain_roundtrip_and_tamper(self):
        e1 = seal.seal_bytes("t", b"data-1")
        e2 = seal.seal_bytes("t", b"data-2")
        self.assertEqual(e2["prev_hash"], e1["hash"])
        v = seal.verify()
        self.assertTrue(v["ok"], v)
        self.assertEqual(v["size"], e2["idx"])
        # tamper: rewrite an earlier payload hash → chain breaks there
        with storage._LOCK:
            storage._db().execute(
                "UPDATE chain SET payload_sha256='deadbeef' WHERE idx=?",
                (e1["idx"],))
            storage._db().commit()
        v2 = seal.verify()
        self.assertFalse(v2["ok"])
        self.assertEqual(v2["broken_at_idx"], e1["idx"])


class StorageTests(unittest.TestCase):
    def test_task_and_shards_crud(self):
        tid = "t" + planner.decompose("demo goal")[0]["sid"]
        storage.new_task(tid, "demo goal", 2)
        storage.update_task(tid, status="done")
        self.assertEqual(storage.get_task(tid)["status"], "done")


def main():
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
