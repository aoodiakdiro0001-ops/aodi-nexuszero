"""Aodı-NexusZero — zero-cloud fuzzer: bounded crash-hunting in an isolated box.

Batched mutations run inside a single `python -I` child per execution, with
rlimits (memory/CPU/fork) and process-group kill on timeout — local only, and
LOUDLY honest: a found crash is surfaced, never silently swallowed.
"""
import json, os, resource, signal, subprocess, sys, tempfile, time
from pathlib import Path

import config


def _prep():
    def apply():
        mem = config.SANDBOX_MEM_MB * 1024 * 1024
        for res, lim in ((resource.RLIMIT_AS, (mem, mem)),
                         (resource.RLIMIT_CORE, (0, 0)),
                         (resource.RLIMIT_NPROC, (24, 24))):
            try:
                resource.setrlimit(res, lim)
            except Exception:
                pass
        try:
            c = config.SANDBOX_TIMEOUT
            resource.setrlimit(resource.RLIMIT_CPU, (c, c + 2))
        except Exception:
            pass
    return apply


def _seeds():
    return [0, 1, -1, 10 ** 9, 2 ** 63, "", "a", "A" * 64, "boom",
            "\x00", "🙂", None]


def _mutate():
    seeds = _seeds()
    out = []
    for s in seeds:
        out.append([s])
        out.append([s, s])
    out += [[1, 0], [0, -1], ["boom", 1], [None, None], [[1], 2]]
    return out


def fuzz_code(code, function, batch=None):
    """Run mutated calls of `function` in an isolated child.

    Returns {"rounds":N,"crashes":[{args,exception}], "ok":bool.clean_run}
    """
    batch = batch or min(config.FUZZ_ROUNDS, len(_mutate()))
    cases = _mutate()[:batch]
    with tempfile.TemporaryDirectory(prefix="nzx_fuzz_") as d:
        runner = os.path.join(d, "runner.py")
        cases_file = os.path.join(d, "cases.json")
        payload = (code + "\n\nimport json, traceback\n"
                   "cases = json.load(open(%r, encoding='utf-8'))\n"
                   "crashes = []\n"
                   "for c in cases:\n"
                   "    try:\n"
                   "        %s(*c)\n"
                   "    except Exception as e:\n"
                   "        crashes.append({'args': repr(c)[:120], 'type': type(e).__name__, 'error': str(e)[:160]})\n"
                   "print('NZX_FUZZ:' + json.dumps(crashes))\n" % (cases_file, function))
        Path(runner).write_text(payload, encoding="utf-8")
        Path(cases_file).write_text(json.dumps(cases), encoding="utf-8")
        t0 = time.time()
        try:
            proc = subprocess.Popen(
                [sys.executable, "-I", runner], cwd=d,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                preexec_fn=_prep(), start_new_session=True)
            out, _ = proc.communicate(timeout=config.SANDBOX_TIMEOUT)
            dur = int((time.time() - t0) * 1000)
            txt = out.decode("utf-8", "replace")[-3000:]
            if proc.returncode != 0:
                return {"rounds": batch, "crashes": [], "ok": False,
                        "fail_error": txt[-400:], "duration_ms": dur}
            marker = txt.rfind("NZX_FUZZ:")
            if marker < 0:
                return {"rounds": batch, "crashes": [], "ok": False,
                        "fail_error": "no fuzz marker", "duration_ms": dur}
            crashes = json.loads(txt[marker + 9:].splitlines()[0] or "[]")
            return {"rounds": batch, "crashes": crashes,
                    "ok": not crashes, "clean": not crashes,
                    "duration_ms": dur}
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
            return {"rounds": batch, "crashes": [{"args": "N/A", "type": "TIMEOUT",
                                                 "error": "fuzz batch exceeded sandbox timeout"}],
                    "ok": False, "clean": False,
                    "duration_ms": int((time.time() - t0) * 1000)}
