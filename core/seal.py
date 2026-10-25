"""Aodı-NexusZero — sha256 seal chain (tamper-evident local attestation).

Each sealed artifact: hash = sha256(prev_hash + payload_sha256 + kind).
Verify walks the whole chain and reports the first broken link.
Optional public anchor: seal-solidity/NexusSeal.sol (store the head hash).
"""
import hashlib, time

import storage


def _hash(prev, payload_hash, kind):
    h = hashlib.sha256()
    h.update((prev + payload_hash + kind).encode("utf-8"))
    return h.hexdigest()


def head():
    rows = storage.chain_rows()
    return rows[-1] if rows else None


def seal_bytes(kind, data: bytes):
    payload_hash = hashlib.sha256(data).hexdigest()
    h0 = (head() or {}).get("hash", "") or "GENESIS"
    hexhash = _hash(h0, payload_hash, kind)
    idx = storage.chain_append(kind, payload_hash, h0, hexhash)
    return {"idx": idx, "kind": kind, "payload_sha256": payload_hash,
            "prev_hash": h0, "hash": hexhash, "ts": time.time()}


def seal_file(path, kind="artifact"):
    with open(path, "rb") as f:
        return seal_bytes(kind, f.read())


def verify():
    rows = storage.chain_rows()
    prev = "GENESIS"
    for r in rows:
        expect = _hash(prev, r["payload_sha256"], r["kind"])
        if expect != r["hash"]:
            return {"ok": False, "broken_at_idx": r["idx"], "size": len(rows),
                    "detail": f"link {r['idx']} hash mismatch"}
        prev = r["hash"]
    return {"ok": True, "broken_at_idx": None, "size": len(rows),
            "head": prev}
