import json
import tempfile
import unittest
from pathlib import Path

from signal_society import SignalSociety25
from signal_society.experience_transition import REQUIRED_FIELDS


class SignalSocietyV031ExperienceTransition(unittest.TestCase):
    def test_adaptation_serializes_canonical_contract(self):
        with tempfile.TemporaryDirectory() as td:
            s=SignalSociety25(Path(td)/"x.db",25,"none")
            ev=s.db.event(1,1,"test.observation",None,"A01",{"value":1})
            s.learn.record_experience("A01",1,day=1,prediction_correct=False,surprise=1.0,source_event_id=ev)
            payload=json.loads(s.db.conn.execute(
                "SELECT payload_json FROM learning_history WHERE agent_id='A01' ORDER BY sequence DESC LIMIT 1"
            ).fetchone()[0])
            self.assertEqual(set(REQUIRED_FIELDS),set(payload.keys()))
            self.assertTrue(payload["transition_id"].startswith("ET-"))
            self.assertEqual(payload["verification"]["status"],"verified")
            self.assertEqual(payload["verification"]["evidence_refs"],[ev])
            self.assertTrue(s.db.verify_learning_history())
            self.assertTrue(s.learn.replay_matches_materialized("A01"))
            self.assertTrue(s.learn.canonical_history_valid("A01"))
            s.db.close()

    def test_transitions_form_per_agent_parent_chain(self):
        with tempfile.TemporaryDirectory() as td:
            s=SignalSociety25(Path(td)/"x.db",25,"none")
            ev1=s.db.event(1,1,"test.one",None,"A01",{})
            s.learn.record_experience("A01",1,day=1,prediction_correct=False,surprise=.8,source_event_id=ev1)
            ev2=s.db.event(2,1,"test.two",None,"A01",{})
            s.learn.record_experience("A01",2,day=1,prediction_correct=True,surprise=.1,source_event_id=ev2)
            rows=[json.loads(r[0]) for r in s.db.conn.execute(
                "SELECT payload_json FROM learning_history WHERE agent_id='A01' ORDER BY sequence"
            )]
            self.assertEqual(rows[1]["parent_transition_ref"],rows[0]["transition_id"])
            self.assertTrue(s.learn.canonical_history_valid("A01"))
            s.db.close()

    def test_missing_source_event_is_inconclusive_not_verified(self):
        with tempfile.TemporaryDirectory() as td:
            s=SignalSociety25(Path(td)/"x.db",25,"none")
            s.learn.record_experience("A01",1,day=1,prediction_correct=None,surprise=.2)
            payload=json.loads(s.db.conn.execute(
                "SELECT payload_json FROM learning_history WHERE agent_id='A01' ORDER BY sequence DESC LIMIT 1"
            ).fetchone()[0])
            self.assertEqual(payload["verification"]["status"],"inconclusive")
            self.assertEqual(payload["verification"]["evidence_refs"],[])
            self.assertTrue(s.learn.canonical_history_valid("A01"))
            s.db.close()


if __name__=="__main__": unittest.main()
