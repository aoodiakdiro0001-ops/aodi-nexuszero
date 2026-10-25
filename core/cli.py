#!/usr/bin/env python3
"""Aodı-NexusZero — nzctl CLI (stdlib only).

  nzctl status                     fleet + seal head
  nzctl nodes add <name> <url> [tags]         register a compute node
  nzctl run "<goal>"               distributed shard run
  nzctl scan <path>                zero-cloud sentinel audit
  nzctl fuzz <file> <function>     isolated crash-hunt
  nzctl seal <path>                append file digest to the seal chain
  nzctl verify                     verify seal chain integrity
  nzctl chain                      print chain links
  nzctl serve                      start core API server on :9302
"""
import json, os, sys

CORE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CORE)
import config
import peers
import sentinel
import seal
import fuzzer
import storage


def cmd_status():
    nodes = peers.topology()
    print(config.banner())
    print("\n[fleet] %d node(s)" % len(nodes))
    for n in nodes:
        state = "UP" if n.get("up") else "DOWN"
        batt = n.get("battery")
        print("  %-22s %s  load=%.2f  lat=%sms  batt=%s  tags=%s"
              % (n.get("name"), state, n.get("load") or 0,
                 n.get("latency_ms") or "-",
                 (str(batt) + "%") if isinstance(batt, int) else "n/a",
                 ",".join(n.get("tags") or [])))
    h = seal.verify()
    print("[seal] head=%s  links=%d  verify=%s"
          % ((h.get("head") or "")[:16] or "-", h.get("size") or 0,
             "OK" if h.get("ok") else "TAMPERED@" + str(h.get("broken_at_idx"))))


def cmd_nodes_add(name, url, *tags):
    nodes = [n for n in config.load_nodes() if n.get("name") != name]
    nodes.append({"name": name, "ollama_url": url,
                  "tags": [t for t in (tags or ["lite"])]})
    config.save_nodes(nodes)
    print("registered", name, "→", url, "tags:", nodes[-1]["tags"])


def cmd_run(goal):
    import hivemind
    import time
    rec = hivemind.new_task(goal)
    print("task", rec["id"], "→ shards:",
          ", ".join(s["kind"] for s in rec["shards"]))
    while True:
        time.sleep(2)
        r = hivemind.get(rec["id"])
        if r["status"] not in ("queued", "running"):
            break
    for s in r["shards"]:
        print("  shard %-8s %-10s → %-16s %s %sms %s"
              % (s["idx"], s["kind"], s.get("node") or "-",
                 "✓" if s["status"] == "done" else "✗", s.get("ms"),
                 (s.get("error") or "")[:60]))
    print("status:", r["status"], "| artifact:", r.get("artifact"))
    print("sentinel:", r.get("findings") and len(r["findings"]) or 0,
          "| seal idx:", (r.get("seal") or {}).get("idx"))


def cmd_scan(path):
    hits = sentinel.scan_path(path)
    storage.clear_findings(path)
    for hf in hits:
        storage.add_finding(hf["path"], hf["line"], hf["rule"],
                            hf["severity"], hf["message"])
    s = sentinel.summary(hits)
    print(json.dumps(s, ensure_ascii=False))
    for hf in hits:
        print("  [%s] %s:%s %s  ← %s" % (hf["severity"], hf["path"],
                                         hf["line"], hf["rule"],
                                         hf["snippet"][:70]))
    entry = seal.seal_file(path if os.path.isfile(path) else
                           os.path.join(CORE, "..", "README.md"),
                           "scan")
    print("sealed: idx", entry["idx"], entry["hash"][:16])


def cmd_fuzz(path, function):
    code = open(path, encoding="utf-8").read()
    rep = fuzzer.fuzz_code(code, function)
    print(json.dumps(rep, ensure_ascii=False, indent=1)[:1600])


def cmd_seal(path):
    e = seal.seal_file(path)
    print("sealed idx", e["idx"], "#", e["hash"], "prev", e["prev_hash"][:12])


def cmd_verify():
    r = seal.verify()
    print(json.dumps(r, ensure_ascii=False))


def cmd_chain():
    for r in storage.chain_rows()[-10:]:
        print("%3d  %s  %-16s %s" % (r["idx"], r["kind"],
                                     r["hash"][:16], r["prev_hash"][:12]))


def main():
    import argparse
    ap = argparse.ArgumentParser(prog="nzctl",
                                 description="Aodı-NexusZero control plane")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    na = sub.add_parser("nodes"); na.add_argument("add"); na.add_argument("name")
    na.add_argument("url"); na.add_argument("tags", nargs="*")
    rn = sub.add_parser("run"); rn.add_argument("goal")
    sc = sub.add_parser("scan"); sc.add_argument("path")
    fz = sub.add_parser("fuzz"); fz.add_argument("path"); fz.add_argument("function")
    sl = sub.add_parser("seal"); sl.add_argument("path")
    sub.add_parser("verify"); sub.add_parser("chain"); sub.add_parser("serve")
    a = ap.parse_args()
    if a.cmd == "status":
        cmd_status()
    elif a.cmd == "nodes":
        cmd_nodes_add(a.name, a.url, *a.tags)
    elif a.cmd == "run":
        cmd_run(a.goal)
    elif a.cmd == "scan":
        cmd_scan(a.path)
    elif a.cmd == "fuzz":
        cmd_fuzz(a.path, a.function)
    elif a.cmd == "seal":
        cmd_seal(a.path)
    elif a.cmd == "verify":
        cmd_verify()
    elif a.cmd == "chain":
        cmd_chain()
    elif a.cmd == "serve":
        import server
        server.main()


if __name__ == "__main__":
    main()
