import tempfile, unittest
from pathlib import Path
from signal_society import SignalSociety25
class T(unittest.TestCase):
    def make(self):
        td=tempfile.TemporaryDirectory(); s=SignalSociety25(Path(td.name)/'x.db',25); return td,s
    def test_agents_schedules(self):
        td,s=self.make(); self.assertEqual(len(s.agents),25); self.assertEqual(s.db.conn.execute('SELECT COUNT(*) FROM schedules').fetchone()[0],125); s.db.close(); td.cleanup()
    def test_seed_learning(self):
        td,s=self.make(); s.introduce_seed(); self.assertGreater(s.db.conn.execute("SELECT COUNT(*) FROM learning_examples WHERE verified=1").fetchone()[0],0); s.db.close(); td.cleanup()
    def test_audio_group_query(self):
        td,s=self.make(); s.tick=1;s.day=1;s.group(['A01','A02','A03']); self.assertEqual(s.db.conn.execute("SELECT COUNT(*) FROM audio_segments").fetchone()[0],1); self.assertEqual(s.ask('A02','What happened in the group?')['agent_id'],'A02'); s.db.close(); td.cleanup()
    def test_deterministic(self):
        t1,s1=self.make(); t2,s2=self.make(); r1=s1.run(4,8,1,1); r2=s2.run(4,8,1,1); self.assertEqual(r1,r2); s1.db.close();s2.db.close();t1.cleanup();t2.cleanup()
    def test_export(self):
        td,s=self.make(); s.run(2,4,1,1); out=Path(td.name)/'training'; c=s.export(out); self.assertEqual(len(c),25); self.assertTrue((out/'A14.jsonl').exists()); s.db.close();td.cleanup()
if __name__=='__main__':unittest.main()
