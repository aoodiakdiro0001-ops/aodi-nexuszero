"""Aodı-NexusZero — Zero-Cloud Sentinel: local silent vulnerability scanner.

Rules NZ-X01..X12 run on plain text; no network, no cloud, no vendor leak.
Severity: high | medium | low.
"""
import re
from pathlib import Path

RULES = [
    ("NZ-X01", re.compile(r"(AKIA[0-9A-Z]{16}|(?i:api[_-]?key\s*=\s*[\"'][^\"']{12,}))"),
     "high", "hardcoded cloud credential / API key literal"),
    ("NZ-X02", re.compile(r"(?<![\w.])(eval|exec)\s*\(", re.I),
     "high", "dynamic code execution (eval/exec)"),
    ("NZ-X03", re.compile(r"(pickle|marshal)\.loads?\s*\("),
     "high", "unsafe deserialization (pickle/marshal)"),
    ("NZ-X04", re.compile(r"yaml\.load\s*\((?![^)]*Loader)"),
     "medium", "yaml.load without explicit safe Loader"),
    ("NZ-X05", re.compile(r"shell\s*=\s*True"),
     "high", "subprocess shell=True injection surface"),
    ("NZ-X06", re.compile(r"os\.(system|popen)\s*\("),
     "high", "os.system / os.popen shell call"),
    ("NZ-X07", re.compile(r"hashlib\.(md5|sha1)\s*\("),
     "medium", "weak hash algorithm (md5/sha1)"),
    ("NZ-X08", re.compile(r"verify\s*=\s*False|check_hostname\s*=\s*False"),
     "high", "TLS verification disabled"),
    ("NZ-X09", re.compile(
        r"(?i)(select|insert|update|delete)[^;\n]{0,80}(%\s*\w|\{[a-z_]+\}|f[\"'])"),
     "high", "SQL built by string concatenation/interpolation"),
    ("NZ-X10", re.compile(r"debug\s*=\s*True"),
     "low", "debug mode enabled in production code"),
    ("NZ-X11", re.compile(
        r"(?i)(token|secret|nonce|salt)\s*=\s*random\.(random|choice|randint)"),
     "medium", "predictable randomness used for security values"),
    ("NZ-X12", re.compile(r"subprocess\.\w+\([^)]*open\("),
     "low", "subprocess argument built from dynamic file handle"),
]

EXTS = {".py", ".js", ".go", ".sol", ".java", ".sh"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", "bin", "venv", ".aodim", ".aodix", ".nzx"}


def scan_text(text, origin="<memory>"):
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for rid, rx, sev, msg in RULES:
            if rx.search(line):
                out.append({"path": origin, "line": i, "rule": rid,
                            "severity": sev, "message": msg,
                            "snippet": line.strip()[:160]})
    return out


def scan_path(path):
    """Walk a directory or scan a single file. Returns list of findings."""
    p = Path(path)
    if p.is_file():
        return scan_file(p)
    hits = []
    for f in sorted(p.rglob("*")):
        if not f.is_file() or f.suffix.lower() not in EXTS:
            continue
        if any(d in f.parts for d in SKIP_DIRS):
            continue
        hits.extend(scan_file(f))
    return hits


def scan_file(f):
    try:
        text = f.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    return [{"path": str(f), "line": r["line"], "rule": r["rule"],
             "severity": r["severity"], "message": r["message"],
             "snippet": r["snippet"]} for r in scan_text(text, str(f))]


def summary(findings):
    by = {}
    for fnd in findings:
        key = fnd["severity"]
        by[key] = by.get(key, 0) + 1
    return {"total": len(findings),
            "by_severity": {k: by[k] for k in ("high", "medium", "low") if k in by}}
