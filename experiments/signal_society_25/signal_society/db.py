from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

VERSION="0.2.0"


def canonical_json(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)


def _hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


SCHEMA="""
CREATE TABLE agents(agent_id TEXT PRIMARY KEY,profile_json TEXT NOT NULL,self_narrative TEXT NOT NULL DEFAULT '',learning_version INTEGER NOT NULL DEFAULT 0);
CREATE TABLE schedules(agent_id TEXT,block_order INTEGER,start_hour INTEGER,end_hour INTEGER,activity TEXT,location TEXT,PRIMARY KEY(agent_id,block_order));
CREATE TABLE events(sequence INTEGER PRIMARY KEY,event_id TEXT UNIQUE,tick INTEGER,day INTEGER,event_type TEXT,actor_id TEXT,target_id TEXT,payload_json TEXT,previous_chain_hash TEXT,event_hash TEXT,chain_hash TEXT UNIQUE);
CREATE TABLE informatrons(informatron_id TEXT PRIMARY KEY,tick INTEGER,agent_id TEXT,kind TEXT,subject TEXT,predicate TEXT,object_json TEXT,evidence_event_id TEXT,confidence REAL,provenance_json TEXT);
CREATE TABLE memories(memory_id TEXT PRIMARY KEY,agent_id TEXT,memory_type TEXT,source_event_id TEXT,content TEXT,salience REAL,confidence REAL,tick_created INTEGER);
CREATE TABLE beliefs(agent_id TEXT,belief_key TEXT,belief_value_json TEXT,confidence REAL,source_event_id TEXT,tick_updated INTEGER,PRIMARY KEY(agent_id,belief_key));
CREATE TABLE relationships(source_agent_id TEXT,target_agent_id TEXT,trust REAL,familiarity REAL,last_tick INTEGER,PRIMARY KEY(source_agent_id,target_agent_id));
CREATE TABLE questions(question_id TEXT PRIMARY KEY,agent_id TEXT,question TEXT,status TEXT,answer TEXT,source_event_id TEXT,resolved_event_id TEXT,tick_created INTEGER,tick_resolved INTEGER);
CREATE TABLE artifacts(artifact_id TEXT PRIMARY KEY,creator_agent_id TEXT,medium TEXT,content TEXT,parent_artifact_id TEXT,inherited_json TEXT,mutations_json TEXT,open_handle TEXT,tick_created INTEGER,canonical INTEGER,canon_reasons_json TEXT);
CREATE TABLE awareness(agent_id TEXT,artifact_id TEXT,first_tick INTEGER,source_event_id TEXT,PRIMARY KEY(agent_id,artifact_id));
CREATE TABLE learning_examples(example_id TEXT PRIMARY KEY,agent_id TEXT,task_type TEXT,input_json TEXT,target_json TEXT,source_event_id TEXT,verified INTEGER,quality REAL,tick_created INTEGER);
CREATE TABLE audio_segments(audio_id TEXT PRIMARY KEY,event_id TEXT,speaker_agent_id TEXT,transcript TEXT,source_path TEXT,start_ms INTEGER,end_ms INTEGER,sha256 TEXT);
CREATE TABLE agent_learning_state(agent_id TEXT PRIMARY KEY,experience_count INTEGER DEFAULT 0,prediction_total INTEGER DEFAULT 0,prediction_correct INTEGER DEFAULT 0,share_bias REAL DEFAULT 0.0,question_bias REAL DEFAULT 0.0,adaptation_score REAL DEFAULT 0.0,last_tick INTEGER DEFAULT 0);
CREATE TABLE version_history(version_seq INTEGER PRIMARY KEY AUTOINCREMENT,version TEXT UNIQUE,change_json TEXT,previous_version_hash TEXT,version_hash TEXT UNIQUE);
CREATE INDEX idx_events_actor ON events(actor_id,tick);
CREATE INDEX idx_inf_agent ON informatrons(agent_id,tick);
CREATE INDEX idx_memory_agent ON memories(agent_id,tick_created);
CREATE TRIGGER events_no_update BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'events are append-only'); END;
CREATE TRIGGER events_no_delete BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'events are append-only'); END;
CREATE TRIGGER inf_no_update BEFORE UPDATE ON informatrons BEGIN SELECT RAISE(ABORT,'informatrons are append-only'); END;
CREATE TRIGGER inf_no_delete BEFORE DELETE ON informatrons BEGIN SELECT RAISE(ABORT,'informatrons are append-only'); END;
CREATE TRIGGER memories_no_update BEFORE UPDATE ON memories BEGIN SELECT RAISE(ABORT,'memories are append-only'); END;
CREATE TRIGGER memories_no_delete BEFORE DELETE ON memories BEGIN SELECT RAISE(ABORT,'memories are append-only'); END;
CREATE TRIGGER artifacts_no_update BEFORE UPDATE ON artifacts BEGIN SELECT RAISE(ABORT,'artifacts are append-only'); END;
CREATE TRIGGER artifacts_no_delete BEFORE DELETE ON artifacts BEGIN SELECT RAISE(ABORT,'artifacts are append-only'); END;
CREATE TRIGGER learning_no_update BEFORE UPDATE ON learning_examples BEGIN SELECT RAISE(ABORT,'learning examples are append-only'); END;
CREATE TRIGGER learning_no_delete BEFORE DELETE ON learning_examples BEGIN SELECT RAISE(ABORT,'learning examples are append-only'); END;
CREATE TRIGGER versions_no_update BEFORE UPDATE ON version_history BEGIN SELECT RAISE(ABORT,'version history is append-only'); END;
CREATE TRIGGER versions_no_delete BEFORE DELETE ON version_history BEGIN SELECT RAISE(ABORT,'version history is append-only'); END;
"""


