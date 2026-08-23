import argparse, json
from signal_society import SignalSociety25

p=argparse.ArgumentParser()
p.add_argument('--db',default='signal_society_25.db')
p.add_argument('--seed',type=int,default=25)
p.add_argument('--seed-mode',choices=['signal','neutral','none'],default=None)
p.add_argument('--agent',default=None)
p.add_argument('--objective',default='What should I do next based on what I have learned?')
p.add_argument('--parent-artifact',default=None)
a=p.parse_args()

sim=SignalSociety25(a.db,a.seed,a.seed_mode)
try:
    snapshots=sim.bootstrap_experience()
    out={
        'version':'0.3.0',
        'snapshots_created':len(snapshots),
        'snapshot_chain_valid':sim.db.verify_experience_snapshots(),
        'learning_history_valid':sim.db.verify_learning_history(),
        'learning_replay_matches':sim.verify_learning_replay(),
        'snapshots':snapshots,
    }
    if a.agent:
        out['copilot']=sim.copilot(a.agent,a.objective,a.parent_artifact)
    print(json.dumps(out,indent=2,sort_keys=True))
finally:
    sim.db.close()
