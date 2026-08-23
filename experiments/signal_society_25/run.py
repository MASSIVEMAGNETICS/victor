import argparse, json
from pathlib import Path
from signal_society import SignalSociety25
p=argparse.ArgumentParser(); p.add_argument('--db',default='signal_society_25.db'); p.add_argument('--days',type=int,default=30); p.add_argument('--interactions-per-day',type=int,default=35); p.add_argument('--groups-per-day',type=int,default=2); p.add_argument('--seed',type=int,default=25); p.add_argument('--export-training-data',default=None); a=p.parse_args(); db=Path(a.db); db.unlink(missing_ok=True); sim=SignalSociety25(db,a.seed)
try:
    r=sim.run(a.days,a.interactions_per_day,a.groups_per_day)
    if a.export_training_data:r['training_exports']=sim.export(a.export_training_data)
    print(json.dumps(r,indent=2,sort_keys=True))
finally:sim.db.close()
