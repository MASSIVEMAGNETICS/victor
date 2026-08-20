from __future__ import annotations
import hashlib, json, sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

SCHEMA = """
CREATE TABLE agents(agent_id TEXT PRIMARY KEY,profile_json TEXT NOT NULL,self_narrative TEXT NOT NULL DEFAULT '',learning_version INTEGER NOT NULL DEFAULT 0);
CREATE TABLE schedules(agent_id TEXT,block_order INTEGER,start_hour INTEGER,end_hour INTEGER,activity TEXT,location TEXT,PRIMARY KEY(agent_id,block_order));
CREATE TABLE events(event_id TEXT PRIMARY KEY,tick INTEGER,day INTEGER,event_type TEXT,actor_id TEXT,target_id TEXT,payload_json TEXT NOT NULL);
CREATE TABLE informatrons(informatron_id TEXT PRIMARY KEY,tick INTEGER,agent_id TEXT,kind TEXT,subject TEXT,predicate TEXT,object_json TEXT,evidence_event_id TEXT,confidence REAL,provenance_json TEXT);
CREATE TABLE memories(memory_id TEXT PRIMARY KEY,agent_id TEXT,memory_type TEXT,source_event_id TEXT,content TEXT,salience REAL,confidence REAL,tick_created INTEGER);
CREATE TABLE beliefs(agent_id TEXT,belief_key TEXT,belief_value_json TEXT,confidence REAL,source_event_id TEXT,tick_updated INTEGER,PRIMARY KEY(agent_id,belief_key));
CREATE TABLE relationships(source_agent_id TEXT,target_agent_id TEXT,trust REAL,familiarity REAL,last_tick INTEGER,PRIMARY KEY(source_agent_id,target_agent_id));
CREATE TABLE questions(question_id TEXT PRIMARY KEY,agent_id TEXT,question TEXT,status TEXT,answer TEXT,source_event_id TEXT,resolved_event_id TEXT,tick_created INTEGER,tick_resolved INTEGER);
CREATE TABLE artifacts(artifact_id TEXT PRIMARY KEY,creator_agent_id TEXT,medium TEXT,content TEXT,parent_artifact_id TEXT,inherited_json TEXT,mutations_json TEXT,open_handle TEXT,tick_created INTEGER,canonical INTEGER);
CREATE TABLE awareness(agent_id TEXT,artifact_id TEXT,first_tick INTEGER,source_event_id TEXT,PRIMARY KEY(agent_id,artifact_id));
CREATE TABLE learning_examples(example_id TEXT PRIMARY KEY,agent_id TEXT,task_type TEXT,input_json TEXT,target_json TEXT,source_event_id TEXT,verified INTEGER,quality REAL,tick_created INTEGER);
CREATE TABLE audio_segments(audio_id TEXT PRIMARY KEY,event_id TEXT,speaker_agent_id TEXT,transcript TEXT,source_path TEXT,start_ms INTEGER,end_ms INTEGER,sha256 TEXT);
CREATE INDEX idx_events_actor ON events(actor_id,tick);
CREATE INDEX idx_inf_agent ON informatrons(agent_id,tick);
CREATE INDEX idx_memory_agent ON memories(agent_id,tick_created);
"""

def _h(value: str, n: int = 20) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:n]

class SocietyDB:
    def __init__(self,path: str|Path):
        self.conn=sqlite3.connect(str(path)); self.conn.execute("PRAGMA journal_mode=WAL"); self.conn.executescript(SCHEMA); self.conn.commit()
    def close(self): self.conn.commit(); self.conn.close()
    def add_agent(self,p): self.conn.execute("INSERT INTO agents(agent_id,profile_json) VALUES(?,?)",(p.agent_id,json.dumps(asdict(p),sort_keys=True)))
    def add_schedule(self,aid,role):
        blocks=[(0,0,7,"sleep/home","home"),(1,7,9,"morning","home"),(2,9,17,f"work:{role}","work"),(3,17,21,"social/free_time","town"),(4,21,24,"home/reflection","home")]
        self.conn.executemany("INSERT INTO schedules VALUES(?,?,?,?,?,?)",[(aid,*b) for b in blocks])
    def event(self,tick,day,kind,actor,target,payload):
        eid="EV-"+_h(json.dumps([tick,day,kind,actor,target,payload],sort_keys=True)); self.conn.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?)",(eid,tick,day,kind,actor,target,json.dumps(payload,sort_keys=True))); return eid
    def inf(self,tick,aid,kind,subject,predicate,obj,eid,confidence=1.0):
        iid="INF-"+_h(json.dumps([tick,aid,kind,subject,predicate,obj,eid],sort_keys=True),24); self.conn.execute("INSERT INTO informatrons VALUES(?,?,?,?,?,?,?,?,?,?)",(iid,tick,aid,kind,subject,predicate,json.dumps(obj,sort_keys=True),eid,confidence,json.dumps({"source":"signal_society_25","event_id":eid},sort_keys=True))); return iid
    def memory(self,aid,mtype,eid,content,salience,confidence,tick):
        mid="MEM-"+_h(f"{aid}|{mtype}|{eid}|{content}"); self.conn.execute("INSERT OR IGNORE INTO memories VALUES(?,?,?,?,?,?,?,?)",(mid,aid,mtype,eid,content,salience,confidence,tick))
    def belief(self,aid,key,value,confidence,eid,tick):
        self.conn.execute("INSERT INTO beliefs VALUES(?,?,?,?,?,?) ON CONFLICT(agent_id,belief_key) DO UPDATE SET belief_value_json=excluded.belief_value_json,confidence=excluded.confidence,source_event_id=excluded.source_event_id,tick_updated=excluded.tick_updated",(aid,key,json.dumps(value,sort_keys=True),confidence,eid,tick))
    def relation(self,a,b,trust_delta,fam_delta,tick):
        row=self.conn.execute("SELECT trust,familiarity FROM relationships WHERE source_agent_id=? AND target_agent_id=?",(a,b)).fetchone(); trust,fam=row or (0.5,0.0); trust=max(0,min(1,trust+trust_delta)); fam=max(0,min(1,fam+fam_delta)); self.conn.execute("INSERT INTO relationships VALUES(?,?,?,?,?) ON CONFLICT(source_agent_id,target_agent_id) DO UPDATE SET trust=excluded.trust,familiarity=excluded.familiarity,last_tick=excluded.last_tick",(a,b,trust,fam,tick))
    def question(self,aid,text,eid,tick):
        qid="Q-"+_h(f"{aid}|{text}|{eid}"); self.conn.execute("INSERT OR IGNORE INTO questions(question_id,agent_id,question,status,source_event_id,tick_created) VALUES(?,?,?,?,?,?)",(qid,aid,text,"UNRESOLVED",eid,tick)); return qid
    def learn(self,aid,task,inp,target,eid,verified,quality,tick):
        lid="LE-"+_h(json.dumps([aid,task,inp,target,eid],sort_keys=True)); self.conn.execute("INSERT OR IGNORE INTO learning_examples VALUES(?,?,?,?,?,?,?,?,?)",(lid,aid,task,json.dumps(inp,sort_keys=True),json.dumps(target,sort_keys=True),eid,int(verified),quality,tick))
    def audio(self,eid,speaker,transcript):
        digest=hashlib.sha256(transcript.encode()).hexdigest(); aid="AUD-"+_h(eid+digest); self.conn.execute("INSERT OR IGNORE INTO audio_segments(audio_id,event_id,speaker_agent_id,transcript,sha256) VALUES(?,?,?,?,?)",(aid,eid,speaker,transcript,digest)); return aid
