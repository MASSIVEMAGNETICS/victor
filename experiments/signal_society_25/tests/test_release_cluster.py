import tempfile
import unittest
from pathlib import Path

from signal_society import SignalSociety25
from cluster.model_swap import cold_swap_check
from cluster.rd_cluster import RecursiveRDCluster
from cluster.release_train import RELEASES, manifest
from cluster.runner import run_cluster
from cluster.sentinel import VictorOmniSentinel

class ReleaseClusterTests(unittest.TestCase):
    def test_seven_release_manifest(self):
        self.assertEqual([x.version for x in RELEASES],["0.4.0","0.5.0","0.6.0","0.7.0","0.8.0","0.9.0","1.0.0"])
        self.assertEqual(manifest()["package_version"],"1.0.0")

    def test_recursive_rd_controls_and_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            rd=RecursiveRDCluster(Path(td)/"rd",25)
            result=rd.run(cycles=1,days=2,interactions_per_day=4)
            self.assertTrue(result["history_valid"])
            arms=result["cycle_reports"][0]["results"]
            self.assertEqual(set(arms),{"signal","neutral","no_seed"})

    def test_sentinel_and_swap(self):
        with tempfile.TemporaryDirectory() as td:
            sim=SignalSociety25(Path(td)/"x.db",25,"signal")
            try:
                sim.run(days=3,interactions_per_day=5,groups_per_day=1)
                sim.learn.bootstrap(sorted(sim.agents),sim.tick,sim.day)
                report=VictorOmniSentinel(sim).scan()
                self.assertFalse(report["hard_failures"],report)
                self.assertIn(report["status"],{"GREEN","AMBER"})
                swap=cold_swap_check(sim)
                self.assertTrue(swap["decision_equivalence"])
                self.assertEqual(swap["zero_context_boundary"],"canonical_state_only")
            finally:
                sim.db.close()

    def test_cluster_package_deployable(self):
        with tempfile.TemporaryDirectory() as td:
            result=run_cluster(Path(td)/"deploy",seed=25,days=2,interactions_per_day=4,cycles=1,fresh=True)
            self.assertTrue(result["release_receipt_chain_valid"])
            self.assertTrue(result["release_results"]["0.4.0"]["passed"])
            self.assertTrue(result["release_results"]["0.5.0"]["passed"])
            self.assertTrue(result["release_results"]["0.7.0"]["passed"])
            self.assertTrue(result["release_results"]["0.9.0"]["passed"])
            self.assertTrue(result["deployable"])
            self.assertTrue((Path(td)/"deploy"/"deployment_manifest.json").exists())

if __name__=="__main__":
    unittest.main()
