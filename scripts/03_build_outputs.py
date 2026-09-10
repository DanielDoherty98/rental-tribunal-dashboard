"""Stage 4-5 only: workbook, CSV and dashboard JSON."""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "src"))
import config
from rtscraper import dataset
recs = json.loads((config.DATA / "records.json").read_text("utf-8"))
df = dataset.to_frame(recs)
dataset.write_excel(df); dataset.write_csv(df); dataset.write_dashboard_json(df)
print(dataset.summary_frame(df).to_string(index=False))
