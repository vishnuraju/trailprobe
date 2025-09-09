import json, time, sys

class Recorder:
    def __init__(self, fp=None):
        self.fp = fp or sys.stdout

    def write(self, record: dict):
        record.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        self.fp.write(json.dumps(record, separators=(",", ":")) + "\n")
        self.fp.flush()
