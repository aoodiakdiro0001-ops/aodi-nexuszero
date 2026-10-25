# ARCHITECTURE — Aodı-NexusZero v1.0.0

## Key design decisions

1. **Go owns discovery, Python owns planning.** The atlas daemon (Go stdlib)
   runs bounded concurrent heartbeats and only feeds topology. The hivemind
   core (Python stdlib) consumes that feed plus a manual registry. Each layer
   does exactly one job and both expose plain HTTP APIs for auditability.

2. **Deterministic planning, zero LLM.** Shard splitting (`analyze` /
   `implement` / `test`, ≤ 3) and candidate scoring are pure rules. LLM calls
   happen only for shard execution. Cost surface stays zero and behavior is
   reproducible.

3. **Capability scoring with energy honesty.** Score = tag affinity
   (gpu/strong for implement shards) + inverse load + latency penalty +
   **battery penalty** (≤20% ⇒ −3.0 so a dying device loses to any healthy
   device even with tag advantage). Missing fields degrade gracefully (`null`
   never blocks planning).

4. **Bounded autonomy everywhere.** MAX_ATTEMPTS=3 per shard; a device missing
   3 heartbeats is excluded; fuzzer rounds are capped; all child executions run
   under `python -I` with RLIMIT_AS/CPU/NPROC/CORE=0 and process-group kill.

5. **Local-only truth with optional public proof.** All state, findings and
   artifacts live in `~/.nzx`. The seal chain
   (`hash = sha256(prev_hash + payload_hash + kind)`) is tamper-evident and
   verifiable offline; the optional NexusSeal contract anchors only the head
   hash publicly.

## Task flow (full path)

```
POST :9302/api/task {goal}
  → planner.decompose(goal)               [rules, ~µs]
  → peers.topology()                      [atlas feed + registry probes]
  → per shard: planner.pick(nodes, shard, exclude=down)
      → peers.generate(node, system, prompt)   → Ollama /api/generate
      → fail/none up? re-shuffle to next candidate (≤ MAX_ATTEMPTS)
  → sentinel.scan_text(bundle)            [12 local rules]
  → artifacts written to ~/.nzx/artifacts/<tid>/ + manifest.json
  → seal.seal_file(manifest)              [sha256 chain append]
  → telemetry.emit(...)                   [daemon thread → Telegram]
```

## SQLite schema (stdlib sqlite3)

| Table | Purpose |
|---|---|
| `tasks` | goal, status, shard totals, artifact path |
| `shards` | per-plan units: kind, tags, node, status, ms, error |
| `findings` | sentinel scan results (path, line, rule, severity) |
| `chain` | seal chain: idx, kind, payload_sha256, prev_hash, hash |
| `events` | telemetry tail for dashboard + phone |

## Security posture

- Sentinel rules are plain regexes over local text; no filenames of user code
  ever leave the machine (only the head hash does, if you choose to anchor).
- The fuzzer treats any uncaught exception as a finding — never silently
  swallowed; timeouts kill the entire process group.
- The dashboard uses HTML-escaping (`esc()`) for every dynamic string.

## Explicit limits (honest)

- No mTLS pinning between atlas peers yet; rely on the tailnet for transport
  privacy in v1.0.
- Battery/readiness hints are best-effort per platform (mac via `pmset`).
- "Neural hivemind" is orchestration-grade federation, not weights-sharding.
