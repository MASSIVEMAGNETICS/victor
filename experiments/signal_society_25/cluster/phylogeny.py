from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

def phylogeny_metrics(sim) -> dict[str, Any]:
    rows=sim.db.conn.execute(
        "SELECT artifact_id,parent_artifact_id,canonical FROM artifacts ORDER BY tick_created,artifact_id"
    ).fetchall()
    children=defaultdict(list)
    roots=[]
    canonical=0; noncanonical=0
    for aid,parent,canon in rows:
        if parent:
            children[parent].append(aid)
            if canon: canonical+=1
            else: noncanonical+=1
        else:
            roots.append(aid)
    depth={}
    queue=deque((r,0) for r in roots)
    while queue:
        node,d=queue.popleft()
        depth[node]=max(depth.get(node,-1),d)
        for child in children.get(node,()):
            queue.append((child,d+1))
    descendant_nodes=[aid for aid,parent,_ in rows if parent]
    leaves=[aid for aid in descendant_nodes if not children.get(aid)]
    branch_nodes=[aid for aid,kids in children.items() if len(kids)>1]
    total_desc=canonical+noncanonical
    return {
        "artifact_count":len(rows),
        "root_count":len(roots),
        "descendant_count":len(descendant_nodes),
        "max_lineage_depth":max(depth.values(),default=0),
        "branch_nodes":len(branch_nodes),
        "leaf_descendants":len(leaves),
        "canonical_descendants":canonical,
        "noncanonical_descendants":noncanonical,
        "canon_ratio":(canonical/total_desc) if total_desc else None,
        "terminal_branch_count":len(leaves),
    }
