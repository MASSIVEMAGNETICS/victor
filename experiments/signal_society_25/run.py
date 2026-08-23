import argparse, json
from pathlib import Path
from signal_society import SignalSociety25

p=argparse.ArgumentParser()
p.add_argument('--db',default='signal_society_25.db')
p.add_argument('--days',type=int,default=30)
p.add_argument('--interactions-per-day',type=int,default=35)
p.add_argument('--groups-per-day',type=int,default=2)
p.add_argument('--seed',type=int,default=25)
p.add_argument('--seed-mode',choices=['signal','neutral','none'],default=None)
p.add_argument('--fresh',action='store_true',help='Explicitly discard the current materialized DB and start a new controlled run.')
p.add_argument('--bootstrap-experience',action='store_true')
p.add_argument('--verify-learning-replay',action='store_true')
p.add_argument('--export-training-data',default=None)
p.add_argument('--help-agent',default=None)
p.add_argument('--objective',default='What should I do next based on what I have learned?')
p.add_argument('--parent-artifact',default=None)
a=p.parse_args()
db=Path(a.db)
if a.fresh:
    db.unlink(missing_ok=True)
sim=SignalSociety25(db,a.seed,a.seed_mode)
try:
    r=sim.run(a.days,a.interactions_per_day,a.groups_per_day)
    if a.bootstrap_experience:
        r['experience_bootstrap']=sim.bootstrap_experience()
        r['experience_snapshots']=sim.db.conn.execute("SELECT COUNT(*) FROM experience_snapshots").fetchone()[0]
    if a.verify_learning_replay:
        r['learning_replay_matches']=sim.verify_learning_replay()
    if a.export_training_data:
        r['training_exports']=sim.export(a.export_training_data)
    if a.help_agent:
        r['copilot']=sim.copilot(a.help_agent,a.objective,a.parent_artifact)
    print(json.dumps(r,indent=2,sort_keys=True))
finally:
    sim.db.close()
