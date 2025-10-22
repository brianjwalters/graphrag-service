#!/usr/bin/env python3
"""
Generate synthetic database records for GraphRAG service tables.

Generates data for:
- graph.document_registry (100 rows)
- graph.chunks (25,000 rows)
- graph.enhanced_contextual_chunks (25,000 rows)
- graph.text_units (25,000 rows)

Usage:
    source venv/bin/activate
    python scripts/generate_database_records.py
"""

import json
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import sys


class LegalContentGenerator:
    """Generate realistic legal document content."""

    COURTS = [
        "Supreme Court of the United States",
        "United States Court of Appeals for the Fifth Circuit",
        "United States Court of Appeals for the Ninth Circuit",
        "United States District Court for the Southern District of New York",
        "United States District Court for the Central District of California",
        "Texas Supreme Court",
        "California Supreme Court",
        "New York Court of Appeals"
    ]

    CASE_NAMES = [
        "United States v. Rahimi", "Brown v. Board of Education",
        "Miranda v. Arizona", "Roe v. Wade", "Marbury v. Madison",
        "Gideon v. Wainwright", "Terry v. Ohio", "New York Times v. Sullivan",
        "Citizens United v. FEC", "District of Columbia v. Heller",
        "McDonald v. City of Chicago", "Obergefell v. Hodges",
        "Mapp v. Ohio", "Griswold v. Connecticut", "Katz v. United States",
        "Brandenburg v. Ohio", "Tinker v. Des Moines", "Texas v. Johnson",
        "United States v. Nixon", "Bush v. Gore"
    ]

    LEGAL_TOPICS = [
        "Second Amendment", "Fourth Amendment", "First Amendment",
        "Due Process", "Equal Protection", "Commerce Clause",
        "Supremacy Clause", "Establishment Clause", "Free Exercise Clause",
        "Search and Seizure", "Miranda Rights", "Habeas Corpus",
        "Qualified Immunity", "Strict Scrutiny", "Rational Basis Review"
    ]

    LEGAL_CONTENT_TEMPLATES = [
        "The {amendment} provides: '{quote}' This case concerns the interpretation of constitutional protections in the context of {topic}. The Court must determine whether the challenged law violates fundamental rights.",
        "In analyzing this {topic} claim, we apply the framework established in {precedent}. The constitutional inquiry requires examining both the text and the historical understanding at the time of ratification.",
        "The government argues that {topic} permits reasonable regulations when public safety concerns are paramount. However, the respondent contends that such restrictions impermissibly burden core constitutional rights.",
        "This Court has long held that {topic} is subject to judicial review under the {standard} standard. The question presented is whether the lower court properly applied this framework.",
        "The historical record demonstrates that at the Founding, {topic} was understood to encompass protections against governmental overreach. Modern applications must remain faithful to this original understanding.",
        "Applying the principles articulated in {precedent}, we conclude that the challenged regulation is constitutionally permissible. The government has demonstrated a compelling interest in {topic}.",
        "The dissent argues that {topic} requires a different analytical approach. We respectfully disagree, finding that the established precedent provides clear guidance for resolving this matter.",
        "The {amendment} does not establish an unlimited right. Rather, it must be balanced against legitimate governmental interests in {topic}, particularly where public safety is at stake."
    ]

    AMENDMENTS = [
        "First Amendment", "Second Amendment", "Fourth Amendment",
        "Fifth Amendment", "Sixth Amendment", "Eighth Amendment",
        "Tenth Amendment", "Fourteenth Amendment"
    ]

    CONSTITUTIONAL_QUOTES = [
        "A well regulated Militia, being necessary to the security of a free State, the right of the people to keep and bear Arms, shall not be infringed.",
        "The right of the people to be secure in their persons, houses, papers, and effects, against unreasonable searches and seizures, shall not be violated.",
        "Congress shall make no law respecting an establishment of religion, or prohibiting the free exercise thereof.",
        "No person shall be deprived of life, liberty, or property, without due process of law.",
        "In all criminal prosecutions, the accused shall enjoy the right to a speedy and public trial.",
        "Excessive bail shall not be required, nor excessive fines imposed, nor cruel and unusual punishments inflicted."
    ]

    STANDARDS = [
        "strict scrutiny", "intermediate scrutiny", "rational basis review",
        "heightened scrutiny", "substantial relationship test"
    ]

    def generate_chunk_content(self, seed: int) -> str:
        """Generate realistic legal content for a chunk."""
        random.seed(seed)

        template = random.choice(self.LEGAL_CONTENT_TEMPLATES)
        content = template.format(
            amendment=random.choice(self.AMENDMENTS),
            quote=random.choice(self.CONSTITUTIONAL_QUOTES),
            topic=random.choice(self.LEGAL_TOPICS),
            precedent=random.choice(self.CASE_NAMES),
            standard=random.choice(self.STANDARDS)
        )

        # Add additional context to reach 500-1000 characters
        if len(content) < 500:
            content += f" The petitioner raises several constitutional challenges to the disputed law. " \
                      f"First, the law allegedly infringes upon fundamental rights protected by the {random.choice(self.AMENDMENTS)}. " \
                      f"Second, the statutory scheme lacks sufficient procedural safeguards. " \
                      f"Third, the legislative history suggests an improper purpose. " \
                      f"The government responds that the law serves compelling interests and is narrowly tailored. " \
                      f"The lower courts divided on these questions, creating a circuit split requiring resolution."

        return content


