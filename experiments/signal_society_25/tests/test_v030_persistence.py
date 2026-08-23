import sqlite3, tempfile, unittest
from pathlib import Path
from signal_society import SignalSociety25

class SignalSocietyV030Persistence(unittest.TestCase):
    def test_resume_is_append_not_reset(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.db"
            s=SignalSociety25(p,25,"signal"); r1=s.run(2,4,1,1); h1=s.db.chronos_head(); e1=r1["events"]; d1=s.day; t1=s.tick; s.db.close()
            s2=SignalSociety25(p,25,None)
            self.assertEqual((s2.day,s2.tick),(d1,t1))
            r2=s2.run(1,2,0,1)
            self.assertEqual(r2["days"],d1+1); self.assertGreater(r2["events"],e1); self.assertNotEqual(s2.db.chronos_head(),h1); self.assertTrue(r2["chronos_valid"]); s2.db.close()

    def test_learning_history_is_append_only_and_replayable(self):
        with tempfile.TemporaryDirectory() as td:
            s=SignalSociety25(Path(td)/"x.db",25)
            s.learn.record_experience("A01",1,day=1,prediction_correct=False,surprise=1.0)
            self.assertTrue(s.db.verify_learning_history()); self.assertTrue(s.learn.replay_matches_materialized("A01"))
            with self.assertRaises(sqlite3.DatabaseError):
                s.db.conn.execute("DELETE FROM learning_history WHERE sequence=1")
            s.db.conn.rollback(); self.assertTrue(s.db.verify_learning_history()); s.db.close()

    def test_versioned_experience_snapshots(self):
        with tempfile.TemporaryDirectory() as td:
            s=SignalSociety25(Path(td)/"x.db",25); s.run(2,3,0,1)
            a=s.bootstrap_experience(); b=s.bootstrap_experience()
            self.assertEqual(a["A01"]["version"],1); self.assertEqual(b["A01"]["version"],2)
            self.assertTrue(s.db.verify_experience_snapshots()); self.assertEqual(s.db.conn.execute("SELECT learning_version FROM agents WHERE agent_id='A01'").fetchone()[0],2); s.db.close()

    def test_copilot_uses_agent_evidence_and_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            s=SignalSociety25(Path(td)/"x.db",25); s.day=3; s.introduce_seed("A14")
            out=s.copilot("A14","What phrase did I find?","ART-SEED-001")
            self.assertEqual(out["help"]["agent_id"],"A14")
            self.assertTrue(out["help"]["evidence"])
            self.assertEqual(out["co_create"]["status"],"READY")
            self.assertEqual(out["co_create"]["parent_artifact_id"],"ART-SEED-001")
            s.db.close()

    def test_version_history_appends_030(self):
        with tempfile.TemporaryDirectory() as td:
            s=SignalSociety25(Path(td)/"x.db",25)
            versions=[r[0] for r in s.db.conn.execute("SELECT version FROM version_history ORDER BY version_seq")]
            self.assertIn("0.3.0",versions); s.db.close()

if __name__=="__main__": unittest.main()
