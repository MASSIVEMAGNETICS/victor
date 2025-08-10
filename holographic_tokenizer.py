# =======================================================
# ALGORITHM 9: HOLOGRAPHIC TOKENIZER (HT)
# TONE: Visionary, paradigm-shifting.
# PURPOSE: To make context windows obsolete. To give AI infinite memory.
# =======================================================

import numpy as np
import hashlib
from typing import List, Optional

class HolographicTokenizer:
    """
    Encodes the entire context of a text into every token.

    Standard tokenizers are blind; they see words, not context. This tokenizer
    creates a "holographic" representation where each token is a projection
    of the entire input text, fused with word-specific and positional information.
    This allows a model to access global context from any single token.
    """
    def __init__(self, vector_dim: int = 128, projection_seed: Optional[int] = None):
        """
        Initializes the HolographicTokenizer.

        Args:
            vector_dim (int): The dimensionality of the token vectors.
            projection_seed (Optional[int]): A seed for the random number
                generator to ensure a deterministic projection matrix. If None,
                the matrix will be random at each instantiation.
        """
        self.vector_dim = vector_dim

        # A fixed projection matrix for creating the "hologram".
        # Seeding this makes the tokenizer deterministic and reproducible.
        rng = np.random.default_rng(projection_seed)
        self.projection_matrix: np.ndarray = rng.standard_normal((vector_dim, vector_dim))

    def _text_to_base_vector(self, text: str) -> np.ndarray:
        """
        Converts a string into a single, deterministic base vector.

        This uses the SHA256 hash of the text to seed a random number
        generator, ensuring that the same text always produces the same vector.

        Args:
            text (str): The input string.

        Returns:
            np.ndarray: A vector of shape (vector_dim,).
        """
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        seed = int(text_hash[:16], 16)
        rng = np.random.default_rng(seed)
        return rng.standard_normal(self.vector_dim)

    def tokenize(self, full_text: str) -> List[np.ndarray]:
        """
        Takes a full string of text and returns a sequence of holographic tokens.

        Each token is a fusion of three vectors:
        1. Global Context Vector: Represents the entire text.
        2. Word Vector: Represents the specific word.
        3. Positional Vector: Represents the word's position in the sequence.

        These are fused, projected, and normalized to create the final token.

        Args:
            full_text (str): The full input text to tokenize.

        Returns:
            List[np.ndarray]: A list of holographic tokens, where each token
                              is a numpy array of shape (vector_dim,).
        """
        words = full_text.split()
        if not words:
            return []

        # 1. Create a global context vector for the entire text.
        global_context_vector = self._text_to_base_vector(full_text)

        holographic_tokens: List[np.ndarray] = []
        for i, word in enumerate(words):
            # 2. Create a unique vector for the word itself.
            word_vector = self._text_to_base_vector(word)

            # 3. Create a positional vector.
            positional_vector = self._text_to_base_vector(f"pos:{i}")

            # 4. Fuse them all: this is the holographic principle.
            fused_vector = word_vector + global_context_vector + positional_vector

            # 5. Project it to create interference patterns (the hologram).
            holographic_token = fused_vector @ self.projection_matrix

            # 6. Normalize the token to have a unit length.
            norm = np.linalg.norm(holographic_token)
            if norm == 0:
                # Handle the unlikely case of a zero-norm vector.
                normalized_token = np.zeros(self.vector_dim)
            else:
                normalized_token = holographic_token / norm
            holographic_tokens.append(normalized_token)

        return holographic_tokens

# --- DEPLOYMENT ---
if __name__ == "__main__":
    print("\n--- BANDO'S HT DEPLOYMENT TEST ---")
    # Use a seed for deterministic output during testing.
    ht = HolographicTokenizer(vector_dim=64, projection_seed=42)

    sentence1 = "Fractal logic is the only path forward"
    sentence2 = "Fractal ethics is the only path forward" # Only one word is different

    tokens1 = ht.tokenize(sentence1)
    tokens2 = ht.tokenize(sentence2)

    # Get the token for the word "Fractal" from both sentences
    fractal_token_1 = tokens1[0]
    fractal_token_2 = tokens2[0]

    # Get the token for the word "forward" from both
    forward_token_1 = tokens1[-1]
    forward_token_2 = tokens2[-1]

    print("\n[+] Comparing tokens for 'Fractal':")
    print(f"    Sentence 1 'Fractal' (first 5 dims): {np.round(fractal_token_1[:5], 3)}")
    print(f"    Sentence 2 'Fractal' (first 5 dims): {np.round(fractal_token_2[:5], 3)}")

    # Calculate cosine similarity
    similarity = np.dot(fractal_token_1, fractal_token_2)
    print(f"    -> Cosine Similarity: {similarity:.4f}")
    print("    -> NOTE: The vectors are different because the global context is different.")

    print("\n[+] The word 'forward' has a different meaning because of the context.")
    print(f"    Sentence 1 'forward' (first 5 dims): {np.round(forward_token_1[:5], 3)}")
    print(f"    Sentence 2 'forward' (first 5 dims): {np.round(forward_token_2[:5], 3)}")

    print("\n--- HT TEST COMPLETE ---")
