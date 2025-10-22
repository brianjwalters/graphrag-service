#!/usr/bin/env python3
"""
Generate Synthetic Legal Entities and Relationships for GraphRAG Testing

Creates realistic legal knowledge graph data with:
- 10,000 nodes (entities, concepts, documents, chunks)
- 20,000 edges (relationships between nodes)
- Realistic legal entity types and relationships
- Valid UUID references for client_id and case_id

Output:
- /srv/luris/be/graphrag-service/data/nodes.json
- /srv/luris/be/graphrag-service/data/edges.json
"""

import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

# Legal entity name databases
LANDMARK_CASES = [
    ("Brown v. Board of Education", "347 U.S. 483", "1954", "School segregation unconstitutional"),
    ("Miranda v. Arizona", "384 U.S. 436", "1966", "Rights during custodial interrogation"),
    ("Roe v. Wade", "410 U.S. 113", "1973", "Abortion rights (overruled)"),
    ("Gideon v. Wainwright", "372 U.S. 335", "1963", "Right to counsel in criminal cases"),
    ("Mapp v. Ohio", "367 U.S. 643", "1961", "Exclusionary rule applies to states"),
    ("United States v. Rahimi", "602 U.S. ___", "2024", "Second Amendment and domestic violence"),
    ("New York State Rifle & Pistol Ass'n v. Bruen", "597 U.S. 1", "2022", "Second Amendment carry rights"),
    ("District of Columbia v. Heller", "554 U.S. 570", "2008", "Individual right to bear arms"),
    ("McDonald v. City of Chicago", "561 U.S. 742", "2010", "Second Amendment incorporation"),
    ("Marbury v. Madison", "5 U.S. 137", "1803", "Judicial review established"),
    ("McCulloch v. Maryland", "17 U.S. 316", "1819", "Federal supremacy doctrine"),
    ("Gibbons v. Ogden", "22 U.S. 1", "1824", "Commerce Clause interpretation"),
    ("Dred Scott v. Sandford", "60 U.S. 393", "1857", "Citizenship rights (overruled)"),
    ("Plessy v. Ferguson", "163 U.S. 537", "1896", "Separate but equal (overruled)"),
    ("Korematsu v. United States", "323 U.S. 214", "1944", "Japanese internment"),
    ("Terry v. Ohio", "392 U.S. 1", "1968", "Stop and frisk doctrine"),
    ("Katz v. United States", "389 U.S. 347", "1967", "Fourth Amendment privacy"),
    ("Griswold v. Connecticut", "381 U.S. 479", "1965", "Right to privacy"),
    ("Loving v. Virginia", "388 U.S. 1", "1967", "Interracial marriage rights"),
    ("Brandenburg v. Ohio", "395 U.S. 444", "1969", "Free speech incitement test"),
]

CIRCUIT_CASES = [
    ("United States v. Jones", "9th Cir.", "2023", "Qualified immunity analysis"),
    ("Smith v. State Department", "D.C. Cir.", "2024", "FOIA disclosure requirements"),
    ("Johnson v. City of Los Angeles", "9th Cir.", "2022", "Excessive force claim"),
    ("Garcia v. Immigration Services", "5th Cir.", "2023", "Immigration detention"),
    ("Williams v. School District", "3rd Cir.", "2024", "Title IX compliance"),
    ("Davis v. County Sheriff", "11th Cir.", "2023", "Jail conditions litigation"),
    ("Thompson v. Federal Bureau", "2nd Cir.", "2024", "Whistleblower protection"),
    ("Martinez v. State Prison", "9th Cir.", "2022", "Eighth Amendment medical care"),
    ("Anderson v. City Council", "7th Cir.", "2023", "First Amendment retaliation"),
    ("Wilson v. Police Department", "6th Cir.", "2024", "Fourth Amendment seizure"),
]

