from __future__ import annotations
import hashlib, json, random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
from .db import SocietyDB

SEED_TEXT="Carry something forward. Change something. Leave something unfinished."
ROLES=["mechanic","cook","warehouse_worker","nurse","teacher","parent","caregiver","programmer","carpenter","entrepreneur","journalist","accountant","scientist","musician","bartender","storyteller","student","gamer","aspiring_artist","retiree","veteran","grandparent","driver","librarian","electrician"]
VALUES=["family","evidence","independence","tradition","curiosity","craft","community","loyalty","freedom","stability","truth","creativity","care","skepticism","legacy"]

@dataclass(frozen=True)
class Agent:
    agent_id:str; name:str; role:str; openness:float; conscientiousness:float; extraversion:float; agreeableness:float; skepticism:float; values:Tuple[str,...]

class SignalSociety25:
    def __init__(self,db_path:str|Path,seed:int=25):
        self.rng=random.Random(seed); self.db=SocietyDB(db_path); self.tick=0; self.day=0; self.agents={}; self._agents(); self._seed_artifact()
    def _agents(self):
        for i in range(25):
            aid=f"A{i+1:02d}"; a=Agent(aid,f"Agent-{i+1:02d}",ROLES[i],*[round(self.rng.random(),3) for _ in range(5)],tuple(self.rng.sample(VALUES,3))); self.agents[aid]=a; self.db.add_agent(a); self.db.add_schedule(aid,a.role)
        self.db.conn.commit()
    def _seed_artifact(self):
        self.db.conn.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",("ART-SEED-001",None,"handwritten_card",SEED_TEXT,None,json.dumps(["evidence_over_authority","knowledge_continuity"]),"[]","What should be carried forward next?",0,1)); self.db.conn.commit()
    def introduce_seed(self,aid="A14"):
        ev=self.db.event(self.tick,self.day,"seed.introduced",None,aid,{"artifact_id":"ART-SEED-001","text":SEED_TEXT,"delivery":"found_beside_radio"}); self.db.conn.execute("INSERT OR IGNORE INTO awareness VALUES(?,?,?,?)",(aid,"ART-SEED-001",self.tick,ev)); self.db.memory(aid,"episodic",ev,f"Found a card: {SEED_TEXT}",.95,1,self.tick); self.db.belief(aid,"seed_awareness",{"artifact_id":"ART-SEED-001"},1,ev,self.tick); self.db.inf(self.tick,aid,"observation",aid,"encountered_artifact",{"artifact_id":"ART-SEED-001"},ev); self.db.question(aid,"Who created the card and why was it left there?",ev,self.tick); self.db.learn(aid,"episodic_recall",{"question":"What phrase did you find beside the radio?"},{"answer":SEED_TEXT},ev,True,1,self.tick); self.db.conn.commit()
    def known(self,aid): return [r[0] for r in self.db.conn.execute("SELECT artifact_id FROM awareness WHERE agent_id=? ORDER BY first_tick",(aid,))]
    def utterance(self,artifact):
        if artifact: return self.rng.choice(["I found this phrase and I'm not sure what to make of it.","Someone left a message about carrying something forward.","Carry something forward, change something, leave something unfinished.","I don't know if this means anything, but I thought you might have a take on it."])
        return self.rng.choice(["How's your day going?","Anything strange happen lately?","I've been thinking about what people leave behind.","Work's been a lot today."])
    def descendant(self,aid,parent):
        a=self.agents[aid]; medium=self.rng.choice(["note","song_fragment","graffiti","story","joke","spoken_transmission"]); symbol=self.rng.choice(["radio","fire","road","ledger","static","machine"]); inherited=[symbol,self.rng.choice(["evidence_over_authority","knowledge_continuity","finite_life"])]; mutations=["medium"]+(["interpretation"] if a.openness>.55 else []); content=self.rng.choice([f"Keep the {symbol} alive, but don't repeat it exactly.",f"What survives us should change hands, not become a cage. ({symbol})",f"Pass the {symbol} on. Alter the route. Leave a question behind.",f"The {symbol} isn't the message. Carry one piece, change one piece, leave one piece open."]); art="ART-"+hashlib.sha256(f"{aid}|{parent}|{content}|{self.tick}".encode()).hexdigest()[:16]; handle=self.rng.choice(["Who receives it next?","What did the first version mean?","What happens if nobody carries it?","Who was transmitting before us?"]); self.db.conn.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",(art,aid,medium,content,parent,json.dumps(inherited),json.dumps(mutations),handle,self.tick,1)); ev=self.db.event(self.tick,self.day,"artifact.created",aid,None,{"artifact_id":art,"parent_artifact_id":parent,"content":content,"medium":medium}); self.db.conn.execute("INSERT OR IGNORE INTO awareness VALUES(?,?,?,?)",(aid,art,self.tick,ev)); self.db.inf(self.tick,aid,"artifact_mutation",art,"descends_from",{"parent":parent,"inherited":inherited,"mutations":mutations,"open_handle":handle},ev); self.db.learn(aid,"lineage",{"artifact":art},{"parent":parent,"inherited":inherited,"mutations":mutations},ev,True,.95,self.tick); return art
    def dyad(self,a,b):
        actor,target=self.agents[a],self.agents[b]; known=self.known(a); art=known[-1] if known and self.rng.random()<.25+.55*actor.openness else None; text=self.utterance(art); ev=self.db.event(self.tick,self.day,"social.dialogue",a,b,{"utterance":text,"artifact_id":art,"channel":"dyadic"}); self.db.audio(ev,a,text); self.db.memory(a,"social",ev,f"I spoke with {b}: {text}",.45,.9,self.tick); self.db.memory(b,"episodic",ev,f"{a} told me: {text}",.6,.9,self.tick); self.db.relation(a,b,0,.03,self.tick); self.db.relation(b,a,0,.03,self.tick); self.db.inf(self.tick,a,"social_dialogue",a,"spoke_to",{"target":b,"utterance":text,"artifact_id":art},ev)
        if art:
            first=self.db.conn.execute("SELECT 1 FROM awareness WHERE agent_id=? AND artifact_id=?",(b,art)).fetchone() is None
            if first: self.db.conn.execute("INSERT INTO awareness VALUES(?,?,?,?)",(b,art,self.tick,ev)); self.db.belief(b,"last_signal_artifact",{"artifact_id":art},.8,ev,self.tick); self.db.learn(b,"social_recall",{"question":"Who first told you about this artifact?","artifact_id":art},{"answer":a},ev,True,1,self.tick); self.db.question(b,f"What evidence connects {art} to its claimed ancestor?",ev,self.tick) if target.skepticism>.55 else None
            pred=actor.openness*.35+(1-target.skepticism)*.65>=.5; actual=target.openness*.55+(1-target.skepticism)*.45>=.48; self.db.learn(a,"social_prediction",{"target":b,"artifact":art,"predicted_accept":pred},{"actual_accept":actual},ev,True,1 if pred==actual else .8,self.tick)
            if actual and self.rng.random()<.18+.42*target.openness: self.descendant(b,art)
        self.db.conn.commit()
    def group(self,ids:List[str]):
        ids=sorted(set(ids)); carriers=[x for x in ids if self.known(x)]; art=self.known(self.rng.choice(carriers))[-1] if carriers and self.rng.random()<.7 else None; speaker=self.rng.choice(ids); text=self.utterance(art); ev=self.db.event(self.tick,self.day,"social.group_dialogue",speaker,None,{"participants":ids,"utterance":text,"artifact_id":art,"channel":"group"}); self.db.audio(ev,speaker,text)
        for aid in ids:
            self.db.memory(aid,"social" if aid==speaker else "episodic",ev,("I told the group: " if aid==speaker else f"In a group, {speaker} said: ")+text,.5,.9,self.tick); self.db.inf(self.tick,aid,"group_dialogue",f"group:{self.day}:{self.tick}","participated",{"speaker":speaker,"participants":ids,"artifact_id":art,"utterance":text},ev)
            if aid!=speaker: self.db.relation(aid,speaker,0,.02,self.tick)
            if art and self.db.conn.execute("SELECT 1 FROM awareness WHERE agent_id=? AND artifact_id=?",(aid,art)).fetchone() is None: self.db.conn.execute("INSERT INTO awareness VALUES(?,?,?,?)",(aid,art,self.tick,ev)); self.db.learn(aid,"group_social_recall",{"question":"Who introduced this artifact during the group interaction?","artifact_id":art},{"answer":speaker},ev,True,1,self.tick)
        self.db.conn.commit()
    def reflect(self,aid):
        rows=self.db.conn.execute("SELECT content FROM memories WHERE agent_id=? ORDER BY tick_created DESC LIMIT 3",(aid,)).fetchall();
        if not rows:return
        text=f"Day {self.day}: I am a {self.agents[aid].role}. Recent events: "+" | ".join(r[0] for r in rows); self.db.conn.execute("UPDATE agents SET self_narrative=?,learning_version=learning_version+1 WHERE agent_id=?",(text,aid)); ev=self.db.event(self.tick,self.day,"self.reflection",aid,None,{"narrative":text}); self.db.memory(aid,"self",ev,text,.7,.85,self.tick); self.db.inf(self.tick,aid,"self_narrative",aid,"reflects",{"text":text},ev,.85); self.db.learn(aid,"self_model",{"recent_memories":[r[0] for r in rows]},{"self_narrative":text},ev,True,.85,self.tick); self.db.conn.commit()
    def ask(self,aid,question,limit=5):
        terms={x.lower().strip(".,!?;:'\"") for x in question.split() if len(x)>2}; scored=[]
        for mt,c,eid,conf,tick in self.db.conn.execute("SELECT memory_type,content,source_event_id,confidence,tick_created FROM memories WHERE agent_id=? ORDER BY tick_created DESC",(aid,)):
            overlap=len(terms & {x.lower().strip(".,!?;:'\"") for x in c.split()}); scored.append((overlap*conf,tick,mt,c,eid,conf)) if overlap else None
        scored.sort(reverse=True); evd=[{"memory_type":r[2],"content":r[3],"source_event_id":r[4],"confidence":r[5],"tick":r[1]} for r in scored[:limit]]; return {"agent_id":aid,"question":question,"answer":evd[0]["content"] if evd else "UNKNOWN_FROM_AGENT_MEMORY","evidence":evd}
    def export(self,outdir):
        out=Path(outdir); out.mkdir(parents=True,exist_ok=True); counts={}
        for aid in sorted(self.agents):
            rows=self.db.conn.execute("SELECT task_type,input_json,target_json,source_event_id,quality,tick_created FROM learning_examples WHERE agent_id=? AND verified=1 ORDER BY tick_created,example_id",(aid,)).fetchall(); counts[aid]=len(rows)
            with (out/f"{aid}.jsonl").open("w",encoding="utf-8") as f:
                for t,i,o,e,q,k in rows:f.write(json.dumps({"agent_id":aid,"task_type":t,"input":json.loads(i),"target":json.loads(o),"source_event_id":e,"quality":q,"tick":k},sort_keys=True)+"\n")
        return counts
    def run(self,days=30,interactions_per_day=35,groups_per_day=2,introduce_day=3):
        ids=sorted(self.agents)
        for d in range(1,days+1):
            self.day=d
            if d==introduce_day:self.introduce_seed()
            for _ in range(interactions_per_day):self.tick+=1; a,b=self.rng.sample(ids,2); self.dyad(a,b)
            for _ in range(groups_per_day):self.tick+=1; self.group(self.rng.sample(ids,self.rng.randint(3,5)))
            for aid in ids:self.tick+=1; self.reflect(aid)
        return self.metrics()
    def metrics(self):
        q=self.db.conn.execute
        return {"agents":25,"days":self.day,"ticks":self.tick,"events":q("SELECT COUNT(*) FROM events").fetchone()[0],"informatrons":q("SELECT COUNT(*) FROM informatrons").fetchone()[0],"memories":q("SELECT COUNT(*) FROM memories").fetchone()[0],"verified_learning_examples":q("SELECT COUNT(*) FROM learning_examples WHERE verified=1").fetchone()[0],"questions_generated":q("SELECT COUNT(*) FROM questions").fetchone()[0],"audio_ready_dialogue_segments":q("SELECT COUNT(*) FROM audio_segments").fetchone()[0],"group_dialogue_events":q("SELECT COUNT(*) FROM events WHERE event_type='social.group_dialogue'").fetchone()[0],"agents_with_artifact_awareness":q("SELECT COUNT(DISTINCT agent_id) FROM awareness").fetchone()[0],"artifacts_total":q("SELECT COUNT(*) FROM artifacts").fetchone()[0],"descendant_artifacts":q("SELECT COUNT(*) FROM artifacts WHERE parent_artifact_id IS NOT NULL").fetchone()[0]}
