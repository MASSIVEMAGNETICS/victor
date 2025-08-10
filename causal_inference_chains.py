# =======================================================
# ALGORITHM 10: CAUSAL INFERENCE CHAINS (CIC)
# TONE: Grounded in reality, ruthlessly logical.
# PURPOSE: To distinguish correlation from causation. To understand *why*.
# =======================================================

import networkx as nx
import matplotlib.pyplot as plt
from typing import Any, Set, Optional

class CausalInferenceChains:
    """
    Builds and analyzes a causal graph to distinguish causation from correlation.

    This class uses a directed acyclic graph (DAG) to represent causal
    relationships between variables. It allows for identifying common causes
    of observed effects and simulating interventions using Pearl's do-calculus.
    """

    def __init__(self):
        """Initializes the CausalInferenceChains with an empty graph."""
        self.graph: nx.DiGraph = nx.DiGraph()

    def add_causal_link(self, cause: Any, effect: Any):
        """
        Defines a direct causal relationship from a cause to an effect.

        Args:
            cause (Any): The node representing the cause.
            effect (Any): The node representing the effect.
        """
        self.graph.add_edge(cause, effect)

    def find_common_cause(self, effect1: Any, effect2: Any) -> Set[Any]:
        """
        Finds common ancestors (causes) between two effects in the causal graph.

        This method is useful for identifying potential confounding variables that
        might explain a correlation between two observed effects.

        Args:
            effect1 (Any): The first observed effect node.
            effect2 (Any): The second observed effect node.

        Returns:
            Set[Any]: A set of nodes that are common ancestors to both effects.
                      Returns an empty set if no common cause is found or if
                      one of the nodes does not exist in the graph.
        """
        try:
            ancestors1 = nx.ancestors(self.graph, effect1)
            ancestors2 = nx.ancestors(self.graph, effect2)
            return ancestors1.intersection(ancestors2)
        except nx.NetworkXError:
            # This occurs if effect1 or effect2 is not in the graph.
            return set()

    def do_calculus_intervention(self, node_to_intervene: Any) -> nx.DiGraph:
        """
        Simulates a causal intervention using Pearl's do-calculus.

        This operation creates a new graph where all causal links pointing into
        the `node_to_intervene` are severed. This simulates a scenario where the
        node's value is forced, independent of its usual causes.

        Args:
            node_to_intervene (Any): The node on which to perform the intervention.

        Returns:
            nx.DiGraph: A new graph representing the state of the world after
                        the intervention. The original graph is not modified.
        """
        intervened_graph = self.graph.copy()

        # Get all parent nodes (causes) of the intervened node.
        incoming_edges = list(intervened_graph.in_edges(node_to_intervene))

        # Remove the natural causes.
        intervened_graph.remove_edges_from(incoming_edges)

        return intervened_graph

    def visualize_graph(self, output_path: Optional[str] = None):
        """
        Draws the causal graph and either shows it or saves it to a file.

        Args:
            output_path (Optional[str]): The file path to save the visualization.
                If None, the plot is displayed directly using plt.show().
        """
        plt.figure(figsize=(10, 7))
        pos = nx.spring_layout(self.graph, seed=42)
        nx.draw(self.graph, pos, with_labels=True, node_size=2500, node_color="skyblue",
                font_size=10, font_weight="bold", arrowsize=20)
        plt.title("Causal Inference Graph")

        if output_path:
            plt.savefig(output_path)
            print(f"[CIC] Graph visualization saved to {output_path}")
        else:
            plt.show()
        plt.close()


# --- DEPLOYMENT ---
if __name__ == "__main__":
    print("\n--- BANDO'S CIC DEPLOYMENT TEST ---")
    cic = CausalInferenceChains()

    # --- Build a simple causal model of summer activities ---
    print("\n[CIC] Building Causal Graph...")
    cic.add_causal_link("Summer Season", "More Sunlight")
    cic.add_causal_link("More Sunlight", "People Go to Beach")
    cic.add_causal_link("Summer Season", "Higher Temperature")
    cic.add_causal_link("Higher Temperature", "Ice Cream Sales Increase")
    cic.add_causal_link("People Go to Beach", "Shark Attacks Increase")
    cic.add_causal_link("Higher Temperature", "People Go to Beach")

    # --- Scenario 1: Correlation vs Causation ---
    print("\n[CIC] Scenario 1: Correlation vs Causation")
    effect_A = "Ice Cream Sales Increase"
    effect_B = "Shark Attacks Increase"
    common_causes = cic.find_common_cause(effect_A, effect_B)
    print(f"    -> Query: Does '{effect_A}' cause '{effect_B}'?")
    print(f"    -> Analysis: No direct path. Common Causes found: {common_causes}")

    # --- Scenario 2: Intervention ---
    print("\n[CIC] Scenario 2: Intervention")
    # What if we artificially boost ice cream sales in the winter?
    # A dumb model would predict more shark attacks. A causal model knows better.
    intervened_reality = cic.do_calculus_intervention("Ice Cream Sales Increase")

    # In the new reality, does the boost affect shark attacks?
    has_path = nx.has_path(intervened_reality, "Ice Cream Sales Increase", "Shark Attacks Increase")
    print(f"    -> In the intervened reality, is there a causal path from ice cream to shark attacks? {'Yes' if has_path else 'No'}")

    print("\n[CIC] Visualizing the map of reality...")
    # Save the graph to a file instead of showing it directly
    cic.visualize_graph("causal_graph.png")

    print("\n--- CIC TEST COMPLETE ---")