class DatabaseRecordGenerator:
    """Generate synthetic database records for GraphRAG tables."""

    def __init__(self, output_dir: str = "/srv/luris/be/graphrag-service/data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.content_generator = LegalContentGenerator()

        # Storage for generated IDs
        self.document_ids = []
        self.chunk_ids = []
        self.entity_ids = []
        self.relationship_ids = []

        # Pre-generate some entity and relationship IDs
        self._generate_entity_relationship_ids()

    def _generate_entity_relationship_ids(self):
        """Pre-generate entity and relationship IDs for text_units."""
        entity_types = ["case", "person", "court", "statute", "amendment", "concept"]
        for i in range(500):
            entity_type = random.choice(entity_types)
            self.entity_ids.append(f"entity_{entity_type}_{str(uuid.uuid4())[:8]}")

        for i in range(1000):
            rel_type = random.choice(["cites", "applies", "overrules", "distinguishes"])
            self.relationship_ids.append(f"edge_{rel_type}_{str(uuid.uuid4())[:8]}")

    def generate_document_registry(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate graph.document_registry records."""
        print(f"Generating {count} document_registry records...")

        documents = []
        document_types = ["case", "statute", "regulation", "brief", "motion"]
        source_schemas = ["law", "client"]
        statuses = ["completed", "pending", "failed"]
        processing_statuses = ["graph_completed", "graph_pending"]

        for i in range(count):
            doc_id = f"doc_{random.choice(self.content_generator.CASE_NAMES).lower().replace(' ', '_').replace('.', '')}_{str(uuid.uuid4())[:8]}"
            self.document_ids.append(doc_id)

            source_schema = random.choices(source_schemas, weights=[0.7, 0.3])[0]
            status = random.choices(statuses, weights=[0.8, 0.15, 0.05])[0]

            created_at = datetime.now() - timedelta(days=random.randint(1, 365))
            updated_at = created_at + timedelta(hours=random.randint(1, 48))

            document = {
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "title": random.choice(self.content_generator.CASE_NAMES),
                "document_type": random.choice(document_types),
                "source_schema": source_schema,
                "status": status,
                "metadata": {
                    "court": random.choice(self.content_generator.COURTS),
                    "year": str(random.randint(1950, 2024)),
                    "citation": f"{random.randint(100, 999)} U.S. {random.randint(1, 999)}",
                    "page_count": random.randint(10, 150)
                },
                "client_id": str(uuid.uuid4()) if source_schema == "client" else None,
                "case_id": str(uuid.uuid4()) if source_schema == "law" else None,
                "processing_status": random.choice(processing_statuses),
                "created_at": created_at.isoformat() + "Z",
                "updated_at": updated_at.isoformat() + "Z"
            }

            documents.append(document)

            if (i + 1) % 25 == 0:
                print(f"  Generated {i + 1}/{count} documents...")

        print(f"✓ Completed document_registry generation: {len(documents)} records")
        return documents

    def generate_chunks(self, documents: List[Dict[str, Any]], chunks_per_doc: int = 250) -> List[Dict[str, Any]]:
        """Generate graph.chunks records."""
        total_chunks = len(documents) * chunks_per_doc
        print(f"Generating {total_chunks} chunk records ({chunks_per_doc} per document)...")

        chunks = []
        content_types = ["text", "heading", "list", "table", "code"]
        chunk_methods = ["simple", "semantic", "legal_boundary"]

        for doc_idx, document in enumerate(documents):
            doc_id = document["document_id"]

            for chunk_idx in range(chunks_per_doc):
                chunk_id = f"chunk_{doc_id}_{chunk_idx:04d}"
                self.chunk_ids.append(chunk_id)

                # Generate content
                seed = hash(f"{doc_id}_{chunk_idx}") % (2**31)
                content = self.content_generator.generate_chunk_content(seed)

                # Calculate metrics
                token_count = len(content.split())
                chunk_size = len(content.encode('utf-8'))
                overlap_size = random.randint(0, 200)

                # Generate context
                context_before = f"...previous context from chunk {chunk_idx-1}..." if chunk_idx > 0 else None
                context_after = f"...following context from chunk {chunk_idx+1}..." if chunk_idx < chunks_per_doc - 1 else None

                chunk = {
                    "id": str(uuid.uuid4()),
                    "chunk_id": chunk_id,
                    "document_id": doc_id,
                    "chunk_index": chunk_idx,
                    "content": content,
                    "content_type": random.choices(content_types, weights=[0.7, 0.1, 0.1, 0.05, 0.05])[0],
                    "token_count": token_count,
                    "chunk_size": chunk_size,
                    "overlap_size": overlap_size,
                    "chunk_method": random.choice(chunk_methods),
                    "parent_chunk_id": None,  # Could be set for hierarchical chunks
                    "context_before": context_before,
                    "context_after": context_after,
                    "metadata": {
                        "section": random.choice(["Opinion of the Court", "Dissent", "Concurrence", "Facts", "Analysis"]),
                        "page_number": (chunk_idx // 10) + 1
                    },
                    "content_embedding": None,  # Added by embeddings agent
                    "created_at": datetime.now().isoformat() + "Z"
                }

                chunks.append(chunk)

            if (doc_idx + 1) % 10 == 0:
                print(f"  Generated chunks for {doc_idx + 1}/{len(documents)} documents...")

        print(f"✓ Completed chunks generation: {len(chunks)} records")
        return chunks

    def generate_enhanced_contextual_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate graph.enhanced_contextual_chunks records."""
        print(f"Generating {len(chunks)} enhanced_contextual_chunks records...")

        enhanced_chunks = []

        for idx, chunk in enumerate(chunks):
            # Generate contextualized content
            doc_title = random.choice(self.content_generator.CASE_NAMES)
            context_topic = random.choice(self.content_generator.LEGAL_TOPICS)
            contextualized_content = f"Document: {doc_title} ({random.randint(1950, 2024)}). Context: {context_topic} analysis. {chunk['content']}"

            # Generate client_id as TEXT (not UUID!)
            client_id = f"client-text-{random.randint(1, 50)}"

            enhanced_chunk = {
                "id": str(uuid.uuid4()),
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "contextualized_content": contextualized_content,
                "chunk_size": len(contextualized_content.encode('utf-8')),
                "vector": None,  # Added by embeddings agent (2048-dim)
                "client_id": client_id,  # TEXT format, not UUID!
                "metadata": {
                    "document_title": doc_title,
                    "contextualization_method": "llm",
                    "original_chunk_size": chunk["chunk_size"]
                },
                "created_at": datetime.now().isoformat() + "Z",
                "updated_at": datetime.now().isoformat() + "Z"
            }

            enhanced_chunks.append(enhanced_chunk)

            if (idx + 1) % 5000 == 0:
                print(f"  Generated {idx + 1}/{len(chunks)} enhanced chunks...")

        print(f"✓ Completed enhanced_contextual_chunks generation: {len(enhanced_chunks)} records")
        return enhanced_chunks

    def generate_text_units(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate graph.text_units records."""
        print(f"Generating {len(chunks)} text_units records...")

        text_units = []

        for idx, chunk in enumerate(chunks):
            text_unit_id = f"tu_{chunk['chunk_id']}"

            # Link to entities and relationships
            num_entities = random.randint(3, 12)
            num_relationships = random.randint(2, 8)
            num_covariates = random.randint(0, 3)

            entity_ids = random.sample(self.entity_ids, min(num_entities, len(self.entity_ids)))
            relationship_ids = random.sample(self.relationship_ids, min(num_relationships, len(self.relationship_ids)))
            covariate_ids = [f"covariate_{str(uuid.uuid4())[:8]}" for _ in range(num_covariates)]

            text_unit = {
                "id": str(uuid.uuid4()),
                "text_unit_id": text_unit_id,
                "chunk_id": chunk["chunk_id"],
                "text": chunk["content"],
                "n_tokens": chunk["token_count"],
                "document_ids": [chunk["document_id"]],  # TEXT ARRAY
                "entity_ids": entity_ids,  # TEXT ARRAY
                "relationship_ids": relationship_ids,  # TEXT ARRAY
                "covariate_ids": covariate_ids,  # TEXT ARRAY
                "metadata": {
                    "extraction_method": "graphrag",
                    "entity_count": len(entity_ids),
                    "relationship_count": len(relationship_ids)
                },
                "created_at": datetime.now().isoformat() + "Z"
            }

            text_units.append(text_unit)

            if (idx + 1) % 5000 == 0:
                print(f"  Generated {idx + 1}/{len(chunks)} text units...")

        print(f"✓ Completed text_units generation: {len(text_units)} records")
        return text_units

    def save_to_json(self, data: List[Dict[str, Any]], filename: str) -> Path:
        """Save data to JSON file."""
        filepath = self.output_dir / filename
        print(f"Saving {len(data)} records to {filepath}...")

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        file_size_mb = filepath.stat().st_size / (1024 * 1024)
        print(f"✓ Saved {filepath} ({file_size_mb:.2f} MB)")
        return filepath

    def validate_data(self, documents: List[Dict], chunks: List[Dict],
                     enhanced_chunks: List[Dict], text_units: List[Dict]) -> Dict[str, Any]:
        """Validate generated data integrity."""
        print("\nValidating generated data...")

        validation = {
            "document_registry": {
                "count": len(documents),
                "unique_document_ids": len(set(d["document_id"] for d in documents)),
                "law_schema_count": sum(1 for d in documents if d["source_schema"] == "law"),
                "client_schema_count": sum(1 for d in documents if d["source_schema"] == "client"),
                "completed_status": sum(1 for d in documents if d["status"] == "completed")
            },
            "chunks": {
                "count": len(chunks),
                "unique_chunk_ids": len(set(c["chunk_id"] for c in chunks)),
                "avg_token_count": sum(c["token_count"] for c in chunks) / len(chunks),
                "avg_chunk_size": sum(c["chunk_size"] for c in chunks) / len(chunks),
                "text_content_type": sum(1 for c in chunks if c["content_type"] == "text")
            },
            "enhanced_contextual_chunks": {
                "count": len(enhanced_chunks),
                "unique_chunk_ids": len(set(ec["chunk_id"] for ec in enhanced_chunks)),
                "avg_contextualized_size": sum(ec["chunk_size"] for ec in enhanced_chunks) / len(enhanced_chunks),
                "client_id_format_valid": all(isinstance(ec["client_id"], str) and ec["client_id"].startswith("client-text-")
                                              for ec in enhanced_chunks)
            },
            "text_units": {
                "count": len(text_units),
                "unique_text_unit_ids": len(set(tu["text_unit_id"] for tu in text_units)),
                "avg_entities_per_unit": sum(len(tu["entity_ids"]) for tu in text_units) / len(text_units),
                "avg_relationships_per_unit": sum(len(tu["relationship_ids"]) for tu in text_units) / len(text_units),
                "total_entity_links": sum(len(tu["entity_ids"]) for tu in text_units),
                "total_relationship_links": sum(len(tu["relationship_ids"]) for tu in text_units)
            },
            "data_integrity": {
                "chunk_ids_match": set(c["chunk_id"] for c in chunks) == set(ec["chunk_id"] for ec in enhanced_chunks),
                "text_units_link_to_chunks": all(tu["chunk_id"] in set(c["chunk_id"] for c in chunks) for tu in text_units),
                "documents_have_chunks": len(set(c["document_id"] for c in chunks)) == len(documents)
            }
        }

        print("✓ Validation completed")
        return validation

    def generate_summary_report(self, validation: Dict[str, Any], file_paths: Dict[str, Path]) -> str:
        """Generate summary report."""
        report = f"""
# Database Record Generation Summary

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Generated Files

| Table | File | Size | Records |
|-------|------|------|---------|
| document_registry | {file_paths['documents'].name} | {file_paths['documents'].stat().st_size / (1024*1024):.2f} MB | {validation['document_registry']['count']} |
| chunks | {file_paths['chunks'].name} | {file_paths['chunks'].stat().st_size / (1024*1024):.2f} MB | {validation['chunks']['count']} |
| enhanced_contextual_chunks | {file_paths['enhanced_chunks'].name} | {file_paths['enhanced_chunks'].stat().st_size / (1024*1024):.2f} MB | {validation['enhanced_contextual_chunks']['count']} |
| text_units | {file_paths['text_units'].name} | {file_paths['text_units'].stat().st_size / (1024*1024):.2f} MB | {validation['text_units']['count']} |

## Data Statistics

### Document Registry
- Total documents: {validation['document_registry']['count']}
- Unique document IDs: {validation['document_registry']['unique_document_ids']}
- Law schema: {validation['document_registry']['law_schema_count']} (70%)
- Client schema: {validation['document_registry']['client_schema_count']} (30%)
- Completed status: {validation['document_registry']['completed_status']}

### Chunks
- Total chunks: {validation['chunks']['count']}
- Unique chunk IDs: {validation['chunks']['unique_chunk_ids']}
- Average tokens: {validation['chunks']['avg_token_count']:.1f}
- Average size: {validation['chunks']['avg_chunk_size']:.1f} bytes
- Text content: {validation['chunks']['text_content_type']}

### Enhanced Contextual Chunks
- Total enhanced chunks: {validation['enhanced_contextual_chunks']['count']}
- Unique chunk IDs: {validation['enhanced_contextual_chunks']['unique_chunk_ids']}
- Average contextualized size: {validation['enhanced_contextual_chunks']['avg_contextualized_size']:.1f} bytes
- Client ID format valid: {validation['enhanced_contextual_chunks']['client_id_format_valid']}

### Text Units
- Total text units: {validation['text_units']['count']}
- Unique text unit IDs: {validation['text_units']['unique_text_unit_ids']}
- Average entities per unit: {validation['text_units']['avg_entities_per_unit']:.1f}
- Average relationships per unit: {validation['text_units']['avg_relationships_per_unit']:.1f}
- Total entity links: {validation['text_units']['total_entity_links']}
- Total relationship links: {validation['text_units']['total_relationship_links']}

## Data Integrity

- ✓ Chunk IDs match between chunks and enhanced_contextual_chunks: {validation['data_integrity']['chunk_ids_match']}
- ✓ Text units link to valid chunks: {validation['data_integrity']['text_units_link_to_chunks']}
- ✓ All documents have chunks: {validation['data_integrity']['documents_have_chunks']}

## Sample Records

### Sample Document Registry Record
```json
{{
  "id": "uuid-here",
  "document_id": "doc_supreme_court_rahimi_001",
  "title": "United States v. Rahimi",
  "document_type": "case",
  "source_schema": "law",
  "status": "completed",
  "metadata": {{
    "court": "Supreme Court",
    "year": "2024",
    "citation": "144 S.Ct. 1889",
    "page_count": 45
  }},
  "processing_status": "graph_completed",
  "created_at": "2025-10-08T10:00:00Z"
}}
```

### Sample Chunk Record
```json
{{
  "chunk_id": "chunk_doc_rahimi_001_0001",
  "document_id": "doc_supreme_court_rahimi_001",
  "content": "Legal content...",
  "token_count": 487,
  "chunk_size": 1842,
  "chunk_method": "semantic"
}}
```

### Sample Enhanced Contextual Chunk Record
```json
{{
  "chunk_id": "chunk_doc_rahimi_001_0001",
  "client_id": "client-text-1",
  "contextualized_content": "Document: Case Name. Context: Topic. Content..."
}}
```

### Sample Text Unit Record
```json
{{
  "text_unit_id": "tu_chunk_rahimi_001_0001",
  "chunk_id": "chunk_doc_rahimi_001_0001",
  "entity_ids": ["entity_case_001", "entity_court_002"],
  "relationship_ids": ["edge_cites_001", "edge_applies_002"]
}}
```
"""
        return report


def main():
    """Main execution function."""
    print("=" * 80)
    print("GraphRAG Database Record Generator")
    print("=" * 80)
    print()

    # Initialize generator
    generator = DatabaseRecordGenerator()

    # Generate data
    print("\n" + "=" * 80)
    print("PHASE 1: Generate document_registry records")
    print("=" * 80)
    documents = generator.generate_document_registry(count=100)

    print("\n" + "=" * 80)
    print("PHASE 2: Generate chunks records")
    print("=" * 80)
    chunks = generator.generate_chunks(documents, chunks_per_doc=250)

    print("\n" + "=" * 80)
    print("PHASE 3: Generate enhanced_contextual_chunks records")
    print("=" * 80)
    enhanced_chunks = generator.generate_enhanced_contextual_chunks(chunks)

    print("\n" + "=" * 80)
    print("PHASE 4: Generate text_units records")
    print("=" * 80)
    text_units = generator.generate_text_units(chunks)

    # Save to JSON files
    print("\n" + "=" * 80)
    print("PHASE 5: Save to JSON files")
    print("=" * 80)
    file_paths = {
        "documents": generator.save_to_json(documents, "document_registry.json"),
        "chunks": generator.save_to_json(chunks, "chunks.json"),
        "enhanced_chunks": generator.save_to_json(enhanced_chunks, "enhanced_contextual_chunks.json"),
        "text_units": generator.save_to_json(text_units, "text_units.json")
    }

    # Validate data
    print("\n" + "=" * 80)
    print("PHASE 6: Validation")
    print("=" * 80)
    validation = generator.validate_data(documents, chunks, enhanced_chunks, text_units)

    # Generate and save summary report
    print("\n" + "=" * 80)
    print("PHASE 7: Generate Summary Report")
    print("=" * 80)
    report = generator.generate_summary_report(validation, file_paths)
    report_path = generator.output_dir / "generation_summary.md"
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"✓ Summary report saved to {report_path}")

    # Print summary
    print("\n" + "=" * 80)
    print("GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nTotal records generated: {len(documents) + len(chunks) + len(enhanced_chunks) + len(text_units)}")
    print(f"Output directory: {generator.output_dir}")
    print(f"\nFiles created:")
    for name, path in file_paths.items():
        print(f"  - {path.name}")
    print(f"  - {report_path.name}")
    print("\n✓ All data generation tasks completed successfully!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
