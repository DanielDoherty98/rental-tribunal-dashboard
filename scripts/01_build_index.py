"""Stage 1 only: build data/index.json."""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "src"))
import config
from rtscraper import index as idx
rows = idx.build_index()
(config.DATA / "index.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
print(f"saved {len(rows)} entries")
