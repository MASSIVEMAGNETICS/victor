from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

VERSION="0.3.0"

def canonical_json(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def _hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

SCHEMA="""
CREATE TABLE IF NOT EXISTS agents(agent_id TEXT PRIMARY KEY,profile_json TEXT NOT NULL,self_narrative TEXT NOT NULL DEFAULT '',learning_version INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS schedules(agent_id TEXT,block_order INTEGER,start_hour INTEGER,end_hour INTEGER,activity TEXT,location TEXT,PRIMARY KEY(agent_id,block_order));
CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY,event_id TEXT UNIQUE,tick INTEGER,day INTEGER,event_type TEXT,actor_id TEXT,target_id TEXT,payload_json TEXT,previous_chain_hash TEXT,event_hash TEXT,chain_hash TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS informatrons(informatron_id TEXT PRIMARY KEY,tick INTEGER,agent_id TEXT,kind TEXT,subject TEXT,predicate TEXT,object_json TEXT,evidence_event_id TEXT,confidence REAL,provenance_json TEXT);
CREATE TABLE IF NOT EXISTS memories(memory_id TEXT PRIMARY KEY,agent_id TEXT,memory_type TEXT,source_event_id TEXT,content TEXT,salience REAL,confidence REAL,tick_created INTEGER);
CREATE TABLE IF NOT EXISTS beliefs(agent_id TEXT,belief_key TEXT,belief_value_json TEXT,confidence REAL,source_event_id TEXT,tick_updated INTEGER,PRIMARY KEY(agent_id,belief_key));
CREATE TABLE IF NOT EXISTS relationships(source_agent_id TEXT,target_agent_id TEXT,trust REAL,familiarity REAL,last_tick INTEGER,PRIMARY KEY(source_agent_id,target_agent_id));
CREATE TABLE IF NOT EXISTS questions(question_id TEXT PRIMARY KEY,agent_id TEXT,question TEXT,status TEXT,answer TEXT,source_event_id TEXT,resolved_event_id TEXT,tick_created INTEGER,tick_resolved INTEGER);
CREATE TABLE IF NOT EXISTS artifacts(artifact_id TEXT PRIMARY KEY,creator_agent_id TEXT,medium TEXT,content TEXT,parent_artifact_id TEXT,inherited_json TEXT,mutations_json TEXT,open_handle TEXT,tick_created INTEGER,canonical INTEGER,canon_reasons_json TEXT);
CREATE TABLE IF NOT EXISTS awareness(agent_id TEXT,artifact_id TEXT,first_tick INTEGER,source_event_id TEXT,PRIMARY KEY(agent_id,artifact_id));
CREATE TABLE IF NOT EXISTS learning_examples(example_id TEXT PRIMARY KEY,agent_id TEXT,task_type TEXT,input_json TEXT,target_json TEXT,source_event_id TEXT,verified INTEGER,quality REAL,tick_created INTEGER);
CREATE TABLE IF NOT EXISTS audio_segments(audio_id TEXT PRIMARY KEY,event_id TEXT,speaker_agent_id TEXT,transcript TEXT,source_path TEXT,start_ms INTEGER,end_ms INTEGER,sha256 TEXT);
CREATE TABLE IF NOT EXISTS agent_learning_state(agent_id TEXT PRIMARY KEY,experience_count INTEGER DEFAULT 0,prediction_total INTEGER DEFAULT 0,prediction_correct INTEGER DEFAULT 0,share_bias REAL DEFAULT 0.0,question_bias REAL DEFAULT 0.0,adaptation_score REAL DEFAULT 0.0,last_tick INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS version_history(version_seq INTEGER PRIMARY KEY AUTOINCREMENT,version TEXT UNIQUE,change_json TEXT,previous_version_hash TEXT,version_hash TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS simulation_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS learning_history(
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    history_id TEXT UNIQUE,
    agent_id TEXT NOT NULL,
    tick INTEGER NOT NULL,
    day INTEGER NOT NULL,
    source_event_id TEXT,
    payload_json TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    entry_hash TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS experience_snapshots(
    snapshot_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    tick INTEGER NOT NULL,
    day INTEGER NOT NULL,
    state_json TEXT NOT NULL,
    source_history_count INTEGER NOT NULL,
    previous_snapshot_hash TEXT NOT NULL,
    snapshot_hash TEXT UNIQUE NOT NULL,
    UNIQUE(agent_id,version)
);
CREATE INDEX IF NOT EXISTS idx_events_actor ON events(actor_id,tick);
CREATE INDEX IF NOT EXISTS idx_inf_agent ON informatrons(agent_id,tick);
CREATE INDEX IF NOT EXISTS idx_memory_agent ON memories(agent_id,tick_created);
CREATE INDEX IF NOT EXISTS idx_learning_history_agent ON learning_history(agent_id,sequence);
CREATE INDEX IF NOT EXISTS idx_experience_snapshots_agent ON experience_snapshots(agent_id,version);
"""

APPEND_ONLY = (
    "events","informatrons","memories","artifacts","learning_examples",
    "version_history","learning_history","experience_snapshots"
)

class SocietyDB:
    def __init__(self,path:str|Path):
        self.conn=sqlite3.connect(str(path),timeout=30.0)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(SCHEMA)
        self._protect_append_only()
        self._version(VERSION,[
            "persistent resume by default",
            "append-only learning history",
            "versioned experience snapshots",
            "experience-state replay verification",
            "evidence-grounded copilot and co-creation help",
            "explicit destructive reset only",
            "deployable bootstrap workflow artifact",
        ])
        self.conn.commit()

    def _protect_append_only(self):
        for table in APPEND_ONLY:
            self.conn.executescript(f"""
            CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table}
            BEGIN SELECT RAISE(ABORT,'{table} is append-only'); END;
            CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table}
            BEGIN SELECT RAISE(ABORT,'{table} is append-only'); END;
            """)

    def close(self):
        self.conn.commit(); self.conn.close()

    def _version(self,version,changes):
        if self.conn.execute("SELECT 1 FROM version_history WHERE version=?",(version,)).fetchone(): return
        row=self.conn.execute("SELECT version_hash FROM version_history ORDER BY version_seq DESC LIMIT 1").fetchone()
        previous=row[0] if row else "GENESIS"
        core={"version":version,"changes":changes,"previous_version_hash":previous}
        vh=_hash(canonical_json(core))
        self.conn.execute("INSERT INTO version_history(version,change_json,previous_version_hash,version_hash) VALUES(?,?,?,?)",(version,canonical_json(changes),previous,vh))

    def set_meta(self,key,value):
        self.conn.execute("INSERT INTO simulation_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(key,str(value)))

    def get_meta(self,key,default=None):
        row=self.conn.execute("SELECT value FROM simulation_meta WHERE key=?",(key,)).fetchone()
        return row[0] if row else default

    def add_agent(self,p):
        self.conn.execute("INSERT OR IGNORE INTO agents(agent_id,profile_json) VALUES(?,?)",(p.agent_id,canonical_json(asdict(p))))
        self.conn.execute("INSERT OR IGNORE INTO agent_learning_state(agent_id) VALUES(?)",(p.agent_id,))

    def add_schedule(self,aid,role):
        zone=f"work_zone_{(int(aid[1:])-1)%5}"
        blocks=[(0,0,7,"sleep/home","home"),(1,7,9,"morning","home"),(2,9,17,f"work:{role}",zone),(3,17,21,"social/free_time","town"),(4,21,24,"home/reflection","home")]
        self.conn.executemany("INSERT OR IGNORE INTO schedules VALUES(?,?,?,?,?,?)",[(aid,*b) for b in blocks])

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

    def append_learning_history(self,aid,tick,day,payload,source_event_id=None):
        row=self.conn.execute("SELECT sequence,entry_hash FROM learning_history ORDER BY sequence DESC LIMIT 1").fetchone()
        sequence=(row[0]+1) if row else 1
        previous=row[1] if row else "GENESIS"
        core={"sequence":sequence,"agent_id":aid,"tick":int(tick),"day":int(day),"source_event_id":source_event_id,"payload":payload,"previous_hash":previous}
        entry_hash=_hash(canonical_json(core)); hid="LH-"+entry_hash[:24]
        self.conn.execute("INSERT INTO learning_history(history_id,agent_id,tick,day,source_event_id,payload_json,previous_hash,entry_hash) VALUES(?,?,?,?,?,?,?,?)",(hid,aid,tick,day,source_event_id,canonical_json(payload),previous,entry_hash))
        return hid

    def verify_learning_history(self):
        previous="GENESIS"; expected=1
        rows=self.conn.execute("SELECT sequence,history_id,agent_id,tick,day,source_event_id,payload_json,previous_hash,entry_hash FROM learning_history ORDER BY sequence").fetchall()
        for sequence,hid,aid,tick,day,source_event_id,payload_json,prev,entry_hash in rows:
            core={"sequence":sequence,"agent_id":aid,"tick":tick,"day":day,"source_event_id":source_event_id,"payload":json.loads(payload_json),"previous_hash":prev}
            actual=_hash(canonical_json(core))
            if sequence!=expected or prev!=previous or actual!=entry_hash or hid!="LH-"+actual[:24]: return False
            previous=entry_hash; expected+=1
        return True

    def experience_snapshot(self,aid,tick,day,state):
        row=self.conn.execute("SELECT version,snapshot_hash FROM experience_snapshots WHERE agent_id=? ORDER BY version DESC LIMIT 1",(aid,)).fetchone()
        version=(row[0]+1) if row else 1
        previous=row[1] if row else "GENESIS"
        count=self.conn.execute("SELECT COUNT(*) FROM learning_history WHERE agent_id=?",(aid,)).fetchone()[0]
        core={"agent_id":aid,"version":version,"tick":int(tick),"day":int(day),"state":state,"source_history_count":count,"previous_snapshot_hash":previous}
        snapshot_hash=_hash(canonical_json(core)); sid=f"XS-{aid}-{version:04d}-{snapshot_hash[:12]}"
        self.conn.execute("INSERT INTO experience_snapshots VALUES(?,?,?,?,?,?,?,?,?)",(sid,aid,version,tick,day,canonical_json(state),count,previous,snapshot_hash))
        self.conn.execute("UPDATE agents SET learning_version=? WHERE agent_id=?",(version,aid))
        return {"snapshot_id":sid,"version":version,"snapshot_hash":snapshot_hash,"source_history_count":count}

    def verify_experience_snapshots(self,aid=None):
        aids=[aid] if aid else [r[0] for r in self.conn.execute("SELECT DISTINCT agent_id FROM experience_snapshots ORDER BY agent_id")]
        for agent_id in aids:
            previous="GENESIS"; expected=1
            rows=self.conn.execute("SELECT snapshot_id,version,tick,day,state_json,source_history_count,previous_snapshot_hash,snapshot_hash FROM experience_snapshots WHERE agent_id=? ORDER BY version",(agent_id,)).fetchall()
            for sid,version,tick,day,state_json,count,prev,snapshot_hash in rows:
                core={"agent_id":agent_id,"version":version,"tick":tick,"day":day,"state":json.loads(state_json),"source_history_count":count,"previous_snapshot_hash":prev}
                actual=_hash(canonical_json(core))
                if version!=expected or prev!=previous or actual!=snapshot_hash or not sid.startswith(f"XS-{agent_id}-{version:04d}-"): return False
                previous=snapshot_hash; expected+=1
        return True
