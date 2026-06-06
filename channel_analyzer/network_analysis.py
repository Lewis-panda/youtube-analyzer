from __future__ import annotations

import math
import warnings

import networkx as nx
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from .config import AnalyzerConfig


RANDOM_SEED = 42


def build_network_outputs(
    comments: pd.DataFrame,
    config: AnalyzerConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    actor_video = comments[["author_actor_id", "video_id"]].drop_duplicates()
    counts = actor_video.groupby("author_actor_id")["video_id"].nunique()
    keep_actors = counts[counts >= config.analysis.min_actor_videos].index
    actor_video = actor_video[actor_video["author_actor_id"].isin(keep_actors)]
    if actor_video.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, empty, empty

    actors = sorted(actor_video["author_actor_id"].unique())
    videos = sorted(actor_video["video_id"].unique())
    actor_idx = {actor: i for i, actor in enumerate(actors)}
    video_idx = {video: i for i, video in enumerate(videos)}
    rows = actor_video["author_actor_id"].map(actor_idx).to_numpy()
    cols = actor_video["video_id"].map(video_idx).to_numpy()
    matrix = csr_matrix(
        (np.ones(len(actor_video), dtype=np.float32), (rows, cols)),
        shape=(len(actors), len(videos)),
    )
    co = (matrix @ matrix.T).tocsr()
    co.setdiag(0)
    co = co.multiply(co >= config.analysis.min_co_videos)
    co.eliminate_zeros()
    graph = nx.from_scipy_sparse_array(co, edge_attribute="weight")
    graph = nx.relabel_nodes(graph, {i: actor for i, actor in enumerate(actors)})
    graph.remove_nodes_from(list(nx.isolates(graph)))
    if graph.number_of_nodes() == 0:
        empty = pd.DataFrame()
        return empty, empty, empty, empty, empty

    partition, modularity, method = detect_communities(
        graph, config.analysis.community_algorithm
    )
    core_numbers = safe_core_numbers(graph)
    betweenness = approximate_betweenness(
        graph, config.analysis.betweenness_sample_size
    )
    node_metrics = build_node_metrics(
        graph,
        partition,
        core_numbers,
        betweenness,
        node_col="author_actor_id",
        community_col="community",
    )
    actor_communities = pd.DataFrame(
        [
            {"author_actor_id": actor, "community": comm}
            for actor, comm in partition.items()
        ]
    )
    community_summary = summarize_communities(
        graph, partition, core_numbers, community_col="community"
    )
    bridge_actors = rank_bridge_actors(node_metrics, config.analysis.top_bridge_actors)
    network_actor_metrics = top_network_nodes(
        node_metrics, config.analysis.top_network_actors
    )
    network_summary = summarize_graph(
        graph,
        partition,
        core_numbers,
        community_summary,
        modularity=modularity,
        method=method,
        n_communities_col="n_communities",
        extra={
            "min_actor_videos": config.analysis.min_actor_videos,
            "min_co_videos": config.analysis.min_co_videos,
            "betweenness_sample_size": min(
                max(0, config.analysis.betweenness_sample_size),
                graph.number_of_nodes(),
            ),
            "top_network_actors": config.analysis.top_network_actors,
        },
    )
    return (
        network_summary,
        community_summary,
        bridge_actors,
        actor_communities,
        network_actor_metrics,
    )


def detect_communities(
    graph: nx.Graph,
    requested_algorithm: str = "auto",
) -> tuple[dict[str, int], float, str]:
    requested = (requested_algorithm or "auto").strip().lower().replace("_", "-")
    if requested not in {
        "auto",
        "leiden",
        "infomap",
        "louvain",
        "python-louvain",
        "networkx-louvain",
        "greedy",
    }:
        warnings.warn(f"Unknown community_algorithm={requested_algorithm}; using auto")
        requested = "auto"

    if requested in {"auto", "leiden"}:
        result = _detect_leiden(graph)
        if result is not None:
            return result
        if requested == "leiden":
            warnings.warn("Leiden unavailable or failed; falling back to Louvain")

    if requested == "infomap":
        result = _detect_infomap(graph)
        if result is not None:
            return result
        warnings.warn("Infomap unavailable or failed; falling back to Louvain")

    if requested in {"auto", "louvain", "python-louvain", "leiden", "infomap"}:
        result = _detect_python_louvain(graph)
        if result is not None:
            return result

    if requested in {
        "auto",
        "louvain",
        "networkx-louvain",
        "python-louvain",
        "leiden",
        "infomap",
    }:
        result = _detect_networkx_louvain(graph)
        if result is not None:
            return result

    return _detect_greedy_or_components(graph)


def _detect_leiden(graph: nx.Graph) -> tuple[dict[str, int], float, str] | None:
    try:
        import igraph as ig  # type: ignore
        import leidenalg  # type: ignore
    except Exception:
        return None

    try:
        nodes = list(graph.nodes())
        node_idx = {node: i for i, node in enumerate(nodes)}
        edges = [(node_idx[u], node_idx[v]) for u, v in graph.edges()]
        weights = [
            float(attrs.get("weight", 1.0))
            for _, _, attrs in graph.edges(data=True)
        ]
        ig_graph = ig.Graph(n=len(nodes), edges=edges, directed=False)
        partition = leidenalg.find_partition(
            ig_graph,
            leidenalg.ModularityVertexPartition,
            weights=weights,
            seed=RANDOM_SEED,
        )
        communities = [{nodes[i] for i in community} for community in partition]
        part = community_partition(communities)
        modularity = nx.algorithms.community.modularity(
            graph, communities, weight="weight"
        )
        return part, float(modularity), "leiden"
    except Exception:
        return None


def _detect_infomap(graph: nx.Graph) -> tuple[dict[str, int], float, str] | None:
    try:
        from infomap import Infomap  # type: ignore
    except Exception:
        return None

    try:
        nodes = list(graph.nodes())
        node_idx = {node: i for i, node in enumerate(nodes)}
        im = Infomap(f"--two-level --silent --seed {RANDOM_SEED}")
        add_link = getattr(im, "add_link", None) or getattr(im, "addLink")
        for u, v, attrs in graph.edges(data=True):
            add_link(node_idx[u], node_idx[v], float(attrs.get("weight", 1.0)))
        im.run()
        module_by_node = {}
        for node in im.tree:
            if getattr(node, "is_leaf", False):
                module_by_node[nodes[node.node_id]] = node.module_id
        if not module_by_node:
            return None
        grouped: dict[int, set[str]] = {}
        for node, module in module_by_node.items():
            grouped.setdefault(int(module), set()).add(node)
        communities = list(grouped.values())
        part = community_partition(communities)
        modularity = nx.algorithms.community.modularity(
            graph, communities, weight="weight"
        )
        return part, float(modularity), "infomap"
    except Exception:
        return None


def _detect_python_louvain(graph: nx.Graph) -> tuple[dict[str, int], float, str] | None:
    try:
        import community as community_louvain  # type: ignore

        part = community_louvain.best_partition(
            graph, weight="weight", random_state=RANDOM_SEED
        )
        modularity = community_louvain.modularity(part, graph, weight="weight")
        return part, float(modularity), "louvain"
    except Exception:
        return None


def _detect_networkx_louvain(graph: nx.Graph) -> tuple[dict[str, int], float, str] | None:
    louvain = getattr(nx.algorithms.community, "louvain_communities", None)
    if louvain is not None:
        try:
            communities = list(louvain(graph, weight="weight", seed=RANDOM_SEED))
            part = community_partition(communities)
            modularity = nx.algorithms.community.modularity(
                graph, communities, weight="weight"
            )
            return part, float(modularity), "networkx_louvain"
        except Exception:
            warnings.warn("NetworkX Louvain failed; using greedy modularity fallback")
    else:
        warnings.warn("No Louvain implementation available; using greedy modularity fallback")
    return None


def _detect_greedy_or_components(graph: nx.Graph) -> tuple[dict[str, int], float, str]:
    if graph.number_of_edges() <= 200_000:
        communities = list(
            nx.algorithms.community.greedy_modularity_communities(
                graph, weight="weight"
            )
        )
    else:
        communities = [set(c) for c in nx.connected_components(graph)]
    part = community_partition(communities)
    modularity = nx.algorithms.community.modularity(graph, communities, weight="weight")
    return part, float(modularity), "networkx_fallback"


def community_partition(communities: list[set[str]]) -> dict[str, int]:
    part: dict[str, int] = {}
    for i, comm in enumerate(communities):
        for node in comm:
            part[node] = i
    return part


def safe_core_numbers(graph: nx.Graph) -> dict[str, int]:
    try:
        return {node: int(core) for node, core in nx.core_number(graph).items()}
    except Exception:
        return {node: 0 for node in graph.nodes()}


def approximate_betweenness(graph: nx.Graph, sample_size: int) -> dict[str, float]:
    if graph.number_of_nodes() <= 1 or sample_size <= 0:
        return {node: 0.0 for node in graph.nodes()}
    k = min(sample_size, graph.number_of_nodes())
    try:
        if k >= graph.number_of_nodes():
            return {
                node: float(value)
                for node, value in nx.betweenness_centrality(
                    graph, normalized=True, weight=None
                ).items()
            }
        return {
            node: float(value)
            for node, value in nx.betweenness_centrality(
                graph,
                k=k,
                normalized=True,
                weight=None,
                seed=RANDOM_SEED,
            ).items()
        }
    except Exception:
        return {node: 0.0 for node in graph.nodes()}


def build_node_metrics(
    graph: nx.Graph,
    partition: dict[str, int],
    core_numbers: dict[str, int],
    betweenness: dict[str, float],
    node_col: str,
    community_col: str,
) -> pd.DataFrame:
    weighted_degree = dict(graph.degree(weight="weight"))
    degree = dict(graph.degree())
    rows = []
    for node in graph.nodes():
        total = float(weighted_degree.get(node, 0.0))
        own_community = partition.get(node)
        by_comm: dict[int, float] = {}
        same_weight = 0.0
        cross_weight = 0.0
        for nbr, attrs in graph[node].items():
            weight = float(attrs.get("weight", 1.0))
            comm = partition.get(nbr)
            if comm is None:
                continue
            by_comm[comm] = by_comm.get(comm, 0.0) + weight
            if comm == own_community:
                same_weight += weight
            else:
                cross_weight += weight
        participation = (
            1.0 - sum((weight / total) ** 2 for weight in by_comm.values())
            if total > 0
            else 0.0
        )
        bridge_score = total * participation
        rows.append(
            {
                node_col: node,
                community_col: own_community,
                "degree": int(degree.get(node, 0)),
                "weighted_degree": total,
                "core_number": int(core_numbers.get(node, 0)),
                "betweenness_centrality": float(betweenness.get(node, 0.0)),
                "neighbor_communities": len(by_comm),
                "same_community_weight": same_weight,
                "cross_community_weight": cross_weight,
                "cross_community_share": cross_weight / total if total > 0 else 0.0,
                "participation_coefficient": participation,
                "bridge_score": bridge_score,
                "structural_bridge_score": bridge_score
                * (1.0 + float(betweenness.get(node, 0.0))),
            }
        )
    return pd.DataFrame(rows)


def top_network_nodes(node_metrics: pd.DataFrame, top_k: int) -> pd.DataFrame:
    if node_metrics.empty:
        return node_metrics
    out = node_metrics.sort_values(
        [
            "structural_bridge_score",
            "betweenness_centrality",
            "core_number",
            "weighted_degree",
        ],
        ascending=False,
    )
    if top_k > 0:
        out = out.head(top_k)
    return out


def summarize_communities(
    graph: nx.Graph,
    partition: dict[str, int],
    core_numbers: dict[str, int],
    community_col: str = "community",
) -> pd.DataFrame:
    rows = []
    graph_volume = 2.0 * float(graph.size(weight="weight"))
    for comm in sorted(set(partition.values())):
        nodes = [node for node, c in partition.items() if c == comm]
        node_set = set(nodes)
        sub = graph.subgraph(nodes)
        internal_edge_weight = float(sub.size(weight="weight"))
        total_weighted_degree = float(
            sum(dict(graph.degree(nodes, weight="weight")).values())
        )
        external_edges = 0
        external_edge_weight = 0.0
        for node in node_set:
            for nbr, attrs in graph[node].items():
                if nbr in node_set:
                    continue
                external_edges += 1
                external_edge_weight += float(attrs.get("weight", 1.0))
        rest_volume = graph_volume - total_weighted_degree
        denominator = min(total_weighted_degree, rest_volume)
        conductance = (
            external_edge_weight / denominator if denominator > 0 else math.nan
        )
        community_cores = [core_numbers.get(node, 0) for node in nodes]
        rows.append(
            {
                community_col: comm,
                "n_nodes": len(nodes),
                "pct_nodes": len(nodes) / graph.number_of_nodes() * 100,
                "internal_edges": sub.number_of_edges(),
                "external_edges": external_edges,
                "internal_edge_weight": internal_edge_weight,
                "external_edge_weight": external_edge_weight,
                "total_weighted_degree": total_weighted_degree,
                "internal_weighted_degree": 2.0 * internal_edge_weight,
                "conductance": conductance,
                "avg_core_number": float(np.mean(community_cores))
                if community_cores
                else math.nan,
                "max_core_number": max(community_cores) if community_cores else 0,
            }
        )
    return pd.DataFrame(rows).sort_values("n_nodes", ascending=False)


def rank_bridge_actors(node_metrics: pd.DataFrame, top_k: int) -> pd.DataFrame:
    if node_metrics.empty:
        return node_metrics
    return (
        node_metrics.sort_values(
            [
                "structural_bridge_score",
                "bridge_score",
                "participation_coefficient",
            ],
            ascending=False,
        )
        .head(top_k)
    )


def summarize_graph(
    graph: nx.Graph,
    partition: dict[str, int],
    core_numbers: dict[str, int],
    community_summary: pd.DataFrame,
    modularity: float,
    method: str,
    n_communities_col: str,
    extra: dict[str, object],
) -> pd.DataFrame:
    community_sizes = (
        community_summary["n_nodes"].astype(float).to_numpy()
        if not community_summary.empty and "n_nodes" in community_summary.columns
        else np.array([], dtype=float)
    )
    shares = community_sizes / community_sizes.sum() if community_sizes.sum() else []
    concentration_hhi = float(np.sum(np.square(shares))) if len(shares) else math.nan
    top3_share = float(np.sort(shares)[-3:].sum()) if len(shares) else math.nan
    core_values = list(core_numbers.values())
    max_core = max(core_values) if core_values else 0
    weighted_degrees = [d for _, d in graph.degree(weight="weight")]
    row = {
        "n_nodes": graph.number_of_nodes(),
        "n_edges": graph.number_of_edges(),
        "density": nx.density(graph),
        "avg_degree": float(np.mean([d for _, d in graph.degree()])),
        "weighted_avg_degree": float(np.mean(weighted_degrees))
        if weighted_degrees
        else math.nan,
        n_communities_col: len(set(partition.values())),
        "modularity": modularity,
        "community_method": method,
        "community_concentration_hhi": concentration_hhi,
        "effective_communities": 1.0 / concentration_hhi
        if concentration_hhi and concentration_hhi > 0
        else math.nan,
        "largest_community_share": float(np.max(shares)) if len(shares) else math.nan,
        "top3_community_share": top3_share,
        "max_core_number": max_core,
        "max_core_node_share": (
            sum(1 for value in core_values if value == max_core) / len(core_values)
            if core_values and max_core
            else 0.0
        ),
        "avg_core_number": float(np.mean(core_values)) if core_values else math.nan,
        "degree_assortativity": safe_degree_assortativity(graph),
        "community_assortativity": safe_attribute_assortativity(graph, partition),
    }
    row.update(extra)
    return pd.DataFrame([row])


def safe_degree_assortativity(graph: nx.Graph) -> float:
    try:
        value = nx.degree_assortativity_coefficient(graph)
        return float(value) if np.isfinite(value) else math.nan
    except Exception:
        return math.nan


def safe_attribute_assortativity(graph: nx.Graph, partition: dict[str, int]) -> float:
    try:
        nx.set_node_attributes(graph, partition, "detected_community")
        value = nx.attribute_assortativity_coefficient(graph, "detected_community")
        return float(value) if np.isfinite(value) else math.nan
    except Exception:
        return math.nan


def build_video_cluster_outputs(
    videos: pd.DataFrame,
    comments: pd.DataFrame,
    video_themes: pd.DataFrame,
    video_theme_labels: pd.DataFrame,
    config: AnalyzerConfig,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    actor_video = comments[["author_actor_id", "video_id"]].drop_duplicates()
    commenter_counts = actor_video.groupby("video_id")["author_actor_id"].nunique()
    keep_videos = commenter_counts[
        commenter_counts >= config.analysis.min_video_commenters
    ].index
    actor_video = actor_video[actor_video["video_id"].isin(keep_videos)]
    if actor_video.empty or actor_video["video_id"].nunique() < 2:
        empty = pd.DataFrame()
        return empty, empty, empty, empty, empty, empty

    video_ids = sorted(actor_video["video_id"].unique())
    actors = sorted(actor_video["author_actor_id"].unique())
    video_idx = {video_id: i for i, video_id in enumerate(video_ids)}
    actor_idx = {actor: i for i, actor in enumerate(actors)}
    rows = actor_video["video_id"].map(video_idx).to_numpy()
    cols = actor_video["author_actor_id"].map(actor_idx).to_numpy()
    matrix = csr_matrix(
        (np.ones(len(actor_video), dtype=np.float32), (rows, cols)),
        shape=(len(video_ids), len(actors)),
    )
    co = (matrix @ matrix.T).tocsr()
    co.setdiag(0)
    co = co.multiply(co >= config.analysis.min_shared_video_commenters)
    co.eliminate_zeros()
    graph = nx.from_scipy_sparse_array(co, edge_attribute="weight")
    graph = nx.relabel_nodes(
        graph, {i: video_id for i, video_id in enumerate(video_ids)}
    )
    graph.remove_nodes_from(list(nx.isolates(graph)))
    if graph.number_of_nodes() == 0:
        empty = pd.DataFrame()
        return empty, empty, empty, empty, empty, empty

    partition, modularity, method = detect_communities(
        graph, config.analysis.community_algorithm
    )
    core_numbers = safe_core_numbers(graph)
    betweenness = approximate_betweenness(
        graph, config.analysis.betweenness_sample_size
    )
    video_network_metrics = build_node_metrics(
        graph,
        partition,
        core_numbers,
        betweenness,
        node_col="video_id",
        community_col="video_cluster",
    )
    structural_cluster_summary = summarize_communities(
        graph, partition, core_numbers, community_col="video_cluster"
    ).rename(columns={"n_nodes": "n_graph_videos", "pct_nodes": "pct_graph_videos"})
    network_summary = summarize_graph(
        graph,
        partition,
        core_numbers,
        structural_cluster_summary.rename(
            columns={"n_graph_videos": "n_nodes", "pct_graph_videos": "pct_nodes"}
        ),
        modularity=modularity,
        method=method,
        n_communities_col="n_video_clusters",
        extra={
            "min_video_commenters": config.analysis.min_video_commenters,
            "min_shared_video_commenters": config.analysis.min_shared_video_commenters,
            "betweenness_sample_size": min(
                max(0, config.analysis.betweenness_sample_size),
                graph.number_of_nodes(),
            ),
        },
    )

    video_stats = (
        comments.groupby("video_id")
        .agg(
            observed_comments=("comment_id", "count"),
            observed_commenters=("author_actor_id", "nunique"),
        )
        .reset_index()
    )
    video_clusters = pd.DataFrame(
        [
            {"video_id": video_id, "video_cluster": cluster}
            for video_id, cluster in partition.items()
        ]
    )
    video_cols = [
        "video_id",
        "title",
        "published_at",
        "view_count",
        "like_count",
        "comment_count",
    ]
    video_clusters = (
        video_clusters.merge(videos[video_cols], on="video_id", how="left")
        .merge(video_stats, on="video_id", how="left")
        .merge(
            video_themes[["video_id", "primary_theme", "theme_labels"]],
            on="video_id",
            how="left",
        )
        .sort_values(["video_cluster", "observed_commenters"], ascending=[True, False])
    )
    cluster_summary = summarize_video_clusters(
        video_clusters, comments, video_theme_labels
    )
    if not cluster_summary.empty and not structural_cluster_summary.empty:
        cluster_summary = cluster_summary.merge(
            structural_cluster_summary,
            on="video_cluster",
            how="left",
        )
    cluster_affinity = build_video_cluster_theme_affinity(
        video_clusters, video_theme_labels
    )
    video_network_metrics = (
        video_network_metrics.merge(
            videos[["video_id", "title", "published_at"]],
            on="video_id",
            how="left",
        )
        .sort_values(
            [
                "structural_bridge_score",
                "betweenness_centrality",
                "weighted_degree",
            ],
            ascending=False,
        )
    )
    video_link_opportunities = build_video_link_opportunities(
        graph,
        actor_video,
        video_clusters,
        top_k=config.analysis.top_video_link_opportunities,
        max_candidate_pairs=config.analysis.max_video_link_candidate_pairs,
    )
    return (
        network_summary,
        cluster_summary,
        video_clusters,
        cluster_affinity,
        video_network_metrics,
        video_link_opportunities,
    )


def build_video_link_opportunities(
    graph: nx.Graph,
    actor_video: pd.DataFrame,
    video_clusters: pd.DataFrame,
    top_k: int,
    max_candidate_pairs: int,
) -> pd.DataFrame:
    if graph.number_of_nodes() < 3 or top_k <= 0:
        return pd.DataFrame()

    neighbors = {node: set(graph.neighbors(node)) for node in graph.nodes()}
    degrees = {node: len(values) for node, values in neighbors.items()}
    rows = []
    for u, v in iter_candidate_non_edges(graph, max_candidate_pairs):
        common = neighbors[u] & neighbors[v]
        if not common:
            continue
        union_size = len(neighbors[u] | neighbors[v])
        common_count = len(common)
        jaccard = common_count / union_size if union_size else 0.0
        adamic_adar = sum(
            1.0 / math.log(degrees[node])
            for node in common
            if degrees.get(node, 0) > 1
        )
        resource_allocation = sum(
            1.0 / degrees[node]
            for node in common
            if degrees.get(node, 0) > 0
        )
        score = (
            math.log1p(common_count)
            + 2.0 * jaccard
            + adamic_adar
            + resource_allocation
        )
        rows.append(
            {
                "source_video_id": u,
                "target_video_id": v,
                "common_neighbor_videos": common_count,
                "jaccard_score": jaccard,
                "adamic_adar_score": adamic_adar,
                "resource_allocation_score": resource_allocation,
                "opportunity_score": score,
                "common_neighbor_ids_tuple": tuple(sorted(common)),
            }
        )
    if not rows:
        return pd.DataFrame()

    candidates = (
        pd.DataFrame(rows)
        .sort_values(
            [
                "opportunity_score",
                "adamic_adar_score",
                "resource_allocation_score",
                "jaccard_score",
            ],
            ascending=False,
        )
        .head(top_k)
    )

    actor_sets = {
        video_id: set(group["author_actor_id"])
        for video_id, group in actor_video.groupby("video_id")
    }
    meta = video_clusters.set_index("video_id", drop=False)
    detailed = []
    for row in candidates.itertuples(index=False):
        source = row.source_video_id
        target = row.target_video_id
        source_meta = meta.loc[source].to_dict() if source in meta.index else {}
        target_meta = meta.loc[target].to_dict() if target in meta.index else {}
        current_shared = len(actor_sets.get(source, set()) & actor_sets.get(target, set()))
        common_neighbors = list(row.common_neighbor_ids_tuple)
        common_neighbor_titles = _top_common_neighbor_titles(common_neighbors, meta)
        source_theme = source_meta.get("primary_theme")
        target_theme = target_meta.get("primary_theme")
        source_cluster = source_meta.get("video_cluster")
        target_cluster = target_meta.get("video_cluster")
        detailed.append(
            {
                "source_video_id": source,
                "target_video_id": target,
                "source_title": source_meta.get("title"),
                "target_title": target_meta.get("title"),
                "source_primary_theme": source_theme,
                "target_primary_theme": target_theme,
                "source_video_cluster": source_cluster,
                "target_video_cluster": target_cluster,
                "source_published_at": source_meta.get("published_at"),
                "target_published_at": target_meta.get("published_at"),
                "opportunity_type": classify_video_opportunity(
                    source_theme,
                    target_theme,
                    source_cluster,
                    target_cluster,
                    current_shared,
                ),
                "opportunity_score": row.opportunity_score,
                "jaccard_score": row.jaccard_score,
                "adamic_adar_score": row.adamic_adar_score,
                "resource_allocation_score": row.resource_allocation_score,
                "common_neighbor_videos": row.common_neighbor_videos,
                "current_shared_audience": current_shared,
                "common_neighbor_video_ids": "; ".join(common_neighbors[:10]),
                "common_neighbor_titles": common_neighbor_titles,
            }
        )
    return pd.DataFrame(detailed)


def iter_candidate_non_edges(
    graph: nx.Graph,
    max_candidate_pairs: int,
) -> list[tuple[str, str]]:
    nodes = sorted(graph.nodes())
    n_possible = len(nodes) * (len(nodes) - 1) // 2
    n_non_edges = n_possible - graph.number_of_edges()
    cap = max_candidate_pairs if max_candidate_pairs > 0 else n_non_edges
    if n_non_edges <= cap:
        return [(u, v) for u, v in nx.non_edges(graph)]

    rng = np.random.default_rng(RANDOM_SEED)
    node_count = len(nodes)
    pairs: set[tuple[str, str]] = set()
    attempts = 0
    max_attempts = max(cap * 20, cap + 1000)
    while len(pairs) < cap and attempts < max_attempts:
        i, j = rng.choice(node_count, size=2, replace=False)
        u, v = sorted((nodes[int(i)], nodes[int(j)]))
        attempts += 1
        if graph.has_edge(u, v):
            continue
        pairs.add((u, v))
    return sorted(pairs)


def classify_video_opportunity(
    source_theme: object,
    target_theme: object,
    source_cluster: object,
    target_cluster: object,
    current_shared_audience: int,
) -> str:
    same_theme = str(source_theme or "") == str(target_theme or "")
    same_cluster = source_cluster == target_cluster
    if current_shared_audience == 0 and not same_cluster:
        return "latent_cross_cluster_bridge"
    if not same_cluster and not same_theme:
        return "cross_cluster_theme_bridge"
    if same_cluster and not same_theme:
        return "within_cluster_theme_blend"
    if not same_cluster and same_theme:
        return "same_theme_cross_cluster_bridge"
    return "underconnected_similar_audience"


def _top_common_neighbor_titles(
    common_neighbors: list[str],
    meta: pd.DataFrame,
    limit: int = 5,
) -> str:
    rows = []
    for video_id in common_neighbors:
        if video_id not in meta.index:
            continue
        row = meta.loc[video_id]
        rows.append(
            (
                int(row.get("observed_commenters") or 0),
                str(row.get("title") or video_id),
            )
        )
    rows.sort(reverse=True)
    return "; ".join(title[:72] for _, title in rows[:limit])


def summarize_video_clusters(
    video_clusters: pd.DataFrame,
    comments: pd.DataFrame,
    video_theme_labels: pd.DataFrame,
) -> pd.DataFrame:
    if video_clusters.empty:
        return pd.DataFrame()
    c = comments.merge(
        video_clusters[["video_id", "video_cluster"]],
        on="video_id",
        how="inner",
    )
    rows = []
    for cluster, group in video_clusters.groupby("video_cluster"):
        cluster_comments = c[c["video_cluster"] == cluster]
        labels = video_theme_labels.merge(
            group[["video_id"]],
            on="video_id",
            how="inner",
        )
        top_labels = (
            labels.groupby("theme_label").size().sort_values(ascending=False).head(5)
            if not labels.empty
            else pd.Series(dtype=int)
        )
        top_videos = group.sort_values(
            ["observed_commenters", "observed_comments"], ascending=False
        ).head(5)
        rows.append(
            {
                "video_cluster": cluster,
                "n_videos": len(group),
                "date_min": group["published_at"].min(),
                "date_max": group["published_at"].max(),
                "total_observed_comments": int(
                    group["observed_comments"].fillna(0).sum()
                ),
                "unique_commenters": cluster_comments["author_actor_id"].nunique(),
                "median_observed_commenters": group["observed_commenters"].median(),
                "total_views": int(group["view_count"].fillna(0).sum()),
                "top_theme_labels": "; ".join(
                    f"{label} ({count})" for label, count in top_labels.items()
                ),
                "top_videos": _join_ranked(
                    top_videos, "title", "observed_commenters"
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["unique_commenters", "total_observed_comments"], ascending=False
    )


def build_video_cluster_theme_affinity(
    video_clusters: pd.DataFrame,
    video_theme_labels: pd.DataFrame,
) -> pd.DataFrame:
    if video_clusters.empty or video_theme_labels.empty:
        return pd.DataFrame()
    vc = video_clusters[["video_id", "video_cluster"]].drop_duplicates()
    labeled = vc.merge(
        video_theme_labels[["video_id", "theme_label"]], on="video_id", how="inner"
    )
    if labeled.empty:
        return pd.DataFrame()
    cluster_totals = vc.groupby("video_cluster").size().rename("cluster_videos")
    overall_total = len(vc)
    overall_counts = labeled.groupby("theme_label").size().rename("overall_label_videos")
    rows = (
        labeled.groupby(["video_cluster", "theme_label"])
        .agg(n_videos=("video_id", "nunique"))
        .reset_index()
        .merge(cluster_totals.reset_index(), on="video_cluster", how="left")
        .merge(overall_counts.reset_index(), on="theme_label", how="left")
    )
    rows["cluster_share"] = rows["n_videos"] / rows["cluster_videos"]
    rows["overall_share"] = rows["overall_label_videos"] / overall_total
    rows["lift"] = rows["cluster_share"] / rows["overall_share"].replace(0, np.nan)
    return rows.sort_values(
        ["cluster_videos", "video_cluster", "lift", "n_videos"],
        ascending=[False, True, False, False],
    )


def _join_ranked(frame: pd.DataFrame, label_col: str, value_col: str) -> str:
    values = []
    for row in frame.itertuples(index=False):
        label = str(getattr(row, label_col, "") or "")
        value = getattr(row, value_col, None)
        if not label:
            continue
        values.append(f"{label[:48]} ({value})")
    return "; ".join(values)
