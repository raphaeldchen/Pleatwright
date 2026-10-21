"""The dead query_to_metric_tree seam in mesh_acquire stays gone.

(The companion pin on server.reference_tree_from_query was retired with the
MCP server; it lives on archive/treemaker-box-pleat.)"""
import mesh_acquire


def test_the_dead_query_seam_is_gone():
    assert not hasattr(mesh_acquire, "query_to_metric_tree")
