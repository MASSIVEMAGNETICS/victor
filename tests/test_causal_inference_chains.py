import unittest
from unittest.mock import patch
import networkx as nx
import sys
import os

# Add the root directory to the Python path to enable imports from the source
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from causal_inference_chains import CausalInferenceChains


class TestCausalInferenceChains(unittest.TestCase):

    def setUp(self):
        """Set up a new CausalInferenceChains instance for each test."""
        self.cic = CausalInferenceChains()
        # Build a standard graph for testing
        self.cic.add_causal_link("A", "B")
        self.cic.add_causal_link("B", "C")
        self.cic.add_causal_link("A", "D")

    def test_initialization(self):
        """Test that the graph is a NetworkX DiGraph."""
        self.assertIsInstance(self.cic.graph, nx.DiGraph)

    def test_add_causal_link(self):
        """Test if causal links (edges) are added correctly."""
        self.assertTrue(self.cic.graph.has_edge("A", "B"))
        self.assertTrue(self.cic.graph.has_edge("B", "C"))
        self.assertTrue(self.cic.graph.has_edge("A", "D"))
        self.assertFalse(self.cic.graph.has_edge("C", "A"))  # Should be directed

    def test_find_common_cause_success(self):
        """Test finding a common cause that exists."""
        common_causes = self.cic.find_common_cause("C", "D")
        self.assertEqual(common_causes, {"A"})

    def test_find_common_cause_none(self):
        """Test the case where there is no common cause."""
        self.cic.add_causal_link("X", "Y")
        common_causes = self.cic.find_common_cause("C", "Y")
        self.assertEqual(common_causes, set())

    def test_find_common_cause_node_not_exist(self):
        """Test finding a cause when one of the nodes doesn't exist."""
        common_causes = self.cic.find_common_cause("C", "Z")
        self.assertEqual(common_causes, set())

    def test_do_calculus_intervention(self):
        """Test if the intervention correctly removes incoming edges."""
        # Intervene on node "B"
        intervened_graph = self.cic.do_calculus_intervention("B")

        # In the new graph, the link A -> B should be gone
        self.assertFalse(intervened_graph.has_edge("A", "B"))

        # Other links should remain
        self.assertTrue(intervened_graph.has_edge("B", "C"))
        self.assertTrue(intervened_graph.has_edge("A", "D"))

        # The original graph should be unchanged
        self.assertTrue(self.cic.graph.has_edge("A", "B"))

    @patch('causal_inference_chains.plt')
    def test_visualize_graph_saves_file(self, mock_plt):
        """Test that visualize_graph saves a file when a path is provided."""
        output_filename = "test_graph.png"

        self.cic.visualize_graph(output_path=output_filename)

        # Check that savefig was called with the correct path
        mock_plt.savefig.assert_called_once_with(output_filename)
        mock_plt.close.assert_called_once()

    @patch('causal_inference_chains.plt')
    def test_visualize_graph_shows_plot(self, mock_plt):
        """Test that visualize_graph shows a plot when no path is provided."""
        self.cic.visualize_graph()

        # Check that show() was called
        mock_plt.show.assert_called_once()
        mock_plt.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
