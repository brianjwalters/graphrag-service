#!/usr/bin/env python3
"""
Validate and summarize the generated GraphRAG structures.
"""

import json
import os
from collections import Counter
from typing import Dict, Any


def load_json_file(filepath: str) -> Any:
    """Load a JSON file."""
    with open(filepath, 'r') as f:
        return json.load(f)


def analyze_communities(data_dir: str):
    """Analyze communities data."""
    filepath = os.path.join(data_dir, "communities.json")
    communities = load_json_file(filepath)

    print("\n📊 COMMUNITIES ANALYSIS")
    print("=" * 60)
    print(f"Total Communities: {len(communities)}")

    # Level distribution
    levels = Counter(c["level"] for c in communities)
    print(f"\nLevel Distribution:")
    for level in sorted(levels.keys()):
        print(f"  Level {level}: {levels[level]} communities")

    # Coherence score statistics
    coherence_scores = [c["coherence_score"] for c in communities]
    print(f"\nCoherence Scores:")
    print(f"  Min: {min(coherence_scores):.3f}")
    print(f"  Max: {max(coherence_scores):.3f}")
    print(f"  Avg: {sum(coherence_scores)/len(coherence_scores):.3f}")

    # Node count statistics
    node_counts = [c["node_count"] for c in communities]
    print(f"\nNode Counts per Community:")
    print(f"  Min: {min(node_counts)}")
    print(f"  Max: {max(node_counts)}")
    print(f"  Avg: {sum(node_counts)/len(node_counts):.1f}")
    print(f"  Total: {sum(node_counts)}")

    # Sample community
    print(f"\n📝 Sample Community:")
    sample = communities[0]
    print(f"  ID: {sample['community_id']}")
    print(f"  Title: {sample['title']}")
    print(f"  Level: {sample['level']}")
    print(f"  Nodes: {sample['node_count']}")
    print(f"  Edges: {sample['edge_count']}")
    print(f"  Coherence: {sample['coherence_score']:.3f}")
    print(f"  Topics: {', '.join(sample['metadata'].get('primary_topics', []))}")

    return communities


def analyze_node_communities(data_dir: str):
    """Analyze node-community relationships."""
    filepath = os.path.join(data_dir, "node_communities.json")
    node_communities = load_json_file(filepath)

    print("\n🔗 NODE-COMMUNITY RELATIONSHIPS")
    print("=" * 60)
    print(f"Total Relationships: {len(node_communities)}")

    # Membership strength distribution
    strengths = [nc["membership_strength"] for nc in node_communities]
    print(f"\nMembership Strength Distribution:")
    print(f"  Min: {min(strengths):.3f}")
    print(f"  Max: {max(strengths):.3f}")
    print(f"  Avg: {sum(strengths)/len(strengths):.3f}")

    # Strength ranges
    core = sum(1 for s in strengths if s >= 0.9)
    strong = sum(1 for s in strengths if 0.7 <= s < 0.9)
    moderate = sum(1 for s in strengths if 0.5 <= s < 0.7)

    print(f"\nStrength Categories:")
    print(f"  Core (0.9-1.0): {core} ({core/len(strengths)*100:.1f}%)")
    print(f"  Strong (0.7-0.89): {strong} ({strong/len(strengths)*100:.1f}%)")
    print(f"  Moderate (0.5-0.69): {moderate} ({moderate/len(strengths)*100:.1f}%)")

    # Node participation
    nodes_per_community = Counter(nc["node_id"] for nc in node_communities)
    communities_per_node = list(nodes_per_community.values())

    print(f"\nNodes Participation:")
    print(f"  Unique nodes: {len(nodes_per_community)}")
    print(f"  Avg communities per node: {sum(communities_per_node)/len(communities_per_node):.2f}")
    print(f"  Max communities per node: {max(communities_per_node)}")
    print(f"  Min communities per node: {min(communities_per_node)}")

    # Sample relationship
    print(f"\n📝 Sample Node-Community Relationship:")
    sample = node_communities[0]
    print(f"  Node ID: {sample['node_id']}")
    print(f"  Community ID: {sample['community_id']}")
    print(f"  Membership Strength: {sample['membership_strength']:.3f}")

    return node_communities


