"""
Knowledge Graph Service

Autonomous knowledge graph engine with automatic linking.
"""

import uuid
from typing import List, Dict, Any, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from src.autonomous.models import KnowledgeNode, KnowledgeEdge, EntityType, RelationshipType
from src.models.document import Document
from src.knowledge.models import KnowledgeEntity, KnowledgeConcept, KnowledgeRelationship
from src.core.logging import logger


class KnowledgeGraphService:
    """
    Autonomous knowledge graph engine.
    
    Features:
    - Automatic entity extraction
    - Automatic relationship discovery
    - Duplicate detection
    - Graph traversal
    - Path finding
    - Subgraph extraction
    """
    
    def __init__(self, db: Session):
        """Initialize the knowledge graph service."""
        self.db = db
    
    def create_node(
        self,
        user_id: int,
        name: str,
        entity_type: str,
        description: Optional[str] = None,
        source_document_id: Optional[int] = None,
        citation: Optional[str] = None,
        aliases: Optional[List[str]] = None,
        language: str = "en",
        confidence: float = 0.5
    ) -> KnowledgeNode:
        """
        Create a knowledge node.
        
        Args:
            user_id: User ID
            name: Entity name
            entity_type: Type of entity
            description: Optional description
            source_document_id: Source document
            citation: Citation text
            aliases: Alternative names
            language: Language code
            confidence: Confidence score
            
        Returns:
            Created or existing node
        """
        # Check for duplicate
        existing = self._find_similar_node(user_id, name, entity_type)
        if existing:
            # Update existing node
            self._merge_node(existing, source_document_id, citation, confidence)
            return existing
        
        # Create new node
        node_id = f"node_{uuid.uuid4().hex[:12]}"
        
        node = KnowledgeNode(
            node_id=node_id,
            name=name,
            entity_type=entity_type,
            user_id=user_id,
            description=description,
            source_document_id=source_document_id,
            citation=citation,
            aliases=aliases or [],
            language=language,
            confidence_score=confidence,
            first_seen_at=datetime.utcnow(),
            last_updated_at=datetime.utcnow()
        )
        
        self.db.add(node)
        self.db.commit()
        self.db.refresh(node)
        
        logger.info(f"Created knowledge node: {node_id} ({name})")
        
        return node
    
    def _find_similar_node(
        self,
        user_id: int,
        name: str,
        entity_type: str
    ) -> Optional[KnowledgeNode]:
        """Find a similar existing node."""
        # Exact match
        node = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.user_id == user_id,
            KnowledgeNode.name == name,
            KnowledgeNode.entity_type == entity_type
        ).first()
        
        if node:
            return node
        
        # Case-insensitive match
        node = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.user_id == user_id,
            KnowledgeNode.name.ilike(name),
            KnowledgeNode.entity_type == entity_type
        ).first()
        
        if node:
            return node
        
        # Check aliases
        node = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.user_id == user_id,
            KnowledgeNode.entity_type == entity_type
        ).filter(
            KnowledgeNode.aliases.contains(name)
        ).first()
        
        return node
    
    def _merge_node(
        self,
        node: KnowledgeNode,
        source_document_id: Optional[int],
        citation: Optional[str],
        confidence: float
    ):
        """Merge information into existing node."""
        if source_document_id:
            # Add source document
            if node.source_document_id is None:
                node.source_document_id = source_document_id
        
        if citation and not node.citation:
            node.citation = citation
        
        # Update confidence (weighted average)
        new_confidence = (node.confidence_score + confidence) / 2
        node.confidence_score = new_confidence
        
        # Update timestamp
        node.last_updated_at = datetime.utcnow()
        
        # Increment degree
        node.out_degree += 1
        
        self.db.commit()
    
    def create_edge(
        self,
        source_node_id: int,
        target_node_id: int,
        relationship_type: str,
        source_document_id: Optional[int] = None,
        description: Optional[str] = None,
        confidence: float = 0.5
    ) -> Optional[KnowledgeEdge]:
        """
        Create a relationship edge.
        
        Args:
            source_node_id: Source node ID
            target_node_id: Target node ID
            relationship_type: Type of relationship
            source_document_id: Source document
            description: Relationship description
            confidence: Confidence score
            
        Returns:
            Created or existing edge
        """
        # Check if edge exists
        existing = self.db.query(KnowledgeEdge).filter(
            KnowledgeEdge.source_node_id == source_node_id,
            KnowledgeEdge.target_node_id == target_node_id,
            KnowledgeEdge.relationship_type == relationship_type
        ).first()
        
        if existing:
            return existing
        
        # Create edge
        edge_id = f"edge_{uuid.uuid4().hex[:12]}"
        
        edge = KnowledgeEdge(
            edge_id=edge_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            relationship_type=relationship_type,
            source_document_id=source_document_id,
            description=description,
            confidence_score=confidence,
            is_auto_generated=True
        )
        
        self.db.add(edge)
        
        # Update node degrees
        source_node = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == source_node_id
        ).first()
        target_node = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == target_node_id
        ).first()
        
        if source_node:
            source_node.out_degree += 1
        if target_node:
            target_node.in_degree += 1
        
        self.db.commit()
        self.db.refresh(edge)
        
        return edge
    
    def build_from_entities(self, document_id: int, user_id: int) -> Dict[str, Any]:
        """
        Build knowledge graph from document entities.
        
        Args:
            document_id: Document ID
            user_id: User ID
            
        Returns:
            Graph statistics
        """
        # Get document
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()
        
        if not document:
            return {"nodes_created": 0, "edges_created": 0}
        
        nodes_created = 0
        edges_created = 0
        
        # Get entities
        entities = self.db.query(KnowledgeEntity).filter(
            KnowledgeEntity.document_id == document_id
        ).all()
        
        # Create nodes for entities
        entity_nodes = {}
        for entity in entities:
            node = self.create_node(
                user_id=user_id,
                name=entity.name,
                entity_type=entity.entity_type,
                description=entity.description,
                source_document_id=document_id,
                citation=f"Document: {document.title}",
                language=entity.language or "en",
                confidence=entity.confidence_score or 0.5
            )
            entity_nodes[entity.id] = node
            nodes_created += 1
        
        # Get relationships
        relationships = self.db.query(KnowledgeRelationship).filter(
            KnowledgeRelationship.document_id == document_id
        ).all()
        
        # Create edges
        for rel in relationships:
            # Find source and target nodes
            source_node = self._find_node_by_name(user_id, rel.source_name)
            target_node = self._find_node_by_name(user_id, rel.target_name)
            
            if source_node and target_node:
                edge = self.create_edge(
                    source_node_id=source_node.id,
                    target_node_id=target_node.id,
                    relationship_type=rel.relationship_type,
                    source_document_id=document_id,
                    description=rel.description,
                    confidence=rel.confidence_score or 0.5
                )
                if edge:
                    edges_created += 1
        
        return {
            "nodes_created": nodes_created,
            "edges_created": edges_created,
            "document_id": document_id
        }
    
    def _find_node_by_name(self, user_id: int, name: str) -> Optional[KnowledgeNode]:
        """Find node by name."""
        return self.db.query(KnowledgeNode).filter(
            KnowledgeNode.user_id == user_id,
            KnowledgeNode.name == name
        ).first()
    
    def get_subgraph(
        self,
        node_id: int,
        depth: int = 2,
        relationship_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get subgraph centered on a node.
        
        Args:
            node_id: Center node ID
            depth: Traversal depth
            relationship_types: Filter by relationship types
            
        Returns:
            Subgraph data
        """
        nodes = {}
        edges = []
        
        # BFS traversal
        visited = set()
        queue = [(node_id, 0)]
        
        while queue:
            current_id, current_depth = queue.pop(0)
            
            if current_id in visited or current_depth > depth:
                continue
            
            visited.add(current_id)
            
            # Get node
            node = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.id == current_id
            ).first()
            
            if node:
                nodes[current_id] = {
                    "id": node.node_id,
                    "name": node.name,
                    "entity_type": node.entity_type,
                    "description": node.description,
                    "confidence": node.confidence_score
                }
                
                # Get outgoing edges
                outgoing = self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.source_node_id == current_id
                ).all()
                
                for edge in outgoing:
                    if relationship_types and edge.relationship_type not in relationship_types:
                        continue
                    
                    edges.append({
                        "source": edge.source_node_id,
                        "target": edge.target_node_id,
                        "type": edge.relationship_type,
                        "confidence": edge.confidence_score
                    })
                    
                    if edge.target_node_id not in visited:
                        queue.append((edge.target_node_id, current_depth + 1))
                
                # Get incoming edges
                incoming = self.db.query(KnowledgeEdge).filter(
                    KnowledgeEdge.target_node_id == current_id
                ).all()
                
                for edge in incoming:
                    if relationship_types and edge.relationship_type not in relationship_types:
                        continue
                    
                    edges.append({
                        "source": edge.source_node_id,
                        "target": edge.target_node_id,
                        "type": edge.relationship_type,
                        "confidence": edge.confidence_score
                    })
                    
                    if edge.source_node_id not in visited:
                        queue.append((edge.source_node_id, current_depth + 1))
        
        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
    
    def find_shortest_path(
        self,
        source_name: str,
        target_name: str,
        user_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        """Find shortest path between two nodes."""
        source = self._find_node_by_name(user_id, source_name)
        target = self._find_node_by_name(user_id, target_name)
        
        if not source or not target:
            return None
        
        # BFS
        visited = {source.id}
        queue = [(source.id, [])]
        
        while queue:
            current_id, path = queue.pop(0)
            
            if current_id == target.id:
                return path
            
            edges = self.db.query(KnowledgeEdge).filter(
                KnowledgeEdge.source_node_id == current_id
            ).all()
            
            for edge in edges:
                if edge.target_node_id not in visited:
                    visited.add(edge.target_node_id)
                    new_path = path + [{
                        "source": edge.source_node_id,
                        "target": edge.target_node_id,
                        "relationship": edge.relationship_type
                    }]
                    queue.append((edge.target_node_id, new_path))
        
        return None
    
    def get_connected_concepts(
        self,
        node_id: int,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Get concepts connected to a node."""
        node = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == node_id
        ).first()
        
        if not node:
            return []
        
        connected = []
        
        # Get connected nodes
        edges = self.db.query(KnowledgeEdge).filter(
            or_(
                KnowledgeEdge.source_node_id == node_id,
                KnowledgeEdge.target_node_id == node_id
            )
        ).limit(max_results).all()
        
        for edge in edges:
            connected_id = edge.target_node_id if edge.source_node_id == node_id else edge.source_node_id
            
            connected_node = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.id == connected_id
            ).first()
            
            if connected_node:
                connected.append({
                    "id": connected_node.node_id,
                    "name": connected_node.name,
                    "entity_type": connected_node.entity_type,
                    "relationship": edge.relationship_type,
                    "confidence": edge.confidence_score
                })
        
        return connected
    
    def get_graph_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get knowledge graph statistics."""
        total_nodes = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.user_id == user_id
        ).count()
        
        total_edges = self.db.query(KnowledgeEdge).join(
            KnowledgeNode,
            KnowledgeEdge.source_node_id == KnowledgeNode.id
        ).filter(KnowledgeNode.user_id == user_id).count()
        
        # Count by type
        nodes_by_type = self.db.query(
            KnowledgeNode.entity_type,
            self.db.func.count(KnowledgeNode.id).label('count')
        ).filter(
            KnowledgeNode.user_id == user_id
        ).group_by(KnowledgeNode.entity_type).all()
        
        edges_by_type = self.db.query(
            KnowledgeEdge.relationship_type,
            self.db.func.count(KnowledgeEdge.id).label('count')
        ).join(
            KnowledgeNode,
            KnowledgeEdge.source_node_id == KnowledgeNode.id
        ).filter(
            KnowledgeNode.user_id == user_id
        ).group_by(KnowledgeEdge.relationship_type).all()
        
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "nodes_by_type": {t: c for t, c in nodes_by_type},
            "edges_by_type": {t: c for t, c in edges_by_type},
            "average_connections": (total_edges * 2 / total_nodes) if total_nodes > 0 else 0
        }
    
    def discover_duplicates(self, user_id: int) -> List[Dict[str, Any]]:
        """Find potential duplicate nodes."""
        duplicates = []
        
        nodes = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.user_id == user_id
        ).all()
        
        # Group by entity type and similar names
        groups = defaultdict(list)
        
        for node in nodes:
            key = (node.entity_type, node.name.lower()[:20])
            groups[key].append(node)
        
        # Find groups with duplicates
        for key, group in groups.items():
            if len(group) > 1:
                duplicates.append({
                    "entity_type": key[0],
                    "name_base": key[1],
                    "nodes": [
                        {
                            "id": n.id,
                            "node_id": n.node_id,
                            "name": n.name,
                            "confidence": n.confidence_score
                        }
                        for n in group
                    ]
                })
        
        return duplicates
    
    def merge_nodes(self, node_ids: List[int], user_id: int) -> Optional[KnowledgeNode]:
        """Merge multiple nodes into one."""
        if len(node_ids) < 2:
            return None
        
        primary = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.id == node_ids[0]
        ).first()
        
        if not primary:
            return None
        
        # Merge other nodes into primary
        for node_id in node_ids[1:]:
            node = self.db.query(KnowledgeNode).filter(
                KnowledgeNode.id == node_id
            ).first()
            
            if not node:
                continue
            
            # Move edges to primary
            edges = self.db.query(KnowledgeEdge).filter(
                or_(
                    KnowledgeEdge.source_node_id == node.id,
                    KnowledgeEdge.target_node_id == node.id
                )
            ).all()
            
            for edge in edges:
                if edge.source_node_id == node.id:
                    edge.source_node_id = primary.id
                if edge.target_node_id == node.id:
                    edge.target_node_id = primary.id
            
            # Update counts
            primary.out_degree += node.out_degree
            primary.in_degree += node.in_degree
            
            # Add aliases
            if node.aliases:
                existing_aliases = set(primary.aliases or [])
                existing_aliases.update(node.aliases)
                primary.aliases = list(existing_aliases)
            
            # Update confidence
            primary.confidence_score = max(primary.confidence_score, node.confidence_score)
            
            # Delete merged node
            self.db.delete(node)
        
        primary.last_updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(primary)
        
        return primary
