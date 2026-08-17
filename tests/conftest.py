from pathlib import Path
import sys

API = Path(__file__).resolve().parents[1] / "apps" / "api"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))
