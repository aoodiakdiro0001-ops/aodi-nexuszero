# Contributing — Aodı-NexusZero

The project holds a strict **stdlib-first, zero-dependency** discipline.
Respect it and your patch lands fast.

## Ground rules

1. **Python core**: standard library only (`http.server`, `sqlite3`,
   `resource`, `subprocess`, `json`, `re`, `urllib`). No pip packages.
2. **Atlas**: Go standard library only; `go.mod` stays dependency-free.
3. **Relay**: Node built-ins only (`http`/`https`), zero npm deps.
4. **Bounded autonomy**: any automated loop (retries, re-shuffle, fuzzing)
   stays capped, logged and auditable. Never add an unbounded retry.
5. **Local-only data**: user code and findings never leave the machine. If you
   add a network call, it must carry only hashes/metadata and be documented.
6. **Dashboards must HTML-escape** every dynamic string.
7. **Docs in English** (README/ARCHITECTURE/CHANGELOG/SETUP/CONTRIBUTING/
   BENCHMARKS). Inline comments may be Arabic or English.

## Dev workflow

```bash
python3 core/server.py --port 9302          # core + dashboard
cd atlas && gofmt -w . && go vet ./... && go build -o ../bin/nzx-atlas .
./../bin/nzx-atlas                          # atlas
node relay/relay.js                         # optional relay

python3 tests/test_nexuszero.py -v          # must pass: no network, no Ollama
```

## Pull requests

- One logical change per PR.
- CI runs: Python 3.11 tests + Go vet/build + Node syntax check.
- New sentinel rules: plain regexes with severity + message; add a planted
  fixture line in `examples/vuln_fixture.py` and extend the test list.

## Reporting issues

Include OS, Go/Ollama versions, `nzctl status` output, and (for healing-loop
issues) the `shards` rows from `~/.nzx/nexus.db`.

## License

MIT © 2026 Baran Avisat. Contributions are accepted under the same license.