class SocietyDB:
    def __init__(self,path:str|Path):
        self.conn=sqlite3.connect(str(path),timeout=30.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(SCHEMA)
        self._version(VERSION,["append-only chain","experience adaptation","canon verification","epistemic speaker fix","control modes"])
        self.conn.commit()

    def close(self):
        self.conn.commit(); self.conn.close()

    def _version(self,version,changes):
        if self.conn.execute("SELECT 1 FROM version_history WHERE version=?",(version,)).fetchone(): return
        row=self.conn.execute("SELECT version_hash FROM version_history ORDER BY version_seq DESC LIMIT 1").fetchone()
        previous=row[0] if row else "GENESIS"
        core={"version":version,"changes":changes,"previous_version_hash":previous}
        vh=_hash(canonical_json(core))
        self.conn.execute("INSERT INTO version_history(version,change_json,previous_version_hash,version_hash) VALUES(?,?,?,?)",(version,canonical_json(changes),previous,vh))

    def add_agent(self,p):
        self.conn.execute("INSERT INTO agents(agent_id,profile_json) VALUES(?,?)",(p.agent_id,canonical_json(asdict(p))))
        self.conn.execute("INSERT INTO agent_learning_state(agent_id) VALUES(?)",(p.agent_id,))

    def add_schedule(self,aid,role):
        blocks=[(0,0,7,"sleep/home","home"),(1,7,9,"morning","home"),(2,9,17,f"work:{role}",f"work:{role}"),(3,17,21,"social/free_time","town"),(4,21,24,"home/reflection","home")]
        self.conn.executemany("INSERT INTO schedules VALUES(?,?,?,?,?,?)",[(aid,*b) for b in blocks])

    def location(self,aid,hour):
        row=self.conn.execute("SELECT location FROM schedules WHERE agent_id=? AND start_hour<=? AND end_hour>? ORDER BY block_order LIMIT 1",(aid,hour,hour)).fetchone()
        return row[0] if row else "unknown"

    def event(self,tick,day,kind,actor,target,payload):
        row=self.conn.execute("SELECT sequence,chain_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        sequence=(row[0]+1) if row else 1
        previous=row[1] if row else "GENESIS"
        core={"sequence":sequence,"tick":tick,"day":day,"event_type":kind,"actor_id":actor,"target_id":target,"payload":payload,"previous_chain_hash":previous}
        event_hash=_hash(canonical_json(core)); chain_hash=_hash(previous+":"+event_hash); eid="EV-"+event_hash[:24]
        self.conn.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?)",(sequence,eid,tick,day,kind,actor,target,canonical_json(payload),previous,event_hash,chain_hash))
        return eid

    def verify_chronos(self):
        previous="GENESIS"; expected=1
        rows=self.conn.execute("SELECT sequence,event_id,tick,day,event_type,actor_id,target_id,payload_json,previous_chain_hash,event_hash,chain_hash FROM events ORDER BY sequence").fetchall()
        for sequence,eid,tick,day,kind,actor,target,payload_json,prev,event_hash,chain_hash in rows:
            core={"sequence":sequence,"tick":tick,"day":day,"event_type":kind,"actor_id":actor,"target_id":target,"payload":json.loads(payload_json),"previous_chain_hash":prev}
            actual=_hash(canonical_json(core)); actual_chain=_hash(prev+":"+actual)
            if sequence!=expected or prev!=previous or event_hash!=actual or chain_hash!=actual_chain or eid!="EV-"+actual[:24]: return False
            previous=chain_hash; expected+=1
        return True

    def chronos_head(self):
        row=self.conn.execute("SELECT chain_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone(); return row[0] if row else "GENESIS"

    def inf(self,tick,aid,kind,subject,predicate,obj,eid,confidence=1.0):
        provenance={"source":"signal_society_25","event_id":eid,"version":VERSION}
        core=[tick,aid,kind,subject,predicate,obj,eid,float(confidence),provenance]
        iid="INF-"+_hash(canonical_json(core))[:28]
        self.conn.execute("INSERT OR IGNORE INTO informatrons VALUES(?,?,?,?,?,?,?,?,?,?)",(iid,tick,aid,kind,subject,predicate,canonical_json(obj),eid,float(confidence),canonical_json(provenance)))
        return iid

    def memory(self,aid,mtype,eid,content,salience,confidence,tick):
        mid="MEM-"+_hash(f"{aid}|{mtype}|{eid}|{content}")[:24]
        self.conn.execute("INSERT OR IGNORE INTO memories VALUES(?,?,?,?,?,?,?,?)",(mid,aid,mtype,eid,content,salience,confidence,tick)); return mid

    def belief(self,aid,key,value,confidence,eid,tick):
        self.conn.execute("INSERT INTO beliefs VALUES(?,?,?,?,?,?) ON CONFLICT(agent_id,belief_key) DO UPDATE SET belief_value_json=excluded.belief_value_json,confidence=excluded.confidence,source_event_id=excluded.source_event_id,tick_updated=excluded.tick_updated",(aid,key,canonical_json(value),confidence,eid,tick))

    def relation(self,a,b,trust_delta,fam_delta,tick):
        row=self.conn.execute("SELECT trust,familiarity FROM relationships WHERE source_agent_id=? AND target_agent_id=?",(a,b)).fetchone(); trust,fam=row or (0.5,0.0)
        trust=max(0,min(1,trust+trust_delta)); fam=max(0,min(1,fam+fam_delta))
        self.conn.execute("INSERT INTO relationships VALUES(?,?,?,?,?) ON CONFLICT(source_agent_id,target_agent_id) DO UPDATE SET trust=excluded.trust,familiarity=excluded.familiarity,last_tick=excluded.last_tick",(a,b,trust,fam,tick))

    def question(self,aid,text,eid,tick):
        qid="Q-"+_hash(f"{aid}|{text}|{eid}")[:24]
        self.conn.execute("INSERT OR IGNORE INTO questions(question_id,agent_id,question,status,source_event_id,tick_created) VALUES(?,?,?,?,?,?)",(qid,aid,text,"UNRESOLVED",eid,tick)); return qid

    def resolve_question(self,qid,answer,eid,tick):
        self.conn.execute("UPDATE questions SET status='RESOLVED',answer=?,resolved_event_id=?,tick_resolved=? WHERE question_id=? AND status='UNRESOLVED'",(answer,eid,tick,qid))

    def learn(self,aid,task,inp,target,eid,verified,quality,tick):
        lid="LE-"+_hash(canonical_json([aid,task,inp,target,eid]))[:24]
        self.conn.execute("INSERT OR IGNORE INTO learning_examples VALUES(?,?,?,?,?,?,?,?,?)",(lid,aid,task,canonical_json(inp),canonical_json(target),eid,int(bool(verified)),quality,tick)); return lid

    def audio(self,eid,speaker,transcript):
        digest=_hash(transcript); aid="AUD-"+_hash(eid+digest)[:20]
        self.conn.execute("INSERT OR IGNORE INTO audio_segments(audio_id,event_id,speaker_agent_id,transcript,sha256) VALUES(?,?,?,?,?)",(aid,eid,speaker,transcript,digest)); return aid
