import unittest
import torch
import os
import shutil
from victor_omnibrain.dataset_generator import DatasetGenerator
from victor_omnibrain.dataset_loader import DatasetLoader
from victor_omnibrain.fpkt_block_v0_1 import FPKTBlock
from victor_omnibrain.holographic_memory_shard import HolographicMemoryShard
from victor_omnibrain.victor_envelope import VictorEnvelope

class TestVictorSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a small dataset for testing
        cls.test_dir = "TEST_AI_Forge"
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

        # Override data dir for testing to avoid conflict
        generator = DatasetGenerator(target_size_mb=1)
        generator.data_dir = cls.test_dir
        generator.target_size = 1024 * 1024 # 1MB
        cls.dataset_path = generator.generate_dataset()

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_dir):
            shutil.rmtree(cls.test_dir)

    def test_dataset_generation(self):
        self.assertTrue(os.path.exists(self.dataset_path))
        self.assertTrue(os.path.getsize(self.dataset_path) > 0)

    def test_dataset_loader(self):
        loader = DatasetLoader(self.dataset_path)
        count = loader.get_sample_count()
        self.assertGreater(count, 0)

        sample = loader.load_sample(0)
        self.assertIn('text', sample)
        self.assertIn('image', sample)
        self.assertIn('reasoning', sample)
        self.assertIn('entropy', sample)
        self.assertIsInstance(sample['image'], torch.Tensor)

    def test_fpkt_multimodal(self):
        # Setup FPKT
        block = FPKTBlock(dim=512, num_experts=100, num_local_experts=10)

        # Create fake input
        # B=1, S=1
        input_data = {
            'text': torch.randn(1, 1, 512),
            'image': torch.randn(1, 1, 3, 64, 64),
            'reasoning': torch.randn(1, 1, 128)
        }

        modality_weights = {'text': 1.0, 'image': 1.0, 'reasoning': 1.0}

        out, stats = block(input_data, modality_weights)
        self.assertEqual(out.shape, (1, 1, 512))
        self.assertIn('router_entropy', stats)

    def test_memory_ingest(self):
        memory = HolographicMemoryShard()
        loader = DatasetLoader(self.dataset_path)
        sample = loader.load_sample(0)

        hash_val = memory.ingest_dataset_sample(sample)
        self.assertIsNotNone(hash_val)
        self.assertEqual(len(memory.shards), 1)
        self.assertEqual(memory.shards[0].purpose, "training_data")

if __name__ == '__main__':
    unittest.main()
