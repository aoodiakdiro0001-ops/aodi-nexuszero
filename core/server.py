#!/usr/bin/env python3
"""Aodı-NexusZero — hivemind core API server (stdlib only).

Endpoints:
  GET  /api/state         fleet topology (atlas feed + manual registry)
  POST /api/nodes         {name, ollama_url, tags}
  POST /api/nodes/drop    {name} mark node down (drill / re-shuffle demo)
  POST /api/task          {goal}     → shard plan + distributed run
  GET  /api/task/<tid>    status / shards / seal
  GET  /api/tasks
  GET  /api/findings      sentinel findings tail
  POST /api/scan          {path}     → full sentinel scan, persisted
  POST /api/fuzz          {code, function}
  GET  /api/chain         seal chain rows + verify
  GET  /api/events        telemetry tail
  GET  /                  dashboard (dir=rtl)
"""
import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CORE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CORE)
import config
import peers
import sentinel
import seal
import fuzzer
import hivemind
import storage

STATIC = os.path.join(os.path.dirname(CORE), "dashboard")

# RFC 7230: HTTP headers must remain ASCII-safe; the Turkish dotless ı of the
# brand stays inside JSON bodies (UTF-8) only.
SERVER_NAME = "AodiNexusZero/%s" % config.VERSION


class Handler(BaseHTTPRequestHandler):
    server_version = SERVER_NAME

    def _json(self, code, obj):
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_GET(self):
        p = self.path.split("?", 1)[0]
        if p == "/api/state":
            return self._json(200, {
                "brand": config.BRAND, "version": config.VERSION,
                "atlas": config.ATLAS_URL, "nodes": peers.topology()})
        if p == "/api/tasks":
            return self._json(200, {"tasks": hivemind.all_tasks()})
        if p.startswith("/api/task/"):
            rec = hivemind.get(p.rsplit("/", 1)[1])
            return self._json(200 if rec else 404, rec or {"error": "not found"})
        if p == "/api/findings":
            return self._json(200, {"findings": storage.list_findings()})
        if p == "/api/chain":
            return self._json(200, {"rows": storage.chain_rows()[-20:],
                                    "verify": seal.verify()})
        if p == "/api/events":
            return self._json(200, {"events": storage.event_tail()})
        if p in ("/", "/dashboard"):
            return self._serve_dashboard()
        return self._json(404, {"error": "no route"})

    def do_POST(self):
        p = self.path.split("?", 1)[0]
        body = self._body()
        if p == "/api/task":
            goal = (body.get("goal") or "").strip()
            if not goal:
                return self._json(400, {"error": "goal required"})
            return self._json(202, hivemind.new_task(goal))
        if p == "/api/nodes":
            name = (body.get("name") or "").strip()
            url = (body.get("ollama_url") or "").strip()
            if not name or not url:
                return self._json(400, {"error": "name and ollama_url required"})
            nodes = [n for n in config.load_nodes()
                     if n.get("name") != name]
            nodes.append({"name": name, "ollama_url": url,
                          "tags": body.get("tags", [])})
            config.save_nodes(nodes)
            return self._json(200, {"ok": True, "nodes": peers.topology()})
        if p == "/api/nodes/drop":
            name = (body.get("name") or "").strip()
            if not name:
                return self._json(400, {"error": "name required"})
            hivemind.re_shuffle_demo("drill", name)
            return self._json(200, {"ok": True, "dropped": name})
        if p == "/api/scan":
            path = (body.get("path") or "").strip()
            if not path:
                return self._json(400, {"error": "path required"})
            hits = sentinel.scan_path(path)
            storage.clear_findings(path)
            for hf in hits:
                storage.add_finding(hf["path"], hf["line"], hf["rule"],
                                    hf["severity"], hf["message"])
            s = sentinel.summary(hits)
            return self._json(200, {"path": path, **s,
                                    "findings": hits[:50],
                                    "sealed": seal.seal_bytes(
                                        "scan", json.dumps(s).encode())})
        if p == "/api/fuzz":
            code = body.get("code") or ""
            fn = (body.get("function") or "").strip()
            if not code or not fn:
                return self._json(400, {"error": "code and function required"})
            rep = fuzzer.fuzz_code(code, fn)
            return self._json(200, rep)
        return self._json(404, {"error": "no route"})

    def _serve_dashboard(self):
        idx = os.path.join(STATIC, "index.html")
        if os.path.exists(idx):
            with open(idx, "rb") as f:
                raw = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        else:
            self._json(404, {"error": "missing dashboard"})

    def log_message(self, fmt, *args):  # quiet access log
        pass


def main():
    import argparse
    ap = argparse.ArgumentParser(prog="nzx-core")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=config.DEFAULT_PORT)
    a = ap.parse_args()
    httpd = ThreadingHTTPServer((a.host, a.port), Handler)
    print(config.banner(), flush=True)
    print(f"[core] listening http://{a.host}:{a.port} (NZX_HOME={config.HOME})",
          flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