STATUTES = [
    ("42 U.S.C. § 1983", "Civil rights under color of law", "federal"),
    ("18 U.S.C. § 242", "Criminal civil rights violations", "federal"),
    ("42 U.S.C. § 2000e", "Title VII employment discrimination", "federal"),
    ("29 U.S.C. § 201", "Fair Labor Standards Act", "federal"),
    ("15 U.S.C. § 1", "Sherman Antitrust Act", "federal"),
    ("42 U.S.C. § 12101", "Americans with Disabilities Act", "federal"),
    ("5 U.S.C. § 552", "Freedom of Information Act", "federal"),
    ("18 U.S.C. § 1001", "False statements to federal agents", "federal"),
    ("26 U.S.C. § 501", "Tax-exempt organizations", "federal"),
    ("17 U.S.C. § 106", "Copyright exclusive rights", "federal"),
    ("RCW 7.105", "Washington Civil Protection Orders", "state"),
    ("RCW 9A.32.060", "Washington Murder in Second Degree", "state"),
    ("Cal. Penal Code § 187", "California Murder statute", "state"),
    ("N.Y. Penal Law § 120.05", "New York Assault statute", "state"),
    ("Tex. Penal Code § 19.02", "Texas Murder statute", "state"),
]

COURTS = [
    ("Supreme Court of the United States", "SCOTUS", "federal", "appellate"),
    ("United States Court of Appeals for the Ninth Circuit", "9th Cir.", "federal", "appellate"),
    ("United States Court of Appeals for the Second Circuit", "2nd Cir.", "federal", "appellate"),
    ("United States Court of Appeals for the Fifth Circuit", "5th Cir.", "federal", "appellate"),
    ("United States District Court for the Southern District of New York", "SDNY", "federal", "district"),
    ("United States District Court for the Northern District of California", "NDCA", "federal", "district"),
    ("United States District Court for the District of Columbia", "DDC", "federal", "district"),
    ("Washington Supreme Court", "Wash.", "state", "appellate"),
    ("California Supreme Court", "Cal.", "state", "appellate"),
    ("New York Court of Appeals", "N.Y.", "state", "appellate"),
    ("Superior Court of Washington for King County", "King County", "state", "trial"),
]

JUDGES = [
    ("Chief Justice John Roberts", "SCOTUS", "conservative"),
    ("Justice Sonia Sotomayor", "SCOTUS", "liberal"),
    ("Justice Ketanji Brown Jackson", "SCOTUS", "liberal"),
    ("Justice Brett Kavanaugh", "SCOTUS", "conservative"),
    ("Justice Amy Coney Barrett", "SCOTUS", "conservative"),
    ("Judge Stephen Reinhardt", "9th Cir.", "liberal"),
    ("Judge Alex Kozinski", "9th Cir.", "libertarian"),
    ("Judge Jed Rakoff", "SDNY", "moderate"),
    ("Judge Shira Scheindlin", "SDNY", "liberal"),
    ("Judge Richard Posner", "7th Cir.", "pragmatist"),
]

PARTIES = [
    ("American Civil Liberties Union", "ACLU", "civil_rights", "plaintiff"),
    ("Electronic Frontier Foundation", "EFF", "digital_rights", "plaintiff"),
    ("National Rifle Association", "NRA", "gun_rights", "plaintiff"),
    ("Department of Justice", "DOJ", "government", "defendant"),
    ("Federal Bureau of Investigation", "FBI", "government", "defendant"),
    ("City of Los Angeles", "LA", "municipality", "defendant"),
    ("New York City Police Department", "NYPD", "law_enforcement", "defendant"),
    ("Amazon.com Inc.", "Amazon", "corporation", "defendant"),
    ("Google LLC", "Google", "corporation", "defendant"),
    ("Individual Plaintiff John Doe", "Doe", "individual", "plaintiff"),
]

LEGAL_CONCEPTS = [
    ("Qualified Immunity", "Shields government officials from liability"),
    ("Due Process", "Fundamental fairness in legal proceedings"),
    ("Equal Protection", "Non-discrimination requirement"),
    ("Strict Scrutiny", "Highest standard of judicial review"),
    ("Intermediate Scrutiny", "Middle tier constitutional review"),
    ("Rational Basis", "Lowest tier constitutional review"),
    ("Stare Decisis", "Precedent binding principle"),
    ("Chevron Deference", "Agency interpretation deference (overruled)"),
    ("Probable Cause", "Standard for search and arrest"),
    ("Reasonable Suspicion", "Standard for Terry stop"),
    ("Exclusionary Rule", "Evidence suppression remedy"),
    ("Fruit of Poisonous Tree", "Derivative evidence exclusion"),
    ("Good Faith Exception", "Exception to exclusionary rule"),
    ("Harmless Error", "Error not affecting outcome"),
    ("Plain Error", "Obvious error requiring reversal"),
]

