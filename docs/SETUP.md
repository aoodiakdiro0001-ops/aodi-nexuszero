# Setup — Aodı-NexusZero

No pip. No npm. No Docker required. Python 3.8+, Node 18+ (relay only),
Go 1.21+ (atlas only).

## 1. Local inference (Ollama, free)

```bash
ollama pull qwen2.5-coder
ollama serve    # on every compute machine
```

## 2. Atlas mesh daemon (Go)

```bash
cd atlas
go build -o ../bin/nzx-atlas .
NZX_NAME=mac-atlas NZX_TAGS="lite,gpu" ./../bin/nzx-atlas
```

| Env | Default | Meaning |
|---|---|---|
| `NZX_ADDR` | `:9301` | atlas listen address |
| `NZX_NAME` | hostname | device name in the mesh |
| `NZX_TAGS` | `lite,gpu` | capability tags (csv) |
| `NZX_OLLAMA` | `http://127.0.0.1:11434` | local inference endpoint |
| `NZX_PEERS` | — | seed peers (csv of atlas urls) |
| `NZX_ATLAS_HEARTBEAT_S` | `10` | heartbeat interval seconds |

Seed peers (or on another machine):

```bash
curl -X POST http://127.0.0.1:9301/atlas/peers \
  -H "Content-Type: application/json" \
  -d '{"peers":["http://100.101.102.103:9301"]}'
```

## 3. Hivemind core + dashboard (Python)

```bash
python3 core/server.py --port 9302     # or: python3 core/cli.py serve
open http://127.0.0.1:9302/dashboard
```

| Env | Default | Meaning |
|---|---|---|
| `NZX_HOME` | `~/.nzx` | state: nexus.db, nodes.json, artifacts/ |
| `NZX_ATLAS_URL` | `http://127.0.0.1:9301` | topology feed |
| `NZX_MAX_ATTEMPTS` | `3` | bounded retries per shard |
| `NZX_GEN_TIMEOUT` | `300` | per-generation seconds (600 on slow GPUs) |
| `NZX_SANDBOX_TIMEOUT` / `NZX_MEM_MB` | `12` / `512` | fuzz isolation |
| `NZX_FUZZ_ROUNDS` | `30` | mutations per fuzz batch |
| `NZX_TELEGRAM_RELAY` | — | e.g. `http://127.0.0.1:7442/emit` |
| `NZX_TELEGRAM_TOKEN`/`NZX_TELEGRAM_CHAT` | — | direct Telegram mode |

## 4. Register devices (compute nodes)

```bash
python3 core/cli.py nodes add mac-local  http://127.0.0.1:11434 lite
python3 core/cli.py nodes add win-gpu    http://100.x.y.z:11434 gpu
python3 core/cli.py nodes add excalibur  http://192.168.1.117:11434 gpu
python3 core/cli.py status
```

Or over HTTP: `POST /api/nodes {name, ollama_url, tags}`, drop drill:
`POST /api/nodes/drop {name}`.

## 5. Use it

```bash
python3 core/cli.py run "design an API contract for chat ingest, then implement a batching pipeline"
python3 core/cli.py scan examples/vuln_fixture.py
python3 core/cli.py fuzz examples/buggy_target.py risky
python3 core/cli.py seal README.md && python3 core/cli.py verify
```

## 6. Phone alerts (S25 Ultra via Telegram)

- Relay mode: `TELEGRAM_TOKEN=... TELEGRAM_CHAT=... node relay/relay.js`
  and set `NZX_TELEGRAM_RELAY=http://127.0.0.1:7442/emit` for the core.
- Direct mode: set `NZX_TELEGRAM_TOKEN`/`NZX_TELEGRAM_CHAT`, no relay needed.
- Optional Termux extension (honest): a full Android node needs Termux running
  the core subset; documented for exploration, not required for v1.

## 7. Tailscale mesh (recommended)

Install Tailscale on every device (free plan covers personal mesh).Device
discovery then simply uses the tailnet IPs — e.g. atlas peers on
`http://100.x.y.z:9301` and Ollama endpoints on `http://100.x.y.z:11434`.

## Support

baranavisat@gmail.com · WhatsApp +90 531 326 37 22 (wa.me/905313263722)
MIT © 2026 Baran Avisat
