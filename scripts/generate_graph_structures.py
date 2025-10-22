#!/usr/bin/env python3
"""
Generate synthetic data for GraphRAG-specific tables:
- graph.communities (500 rows)
- graph.node_communities (30,000 rows)
- graph.reports (200 rows)

This script generates realistic legal domain data for testing GraphRAG functionality.
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Legal domain themes for communities
COMMUNITY_THEMES = [
    {
        "theme": "Second Amendment Jurisprudence",
        "topics": ["constitutional_law", "second_amendment", "individual_rights", "gun_control"],
        "key_cases": ["Heller", "McDonald", "Bruen", "Rahimi"],
        "concepts": ["text-history-tradition test", "strict scrutiny", "originalism"]
    },
    {
        "theme": "Qualified Immunity Doctrine",
        "topics": ["civil_rights", "section_1983", "police_misconduct", "sovereign_immunity"],
        "key_cases": ["Harlow", "Pearson", "Mullenix", "Taylor"],
        "concepts": ["clearly established law", "objective reasonableness", "constitutional violation"]
    },
    {
        "theme": "Due Process Analysis",
        "topics": ["procedural_due_process", "substantive_due_process", "fundamental_rights"],
        "key_cases": ["Mathews", "Goldberg", "Cleveland Board", "Washington v. Glucksberg"],
        "concepts": ["liberty interest", "property interest", "balancing test"]
    },
    {
        "theme": "Equal Protection Cases",
        "topics": ["discrimination", "suspect_classification", "rational_basis", "strict_scrutiny"],
        "key_cases": ["Brown", "Loving", "Craig", "Obergefell"],
        "concepts": ["disparate impact", "discriminatory intent", "intermediate scrutiny"]
    },
    {
        "theme": "First Amendment Free Speech",
        "topics": ["free_speech", "content_neutrality", "public_forum", "commercial_speech"],
        "key_cases": ["Brandenburg", "Tinker", "Citizens United", "RAV"],
        "concepts": ["time place manner", "clear and present danger", "prior restraint"]
    },
    {
        "theme": "Fourth Amendment Search & Seizure",
        "topics": ["search_warrant", "probable_cause", "reasonable_expectation", "exclusionary_rule"],
        "key_cases": ["Katz", "Terry", "Carpenter", "Riley"],
        "concepts": ["fruit of poisonous tree", "exigent circumstances", "plain view doctrine"]
    },
    {
        "theme": "Criminal Procedure",
        "topics": ["miranda_rights", "right_to_counsel", "double_jeopardy", "speedy_trial"],
        "key_cases": ["Miranda", "Gideon", "Brady", "Crawford"],
        "concepts": ["ineffective assistance", "confrontation clause", "plea bargaining"]
    },
    {
        "theme": "Civil Rights Litigation",
        "topics": ["voting_rights", "housing_discrimination", "employment_discrimination"],
        "key_cases": ["Shelby County", "Texas Housing", "Griggs", "Bostock"],
        "concepts": ["disparate treatment", "reasonable accommodation", "retaliation"]
    },
    {
        "theme": "Administrative Law",
        "topics": ["chevron_deference", "agency_rulemaking", "arbitrary_capricious", "apa"],
        "key_cases": ["Chevron", "State Farm", "Auer", "Vermont Yankee"],
        "concepts": ["substantial evidence", "notice and comment", "hard look review"]
    },
    {
        "theme": "Habeas Corpus",
        "topics": ["collateral_review", "exhaustion", "procedural_default", "aedpa"],
        "key_cases": ["Stone v. Powell", "Teague", "Williams", "Martinez"],
        "concepts": ["cause and prejudice", "actual innocence", "retroactivity"]
    },
    {
        "theme": "Commerce Clause",
        "topics": ["interstate_commerce", "dormant_commerce", "substantial_effects"],
        "key_cases": ["Wickard", "Lopez", "Morrison", "Raich"],
        "concepts": ["aggregation principle", "economic activity", "channels of commerce"]
    },
    {
        "theme": "Takings Clause",
        "topics": ["eminent_domain", "regulatory_taking", "public_use", "just_compensation"],
        "key_cases": ["Kelo", "Lucas", "Penn Central", "Nollan"],
        "concepts": ["essential nexus", "rough proportionality", "per se taking"]
    },
    {
        "theme": "Establishment Clause",
        "topics": ["religious_freedom", "separation_church_state", "endorsement_test"],
        "key_cases": ["Lemon", "Lynch", "Town of Greece", "Kennedy v. Bremerton"],
        "concepts": ["coercion test", "historical practices", "neutrality principle"]
    },
    {
        "theme": "Contract Clause",
        "topics": ["impairment_contracts", "state_obligations", "substantial_impairment"],
        "key_cases": ["Home Building", "Allied Structural", "Energy Reserves"],
        "concepts": ["legitimate public purpose", "reasonable and necessary", "police power"]
    },
    {
        "theme": "Supremacy Clause",
        "topics": ["preemption", "federal_state_conflict", "field_preemption"],
        "key_cases": ["Arizona v. US", "Crosby", "Geier", "Wyeth"],
        "concepts": ["express preemption", "implied preemption", "obstacle preemption"]
    }
]


class GraphStructureGenerator:
    def __init__(self, seed: int = 42):
        """Initialize the generator with a random seed for reproducibility."""
        random.seed(seed)
        self.communities = []
        self.node_communities = []
        self.reports = []
        self.node_ids = []  # Will be populated with existing node IDs

    def generate_uuid(self) -> str:
        """Generate a UUID4 string."""
        return str(uuid.uuid4())

    def generate_timestamp(self, days_back: int = 30) -> str:
        """Generate a timestamp within the last N days."""
        base_time = datetime.now()
        random_days = random.uniform(0, days_back)
        timestamp = base_time - timedelta(days=random_days)
        return timestamp.isoformat() + "Z"

    def generate_client_and_case_ids(self) -> Tuple[str, str]:
        """Generate client_id and optionally case_id."""
        client_id = self.generate_uuid()
        case_id = self.generate_uuid() if random.random() > 0.3 else None
        return client_id, case_id

    def load_existing_node_ids(self) -> List[str]:
        """Load or generate node IDs for reference."""
        # In a real scenario, we would load these from the database
        # For now, generate synthetic node IDs
        node_ids = []

        # Generate entity nodes
        entity_types = ["case", "statute", "regulation", "judge", "party", "concept", "precedent"]

        for i in range(10000):
            entity_type = random.choice(entity_types)
            node_id = f"entity_{entity_type}_{str(uuid.uuid4())[:8]}"
            node_ids.append(node_id)

        self.node_ids = node_ids
        return node_ids

    def generate_communities(self, count: int = 500) -> List[Dict]:
        """Generate community records with hierarchical structure."""
        communities = []

        # Expand themes to reach 500 communities
        expanded_themes = []
        for theme_data in COMMUNITY_THEMES:
            # Create variations of each theme
            base_theme = theme_data["theme"]

            # Main community
            expanded_themes.append({
                **theme_data,
                "variant": "main",
                "level": 0
            })

            # Circuit-specific variations
            circuits = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "DC"]
            for circuit in random.sample(circuits, min(3, len(circuits))):
                expanded_themes.append({
                    **theme_data,
                    "theme": f"{base_theme} - {circuit} Circuit",
                    "variant": f"circuit_{circuit}",
                    "level": 1
                })

            # Time period variations
            periods = ["Pre-Warren Court", "Warren Court Era", "Burger Court Era",
                      "Rehnquist Court Era", "Roberts Court Era", "Recent Developments"]
            for period in random.sample(periods, 2):
                expanded_themes.append({
                    **theme_data,
                    "theme": f"{base_theme} - {period}",
                    "variant": f"period_{period.lower().replace(' ', '_')}",
                    "level": 1
                })

            # Specialized sub-communities
            if len(theme_data.get("concepts", [])) > 2:
                for concept in random.sample(theme_data["concepts"], 2):
                    expanded_themes.append({
                        **theme_data,
                        "theme": f"{base_theme} - {concept.title()}",
                        "variant": f"concept_{concept.replace(' ', '_')}",
                        "level": 2
                    })

        # Ensure we have enough themes
        while len(expanded_themes) < count:
            # Create synthetic variations
            base_theme = random.choice(COMMUNITY_THEMES)
            variant_num = len(expanded_themes)
            expanded_themes.append({
                **base_theme,
                "theme": f"{base_theme['theme']} - Variation {variant_num}",
                "variant": f"synthetic_{variant_num}",
                "level": random.choices([0, 1, 2], weights=[0.7, 0.2, 0.1])[0]
            })

        # Shuffle and take exactly the count needed
        random.shuffle(expanded_themes)
        selected_themes = expanded_themes[:count]

        # Track parent communities for hierarchical structure
        level_0_communities = []
        level_1_communities = []

        for idx, theme_data in enumerate(selected_themes):
            community_id = f"community_{theme_data['variant']}_{str(uuid.uuid4())[:8]}"

            # Determine parent community
            parent_id = None
            if theme_data["level"] == 1 and level_0_communities:
                parent_id = random.choice(level_0_communities)
            elif theme_data["level"] == 2 and level_1_communities:
                parent_id = random.choice(level_1_communities)

            # Generate node and edge counts
            if theme_data["level"] == 0:
                node_count = random.randint(100, 500)
                edge_count = random.randint(node_count * 2, node_count * 5)
                level_0_communities.append(community_id)
            elif theme_data["level"] == 1:
                node_count = random.randint(50, 200)
                edge_count = random.randint(node_count, node_count * 3)
                level_1_communities.append(community_id)
            else:  # level 2
                node_count = random.randint(20, 80)
                edge_count = random.randint(node_count, node_count * 2)

            # Generate coherence score (higher for smaller, specialized communities)
            if theme_data["level"] == 0:
                coherence_score = random.uniform(0.6, 0.85)
            elif theme_data["level"] == 1:
                coherence_score = random.uniform(0.7, 0.9)
            else:
                coherence_score = random.uniform(0.8, 1.0)

            client_id, case_id = self.generate_client_and_case_ids()

            # Build detailed description
            description = self.generate_community_description(
                theme_data["theme"],
                theme_data.get("topics", []),
                theme_data.get("key_cases", []),
                theme_data.get("concepts", []),
                node_count,
                edge_count
            )

            community = {
                "id": self.generate_uuid(),
                "community_id": community_id,
                "title": theme_data["theme"],
                "summary": f"Community of entities related to {theme_data['theme'].lower()}, "
                          f"containing {node_count} nodes and {edge_count} relationships.",
                "description": description,
                "level": theme_data["level"],
                "node_count": node_count,
                "edge_count": edge_count,
                "coherence_score": round(coherence_score, 3),
                "parent_community_id": parent_id,
                "metadata": {
                    "leiden_resolution": round(random.uniform(0.5, 1.5), 2),
                    "detection_method": random.choice(["leiden_algorithm", "louvain_algorithm",
                                                      "label_propagation", "spectral_clustering"]),
                    "primary_topics": theme_data.get("topics", [])[:3],
                    "key_cases": theme_data.get("key_cases", [])[:4],
                    "key_concepts": theme_data.get("concepts", [])[:3]
                },
                "client_id": client_id,
                "case_id": case_id,
                "summary_embedding": None,
                "created_at": self.generate_timestamp(60),
                "updated_at": self.generate_timestamp(30)
            }

            communities.append(community)
            self.communities.append(community)

        return communities

    def generate_community_description(self, theme: str, topics: List[str],
                                      cases: List[str], concepts: List[str],
                                      node_count: int, edge_count: int) -> str:
        """Generate a detailed description for a community."""
        description_parts = [
            f"This community represents a comprehensive network of legal entities centered around {theme}.",
            f"It encompasses {node_count} distinct entities connected through {edge_count} relationships.",
        ]

        if topics:
            topics_str = ", ".join(topics[:3])
            description_parts.append(f"The primary topics covered include {topics_str}.")

        if cases:
            cases_str = ", ".join(cases[:4])
            description_parts.append(
                f"Key cases forming the foundation of this community include {cases_str}, "
                f"which have shaped the jurisprudence in this area."
            )

        if concepts:
            concepts_str = ", ".join(concepts[:3])
            description_parts.append(
                f"Central legal concepts include {concepts_str}, "
                f"which are frequently referenced and interconnected throughout the network."
            )

        # Add analysis details
        density = edge_count / (node_count * (node_count - 1) / 2) if node_count > 1 else 0
        if density > 0.1:
            description_parts.append(
                f"The community exhibits high interconnectedness with a density of {density:.3f}, "
                f"indicating strong relationships between entities."
            )

        description_parts.append(
            "This cluster was identified through advanced graph analysis techniques "
            "and represents a significant area of legal doctrine with practical implications "
            "for litigation and legal research."
        )

        return " ".join(description_parts)

    def generate_node_communities(self, count: int = 30000) -> List[Dict]:
        """Generate node-community junction table records."""
        if not self.node_ids:
            self.load_existing_node_ids()

        if not self.communities:
            raise ValueError("Communities must be generated first")

        node_communities = []
        community_ids = [c["community_id"] for c in self.communities]

        # Track which nodes are assigned to which communities
        node_assignments = {}

        # Ensure each node gets 1-5 community assignments (average 3)
        for node_id in self.node_ids:
            # Determine number of communities for this node
            num_communities = random.choices(
                [1, 2, 3, 4, 5],
                weights=[0.1, 0.2, 0.4, 0.2, 0.1]
            )[0]

            # Select communities for this node
            selected_communities = random.sample(
                community_ids,
                min(num_communities, len(community_ids))
            )

            node_assignments[node_id] = selected_communities

        # Generate junction records
        for node_id, communities in node_assignments.items():
            for idx, community_id in enumerate(communities):
                # Determine membership strength
                if idx == 0:  # Primary community
                    # 40% core (0.9-1.0)
                    if random.random() < 0.4:
                        strength = random.uniform(0.9, 1.0)
                    # 30% strong (0.7-0.89)
                    elif random.random() < 0.7:
                        strength = random.uniform(0.7, 0.89)
                    # 30% moderate (0.5-0.69)
                    else:
                        strength = random.uniform(0.5, 0.69)
                else:  # Secondary communities
                    # Lower strength for secondary memberships
                    strength = random.uniform(0.5, 0.8)

                junction_record = {
                    "id": self.generate_uuid(),
                    "node_id": node_id,
                    "community_id": community_id,
                    "membership_strength": round(strength, 3),
                    "created_at": self.generate_timestamp(30)
                }

                node_communities.append(junction_record)

                if len(node_communities) >= count:
                    break

            if len(node_communities) >= count:
                break

        # Ensure we have exactly the requested count
        node_communities = node_communities[:count]
        self.node_communities = node_communities

        return node_communities

    def generate_reports(self, count: int = 200) -> List[Dict]:
        """Generate report records (global, community, and node reports)."""
        reports = []

        # Generate 5 global reports
        global_reports = self.generate_global_reports(5)
        reports.extend(global_reports)

        # Generate 150 community reports
        community_reports = self.generate_community_reports(150)
        reports.extend(community_reports)

        # Generate 45 node reports
        node_reports = self.generate_node_reports(45)
        reports.extend(node_reports)

        self.reports = reports[:count]
        return self.reports

    def generate_global_reports(self, count: int) -> List[Dict]:
        """Generate global graph analysis reports."""
        reports = []

        global_themes = [
            {
                "title": "Comprehensive Legal Knowledge Graph Analysis",
                "focus": "Overall graph structure, connectivity patterns, and domain coverage"
            },
            {
                "title": "Constitutional Law Network Topology",
                "focus": "Analysis of constitutional law communities and their interconnections"
            },
            {
                "title": "Citation Network Analysis Across Federal Circuits",
                "focus": "Cross-circuit citation patterns and precedential influence"
            },
            {
                "title": "Temporal Evolution of Legal Doctrine Networks",
                "focus": "How legal communities have evolved over different court eras"
            },
            {
                "title": "Centrality Analysis of Landmark Cases",
                "focus": "Identification of the most influential cases across all legal domains"
            }
        ]

        for idx, theme in enumerate(global_themes[:count]):
            content = self.generate_global_report_content(theme["title"], theme["focus"])

            report = {
                "id": self.generate_uuid(),
                "report_id": f"report_global_{idx+1:03d}",
                "report_type": "global",
                "title": theme["title"],
                "content": content,
                "summary": f"Global analysis of the legal knowledge graph focusing on {theme['focus'].lower()}.",
                "community_id": None,
                "node_id": None,
                "rating": round(random.uniform(8.0, 10.0), 1),
                "metadata": {
                    "generated_at": self.generate_timestamp(7),
                    "analysis_method": "graphrag_global_analysis",
                    "total_nodes": sum(c["node_count"] for c in self.communities),
                    "total_edges": sum(c["edge_count"] for c in self.communities),
                    "total_communities": len(self.communities),
                    "graph_density": round(random.uniform(0.02, 0.08), 4)
                },
                "report_embedding": None,
                "created_at": self.generate_timestamp(30)
            }

            reports.append(report)

        return reports

    def generate_community_reports(self, count: int) -> List[Dict]:
        """Generate community-specific analysis reports."""
        reports = []

        # Select communities to report on
        selected_communities = random.sample(
            self.communities,
            min(count, len(self.communities))
        )

        for idx, community in enumerate(selected_communities):
            content = self.generate_community_report_content(community)

            report = {
                "id": self.generate_uuid(),
                "report_id": f"report_community_{idx+1:03d}",
                "report_type": "community",
                "title": f"{community['title']} Analysis",
                "content": content,
                "summary": f"Detailed analysis of the {community['title']} community with "
                          f"{community['node_count']} entities and {community['edge_count']} relationships.",
                "community_id": community["community_id"],
                "node_id": None,
                "rating": round(random.uniform(6.5, 9.5), 1),
                "metadata": {
                    "generated_at": self.generate_timestamp(7),
                    "analysis_method": "graphrag_community_analysis",
                    "entity_count": community["node_count"],
                    "relationship_count": community["edge_count"],
                    "coherence_score": community["coherence_score"],
                    "community_level": community["level"]
                },
                "report_embedding": None,
                "created_at": self.generate_timestamp(30)
            }

            reports.append(report)

        return reports

    def generate_node_reports(self, count: int) -> List[Dict]:
        """Generate node-specific analysis reports."""
        reports = []

        # Select high-importance nodes
        selected_nodes = random.sample(self.node_ids, min(count, len(self.node_ids)))

        # Node themes for variety
        node_types = {
            "case": ["landmark decision", "precedential value", "circuit split resolution"],
            "statute": ["legislative history", "regulatory implementation", "judicial interpretation"],
            "regulation": ["administrative guidance", "enforcement patterns", "compliance requirements"],
            "judge": ["judicial philosophy", "opinion patterns", "influence metrics"],
            "concept": ["doctrinal evolution", "application contexts", "theoretical foundations"]
        }

        for idx, node_id in enumerate(selected_nodes):
            # Determine node type from ID
            node_type = "case"  # default
            for ntype in node_types.keys():
                if ntype in node_id:
                    node_type = ntype
                    break

            focus = random.choice(node_types.get(node_type, ["general analysis"]))
            content = self.generate_node_report_content(node_id, node_type, focus)

            report = {
                "id": self.generate_uuid(),
                "report_id": f"report_node_{idx+1:03d}",
                "report_type": "node",
                "title": f"Entity Analysis: {node_id.replace('_', ' ').title()}",
                "content": content,
                "summary": f"Detailed analysis of {node_id} focusing on {focus}.",
                "community_id": None,
                "node_id": node_id,
                "rating": round(random.uniform(7.0, 9.8), 1),
                "metadata": {
                    "generated_at": self.generate_timestamp(7),
                    "analysis_method": "graphrag_node_analysis",
                    "node_type": node_type,
                    "analysis_focus": focus,
                    "centrality_score": round(random.uniform(0.1, 0.9), 3),
                    "degree": random.randint(5, 100)
                },
                "report_embedding": None,
                "created_at": self.generate_timestamp(30)
            }

            reports.append(report)

        return reports

    def generate_global_report_content(self, title: str, focus: str) -> str:
        """Generate detailed content for a global report."""
        content_parts = [
            f"# {title}",
            f"\n## Executive Summary",
            f"This comprehensive analysis examines the entire legal knowledge graph, focusing on {focus}. "
            f"The graph encompasses {len(self.communities)} distinct communities representing major areas "
            f"of legal doctrine, with over {sum(c['node_count'] for c in self.communities)} entities "
            f"and {sum(c['edge_count'] for c in self.communities)} relationships.",

            f"\n## Key Findings",
            f"1. **Network Structure**: The graph exhibits a scale-free topology with several highly "
            f"connected hub nodes representing landmark cases and fundamental legal principles.",
            f"2. **Community Detection**: Leiden algorithm identified {len(self.communities)} distinct "
            f"communities with an average coherence score of "
            f"{sum(c['coherence_score'] for c in self.communities) / len(self.communities):.3f}.",
            f"3. **Cross-Domain Connections**: Significant interconnections exist between constitutional law, "
            f"administrative law, and civil rights communities, indicating the interdisciplinary nature "
            f"of modern jurisprudence.",

            f"\n## Detailed Analysis",
            f"The knowledge graph reveals several important patterns in legal doctrine evolution. "
            f"First, constitutional law communities form the backbone of the network, with the "
            f"Second Amendment, Due Process, and Equal Protection communities showing the highest "
            f"centrality scores. These communities serve as bridges connecting various specialized "
            f"areas of law.",

            f"\nSecond, temporal analysis shows increasing complexity in legal relationships over time. "
            f"Cases from the Roberts Court era demonstrate more nuanced connections to historical "
            f"precedent, often citing multiple doctrinal threads simultaneously. This pattern suggests "
            f"an evolution toward more sophisticated legal reasoning that integrates diverse precedential "
            f"sources.",

            f"\nThird, circuit-specific subcommunities reveal regional variations in legal interpretation. "
            f"The Ninth Circuit communities show distinct clustering patterns around immigration and "
            f"environmental law, while Fifth Circuit communities emphasize energy law and maritime issues.",

            f"\n## Implications for Legal Research",
            f"This network structure has significant implications for legal research and practice. "
            f"The high connectivity between certain communities suggests that practitioners should "
            f"consider cross-domain precedents when constructing legal arguments. Additionally, "
            f"the identification of bridge nodes—cases that connect multiple legal domains—provides "
            f"strategic entry points for novel legal theories.",

            f"\n## Recommendations",
            f"1. Leverage highly connected hub cases as starting points for legal research",
            f"2. Explore cross-community connections for innovative legal arguments",
            f"3. Monitor emerging subcommunities for developing areas of law",
            f"4. Use community coherence scores to assess doctrinal stability",

            f"\n## Conclusion",
            f"The legal knowledge graph provides unprecedented insights into the structure and evolution "
            f"of American jurisprudence. By understanding these network patterns, legal professionals "
            f"can more effectively navigate complex legal landscapes and identify strategic opportunities "
            f"for advocacy."
        ]

        return "\n".join(content_parts)

    def generate_community_report_content(self, community: Dict) -> str:
        """Generate detailed content for a community report."""
        topics = community["metadata"].get("primary_topics", [])
        cases = community["metadata"].get("key_cases", [])
        concepts = community["metadata"].get("key_concepts", [])

        content_parts = [
            f"# Community Analysis: {community['title']}",
            f"\n## Overview",
            f"{community['description']}",

            f"\n## Community Statistics",
            f"- **Total Entities**: {community['node_count']}",
            f"- **Total Relationships**: {community['edge_count']}",
            f"- **Coherence Score**: {community['coherence_score']:.3f}",
            f"- **Community Level**: {community['level']}",
            f"- **Detection Method**: {community['metadata']['detection_method']}",
        ]

        if community["parent_community_id"]:
            content_parts.append(f"- **Parent Community**: {community['parent_community_id']}")

        if topics:
            content_parts.extend([
                f"\n## Primary Topics",
                "The following topics form the core of this community:",
                *[f"- **{topic.replace('_', ' ').title()}**: Central to the community's doctrinal framework"
                  for topic in topics]
            ])

        if cases:
            content_parts.extend([
                f"\n## Key Cases",
                "Landmark decisions that anchor this community include:",
                *[f"- **{case}**: Foundational precedent establishing core principles" for case in cases]
            ])

        if concepts:
            content_parts.extend([
                f"\n## Central Concepts",
                "Legal concepts frequently referenced within this community:",
                *[f"- **{concept.title()}**: Essential doctrine applied across multiple cases"
                  for concept in concepts]
            ])

        # Add detailed analysis
        content_parts.extend([
            f"\n## Network Analysis",
            f"This community exhibits a {self._describe_density(community)} network structure. "
            f"The coherence score of {community['coherence_score']:.3f} indicates "
            f"{self._describe_coherence(community['coherence_score'])} internal consistency, "
            f"suggesting that entities within this community share strong thematic and doctrinal connections.",

            f"\nCentrality analysis reveals several hub nodes that serve as critical connection points "
            f"within the community. These high-degree nodes typically represent seminal cases or "
            f"fundamental legal principles that are frequently cited by other entities in the network.",

            f"\n## Evolutionary Patterns",
            f"Temporal analysis of this community shows {self._describe_evolution()}. "
            f"Recent additions to the community indicate {self._describe_trends()}, "
            f"suggesting ongoing doctrinal development in this area of law.",

            f"\n## Practical Applications",
            f"For legal practitioners, this community provides a comprehensive map of related precedents "
            f"and concepts. When researching issues within {community['title'].lower()}, practitioners "
            f"should consider the full network of relationships identified here, as seemingly peripheral "
            f"cases may provide crucial support for legal arguments.",

            f"\n## Cross-Community Connections",
            f"This community maintains significant connections with related legal domains, particularly "
            f"through bridge nodes that span multiple communities. These connections highlight the "
            f"interdisciplinary nature of {community['title'].lower()} and suggest opportunities "
            f"for drawing analogies from adjacent areas of law."
        ])

        return "\n".join(content_parts)

    def generate_node_report_content(self, node_id: str, node_type: str, focus: str) -> str:
        """Generate detailed content for a node report."""
        content_parts = [
            f"# Entity Analysis: {node_id.replace('_', ' ').title()}",
            f"\n## Entity Profile",
            f"- **Type**: {node_type.title()}",
            f"- **Analysis Focus**: {focus.title()}",
            f"- **Network Position**: Central to multiple legal communities",

            f"\n## Executive Summary",
            f"This {node_type} represents a significant node in the legal knowledge graph, "
            f"with particular importance for understanding {focus}. Network analysis reveals "
            f"extensive connections to related entities, establishing this as a key reference "
            f"point for legal research and argumentation.",

            f"\n## Detailed Analysis",
        ]

        if node_type == "case":
            content_parts.extend([
                f"This case has established important precedent in multiple areas of law. "
                f"Its {focus} demonstrates the evolution of judicial reasoning in addressing "
                f"complex constitutional and statutory questions. The decision's impact extends "
                f"beyond its immediate holding, influencing subsequent jurisprudence through "
                f"its analytical framework and doctrinal innovations.",

                f"\n## Precedential Value",
                f"The case has been cited in numerous subsequent decisions, with particular "
                f"influence in shaping the interpretation of related legal principles. Courts "
                f"have relied on this precedent for its clear articulation of the applicable "
                f"legal standard and its practical application to diverse factual scenarios.",

                f"\n## Doctrinal Contributions",
                f"Key doctrinal contributions include the establishment of a multi-factor test "
                f"for evaluating constitutional claims, clarification of the burden of proof "
                f"in specific contexts, and reconciliation of previously conflicting circuit "
                f"court decisions."
            ])
        elif node_type == "statute":
            content_parts.extend([
                f"This statutory provision serves as a cornerstone of the regulatory framework "
                f"governing its subject matter. Analysis of {focus} reveals the statute's "
                f"evolution through legislative amendments and judicial interpretation. "
                f"The provision's network connections demonstrate its integration with related "
                f"statutes and implementing regulations.",

                f"\n## Legislative Intent",
                f"Legislative history indicates that Congress intended this provision to address "
                f"specific gaps in existing law while balancing competing policy interests. "
                f"The statute's language reflects careful drafting to achieve these objectives "
                f"while maintaining flexibility for administrative implementation.",

                f"\n## Judicial Interpretation",
                f"Courts have interpreted this statute in various contexts, developing a body "
                f"of case law that clarifies its scope and application. Key interpretive issues "
                f"include the definition of critical terms, the statute's extraterritorial reach, "
                f"and its interaction with other federal and state laws."
            ])
        elif node_type == "regulation":
            content_parts.extend([
                f"This regulation implements statutory mandates through detailed administrative "
                f"requirements. Examination of {focus} shows how the regulation translates "
                f"broad legislative goals into specific, enforceable standards. The regulation's "
                f"position in the network highlights its role in connecting statutory authority "
                f"with practical compliance obligations.",

                f"\n## Regulatory Framework",
                f"The regulation operates within a complex administrative scheme, interfacing "
                f"with multiple related provisions to create a comprehensive regulatory program. "
                f"Its requirements have been refined through agency guidance and enforcement "
                f"actions, creating a detailed compliance landscape.",

                f"\n## Enforcement Patterns",
                f"Analysis of enforcement data reveals priorities in regulatory implementation, "
                f"with particular emphasis on specific violations that pose the greatest risk "
                f"to regulatory objectives. These patterns inform compliance strategies and "
                f"risk assessment for regulated entities."
            ])
        else:
            content_parts.extend([
                f"This entity plays a crucial role in the legal knowledge network, serving "
                f"as a connection point between various legal domains. Analysis of {focus} "
                f"reveals patterns that inform understanding of broader legal principles and "
                f"their practical application.",

                f"\n## Network Significance",
                f"The entity's position in the graph indicates its importance as a reference "
                f"point for legal analysis. Its connections span multiple communities, suggesting "
                f"broad relevance across different areas of law.",

                f"\n## Analytical Value",
                f"Understanding this entity's role in the legal network provides insights into "
                f"doctrinal development and the interconnected nature of legal principles. "
                f"Its relationships with other entities reveal patterns that can inform legal "
                f"research and argumentation strategies."
            ])

        content_parts.extend([
            f"\n## Network Metrics",
            f"- **Degree Centrality**: {random.uniform(0.1, 0.9):.3f}",
            f"- **Betweenness Centrality**: {random.uniform(0.05, 0.5):.3f}",
            f"- **Closeness Centrality**: {random.uniform(0.3, 0.8):.3f}",
            f"- **PageRank Score**: {random.uniform(0.001, 0.01):.5f}",

            f"\n## Related Entities",
            f"This entity maintains strong connections with related nodes in the network, "
            f"forming clusters of conceptually related legal materials. These relationships "
            f"provide context for understanding the entity's significance and suggest avenues "
            f"for comprehensive legal research.",

            f"\n## Recommendations",
            f"When utilizing this entity in legal research or argumentation:",
            f"1. Consider its network connections for identifying supporting authorities",
            f"2. Examine temporal patterns in its citations for doctrinal trends",
            f"3. Analyze cross-community connections for interdisciplinary insights",
            f"4. Review related entities for comprehensive coverage of legal issues"
        ])

        return "\n".join(content_parts)

    def _describe_density(self, community: Dict) -> str:
        """Describe the density of a community network."""
        density = community["edge_count"] / (community["node_count"] * (community["node_count"] - 1) / 2) \
                  if community["node_count"] > 1 else 0

        if density > 0.3:
            return "highly dense"
        elif density > 0.15:
            return "moderately dense"
        elif density > 0.05:
            return "sparse"
        else:
            return "very sparse"

    def _describe_coherence(self, score: float) -> str:
        """Describe coherence score in qualitative terms."""
        if score >= 0.9:
            return "exceptional"
        elif score >= 0.8:
            return "strong"
        elif score >= 0.7:
            return "good"
        elif score >= 0.6:
            return "moderate"
        else:
            return "weak"

    def _describe_evolution(self) -> str:
        """Generate description of community evolution."""
        patterns = [
            "steady growth in entity count over the past decade",
            "rapid expansion following recent landmark decisions",
            "consolidation around core doctrinal principles",
            "increasing specialization into subcommunities",
            "convergence of previously separate legal threads"
        ]
        return random.choice(patterns)

    def _describe_trends(self) -> str:
        """Generate description of current trends."""
        trends = [
            "increased focus on historical analysis and originalist interpretation",
            "growing emphasis on empirical evidence in judicial decision-making",
            "expansion of doctrine to address technological challenges",
            "refinement of existing standards through circuit court decisions",
            "harmonization of conflicting precedents across jurisdictions"
        ]
        return random.choice(trends)

    def validate_data(self) -> Dict[str, Any]:
        """Validate generated data for consistency and foreign key integrity."""
        validation_results = {
            "communities": {
                "total": len(self.communities),
                "valid": 0,
                "errors": []
            },
            "node_communities": {
                "total": len(self.node_communities),
                "valid": 0,
                "orphaned_nodes": [],
                "orphaned_communities": []
            },
            "reports": {
                "total": len(self.reports),
                "valid": 0,
                "orphaned_communities": [],
                "orphaned_nodes": []
            }
        }

        # Validate communities
        community_ids = set()
        for comm in self.communities:
            if comm["community_id"]:
                community_ids.add(comm["community_id"])
                validation_results["communities"]["valid"] += 1
            else:
                validation_results["communities"]["errors"].append(f"Missing community_id in {comm['id']}")

        # Validate node_communities
        for nc in self.node_communities:
            valid = True

            # Check if node_id exists
            if nc["node_id"] not in self.node_ids:
                validation_results["node_communities"]["orphaned_nodes"].append(nc["node_id"])
                valid = False

            # Check if community_id exists
            if nc["community_id"] not in community_ids:
                validation_results["node_communities"]["orphaned_communities"].append(nc["community_id"])
                valid = False

            if valid:
                validation_results["node_communities"]["valid"] += 1

        # Validate reports
        for report in self.reports:
            valid = True

            # Check community_id if present
            if report["community_id"] and report["community_id"] not in community_ids:
                validation_results["reports"]["orphaned_communities"].append(report["community_id"])
                valid = False

            # Check node_id if present
            if report["node_id"] and report["node_id"] not in self.node_ids:
                validation_results["reports"]["orphaned_nodes"].append(report["node_id"])
                valid = False

            if valid:
                validation_results["reports"]["valid"] += 1

        # Remove duplicates from orphaned lists
        for key in ["node_communities", "reports"]:
            if "orphaned_nodes" in validation_results[key]:
                validation_results[key]["orphaned_nodes"] = list(set(validation_results[key]["orphaned_nodes"]))
            if "orphaned_communities" in validation_results[key]:
                validation_results[key]["orphaned_communities"] = list(set(validation_results[key]["orphaned_communities"]))

        return validation_results

    def save_to_files(self, output_dir: str = "/srv/luris/be/graphrag-service/data") -> Dict[str, str]:
        """Save generated data to JSON files."""
        os.makedirs(output_dir, exist_ok=True)

        files_saved = {}

        # Save communities
        communities_file = os.path.join(output_dir, "communities.json")
        with open(communities_file, "w") as f:
            json.dump(self.communities, f, indent=2)
        files_saved["communities"] = communities_file

        # Save node_communities
        node_communities_file = os.path.join(output_dir, "node_communities.json")
        with open(node_communities_file, "w") as f:
            json.dump(self.node_communities, f, indent=2)
        files_saved["node_communities"] = node_communities_file

        # Save reports
        reports_file = os.path.join(output_dir, "reports.json")
        with open(reports_file, "w") as f:
            json.dump(self.reports, f, indent=2)
        files_saved["reports"] = reports_file

        # Save node_ids for reference
        node_ids_file = os.path.join(output_dir, "node_ids.json")
        with open(node_ids_file, "w") as f:
            json.dump(self.node_ids, f, indent=2)
        files_saved["node_ids"] = node_ids_file

        return files_saved


def main():
    """Main execution function."""
    print("GraphRAG Structure Generator")
    print("=" * 50)
    print()

    # Initialize generator
    generator = GraphStructureGenerator(seed=42)

    # Generate communities
    print("Generating 500 communities...")
    communities = generator.generate_communities(500)
    print(f"✓ Generated {len(communities)} communities")
    print(f"  - Level 0: {sum(1 for c in communities if c['level'] == 0)}")
    print(f"  - Level 1: {sum(1 for c in communities if c['level'] == 1)}")
    print(f"  - Level 2: {sum(1 for c in communities if c['level'] == 2)}")
    print()

    # Generate node_communities
    print("Generating 30,000 node-community relationships...")
    node_communities = generator.generate_node_communities(30000)
    print(f"✓ Generated {len(node_communities)} node-community relationships")
    print()

    # Generate reports
    print("Generating 200 reports...")
    reports = generator.generate_reports(200)
    print(f"✓ Generated {len(reports)} reports")
    print(f"  - Global: {sum(1 for r in reports if r['report_type'] == 'global')}")
    print(f"  - Community: {sum(1 for r in reports if r['report_type'] == 'community')}")
    print(f"  - Node: {sum(1 for r in reports if r['report_type'] == 'node')}")
    print()

    # Validate data
    print("Validating data integrity...")
    validation = generator.validate_data()
    print(f"✓ Validation complete")
    print(f"  - Communities: {validation['communities']['valid']}/{validation['communities']['total']} valid")
    print(f"  - Node-Communities: {validation['node_communities']['valid']}/{validation['node_communities']['total']} valid")
    print(f"  - Reports: {validation['reports']['valid']}/{validation['reports']['total']} valid")

    if validation["node_communities"]["orphaned_nodes"]:
        print(f"  ⚠ Found {len(validation['node_communities']['orphaned_nodes'])} orphaned node references")
    if validation["node_communities"]["orphaned_communities"]:
        print(f"  ⚠ Found {len(validation['node_communities']['orphaned_communities'])} orphaned community references")
    print()

    # Save to files
    print("Saving data to files...")
    files = generator.save_to_files()
    print(f"✓ Data saved to {len(files)} files:")
    for name, path in files.items():
        file_size = os.path.getsize(path) / (1024 * 1024)  # Convert to MB
        print(f"  - {name}: {path} ({file_size:.2f} MB)")
    print()

    # Print sample records
    print("Sample Records:")
    print("=" * 50)

    print("\nSample Community:")
    print(json.dumps(communities[0], indent=2)[:1000] + "...")

    print("\nSample Node-Community Relationship:")
    print(json.dumps(node_communities[0], indent=2))

    print("\nSample Report:")
    print(json.dumps(reports[0], indent=2)[:1000] + "...")

    print("\n" + "=" * 50)
    print("Generation complete!")

    return {
        "files": files,
        "counts": {
            "communities": len(communities),
            "node_communities": len(node_communities),
            "reports": len(reports),
            "nodes": len(generator.node_ids)
        },
        "validation": validation
    }


if __name__ == "__main__":
    result = main()