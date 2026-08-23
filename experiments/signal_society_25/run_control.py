import json
import tempfile
from pathlib import Path

from signal_society import SignalSociety25


def run(mode):
    with tempfile.TemporaryDirectory() as td:
        sim=SignalSociety25(Path(td)/f"{mode}.db",25,mode)
        try:
            return sim.run(days=20,interactions_per_day=20,groups_per_day=1)
        finally:
            sim.db.close()


print(json.dumps({"signal":run("signal"),"neutral":run("neutral"),"no_seed":run("none")},indent=2,sort_keys=True))
