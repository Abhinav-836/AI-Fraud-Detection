import os
import tempfile

# Isolate every test run: database, logs, reports and trained models go to a
# throw-away directory instead of the developer's real data folder.
_TMP = tempfile.mkdtemp(prefix="fraud-tests-")
os.environ["FRAUD_DATA_DIR"] = _TMP
os.environ.pop("FRAUD_API_KEY", None)
os.environ.pop("HISTORY_BACKEND", None)
