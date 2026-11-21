"""Regenerate the small static navigation cache from an extracted official kit."""
import argparse
import gzip
import json
from pathlib import Path
import sys
import zlib

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from navigation import Arena

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kit", type=Path)
    kit = parser.parse_args().kit
    with gzip.open(kit/"check/stream.jsonl.gz", "rt") as f:
        mech = json.loads(next(f))["config"]["mech"]
    arena = Arena(kit/"arena", mech, load_cache=False)
    data = {key: getattr(arena, key) for key in ("fingerprint", "z", "clearance", "edges", "solids")}
    (root/"ground-grid.zlib").write_bytes(zlib.compress(json.dumps(data,separators=(",",":")).encode(), 6))
