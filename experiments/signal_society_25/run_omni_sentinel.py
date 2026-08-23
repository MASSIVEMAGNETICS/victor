import argparse, json
from pathlib import Path
from signal_society import SignalSociety25
from cluster.sentinel import VictorOmniSentinel

p=argparse.ArgumentParser()
p.add_argument("--db",default="deployment/signal_society_25.db")
p.add_argument("--seed",type=int,default=25)
p.add_argument("--seed-mode",choices=["signal","neutral","none"],default="signal")
a=p.parse_args()
sim=SignalSociety25(Path(a.db),a.seed,a.seed_mode)
try:
    print(json.dumps(VictorOmniSentinel(sim).scan(),indent=2,sort_keys=True))
finally:
    sim.db.close()
