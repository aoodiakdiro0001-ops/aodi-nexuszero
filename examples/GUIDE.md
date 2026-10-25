# Aodı-NexusZero — live examples for demos and tests

## 1. Registered live demo (goal → sharded run)

```bash
python3 core/cli.py nodes add mac-local   http://127.0.0.1:11434 lite
python3 core/cli.py nodes add excalibur   http://192.168.1.117:11434 gpu
python3 core/cli.py run "design the API contract for a chat ingest service, then implement a batching pipeline"
```

Watch the dashboard: shard 0 → lite node (analysis), shard 1 → gpu node
(heavy implement), telemetry events feed the phone.

## 2. Sentinel audit (planted findings, offline)

```bash
python3 core/cli.py scan examples/vuln_fixture.py
# → 10 findings across rules NZ-X01..X10 (hardcoded key, eval, pickle,
#    yaml.load, shell=True, os.system, md5, verify=False, SQL f-string, debug)
```

The fixture is *intentionally vulnerable* — never import it in production
code. Each planted line maps to exactly one rule for clean demo counts.

## 3. Fuzzer (isolated crash-hunt)

`examples/buggy_target.py`:

```python
def risky(a, b=1):
    return a / b
```

```bash
python3 core/cli.py fuzz examples/buggy_target.py risky
# → crashes found for b=0, empty/incompatible arg mutations (honest list)
```

## 4. Seal chain

```bash
python3 core/cli.py seal README.md
python3 core/cli.py chain
python3 core/cli.py verify        # OK
# merge one byte in the DB → verify reports the exact broken link
```

## 5. Re-shuffle drill

Push `POST /api/nodes/drop {"name":"excalibur"}` (or pull its atlas heartbeat)
while a task is running: the planner reassigns the shard to the next healthy
candidate and the phone gets the alert.
