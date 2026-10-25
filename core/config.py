"""Aodı-NexusZero 1.0.0 — core config & state (stdlib-only, zero deps)."""
import os
from pathlib import Path

VERSION = "1.0.0"
BRAND = "Aodı-NexusZero"

HOME = Path(os.environ.get("NZX_HOME", str(Path.home() / ".nzx")))
HOME.mkdir(parents=True, exist_ok=True)
NODES_FILE = HOME / "nodes.json"          # manual registry (merged with atlas)
DB_FILE = HOME / "nexus.db"
ARTIFACTS = HOME / "artifacts"

# Services
DEFAULT_PORT = int(os.environ.get("NZX_PORT", "9302"))        # hivemind core
ATLAS_URL = os.environ.get("NZX_ATLAS_URL", "http://127.0.0.1:9301")

# Execution guardrails (bounded everywhere)
MAX_ATTEMPTS = int(os.environ.get("NZX_MAX_ATTEMPTS", "3"))
GEN_TIMEOUT = int(os.environ.get("NZX_GEN_TIMEOUT", "300"))
SANDBOX_TIMEOUT = int(os.environ.get("NZX_SANDBOX_TIMEOUT", "12"))
SANDBOX_MEM_MB = int(os.environ.get("NZX_MEM_MB", "512"))
FUZZ_ROUNDS = int(os.environ.get("NZX_FUZZ_ROUNDS", "30"))

# Optional secrets / secrets-derived chains
TELEGRAM_BOT_TOKEN = os.environ.get("NZX_TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("NZX_TELEGRAM_CHAT", "")
TELEGRAM_RELAY = os.environ.get("NZX_TELEGRAM_RELAY", "")     # http://127.0.0.1:7442/emit

# Capability tags understood by the planner:
#   "gpu"|"strong"  → heavy tensor/model shards
#   "lite"          → analysis / contract / test shards
TIER_TAGS = {"heavy": ("gpu", "strong"), "lite": ("lite",)}

CONTACT = {
    "email": "baranavisat@gmail.com",
    "whatsapp": "+90 531 326 37 22",
    "whatsapp_url": "https://wa.me/905313263722",
    "github": "https://github.com/aoodiakdiro0001-ops",
    "btc": "bc1q8dhtdrndxsl70e97t8grydfe6pjue37zrhzf6c",
    "usdt": "TLWdTjqqogkXNEXGiPWsGdjFP6ioycxeWW",
}


def load_nodes():
    """Manual nodes: [{name, ollama_url, tags[], load?, battery?}] (merged with atlas)."""
    import json
    if NODES_FILE.exists():
        try:
            data = json.loads(NODES_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return [n for n in data if isinstance(n, dict)]
        except Exception:
            pass
    return []


def save_nodes(nodes):
    import json
    NODES_FILE.write_text(
        json.dumps(nodes, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def banner():
    return "\n".join([
        "=======================================================",
        f"  {BRAND} v{VERSION} — sovereign neural hivemind",
        "  atlas P2P mesh · capability sharding · zero-cloud sentinel",
        "  sha256 seal-chain · telegram telemetry (optional)",
        "=======================================================",
    ])
