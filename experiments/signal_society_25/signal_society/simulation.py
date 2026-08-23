from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

from .db import SocietyDB, VERSION, canonical_json, _hash
from .genome import verify_descendant
from .learning import ExperienceLearner

SEED_TEXT="Carry something forward. Change something. Leave something unfinished."
NEUTRAL_SEED="A red cup sits beside the window."
ROLES=["mechanic","cook","warehouse_worker","nurse","teacher","parent","caregiver","programmer","carpenter","entrepreneur","journalist","accountant","scientist","musician","bartender","storyteller","student","gamer","aspiring_artist","retiree","veteran","grandparent","driver","librarian","electrician"]
VALUES=["family","evidence","independence","tradition","curiosity","craft","community","loyalty","freedom","stability","truth","creativity","care","skepticism","legacy"]

@dataclass(frozen=True)
class Agent:
    agent_id:str
    name:str
    role:str
    openness:float
    conscientiousness:float
    extraversion:float
    agreeableness:float
    skepticism:float
    values:Tuple[str,...]

class SignalSociety25:
    def __init__(self,db_path:str|Path,seed:int=25,seed_mode:str|None=None):
        requested=seed_mode
        if requested is not None and requested not in {"signal","neutral","none"}:
            raise ValueError("seed_mode must be signal, neutral, none, or None")
        self.seed=int(seed)
        self.db=SocietyDB(db_path)
        self.learn=ExperienceLearner(self.db)
        self.agents={}
        existing=self.db.conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0] > 0
        if existing:
            self._load_agents()
            inferred=self._infer_existing_seed_mode()
            stored=self.db.get_meta("seed_mode",inferred)
            self.seed_mode=stored
            if requested is not None and requested != self.seed_mode:
                raise ValueError(f"existing database seed_mode={self.seed_mode!r}; requested {requested!r}")
            self.tick=int(self.db.get_meta("tick",self._max_tick()))
            self.day=int(self.db.get_meta("day",self._max_day()))
            stored_seed=int(self.db.get_meta("seed",self.seed))
            if stored_seed != self.seed:
                raise ValueError(f"existing database seed={stored_seed}; requested seed={self.seed}")
        else:
            self.seed_mode=requested or "signal"
            self.tick=0; self.day=0
            self._agents()
            if self.seed_mode!="none": self._seed_artifact()
        self._persist_runtime_meta()
        self.db.conn.commit()

    def _infer_existing_seed_mode(self):
        row=self.db.conn.execute("SELECT content FROM artifacts WHERE artifact_id='ART-SEED-001'").fetchone()
        if not row: return "none"
        if row[0]==NEUTRAL_SEED: return "neutral"
        return "signal"

    def _max_tick(self):
        row=self.db.conn.execute("SELECT COALESCE(MAX(tick),0) FROM events").fetchone()
        return int(row[0] or 0)

    def _max_day(self):
        row=self.db.conn.execute("SELECT COALESCE(MAX(day),0) FROM events").fetchone()
        return int(row[0] or 0)

    def _persist_runtime_meta(self):
        self.db.set_meta("tick",self.tick)
        self.db.set_meta("day",self.day)
        self.db.set_meta("seed",self.seed)
        self.db.set_meta("seed_mode",self.seed_mode)
        self.db.set_meta("version",VERSION)

    def _rng(self,label:str):
        digest=hashlib.sha256(f"{self.seed}|{self.day}|{self.tick}|{label}".encode()).hexdigest()
        return random.Random(int(digest[:16],16))

    def _agents(self):
        for i in range(25):
            aid=f"A{i+1:02d}"
            r=random.Random(int(hashlib.sha256(f"{self.seed}|agent|{i}".encode()).hexdigest()[:16],16))
            traits=[round(r.random(),3) for _ in range(5)]
            a=Agent(aid,f"Agent-{i+1:02d}",ROLES[i],*traits,tuple(r.sample(VALUES,3)))
            self.agents[aid]=a
            self.db.add_agent(a)
            self.db.add_schedule(aid,a.role)
        self.db.conn.commit()

    def _load_agents(self):
        for aid,profile_json in self.db.conn.execute("SELECT agent_id,profile_json FROM agents ORDER BY agent_id"):
            p=json.loads(profile_json); p["values"]=tuple(p.get("values") or ())
            self.agents[aid]=Agent(**p)

    def _seed_artifact(self):
        if self.db.conn.execute("SELECT 1 FROM artifacts WHERE artifact_id='ART-SEED-001'").fetchone():
            return
        content=SEED_TEXT if self.seed_mode=="signal" else NEUTRAL_SEED
        inherited=["evidence_over_authority","knowledge_continuity"] if self.seed_mode=="signal" else ["neutral_observation"]
        self.db.conn.execute(
            "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            ("ART-SEED-001",None,"handwritten_card",content,None,json.dumps(inherited),"[]","What should be carried forward next?",0,1,json.dumps(["seed:canonical"])),
        )
        self.db.conn.commit()

    def introduce_seed(self,aid="A14"):
        if self.seed_mode=="none": return None
        if self.db.conn.execute("SELECT 1 FROM awareness WHERE agent_id=? AND artifact_id='ART-SEED-001'",(aid,)).fetchone():
            return None
        content=SEED_TEXT if self.seed_mode=="signal" else NEUTRAL_SEED
        ev=self.db.event(self.tick,self.day,"seed.introduced",None,aid,{"artifact_id":"ART-SEED-001","text":content,"delivery":"found_beside_radio","seed_mode":self.seed_mode})
        self.db.conn.execute("INSERT OR IGNORE INTO awareness VALUES(?,?,?,?)",(aid,"ART-SEED-001",self.tick,ev))
        self.db.memory(aid,"episodic",ev,f"Found a card: {content}",.95,1,self.tick)
        self.db.belief(aid,"seed_awareness",{"artifact_id":"ART-SEED-001"},1,ev,self.tick)
        self.db.inf(self.tick,aid,"observation",aid,"encountered_artifact",{"artifact_id":"ART-SEED-001"},ev)
        self.db.question(aid,"Who created the card and why was it left there?",ev,self.tick)
        self.db.learn(aid,"episodic_recall",{"question":"What phrase did you find beside the radio?"},{"answer":content},ev,True,1,self.tick)
        self.learn.record_experience(aid,self.tick,day=self.day,surprise=.8,source_event_id=ev)
        self.db.conn.commit()
        return ev

    def known(self,aid):
        return [r[0] for r in self.db.conn.execute("SELECT artifact_id FROM awareness WHERE agent_id=? ORDER BY first_tick,artifact_id",(aid,))]

    def utterance(self,artifact):
        r=self._rng("utterance")
        if artifact:
            return r.choice([
                "I found this phrase and I'm not sure what to make of it.",
                "Someone left a message about carrying something forward.",
                "Carry something forward, change something, leave something unfinished.",
                "I don't know if this means anything, but I thought you might have a take on it.",
            ])
        return r.choice(["How's your day going?","Anything strange happen lately?","I've been thinking about what people leave behind.","Work's been a lot today."])

    def descendant(self,aid,parent):
        actor=self.agents[aid]
        parent_row=self.db.conn.execute("SELECT inherited_json,content FROM artifacts WHERE artifact_id=?",(parent,)).fetchone()
        if not parent_row: return None
        parent_inherited=json.loads(parent_row[0] or "[]")
        r=self._rng(f"descendant:{aid}:{parent}")
        carry=r.choice(parent_inherited) if parent_inherited else "knowledge_continuity"
        symbol=r.choice(["radio","fire","road","ledger","static","machine"])
        inherited=[carry,symbol]
        mutations=["medium"]+(["interpretation"] if actor.openness>.55 else [])
        medium=r.choice(["note","song_fragment","graffiti","story","joke","spoken_transmission"])
        content=r.choice([
            f"Keep the {symbol} alive, but don't repeat it exactly.",
            f"What survives us should change hands, not become a cage. ({symbol})",
            f"Pass the {symbol} on. Alter the route. Leave a question behind.",
            f"The {symbol} isn't the message. Carry one piece, change one piece, leave one piece open.",
        ])
        handle=r.choice(["Who receives it next?","What did the first version mean?","What happens if nobody carries it?","Who was transmitting before us?"])
        art="ART-"+hashlib.sha256(f"{aid}|{parent}|{content}|{self.tick}".encode()).hexdigest()[:16]
        canon=verify_descendant(parent_row[0],parent_row[1],inherited,mutations,handle,content)
        self.db.conn.execute(
            "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (art,aid,medium,content,parent,json.dumps(inherited),json.dumps(mutations),handle,self.tick,int(canon.canonical),json.dumps(canon.reasons)),
        )
        ev=self.db.event(self.tick,self.day,"artifact.created",aid,None,{"artifact_id":art,"parent_artifact_id":parent,"content":content,"medium":medium,"canonical":canon.canonical,"canon_reasons":canon.reasons})
        self.db.conn.execute("INSERT OR IGNORE INTO awareness VALUES(?,?,?,?)",(aid,art,self.tick,ev))
        self.db.inf(self.tick,aid,"artifact_mutation",art,"descends_from",{"parent":parent,"inherited":inherited,"mutations":mutations,"open_handle":handle,"canonical":canon.canonical},ev)
        self.db.learn(aid,"lineage",{"artifact":art},{"parent":parent,"inherited":inherited,"mutations":mutations,"canonical":canon.canonical},ev,True,.95,self.tick)
        self.learn.record_experience(aid,self.tick,day=self.day,surprise=.4,source_event_id=ev)
        return art

    def dyad(self,a,b):
        actor,target=self.agents[a],self.agents[b]
        known=self.known(a); policy=self.learn.state(a); r=self._rng(f"dyad:{a}:{b}")
        share_prob=max(0,min(.95,.25+.55*actor.openness+policy.share_bias))
        art=known[-1] if known and r.random()<share_prob else None
        text=self.utterance(art)
        ev=self.db.event(self.tick,self.day,"social.dialogue",a,b,{"utterance":text,"artifact_id":art,"channel":"dyadic"})
        self.db.audio(ev,a,text)
        self.db.memory(a,"social",ev,f"I spoke with {b}: {text}",.45,.9,self.tick)
        self.db.memory(b,"episodic",ev,f"{a} told me: {text}",.6,.9,self.tick)
        self.db.relation(a,b,0,.03,self.tick); self.db.relation(b,a,0,.03,self.tick)
        self.db.inf(self.tick,a,"social_dialogue",a,"spoke_to",{"target":b,"utterance":text,"artifact_id":art},ev)
        self.learn.record_experience(a,self.tick,day=self.day,surprise=.1,source_event_id=ev)
        self.learn.record_experience(b,self.tick,day=self.day,surprise=.1,source_event_id=ev)
        if art:
            first=self.db.conn.execute("SELECT 1 FROM awareness WHERE agent_id=? AND artifact_id=?",(b,art)).fetchone() is None
            if first:
                self.db.conn.execute("INSERT INTO awareness VALUES(?,?,?,?)",(b,art,self.tick,ev))
                self.db.belief(b,"last_signal_artifact",{"artifact_id":art},.8,ev,self.tick)
                self.db.learn(b,"social_recall",{"question":"Who first told you about this artifact?","artifact_id":art},{"answer":a},ev,True,1,self.tick)
            if target.skepticism+self.learn.state(b).question_bias>.55:
                qid=self.db.question(b,f"What evidence connects {art} to its claimed ancestor?",ev,self.tick)
                parent=self.db.conn.execute("SELECT parent_artifact_id FROM artifacts WHERE artifact_id=?",(art,)).fetchone()
                if parent and parent[0]:
                    answer=f"Recorded parent is {parent[0]}"
                    self.db.resolve_question(qid,answer,ev,self.tick)
                    self.db.learn(b,"question_resolution",{"question_id":qid},{"answer":answer},ev,True,1,self.tick)
            predicted=actor.openness*.35+(1-target.skepticism)*.65>=.5
            actual=target.openness*.55+(1-target.skepticism)*.45>=.48
            self.db.learn(a,"social_prediction",{"target":b,"artifact":art,"predicted_accept":predicted},{"actual_accept":actual},ev,True,1 if predicted==actual else .8,self.tick)
            self.learn.record_experience(a,self.tick,day=self.day,prediction_correct=(predicted==actual),surprise=.8 if predicted!=actual else .1,source_event_id=ev)
            if actual and r.random()<.18+.42*target.openness:
                self.descendant(b,art)
        self.db.conn.commit()

    def group(self,ids:List[str]):
        ids=sorted(set(ids)); carriers=[x for x in ids if self.known(x)]; art=None; r=self._rng("group:"+",".join(ids))
        if carriers and r.random()<.7:
            speaker=r.choice(carriers)
            art=self.known(speaker)[-1]
        else:
            speaker=r.choice(ids)
        text=self.utterance(art)
        ev=self.db.event(self.tick,self.day,"social.group_dialogue",speaker,None,{"participants":ids,"utterance":text,"artifact_id":art,"channel":"group"})
        self.db.audio(ev,speaker,text)
        for aid in ids:
            self.db.memory(aid,"social" if aid==speaker else "episodic",ev,("I told the group: " if aid==speaker else f"In a group, {speaker} said: ")+text,.5,.9,self.tick)
            self.db.inf(self.tick,aid,"group_dialogue",f"group:{self.day}:{self.tick}","participated",{"speaker":speaker,"participants":ids,"artifact_id":art,"utterance":text},ev)
            if aid!=speaker:self.db.relation(aid,speaker,0,.02,self.tick)
            if art and self.db.conn.execute("SELECT 1 FROM awareness WHERE agent_id=? AND artifact_id=?",(aid,art)).fetchone() is None:
                self.db.conn.execute("INSERT INTO awareness VALUES(?,?,?,?)",(aid,art,self.tick,ev))
                self.db.learn(aid,"group_social_recall",{"question":"Who introduced this artifact during the group interaction?","artifact_id":art},{"answer":speaker},ev,True,1,self.tick)
            self.learn.record_experience(aid,self.tick,day=self.day,surprise=.15,source_event_id=ev)
        self.db.conn.commit()

    def reflect(self,aid):
        rows=self.db.conn.execute("SELECT content FROM memories WHERE agent_id=? ORDER BY tick_created DESC LIMIT 3",(aid,)).fetchall()
        if not rows:return
        state=self.learn.state(aid)
        text=f"Day {self.day}: I am a {self.agents[aid].role}. Experience={state.experience_count}. Recent events: "+" | ".join(r[0] for r in rows)
        self.db.conn.execute("UPDATE agents SET self_narrative=? WHERE agent_id=?",(text,aid))
        ev=self.db.event(self.tick,self.day,"self.reflection",aid,None,{"narrative":text,"adaptation_score":state.adaptation_score})
        self.db.memory(aid,"self",ev,text,.7,.85,self.tick)
        self.db.inf(self.tick,aid,"self_narrative",aid,"reflects",{"text":text},ev,.85)
        self.db.learn(aid,"self_model",{"recent_memories":[r[0] for r in rows]},{"self_narrative":text},ev,True,.85,self.tick)
        self.learn.record_experience(aid,self.tick,day=self.day,surprise=.05,source_event_id=ev)
        self.db.conn.commit()

    def ask(self,aid,question,limit=5):
        return self.learn.help(aid,question,limit)

    def copilot(self,aid,objective,parent_artifact_id=None):
        return self.learn.copilot(aid,objective,parent_artifact_id)

    def bootstrap_experience(self):
        return self.learn.bootstrap(self.agents.keys(),self.tick,self.day)

    def verify_learning_replay(self):
        return all(self.learn.replay_matches_materialized(aid) for aid in self.agents)

    def export(self,outdir):
        out=Path(outdir); out.mkdir(parents=True,exist_ok=True); counts={}
        for aid in sorted(self.agents):
            rows=self.db.conn.execute("SELECT task_type,input_json,target_json,source_event_id,quality,tick_created FROM learning_examples WHERE agent_id=? AND verified=1 ORDER BY tick_created,example_id",(aid,)).fetchall()
            counts[aid]=len(rows)
            with (out/f"{aid}.jsonl").open("w",encoding="utf-8") as f:
                for task,inp,target,eid,quality,tick in rows:
                    f.write(json.dumps({"agent_id":aid,"task_type":task,"input":json.loads(inp),"target":json.loads(target),"source_event_id":eid,"quality":quality,"tick":tick,"dataset_version":VERSION},sort_keys=True)+"\n")
        return counts

    def _co_located_pair(self,ids):
        r=self._rng("co-located-pair")
        hour=r.randint(7,22); buckets={}
        for aid in ids:buckets.setdefault(self.db.location(aid,hour),[]).append(aid)
        pools=[v for v in buckets.values() if len(v)>=2]
        return tuple(r.sample(r.choice(pools) if pools else ids,2))

    def run(self,days=30,interactions_per_day=35,groups_per_day=2,introduce_day=3):
        ids=sorted(self.agents)
        start=self.day
        for d in range(start+1,start+days+1):
            self.day=d
            if d==introduce_day:self.introduce_seed()
            for n in range(interactions_per_day):
                self.tick+=1
                a,b=self._co_located_pair(ids)
                self.dyad(a,b)
            for n in range(groups_per_day):
                self.tick+=1
                r=self._rng(f"group-pick:{n}")
                self.group(r.sample(ids,r.randint(3,5)))
            for aid in ids:
                self.tick+=1
                self.reflect(aid)
            self._persist_runtime_meta()
            self.db.conn.commit()
        return self.metrics()

    def materialized_state_digest(self):
        state={
            "agents":[list(r) for r in self.db.conn.execute("SELECT agent_id,self_narrative,learning_version FROM agents ORDER BY agent_id")],
            "beliefs":[list(r) for r in self.db.conn.execute("SELECT agent_id,belief_key,belief_value_json,confidence,source_event_id,tick_updated FROM beliefs ORDER BY agent_id,belief_key")],
            "relationships":[list(r) for r in self.db.conn.execute("SELECT source_agent_id,target_agent_id,trust,familiarity,last_tick FROM relationships ORDER BY source_agent_id,target_agent_id")],
            "questions":[list(r) for r in self.db.conn.execute("SELECT question_id,status,answer,resolved_event_id,tick_resolved FROM questions ORDER BY question_id")],
            "awareness":[list(r) for r in self.db.conn.execute("SELECT agent_id,artifact_id,first_tick,source_event_id FROM awareness ORDER BY agent_id,artifact_id")],
            "learning_state":[list(r) for r in self.db.conn.execute("SELECT * FROM agent_learning_state ORDER BY agent_id")],
        }
        return _hash(canonical_json(state))

    def metrics(self):
        q=self.db.conn.execute
        pred=q("SELECT SUM(prediction_correct),SUM(prediction_total) FROM agent_learning_state").fetchone()
        accuracy=(pred[0]/pred[1]) if pred[1] else None
        return {
            "version":VERSION,"seed_mode":self.seed_mode,"agents":25,"days":self.day,"ticks":self.tick,
            "events":q("SELECT COUNT(*) FROM events").fetchone()[0],
            "informatrons":q("SELECT COUNT(*) FROM informatrons").fetchone()[0],
            "memories":q("SELECT COUNT(*) FROM memories").fetchone()[0],
            "verified_learning_examples":q("SELECT COUNT(*) FROM learning_examples WHERE verified=1").fetchone()[0],
            "learning_history":q("SELECT COUNT(*) FROM learning_history").fetchone()[0],
            "experience_snapshots":q("SELECT COUNT(*) FROM experience_snapshots").fetchone()[0],
            "questions_generated":q("SELECT COUNT(*) FROM questions").fetchone()[0],
            "questions_resolved":q("SELECT COUNT(*) FROM questions WHERE status='RESOLVED'").fetchone()[0],
            "audio_ready_dialogue_segments":q("SELECT COUNT(*) FROM audio_segments").fetchone()[0],
            "group_dialogue_events":q("SELECT COUNT(*) FROM events WHERE event_type='social.group_dialogue'").fetchone()[0],
            "agents_with_artifact_awareness":q("SELECT COUNT(DISTINCT agent_id) FROM awareness").fetchone()[0],
            "artifacts_total":q("SELECT COUNT(*) FROM artifacts").fetchone()[0],
            "canonical_descendants":q("SELECT COUNT(*) FROM artifacts WHERE parent_artifact_id IS NOT NULL AND canonical=1").fetchone()[0],
            "noncanonical_descendants":q("SELECT COUNT(*) FROM artifacts WHERE parent_artifact_id IS NOT NULL AND canonical=0").fetchone()[0],
            "prediction_accuracy":accuracy,
            "chronos_valid":self.db.verify_chronos(),
            "learning_history_valid":self.db.verify_learning_history(),
            "experience_snapshots_valid":self.db.verify_experience_snapshots(),
            "learning_replay_matches":self.verify_learning_replay(),
            "chronos_head":self.db.chronos_head(),
            "materialized_state_digest":self.materialized_state_digest(),
        }
