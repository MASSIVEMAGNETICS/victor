import unittest
import numpy as np
import sys
import os

# Add the root directory to the Python path to enable imports from the source
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from holographic_tokenizer import HolographicTokenizer


class TestHolographicTokenizer(unittest.TestCase):

    def test_initialization(self):
        """Test if the tokenizer initializes correctly."""
        tokenizer = HolographicTokenizer(vector_dim=128, projection_seed=42)
        self.assertEqual(tokenizer.vector_dim, 128)
        self.assertEqual(tokenizer.projection_matrix.shape, (128, 128))

    def test_empty_input(self):
        """Test if the tokenizer returns an empty list for empty text."""
        tokenizer = HolographicTokenizer(vector_dim=64, projection_seed=42)
        tokens = tokenizer.tokenize("")
        self.assertEqual(tokens, [])

    def test_tokenization_output(self):
        """Test the output of the tokenization process."""
        tokenizer = HolographicTokenizer(vector_dim=32, projection_seed=42)
        text = "hello world"
        tokens = tokenizer.tokenize(text)
        self.assertEqual(len(tokens), 2)
        self.assertEqual(tokens[0].shape, (32,))
        # Check if tokens are normalized
        self.assertAlmostEqual(np.linalg.norm(tokens[0]), 1.0, places=5)

    def test_determinism(self):
        """Test tokenizer produces same tokens for same input and seed."""
        # Using the same seed should produce the same projection matrix and
        # thus the same tokens.
        tokenizer1 = HolographicTokenizer(vector_dim=64, projection_seed=1337)
        tokenizer2 = HolographicTokenizer(vector_dim=64, projection_seed=1337)

        text = "the same input text"
        tokens1 = tokenizer1.tokenize(text)
        tokens2 = tokenizer2.tokenize(text)

        self.assertTrue(np.allclose(tokens1, tokens2, atol=1e-6),
                        "Tokens should be identical for the same seed.")

    def test_holographic_principle(self):
        """Test that a word's token is different in different contexts."""
        tokenizer = HolographicTokenizer(vector_dim=64, projection_seed=42)

        sentence1 = "run the code"
        sentence2 = "a long run"

        tokens1 = tokenizer.tokenize(sentence1)
        tokens2 = tokenizer.tokenize(sentence2)

        # The token for "run" should be different in each sentence
        run_token_1 = tokens1[0]
        run_token_2 = tokens2[2]

        # Calculate cosine similarity. Should not be close to 1.
        similarity = np.dot(run_token_1, run_token_2)
        self.assertLess(similarity, 0.99,
                        "Tokens for the same word in different contexts "
                        "should not be highly similar.")

    def test_unseeded_behavior(self):
        """Test that different instances without a seed produce different tokens."""
        # Without a seed, the projection matrix should be different each time.
        tokenizer1 = HolographicTokenizer(vector_dim=64)  # No seed
        tokenizer2 = HolographicTokenizer(vector_dim=64)  # No seed

        text = "the same input text"
        tokens1 = tokenizer1.tokenize(text)
        tokens2 = tokenizer2.tokenize(text)

        # It's astronomically unlikely for them to be the same.
        self.assertFalse(np.allclose(tokens1, tokens2, atol=1e-6),
                         "Tokens should be different for unseeded tokenizers.")


if __name__ == '__main__':
    unittest.main()
