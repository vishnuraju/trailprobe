import json, time, sys
from threading import Lock

class Recorder:
    def __init__(self, fp=None):
        self.fp = fp or sys.stdout
        self._lock = Lock()

    def write(self, record: dict):
        record.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        line = json.dumps(record, separators=(",", ":")) + "\n"
        with self._lock:
            self.fp.write(line)
            self.fp.flush()