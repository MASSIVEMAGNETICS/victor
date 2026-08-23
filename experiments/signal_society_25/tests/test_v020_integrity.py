import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from signal_society import SignalSociety25


class SignalSocietyV020Integrity(unittest.TestCase):
    def make(self,mode="signal"):
        td=tempfile.TemporaryDirectory(); sim=SignalSociety25(Path(td.name)/"x.db",25,mode); return td,sim

    def test_append_only_chain(self):
        td,sim=self.make(); sim.introduce_seed(); self.assertTrue(sim.db.verify_chronos())
        with self.assertRaises(sqlite3.DatabaseError): sim.db.conn.execute("UPDATE events SET event_type='tampered' WHERE sequence=1")
        sim.db.conn.rollback(); self.assertTrue(sim.db.verify_chronos()); sim.db.close(); td.cleanup()

    def test_group_artifact_speaker_is_carrier(self):
        td,sim=self.make(); sim.tick=1; sim.day=1; sim.introduce_seed("A14"); sim.tick=2; sim.group(["A01","A02","A14"])
        actor,payload_json=sim.db.conn.execute("SELECT actor_id,payload_json FROM events WHERE event_type='social.group_dialogue' ORDER BY sequence DESC LIMIT 1").fetchone(); payload=json.loads(payload_json)
        if payload["artifact_id"]: self.assertIn(payload["artifact_id"],sim.known(actor))
        sim.db.close(); td.cleanup()

    def test_experience_adapts(self):
        td,sim=self.make(); before=sim.learn.state("A01"); sim.learn.record_experience("A01",1,prediction_correct=False,surprise=1.0); after=sim.learn.state("A01")
        self.assertGreater(after.experience_count,before.experience_count); self.assertGreater(after.question_bias,before.question_bias); sim.db.close(); td.cleanup()

    def test_no_seed_control(self):
        td,sim=self.make("none"); result=sim.run(3,5,1,1); self.assertEqual(result["artifacts_total"],0); self.assertEqual(result["agents_with_artifact_awareness"],0); self.assertTrue(result["chronos_valid"]); sim.db.close(); td.cleanup()

    def test_deterministic_v020(self):
        t1,s1=self.make(); t2,s2=self.make(); r1=s1.run(3,5,1,1); r2=s2.run(3,5,1,1); self.assertEqual(r1,r2); s1.db.close(); s2.db.close(); t1.cleanup(); t2.cleanup()


if __name__=="__main__": unittest.main()
