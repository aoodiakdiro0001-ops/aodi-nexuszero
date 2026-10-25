# Changelog — Aodı-NexusZero

## 1.0.0 — 2026-10-25

First public release.

### Atlas (Go stdlib)
- P2P mesh discovery daemon: concurrent heartbeats (bounded goroutines),
  3-miss liveness policy, device state (tags, load, latency, battery),
  `/atlas/state` `/atlas/nodes` `/atlas/peers` `/atlas/health`.

### Hivemind core (Python stdlib)
- Deterministic capability planner: goals → ≤ 3 shards
  (analyze / implement / test), zero LLM planning.
- Node scoring: gpu/strong tag preference, inverse load, battery penalty
  (≤20% heavily deprioritized), latency, liveness; per-shard re-shuffle on
  device loss with bounded attempts (MAX_ATTEMPTS=3).
- Distributed execution over any Ollama endpoint (manual registry + atlas feed).
- Zero-Cloud Sentinel: 12 local vulnerability rules (NZ-X01..X12), silent,
  nothing uploaded; findings persisted in SQLite.
- Local fuzzer: batched mutations inside `python -I` isolation
  (RLIMIT_AS/CPU/NPROC/CORE=0 + killpg), honest crash reporting.
- sha256 seal chain (tamper-evident), verify walks the full chain and reports
  the first broken link; artifacts written to `~/.nzx/artifacts/<task>/`.
- nzctl CLI: status / nodes / run / scan / fuzz / seal / verify / chain / serve.
- Non-blocking Telegram telemetry (optional direct or relay).

### Relay (Node, zero deps)
- Telegram Bot notification relay with event buffer, `/emit` `/last` `/health`.

### Optional public anchoring
- `seal-solidity/NexusSeal.sol`: pin the local chain head on any EVM testnet.

### Known limitations (explicit)
- Study note: "hivemind" = orchestrated device federation (heartbeat routing);
  it is not model-weights sharding.
- No mTLS between peers yet — transport privacy relies on the tailnet.
