# Aodı-NexusZero

**The Sovereign Distributed Neural Hivemind & Zero-Cloud Sentinel**

Turn your machines into one sovereign brain: an encrypted-on-wire P2P device
mesh (Tailscale-ready), capability-aware task sharding, a silent local
vulnerability sentinel, and a tamper-evident sha256 seal chain — **zero cloud,
zero paid APIs, zero code leaving your machines.**

| Layer | Language | Role |
|---|---|---|
| `atlas/` | Go 1.21 (stdlib) | P2P mesh discovery: concurrent heartbeats, liveness, device state feed |
| `core/` | Python 3.8+ (stdlib only) | capability planner · distributed hivemind · sentinel rules · fuzzer · seal chain · API |
| `relay/` | Node 18+ (zero npm) | Telegram Bot notifications to your phone |
| `dashboard/` | HTML/JS (zero deps) | Arabic RTL live hivemind board |
| `seal-solidity/` | Solidity | optional public anchor contract for the seal-chain head |

- **License:** MIT © 2026 Baran Avisat
- **Support:** baranavisat@gmail.com · WhatsApp +90 531 326 37 22 (wa.me/905313263722)
- **100% free stack:** Ollama (local) · SQLite · Go/Python/Node stdlibs · Telegram Bot API (optional) · Tailscale (optional)

## The problem it kills

- Cloud AI means your code, your data and your findings leak to someone else's
  servers.
- Working locally means one lonely machine, idle GPUs elsewhere, no
  coordination, no shared audit trail.

**NexusZero merges your devices into one hivemind** (Mac + Windows GPU box +
any box on your tailnet) and keeps everything local:

```
[ atlas (Go, :9301) ]  ←— heartbeats —→  [ atlas peers: every machine ]
        ↓ topology feed
[ hivemind core (Python, :9302) ]  — capability planner picks the right device
        ↓ per-shard generation
[ Ollama fleet: mac · windows-gpu · laptop ]   → shard artifacts
        ↓ self-audit + sealing
[ Sentinel (silent local scan) ] + [ sha256 seal chain (SQLite) ] + [ Telegram → phone ]
```

## Live numbers (recorded hivemind demo)

From the dashboard capture — full dataset in [BENCHMARKS.md](BENCHMARKS.md):

| Metric | Value |
|---|---|
| Atlas heartbeat round-trip | **8 ms** |
| Failed-node re-shuffle (live drill) | `peer-127.0.0.1` dead (`Errno 64`) → shard auto-reassigned to `mac-local`, task **done** in 425 s end-to-end |
| Warm single-shard task | **2.09 s** (sealed, chain link #3) |
| Sentinel planted scan | **10/10 exact** (7 high · 2 med · 1 low) |
| Fuzzer batch | 29 mutations → **19 honest crashes** in **33 ms** |
| Deterministic planner | **18.2 µs/plan ≈ 54.8k plans/sec**, zero LLM planning |
| Seal chain | sha256 chain verified ✓ (tasks, scans, and manifests sealed) |

![Live hivemind dashboard](assets/dashboard-live.png)

## What "capability sharding" means here (honest scope)

- A goal is deterministically split into ≤ 3 shards (`analyze` / `implement`
  / `test`) — no LLM is used for planning or split decisions.
- Each shard is scored against every live node: tag match (`gpu`/`strong` vs
  `lite`), inverse load, **battery penalty** (a device at ≤ 20% is heavily
  deprioritized), latency, liveness.
- A node that drops out of heartbeats is excluded and the shard is re-shuffled
  to the next candidate. Bounded retries only — the mesh never spins.
- The **phone participates as the telemetry commander**: Telegram alerts on
  every assignment, failure and re-shuffle. (A full Android node would require
  Termux — documented as an optional extension, honestly.)

## Zero-Cloud Sentinel (silent local security)

12 self-contained rules (`NZ-X01..X12`): hardcoded credentials, eval/exec,
unsafe deserialization, `yaml.load`, `shell=True`, `os.system`, weak hashes
(md5/sha1), TLS verify disabled, SQL string interpolation, debug mode,
predictable randomness for secrets, dynamic subprocess file handles.
Everything runs from local files; nothing is uploaded, ever.

The **fuzzer** runs batched mutations of a target function inside an isolated
`python -I` child (rlimits: memory 512MB / CPU / fork / core=0, process-group
kill) and *honestly reports* every uncaught crash it finds.

## Seal chain (tamper-evident, offline-verifiable)

Every task manifest and every scan is hashed (`sha256`) and appended to a
local hash chain: `hash = sha256(prev_hash + payload_hash + kind)`. Verify
walks the chain and reports the first broken link. For public proof, pin the
chain head hash into `seal-solidity/NexusSeal.sol` on any testnet.

## Run in 60 seconds (no pip, no npm)

```bash
# 1) atlas mesh daemon (Go stdlib)
cd atlas && go build -o ../bin/nzx-atlas . && ./../bin/nzx-atlas

# 2) hivemind core + dashboard (Python stdlib)
python3 core/server.py --port 9302
open http://127.0.0.1:9302/dashboard

# 3) optional phone alerts
node relay/relay.js
```

First actions:

```bash
python3 core/cli.py nodes add win-gpu http://100.x.y.z:11434 gpu
python3 core/cli.py status
python3 core/cli.py run "design an expression evaluator, then generate tests"
python3 core/cli.py scan examples             # silent local audit
python3 core/cli.py seal README.md
python3 core/cli.py verify
```

Or over HTTP: `curl -X POST :9302/api/task -d '{"goal":"...",}'`, then
`/api/task/<id>`, `/api/findings`, `/api/chain`.

## Tests

```bash
python3 tests/test_nexuszero.py -v    # planner · sentinel · fuzzer · seal
node --check relay/relay.js
cd atlas && gofmt -w . && go vet ./... && go build ./...
```

## Honest disclosure

- "Neural hivemind" here means: orchestrated, capability-routed, locally
  operated device federation over HTTP heartbeats. It is not model-weights
  sharding and does not pretend to be.
- Mesh transport is HTTPS-on-your-Tailscale; the daemons themselves do not
  (yet) mTLS-pin each peer.
- The seal chain is tamper-evident, not a distributed consensus ledger; the
  root hash can be anchored publicly via the optional Solidity contract.
- Battery/readiness hints are best-effort (mac `pmset`); on Linux/Windows
  without tooling the field stays honest `null`.

© 2026 Baran Avisat · MIT · BTC `bc1q8dhtdrndxsl70e97t8grydfe6pjue37zrhzf6c` · USDT-TRC20 `TLWdTjqqogkXNEXGiPWsGdjFP6ioycxeWW`
