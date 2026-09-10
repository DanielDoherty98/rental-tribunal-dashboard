from pathlib import Path
import datetime as _dt
MODEL_VERSION = "5.2.0"
ROOT = Path(__file__).resolve().parent
DATA, OUTPUT, DOCS = ROOT/"data", ROOT/"output", ROOT/"docs"
RAW, CACHE, DOCS_DATA = DATA/"raw", DATA/"cache", DOCS/"data"
for _p in (RAW, CACHE, OUTPUT, DOCS_DATA): _p.mkdir(parents=True, exist_ok=True)
BASE="https://www.gov.uk"; INDEX_PATH="/residential-property-tribunal-decisions"
SEARCH_API="https://www.gov.uk/api/search.json"
FORMAT="residential_property_tribunal_decision"; DECISION_CATEGORIES=["rents"]
PAGE_SIZE=100; SAFE_OFFSET_CEILING=900; MAX_REQUESTS=6000
PREFLIGHT_CACHE=DATA/"api_profile.json"; PREFLIGHT_MAX_AGE_DAYS=14
CANDIDATE_FIELDS=["title","link","description","public_timestamp",
 "tribunal_decision_decided_at","tribunal_decision_category",
 "tribunal_decision_sub_category","tribunal_decision_landlord_type",
 "tribunal_decision_decision_type"]
CANDIDATE_ORDERS=["-public_timestamp","-tribunal_decision_decided_at",""]
CANDIDATE_DATE_FILTERS=["public_timestamp","tribunal_decision_decided_at"]
USER_AGENT="RentalTribunalScraper/5.2 (research; contact: your.email@example.com)"
REQUEST_DELAY=0.6; REQUEST_TIMEOUT=45; MAX_RETRIES=4; BACKOFF=2.0
RRA_COMMENCEMENT=_dt.date(2026,5,1); NEW_FORM_FROM=_dt.date(2026,5,1)
WEEKS_PER_YEAR=52
CONVERSION_METHOD="weekly x 52 / 12; fortnightly x 26 / 12; quarterly / 3; annual / 12"
SUMMARY_ENGINE="rules"; OLLAMA_URL="http://localhost:11434/api/generate"
OLLAMA_MODEL="llama3.1:8b"; SUMMARY_MAX_WORDS=45
FULL_REFRESH=False
