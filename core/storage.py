"""Aodı-NexusZero — SQLite storage (stdlib sqlite3):

    tasks    → hivemind goals
    shards   → planned distributed units + node assignment
    findings → sentinel scan observations
    chain    → sha256 tamper-evident seal chain
    events   → telemetry tail
"""
import json, sqlite3, threading, time

import config

_LOCK = threading.Lock()
_CONN = None


def _db():
    global _CONN
    if _CONN is None:
        _CONN = sqlite3.connect(str(config.DB_FILE), check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
        _CONN.executescript("""
        CREATE TABLE IF NOT EXISTS tasks(
            tid TEXT PRIMARY KEY, goal TEXT NOT NULL, status TEXT DEFAULT 'queued',
            shards_total INTEGER DEFAULT 0, shards_done INTEGER DEFAULT 0,
            artifact TEXT, created REAL, finished REAL);
        CREATE TABLE IF NOT EXISTS shards(
            sid TEXT PRIMARY KEY, tid TEXT, idx INTEGER, kind TEXT, tags TEXT,
            node TEXT, status TEXT DEFAULT 'planned', ms INTEGER,
            error TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS findings(
            fid INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, line INTEGER,
            rule TEXT, severity TEXT, message TEXT, ts REAL);
        CREATE TABLE IF NOT EXISTS chain(
            idx INTEGER PRIMARY KEY, ts REAL, kind TEXT,
            payload_sha256 TEXT, prev_hash TEXT, hash TEXT);
        CREATE TABLE IF NOT EXISTS events(
            ts REAL, task_id TEXT, level TEXT, message TEXT);
        """)
        _CONN.commit()
    return _CONN


# ---------- tasks ----------
def new_task(tid, goal, shards_total=0):
    with _LOCK:
        _db().execute("INSERT INTO tasks(tid,goal,shards_total,created) VALUES(?,?,?,?)",
                      (tid, goal, shards_total, time.time()))
        _db().commit()


def update_task(tid, **kw):
    cols = ", ".join(f"{k}=?" for k in kw)
    with _LOCK:
        _db().execute(f"UPDATE tasks SET {cols} WHERE tid=?", (*kw.values(), tid))
        _db().commit()


def get_task(tid):
    with _LOCK:
        row = _db().execute("SELECT * FROM tasks WHERE tid=?", (tid,)).fetchone()
        if not row:
            return None
        cols = [d[0] for d in _db().execute(
            "SELECT * FROM tasks LIMIT 0").description]
    return dict(zip(cols, row))


def list_tasks(limit=30):
    with _LOCK:
        cur = _db().execute(
            "SELECT tid,status,shards_total,shards_done,artifact,created "
            "FROM tasks ORDER BY created DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------- shards ----------
def new_shard(sid, tid, idx, kind, tags, node=None):
    with _LOCK:
        _db().execute(
            "INSERT OR REPLACE INTO shards(sid,tid,idx,kind,tags,node,status,ts) "
            "VALUES(?,?,?,?,?,?, 'planned', ?)",
            (sid, tid, idx, kind, json.dumps(tags or []), node, time.time()))
        _db().commit()


def update_shard(sid, **kw):
    cols = ", ".join(f"{k}=?" for k in kw)
    with _LOCK:
        _db().execute(f"UPDATE shards SET {cols} WHERE sid=?", (*kw.values(), sid))
        _db().commit()


def shards_of(tid):
    with _LOCK:
        cur = _db().execute(
            "SELECT sid,idx,kind,tags,node,status,ms,error FROM shards "
            "WHERE tid=? ORDER BY idx", (tid,))
        out = []
        for r in cur.fetchall():
            d = dict(zip(["sid", "idx", "kind", "tags", "node", "status",
                          "ms", "error"], r))
            try:
                d["tags"] = json.loads(d.get("tags") or "[]")
            except Exception:
                d["tags"] = []
            out.append(d)
        return out


# ---------- findings ----------
def add_finding(path, line, rule, severity, message):
    with _LOCK:
        _db().execute(
            "INSERT INTO findings(path,line,rule,severity,message,ts) "
            "VALUES(?,?,?,?,?,?)",
            (str(path), line, rule, severity, message[:400], time.time()))
        _db().commit()


def clear_findings(path=None):
    with _LOCK:
        if path:
            _db().execute("DELETE FROM findings WHERE path=?", (str(path),))
        else:
            _db().execute("DELETE FROM findings")
        _db().commit()


def list_findings(limit=100):
    with _LOCK:
        cur = _db().execute(
            "SELECT path,line,rule,severity,message,ts FROM findings "
            "ORDER BY ts DESC LIMIT ?", (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------- seal chain ----------
def chain_append(kind, payload_sha256, prev_hash, hash_hex):
    with _LOCK:
        row = _db().execute("SELECT MAX(idx) FROM chain").fetchone()
        idx = (row[0] or 0) + 1
        _db().execute(
            "INSERT INTO chain(idx,ts,kind,payload_sha256,prev_hash,hash) "
            "VALUES(?,?,?,?,?,?)",
            (idx, time.time(), kind, payload_sha256, prev_hash, hash_hex))
        _db().commit()
    return idx


def chain_rows():
    with _LOCK:
        cur = _db().execute(
            "SELECT idx,ts,kind,payload_sha256,prev_hash,hash FROM chain ORDER BY idx")
        return [dict(zip(["idx", "ts", "kind", "payload_sha256",
                          "prev_hash", "hash"], r)) for r in cur.fetchall()]


# ---------- events ----------
def log_event(task_id, level, message):
    with _LOCK:
        _db().execute(
            "INSERT INTO events(ts,task_id,level,message) VALUES(?,?,?,?)",
            (time.time(), task_id or "", level, message[:400]))
        _db().commit()


def event_tail(limit=40):
    with _LOCK:
        cur = _db().execute(
            "SELECT ts,task_id,level,message FROM events ORDER BY ts DESC LIMIT ?",
            (limit,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