def analyze_reports(data_dir: str):
    """Analyze reports data."""
    filepath = os.path.join(data_dir, "reports.json")
    reports = load_json_file(filepath)

    print("\n📄 REPORTS ANALYSIS")
    print("=" * 60)
    print(f"Total Reports: {len(reports)}")

    # Report type distribution
    types = Counter(r["report_type"] for r in reports)
    print(f"\nReport Type Distribution:")
    for rtype in ["global", "community", "node"]:
        count = types.get(rtype, 0)
        print(f"  {rtype.capitalize()}: {count} reports")

    # Rating statistics
    ratings = [r["rating"] for r in reports]
    print(f"\nRating Statistics:")
    print(f"  Min: {min(ratings):.1f}")
    print(f"  Max: {max(ratings):.1f}")
    print(f"  Avg: {sum(ratings)/len(ratings):.2f}")

    # Content length statistics
    content_lengths = [len(r["content"]) for r in reports]
    print(f"\nContent Length (characters):")
    print(f"  Min: {min(content_lengths):,}")
    print(f"  Max: {max(content_lengths):,}")
    print(f"  Avg: {sum(content_lengths)/len(content_lengths):,.0f}")

    # Sample reports by type
    for rtype in ["global", "community", "node"]:
        sample = next((r for r in reports if r["report_type"] == rtype), None)
        if sample:
            print(f"\n📝 Sample {rtype.capitalize()} Report:")
            print(f"  ID: {sample['report_id']}")
            print(f"  Title: {sample['title']}")
            print(f"  Rating: {sample['rating']:.1f}")
            print(f"  Summary: {sample['summary'][:100]}...")
            if sample.get("community_id"):
                print(f"  Community: {sample['community_id']}")
            if sample.get("node_id"):
                print(f"  Node: {sample['node_id']}")

    return reports


def check_referential_integrity(data_dir: str):
    """Check referential integrity between tables."""
    print("\n✅ REFERENTIAL INTEGRITY CHECK")
    print("=" * 60)

    communities = load_json_file(os.path.join(data_dir, "communities.json"))
    node_communities = load_json_file(os.path.join(data_dir, "node_communities.json"))
    reports = load_json_file(os.path.join(data_dir, "reports.json"))
    node_ids = load_json_file(os.path.join(data_dir, "node_ids.json"))

    community_ids = set(c["community_id"] for c in communities)
    node_id_set = set(node_ids)

    # Check node_communities references
    nc_orphaned_nodes = set()
    nc_orphaned_communities = set()

    for nc in node_communities:
        if nc["node_id"] not in node_id_set:
            nc_orphaned_nodes.add(nc["node_id"])
        if nc["community_id"] not in community_ids:
            nc_orphaned_communities.add(nc["community_id"])

    print("Node-Community Relationships:")
    if nc_orphaned_nodes:
        print(f"  ⚠️  {len(nc_orphaned_nodes)} orphaned node references")
    else:
        print(f"  ✅ All node references valid")

    if nc_orphaned_communities:
        print(f"  ⚠️  {len(nc_orphaned_communities)} orphaned community references")
    else:
        print(f"  ✅ All community references valid")

    # Check reports references
    report_orphaned_communities = set()
    report_orphaned_nodes = set()

    for report in reports:
        if report.get("community_id") and report["community_id"] not in community_ids:
            report_orphaned_communities.add(report["community_id"])
        if report.get("node_id") and report["node_id"] not in node_id_set:
            report_orphaned_nodes.add(report["node_id"])

    print("\nReports:")
    if report_orphaned_communities:
        print(f"  ⚠️  {len(report_orphaned_communities)} orphaned community references")
    else:
        print(f"  ✅ All community references valid")

    if report_orphaned_nodes:
        print(f"  ⚠️  {len(report_orphaned_nodes)} orphaned node references")
    else:
        print(f"  ✅ All node references valid")

    # Check hierarchical community structure
    parent_refs = [c["parent_community_id"] for c in communities if c["parent_community_id"]]
    orphaned_parents = [p for p in parent_refs if p not in community_ids]

    print("\nHierarchical Structure:")
    if orphaned_parents:
        print(f"  ⚠️  {len(orphaned_parents)} invalid parent community references")
    else:
        print(f"  ✅ All parent community references valid")


def main():
    """Main execution."""
    data_dir = "/srv/luris/be/graphrag-service/data"

    print("\n" + "=" * 60)
    print("GraphRAG Structure Validation Report")
    print("=" * 60)

    # Analyze each component
    communities = analyze_communities(data_dir)
    node_communities = analyze_node_communities(data_dir)
    reports = analyze_reports(data_dir)

    # Check referential integrity
    check_referential_integrity(data_dir)

    print("\n" + "=" * 60)
    print("✅ Validation Complete")
    print("=" * 60)

    # Summary statistics
    print("\n📊 SUMMARY STATISTICS")
    print("=" * 60)
    print(f"Total Communities: {len(communities)}")
    print(f"Total Node-Community Relationships: {len(node_communities)}")
    print(f"Total Reports: {len(reports)}")
    print(f"Total Nodes: {len(load_json_file(os.path.join(data_dir, 'node_ids.json')))}")

    # File sizes
    print(f"\n💾 FILE SIZES")
    for filename in ["communities.json", "node_communities.json", "reports.json", "node_ids.json"]:
        filepath = os.path.join(data_dir, filename)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        print(f"  {filename}: {size_mb:.2f} MB")


if __name__ == "__main__":
    main()