REGULATIONS = [
    ("29 C.F.R. § 1630", "ADA employment regulations", "EEOC"),
    ("40 C.F.R. § 50", "National ambient air quality standards", "EPA"),
    ("21 C.F.R. § 314", "New drug applications", "FDA"),
    ("17 C.F.R. § 240", "Securities Exchange Act rules", "SEC"),
    ("14 C.F.R. § 91", "General operating and flight rules", "FAA"),
]

RELATIONSHIP_TYPES = [
    ("CITES", "Direct citation relationship", 0.4),
    ("APPLIES", "Statute applied to case", 0.15),
    ("OVERRULES", "Overruling precedent", 0.1),
    ("DISTINGUISHES", "Distinguishing precedent", 0.1),
    ("REPRESENTS", "Attorney-client relationship", 0.1),
    ("RELIES_ON", "Relies on legal concept", 0.05),
    ("INTERPRETS", "Statutory interpretation", 0.03),
    ("CHALLENGES", "Legal challenge", 0.03),
    ("SUPPORTS", "Supporting authority", 0.02),
    ("CONFLICTS_WITH", "Conflicting holdings", 0.02),
]


class LegalEntityGenerator:
    """Generate realistic legal entities and relationships"""

    def __init__(self, num_nodes: int = 10000, num_edges: int = 20000):
        self.num_nodes = num_nodes
        self.num_edges = num_edges
        self.nodes: List[Dict] = []
        self.edges: List[Dict] = []
        self.node_ids: List[str] = []
        self.node_id_map: Dict[str, Dict] = {}

        # Generate fixed client and case UUIDs
        self.client_ids = [str(uuid.uuid4()) for _ in range(10)]
        self.case_ids = [str(uuid.uuid4()) for _ in range(50)]

        # Track node degrees for later calculation
        self.node_degrees: Dict[str, int] = defaultdict(int)

    def generate_node_id(self, entity_type: str, name: str, index: int) -> str:
        """Generate unique node ID"""
        safe_name = name.lower().replace(" ", "_").replace(".", "")[:30]
        return f"entity_{entity_type.lower()}_{safe_name}_{index:04d}"

    def create_case_entity(self, index: int) -> Dict:
        """Create case citation entity"""
        if index < len(LANDMARK_CASES):
            case_name, citation, year, description = LANDMARK_CASES[index]
            importance = "high"
            rank_score = random.uniform(0.8, 1.0)
        elif index < len(LANDMARK_CASES) + len(CIRCUIT_CASES):
            idx = index - len(LANDMARK_CASES)
            case_name, court, year, description = CIRCUIT_CASES[idx]
            citation = f"{random.randint(1, 999)} F.3d {random.randint(1, 1500)}"
            importance = "medium"
            rank_score = random.uniform(0.5, 0.8)
        else:
            case_name = f"Smith v. Jones {random.randint(1, 500)}"
            citation = f"{random.randint(1, 999)} F.3d {random.randint(1, 1500)}"
            year = str(random.randint(2000, 2024))
            description = random.choice([
                "Civil rights claim under 42 USC 1983",
                "Employment discrimination case",
                "First Amendment free speech challenge",
                "Fourth Amendment search and seizure",
                "Contract dispute litigation"
            ])
            importance = "low"
            rank_score = random.uniform(0.1, 0.5)

        node_id = self.generate_node_id("case", case_name, index)

        return {
            "node_id": node_id,
            "node_type": "entity",
            "title": case_name,
            "description": description,
            "source_id": f"doc_case_{node_id}",
            "source_type": "court_opinion",
            "node_degree": 0,  # Will be calculated later
            "community_id": None,
            "rank_score": round(rank_score, 3),
            "metadata": {
                "entity_type": "CASE_CITATION",
                "citation": citation,
                "year": year,
                "jurisdiction": "federal",
                "importance": importance
            },
            "client_id": random.choice(self.client_ids),
            "case_id": random.choice(self.case_ids),
            "embedding": None
        }

    def create_statute_entity(self, index: int) -> Dict:
        """Create statute citation entity"""
        if index < len(STATUTES):
            citation, description, jurisdiction = STATUTES[index]
        else:
            citation = f"{random.randint(1, 50)} U.S.C. § {random.randint(1, 9999)}"
            description = "Federal statute"
            jurisdiction = "federal"

        node_id = self.generate_node_id("statute", citation, index)

        return {
            "node_id": node_id,
            "node_type": "entity",
            "title": citation,
            "description": description,
            "source_id": f"doc_statute_{node_id}",
            "source_type": "statute",
            "node_degree": 0,
            "community_id": None,
            "rank_score": round(random.uniform(0.6, 0.9), 3),
            "metadata": {
                "entity_type": "STATUTE_CITATION",
                "citation": citation,
                "jurisdiction": jurisdiction,
                "importance": "high" if index < 10 else "medium"
            },
            "client_id": random.choice(self.client_ids),
            "case_id": random.choice(self.case_ids),
            "embedding": None
        }

    def create_court_entity(self, index: int) -> Dict:
        """Create court entity"""
        if index < len(COURTS):
            court_name, abbrev, jurisdiction, court_type = COURTS[index]
        else:
            court_name = f"United States District Court District {random.randint(1, 100)}"
            abbrev = f"D{random.randint(1, 100)}"
            jurisdiction = "federal"
            court_type = "district"

        node_id = self.generate_node_id("court", court_name, index)

        return {
            "node_id": node_id,
            "node_type": "entity",
            "title": court_name,
            "description": f"{jurisdiction.title()} {court_type} court",
            "source_id": f"doc_court_{node_id}",
            "source_type": "court_system",
            "node_degree": 0,
            "community_id": None,
            "rank_score": round(random.uniform(0.7, 1.0) if index < 5 else random.uniform(0.3, 0.7), 3),
            "metadata": {
                "entity_type": "COURT",
                "abbreviation": abbrev,
                "jurisdiction": jurisdiction,
                "court_type": court_type
            },
            "client_id": random.choice(self.client_ids),
            "case_id": random.choice(self.case_ids),
            "embedding": None
        }

    def create_judge_entity(self, index: int) -> Dict:
        """Create judge entity"""
        if index < len(JUDGES):
            judge_name, court, ideology = JUDGES[index]
        else:
            judge_name = f"Judge {random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones'])} {random.choice(['A.', 'B.', 'C.'])} {random.choice(['Anderson', 'Martinez', 'Garcia'])}"
            court = random.choice(["9th Cir.", "2nd Cir.", "SDNY", "NDCA"])
            ideology = random.choice(["liberal", "conservative", "moderate"])

        node_id = self.generate_node_id("judge", judge_name, index)

        return {
            "node_id": node_id,
            "node_type": "entity",
            "title": judge_name,
            "description": f"Judge serving on {court}",
            "source_id": f"doc_judge_{node_id}",
            "source_type": "judicial_biography",
            "node_degree": 0,
            "community_id": None,
            "rank_score": round(random.uniform(0.5, 1.0) if "Justice" in judge_name else random.uniform(0.3, 0.7), 3),
            "metadata": {
                "entity_type": "JUDGE",
                "court": court,
                "ideology": ideology
            },
            "client_id": random.choice(self.client_ids),
            "case_id": random.choice(self.case_ids),
            "embedding": None
        }

    def create_party_entity(self, index: int) -> Dict:
        """Create party entity"""
        if index < len(PARTIES):
            party_name, abbrev, party_type, role = PARTIES[index]
        else:
            party_name = f"{random.choice(['Company', 'Corporation', 'Individual', 'Organization'])} {random.randint(1, 1000)}"
            abbrev = f"{party_name[:3].upper()}"
            party_type = random.choice(["individual", "corporation", "government"])
            role = random.choice(["plaintiff", "defendant"])

        node_id = self.generate_node_id("party", party_name, index)

        return {
            "node_id": node_id,
            "node_type": "entity",
            "title": party_name,
            "description": f"{party_type.title()} party in litigation",
            "source_id": f"doc_party_{node_id}",
            "source_type": "party_information",
            "node_degree": 0,
            "community_id": None,
            "rank_score": round(random.uniform(0.3, 0.8), 3),
            "metadata": {
                "entity_type": "PARTY",
                "abbreviation": abbrev,
                "party_type": party_type,
                "role": role
            },
            "client_id": random.choice(self.client_ids),
            "case_id": random.choice(self.case_ids),
            "embedding": None
        }

    def create_concept_entity(self, index: int) -> Dict:
        """Create legal concept entity"""
        if index < len(LEGAL_CONCEPTS):
            concept_name, description = LEGAL_CONCEPTS[index]
        else:
            concept_name = f"Legal Doctrine {random.randint(1, 500)}"
            description = "Legal principle or doctrine"

        node_id = self.generate_node_id("concept", concept_name, index)

        return {
            "node_id": node_id,
            "node_type": "concept",
            "title": concept_name,
            "description": description,
            "source_id": f"doc_concept_{node_id}",
            "source_type": "legal_treatise",
            "node_degree": 0,
            "community_id": None,
            "rank_score": round(random.uniform(0.4, 0.9), 3),
            "metadata": {
                "entity_type": "LEGAL_CONCEPT",
                "category": random.choice(["constitutional", "procedural", "evidentiary", "substantive"])
            },
            "client_id": random.choice(self.client_ids),
            "case_id": random.choice(self.case_ids),
            "embedding": None
        }

    def create_regulation_entity(self, index: int) -> Dict:
        """Create regulation citation entity"""
        if index < len(REGULATIONS):
            citation, description, agency = REGULATIONS[index]
        else:
            citation = f"{random.randint(1, 50)} C.F.R. § {random.randint(1, 999)}"
            description = "Federal regulation"
            agency = random.choice(["EPA", "FDA", "SEC", "FCC"])

        node_id = self.generate_node_id("regulation", citation, index)

        return {
            "node_id": node_id,
            "node_type": "entity",
            "title": citation,
            "description": description,
            "source_id": f"doc_regulation_{node_id}",
            "source_type": "regulation",
            "node_degree": 0,
            "community_id": None,
            "rank_score": round(random.uniform(0.4, 0.7), 3),
            "metadata": {
                "entity_type": "REGULATION_CITATION",
                "citation": citation,
                "agency": agency,
                "jurisdiction": "federal"
            },
            "client_id": random.choice(self.client_ids),
            "case_id": random.choice(self.case_ids),
            "embedding": None
        }

    def create_document_entity(self, index: int) -> Dict:
        """Create document entity"""
        doc_types = ["motion", "brief", "opinion", "order", "complaint"]
        doc_type = random.choice(doc_types)

        node_id = self.generate_node_id("document", f"{doc_type}_{index}", index)

        return {
            "node_id": node_id,
            "node_type": "document",
            "title": f"{doc_type.title()} {index}",
            "description": f"Legal document of type {doc_type}",
            "source_id": f"doc_{node_id}",
            "source_type": doc_type,
            "node_degree": 0,
            "community_id": None,
            "rank_score": round(random.uniform(0.1, 0.5), 3),
            "metadata": {
                "document_type": doc_type,
                "page_count": random.randint(5, 200)
            },
            "client_id": random.choice(self.client_ids),
            "case_id": random.choice(self.case_ids),
            "embedding": None
        }

    def create_chunk_entity(self, index: int) -> Dict:
        """Create chunk entity"""
        node_id = self.generate_node_id("chunk", f"chunk_{index}", index)

        return {
            "node_id": node_id,
            "node_type": "chunk",
            "title": f"Document Chunk {index}",
            "description": "Text chunk from legal document",
            "source_id": f"doc_chunk_source_{random.randint(1, 500)}",
            "source_type": "document_chunk",
            "node_degree": 0,
            "community_id": None,
            "rank_score": round(random.uniform(0.05, 0.3), 3),
            "metadata": {
                "chunk_size": random.randint(500, 2000),
                "position": random.randint(0, 100)
            },
            "client_id": random.choice(self.client_ids),
            "case_id": random.choice(self.case_ids),
            "embedding": None
        }

    def generate_nodes(self):
        """Generate all nodes with realistic distribution"""
        print(f"Generating {self.num_nodes} nodes...")

        # Calculate entity counts based on distribution
        entity_count = int(self.num_nodes * 0.80)  # 80% entities
        concept_count = int(self.num_nodes * 0.10)  # 10% concepts
        document_count = int(self.num_nodes * 0.05)  # 5% documents
        chunk_count = self.num_nodes - entity_count - concept_count - document_count  # Remaining as chunks

        # Entity type distribution (within the 80% entity allocation)
        case_count = int(entity_count * 0.30)
        statute_count = int(entity_count * 0.20)
        court_count = int(entity_count * 0.15)
        judge_count = int(entity_count * 0.10)
        party_count = int(entity_count * 0.10)
        regulation_count = entity_count - case_count - statute_count - court_count - judge_count - party_count

        node_index = 0

        # Generate entities
        for i in range(case_count):
            node = self.create_case_entity(i)
            self.nodes.append(node)
            self.node_ids.append(node["node_id"])
            self.node_id_map[node["node_id"]] = node
            node_index += 1
            if node_index % 1000 == 0:
                print(f"  Generated {node_index}/{self.num_nodes} nodes...")

        for i in range(statute_count):
            node = self.create_statute_entity(i)
            self.nodes.append(node)
            self.node_ids.append(node["node_id"])
            self.node_id_map[node["node_id"]] = node
            node_index += 1
            if node_index % 1000 == 0:
                print(f"  Generated {node_index}/{self.num_nodes} nodes...")

        for i in range(court_count):
            node = self.create_court_entity(i)
            self.nodes.append(node)
            self.node_ids.append(node["node_id"])
            self.node_id_map[node["node_id"]] = node
            node_index += 1
            if node_index % 1000 == 0:
                print(f"  Generated {node_index}/{self.num_nodes} nodes...")

        for i in range(judge_count):
            node = self.create_judge_entity(i)
            self.nodes.append(node)
            self.node_ids.append(node["node_id"])
            self.node_id_map[node["node_id"]] = node
            node_index += 1
            if node_index % 1000 == 0:
                print(f"  Generated {node_index}/{self.num_nodes} nodes...")

        for i in range(party_count):
            node = self.create_party_entity(i)
            self.nodes.append(node)
            self.node_ids.append(node["node_id"])
            self.node_id_map[node["node_id"]] = node
            node_index += 1
            if node_index % 1000 == 0:
                print(f"  Generated {node_index}/{self.num_nodes} nodes...")

        for i in range(regulation_count):
            node = self.create_regulation_entity(i)
            self.nodes.append(node)
            self.node_ids.append(node["node_id"])
            self.node_id_map[node["node_id"]] = node
            node_index += 1
            if node_index % 1000 == 0:
                print(f"  Generated {node_index}/{self.num_nodes} nodes...")

        # Generate concepts
        for i in range(concept_count):
            node = self.create_concept_entity(i)
            self.nodes.append(node)
            self.node_ids.append(node["node_id"])
            self.node_id_map[node["node_id"]] = node
            node_index += 1
            if node_index % 1000 == 0:
                print(f"  Generated {node_index}/{self.num_nodes} nodes...")

        # Generate documents
        for i in range(document_count):
            node = self.create_document_entity(i)
            self.nodes.append(node)
            self.node_ids.append(node["node_id"])
            self.node_id_map[node["node_id"]] = node
            node_index += 1
            if node_index % 1000 == 0:
                print(f"  Generated {node_index}/{self.num_nodes} nodes...")

        # Generate chunks
        for i in range(chunk_count):
            node = self.create_chunk_entity(i)
            self.nodes.append(node)
            self.node_ids.append(node["node_id"])
            self.node_id_map[node["node_id"]] = node
            node_index += 1
            if node_index % 1000 == 0:
                print(f"  Generated {node_index}/{self.num_nodes} nodes...")

        print(f"✓ Generated {len(self.nodes)} nodes")
        print(f"  - Cases: {case_count}")
        print(f"  - Statutes: {statute_count}")
        print(f"  - Courts: {court_count}")
        print(f"  - Judges: {judge_count}")
        print(f"  - Parties: {party_count}")
        print(f"  - Regulations: {regulation_count}")
        print(f"  - Concepts: {concept_count}")
        print(f"  - Documents: {document_count}")
        print(f"  - Chunks: {chunk_count}")

    def generate_edges(self):
        """Generate realistic legal relationships"""
        print(f"\nGenerating {self.num_edges} edges...")

        base_time = datetime.now(timezone.utc) - timedelta(days=365)

        for i in range(self.num_edges):
            # Select relationship type based on distribution
            rand = random.random()
            cumulative = 0.0
            selected_rel_type = RELATIONSHIP_TYPES[0][0]

            for rel_type, description, probability in RELATIONSHIP_TYPES:
                cumulative += probability
                if rand <= cumulative:
                    selected_rel_type = rel_type
                    break

            # Select source and target nodes
            source_node_id = random.choice(self.node_ids)
            target_node_id = random.choice(self.node_ids)

            # Avoid self-loops
            while target_node_id == source_node_id:
                target_node_id = random.choice(self.node_ids)

            source_node = self.node_id_map[source_node_id]
            target_node = self.node_id_map[target_node_id]

            # Generate realistic relationship based on node types
            relationship_type = self._determine_relationship_type(
                source_node, target_node, selected_rel_type
            )

            # Generate edge data
            edge_id = f"edge_{relationship_type.lower()}_{i:05d}"

            # Calculate timestamps
            created_time = base_time + timedelta(days=random.randint(0, 365))
            updated_time = created_time + timedelta(days=random.randint(0, 30))

            edge = {
                "edge_id": edge_id,
                "source_node_id": source_node_id,
                "target_node_id": target_node_id,
                "relationship_type": relationship_type,
                "weight": round(random.uniform(0.1, 1.0), 2),
                "evidence": self._generate_evidence(relationship_type, source_node, target_node),
                "confidence_score": round(random.uniform(0.5, 1.0), 2),
                "extraction_method": random.choice(["pattern_based", "llm", "co_occurrence", "manual"]),
                "metadata": {
                    "context": self._generate_context(relationship_type),
                    "document_section": random.choice(["Opinion", "Dissent", "Analysis", "Background"])
                },
                "client_id": source_node["client_id"],  # Match source node's client
                "case_id": source_node["case_id"],  # Match source node's case
                "created_at": created_time.isoformat() + "Z",
                "updated_at": updated_time.isoformat() + "Z"
            }

            self.edges.append(edge)

            # Update node degrees
            self.node_degrees[source_node_id] += 1
            self.node_degrees[target_node_id] += 1

            if (i + 1) % 1000 == 0:
                print(f"  Generated {i + 1}/{self.num_edges} edges...")

        print(f"✓ Generated {len(self.edges)} edges")

        # Count relationship types
        rel_counts = defaultdict(int)
        for edge in self.edges:
            rel_counts[edge["relationship_type"]] += 1

        print("\nRelationship Type Distribution:")
        for rel_type, count in sorted(rel_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {rel_type}: {count} ({count/len(self.edges)*100:.1f}%)")

    def _determine_relationship_type(self, source: Dict, target: Dict, preferred: str) -> str:
        """Determine realistic relationship type based on node types"""
        source_type = source["metadata"].get("entity_type", source["node_type"])
        target_type = target["metadata"].get("entity_type", target["node_type"])

        # Case-to-case relationships
        if source_type == "CASE_CITATION" and target_type == "CASE_CITATION":
            return random.choice(["CITES", "OVERRULES", "DISTINGUISHES", "SUPPORTS"])

        # Case-to-statute relationships
        if source_type == "CASE_CITATION" and target_type == "STATUTE_CITATION":
            return random.choice(["APPLIES", "INTERPRETS", "CHALLENGES"])

        # Case-to-concept relationships
        if source_type == "CASE_CITATION" and target_type == "LEGAL_CONCEPT":
            return random.choice(["RELIES_ON", "DEFINES", "APPLIES"])

        # Party-to-case relationships
        if source_type == "PARTY" and target_type == "CASE_CITATION":
            return "REPRESENTS"

        # Default to preferred type
        return preferred

    def _generate_evidence(self, rel_type: str, source: Dict, target: Dict) -> str:
        """Generate realistic evidence text"""
        templates = {
            "CITES": f"The Court in {source['title']} cited {target['title']} for the proposition that...",
            "OVERRULES": f"{source['title']} explicitly overruled {target['title']}, holding that...",
            "DISTINGUISHES": f"The Court distinguished {target['title']} on the grounds that...",
            "APPLIES": f"The Court applied {target['title']} to the facts of this case...",
            "REPRESENTS": f"{source['title']} represents the interests of parties in {target['title']}...",
            "RELIES_ON": f"The analysis relies on the principle of {target['title']}...",
            "INTERPRETS": f"The Court interpreted {target['title']} to mean...",
        }

        return templates.get(rel_type, f"Relationship between {source['title']} and {target['title']}")

    def _generate_context(self, rel_type: str) -> str:
        """Generate realistic context"""
        contexts = {
            "CITES": random.choice(["Constitutional analysis", "Statutory interpretation", "Precedent review"]),
            "OVERRULES": "Precedent reconsideration",
            "DISTINGUISHES": "Factual differentiation",
            "APPLIES": random.choice(["Statutory application", "Constitutional test"]),
            "REPRESENTS": "Party representation",
            "RELIES_ON": random.choice(["Legal doctrine", "Constitutional principle"]),
        }

        return contexts.get(rel_type, "General legal analysis")

    def update_node_degrees(self):
        """Update node_degree field in all nodes"""
        print("\nUpdating node degrees...")

        for node in self.nodes:
            node["node_degree"] = self.node_degrees.get(node["node_id"], 0)

        # Calculate statistics
        degrees = [node["node_degree"] for node in self.nodes]
        avg_degree = sum(degrees) / len(degrees) if degrees else 0
        max_degree = max(degrees) if degrees else 0

        print(f"✓ Updated node degrees")
        print(f"  - Average degree: {avg_degree:.2f}")
        print(f"  - Max degree: {max_degree}")
        print(f"  - Nodes with 0 degree: {sum(1 for d in degrees if d == 0)}")

    def save_data(self, output_dir: str = "/srv/luris/be/graphrag-service/data"):
        """Save nodes and edges to JSON files"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        nodes_file = output_path / "nodes.json"
        edges_file = output_path / "edges.json"

        print(f"\nSaving data to {output_dir}...")

        with open(nodes_file, 'w') as f:
            json.dump(self.nodes, f, indent=2)

        with open(edges_file, 'w') as f:
            json.dump(self.edges, f, indent=2)

        print(f"✓ Saved {len(self.nodes)} nodes to {nodes_file}")
        print(f"✓ Saved {len(self.edges)} edges to {edges_file}")

        return str(nodes_file), str(edges_file)

    def generate_summary(self) -> Dict:
        """Generate summary statistics"""
        # Count entity types
        entity_types = defaultdict(int)
        node_types = defaultdict(int)

        for node in self.nodes:
            node_types[node["node_type"]] += 1
            entity_type = node["metadata"].get("entity_type", "unknown")
            entity_types[entity_type] += 1

        # Count relationship types
        rel_types = defaultdict(int)
        for edge in self.edges:
            rel_types[edge["relationship_type"]] += 1

        # Sample records
        sample_node = self.nodes[0] if self.nodes else {}
        sample_edge = self.edges[0] if self.edges else {}

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_type_distribution": dict(node_types),
            "entity_type_distribution": dict(entity_types),
            "relationship_type_distribution": dict(rel_types),
            "client_count": len(self.client_ids),
            "case_count": len(self.case_ids),
            "sample_node": sample_node,
            "sample_edge": sample_edge
        }


def main():
    """Main execution function"""
    print("=" * 80)
    print("Legal Entities & Relationships Generator for GraphRAG Testing")
    print("=" * 80)

    # Initialize generator
    generator = LegalEntityGenerator(num_nodes=10000, num_edges=20000)

    # Generate data
    generator.generate_nodes()
    generator.generate_edges()
    generator.update_node_degrees()

    # Save data
    nodes_file, edges_file = generator.save_data()

    # Generate and display summary
    print("\n" + "=" * 80)
    print("GENERATION SUMMARY")
    print("=" * 80)

    summary = generator.generate_summary()

    print(f"\nTotal Statistics:")
    print(f"  - Total Nodes: {summary['total_nodes']}")
    print(f"  - Total Edges: {summary['total_edges']}")
    print(f"  - Unique Clients: {summary['client_count']}")
    print(f"  - Unique Cases: {summary['case_count']}")

    print(f"\nNode Type Distribution:")
    for node_type, count in summary['node_type_distribution'].items():
        print(f"  - {node_type}: {count} ({count/summary['total_nodes']*100:.1f}%)")

    print(f"\nEntity Type Distribution:")
    for entity_type, count in sorted(summary['entity_type_distribution'].items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  - {entity_type}: {count}")

    print(f"\nRelationship Type Distribution:")
    for rel_type, count in sorted(summary['relationship_type_distribution'].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {rel_type}: {count} ({count/summary['total_edges']*100:.1f}%)")

    print(f"\nOutput Files:")
    print(f"  - Nodes: {nodes_file}")
    print(f"  - Edges: {edges_file}")

    print("\n" + "=" * 80)
    print("Sample Node:")
    print("=" * 80)
    print(json.dumps(summary['sample_node'], indent=2))

    print("\n" + "=" * 80)
    print("Sample Edge:")
    print("=" * 80)
    print(json.dumps(summary['sample_edge'], indent=2))

    print("\n" + "=" * 80)
    print("✓ Generation Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
