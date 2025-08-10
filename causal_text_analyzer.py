import re
from typing import List

from holographic_tokenizer import HolographicTokenizer
from causal_inference_chains import CausalInferenceChains

class CausalTextAnalyzer:
    """
    Analyzes text to automatically build a causal graph.

    This class uses a simple keyword-based approach to identify causal
    relationships in text and adds them to a CausalInferenceChains instance.
    This is a proof-of-concept for integrating holographic language
    understanding with causal reasoning.
    """

    # Simple keywords that indicate a causal link.
    # In a real system, this would be far more sophisticated.
    CAUSAL_KEYWORDS = ['caused', 'led to', 'resulted in', 'made', 'triggered']

    def __init__(self, cic: CausalInferenceChains):
        """
        Initializes the CausalTextAnalyzer.

        Args:
            cic (CausalInferenceChains): An instance of CausalInferenceChains
                where the discovered causal links will be stored.
        """
        self.cic = cic

    def analyze_text(self, text: str):
        """
        Parses text to find and add causal links to the graph.

        This implementation uses a regex to find simple sentences of the
        form "[Cause Phrase] [causal keyword] [Effect Phrase]".

        Args:
            text (str): The input text to analyze.
        """
        # Create a regex pattern to find causal links.
        # It looks for: (anything) (keyword) (anything)
        pattern = re.compile(
            r"(.+?)\s+(" + "|".join(self.CAUSAL_KEYWORDS) + r")\s+(.+)",
            re.IGNORECASE
        )

        # Split text into sentences for simpler analysis.
        sentences = re.split(r'[.!?]', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            match = pattern.match(sentence)
            if match:
                # Extract cause and effect phrases.
                cause_phrase = match.group(1).strip()
                effect_phrase = match.group(3).strip()

                # For this simple version, we'll normalize the phrases a bit.
                cause = self._normalize_phrase(cause_phrase)
                effect = self._normalize_phrase(effect_phrase)

                print(f"[Analyzer] Found link: '{cause}' -> '{effect}'")
                self.cic.add_causal_link(cause, effect)

    def _normalize_phrase(self, phrase: str) -> str:
        """A simple method to clean up extracted phrases."""
        # Lowercase, remove leading/trailing whitespace.
        return phrase.lower().strip()

# --- DEPLOYMENT ---
if __name__ == '__main__':
    print("\n--- BANDO'S CAUSAL TEXT ANALYZER DEPLOYMENT TEST ---")

    cic_instance = CausalInferenceChains()
    analyzer = CausalTextAnalyzer(cic=cic_instance)

    text_to_analyze = (
        "The heavy rainfall caused widespread flooding. "
        "The widespread flooding led to road closures. "
        "The road closures resulted in major traffic delays. "
        "This event made the city declare a state of emergency."
    )

    print(f"\n[+] Analyzing text: '{text_to_analyze}'")
    analyzer.analyze_text(text_to_analyze)

    print("\n[+] Resulting Causal Graph:")
    # The visualization will be saved to a file.
    cic_instance.visualize_graph("text_causal_graph.png")

    # Verify a path exists
    path_exists = nx.has_path(
        cic_instance.graph,
        "the heavy rainfall",
        "major traffic delays"
    )
    print(f"\n[+] Verification: Is there a causal path from 'the heavy rainfall' to 'major traffic delays'? {'Yes' if path_exists else 'No'}")

    print("\n--- ANALYZER TEST COMPLETE ---")
