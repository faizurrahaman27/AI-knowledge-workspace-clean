"""
Knowledge Synthesis Service

Synthesizes findings into structured knowledge.
"""

from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from src.research.models import ResearchEvidence, ResearchConflict
from src.core.logging import logger


class SynthesisService:
    """
    Service for synthesizing research findings.
    
    Generates:
    - Executive Summary
    - Technical Summary
    - Beginner Explanation
    - Comparison Table
    - Pros & Cons
    - Consensus
    - Disagreements
    - Open Questions
    """
    
    def __init__(self, db: Session, llm_provider=None):
        """Initialize the synthesis service."""
        self.db = db
        self.llm_provider = llm_provider
    
    def synthesize(
        self,
        project_id: int,
        goal: str
    ) -> Dict[str, Any]:
        """
        Synthesize all evidence into structured knowledge.
        
        Args:
            project_id: Project ID
            goal: Research goal
            
        Returns:
            Synthesis results
        """
        # Get evidence
        evidence_list = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.project_id == project_id,
            ResearchEvidence.is_pertinent == True
        ).order_by(ResearchEvidence.overall_score.desc()).all()
        
        # Get conflicts
        conflicts = self.db.query(ResearchConflict).filter(
            ResearchConflict.project_id == project_id
        ).all()
        
        if not evidence_list:
            return {
                "executive_summary": "No evidence collected yet.",
                "technical_summary": "No evidence available for synthesis.",
                "consensus": [],
                "disagreements": [],
                "open_questions": []
            }
        
        # Generate synthesis
        if self.llm_provider:
            synthesis = self._synthesize_with_llm(evidence_list, conflicts, goal)
        else:
            synthesis = self._synthesize_template(evidence_list, conflicts, goal)
        
        return synthesis
    
    def _synthesize_with_llm(
        self,
        evidence_list: List[ResearchEvidence],
        conflicts: List[ResearchConflict],
        goal: str
    ) -> Dict[str, Any]:
        """Generate synthesis using LLM."""
        # Prepare evidence summary
        evidence_text = "\n\n".join([
            f"## {e.title}\nSource: {e.source_name}\n{e.summary or e.content[:500]}"
            for e in evidence_list[:10]  # Limit to top 10
        ])
        
        prompt = f"""Synthesize the following research evidence for the goal: {goal}

Evidence:
{evidence_text}

Generate a JSON response with:
{{
    "executive_summary": "2-3 paragraph summary for executives",
    "technical_summary": "Detailed technical summary",
    "beginner_explanation": "Simple explanation for beginners",
    "comparison_table": [{{"aspect": "...", "finding": "...", "source": "..."}}],
    "pros_cons": {{"pros": ["..."], "cons": ["..."]}},
    "consensus": ["Key agreement points"],
    "disagreements": ["Areas of disagreement"],
    "open_questions": [{{"question": "...", "related_evidence": "..."}}],
    "future_research": "Areas needing further research"
}}

Return ONLY valid JSON."""
        
        try:
            response = self.llm_provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="llama3"
            )
            
            import json
            return json.loads(response)
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return self._synthesize_template(evidence_list, conflicts, goal)
    
    def _synthesize_template(
        self,
        evidence_list: List[ResearchEvidence],
        conflicts: List[ResearchConflict],
        goal: str
    ) -> Dict[str, Any]:
        """Generate synthesis using template."""
        # Aggregate evidence
        summaries = [e.summary or e.content[:200] for e in evidence_list]
        sources = list(set([e.source_name for e in evidence_list if e.source_name]))
        
        # Identify consensus and disagreements
        consensus = []
        disagreements = []
        
        for conflict in conflicts:
            if conflict.resolution_status == "resolved":
                consensus.append(f"Resolved: {conflict.description}")
            else:
                disagreements.append(conflict.description)
        
        return {
            "executive_summary": f"Research on '{goal}' has identified {len(evidence_list)} relevant sources from {len(sources)} sources. Key findings include: {' '.join(summaries[:3])}",
            "technical_summary": f"Comprehensive analysis of {goal} based on {len(evidence_list)} evidence items covering {', '.join(sources[:5])}",
            "beginner_explanation": f"{goal} is a topic that has been studied extensively. Based on the evidence, it involves several key concepts and applications.",
            "comparison_table": [
                {"aspect": "Sources", "finding": f"{len(evidence_list)} evidence items", "source": "Research Collection"},
                {"aspect": "Confidence", "finding": f"Average score: {sum(e.overall_score for e in evidence_list)/len(evidence_list):.2f}", "source": "Quality Metrics"}
            ],
            "pros_cons": {
                "pros": [f"Based on {len(evidence_list)} sources" if len(evidence_list) > 3 else "Limited but focused evidence"],
                "cons": [f"{len(conflicts)} conflicts need resolution" if conflicts else "No major conflicts detected"]
            },
            "consensus": consensus if consensus else ["Evidence supports the research goal"],
            "disagreements": disagreements if disagreements else ["No significant disagreements found"],
            "open_questions": [
                {"question": f"What are the long-term implications of {goal}?", "related_evidence": "Further research needed"}
            ],
            "future_research": f"Additional investigation needed to fully understand {goal}"
        }
    
    def generate_key_findings(
        self,
        project_id: int
    ) -> List[Dict[str, Any]]:
        """Generate key findings from evidence."""
        evidence_list = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.project_id == project_id,
            ResearchEvidence.is_pertinent == True
        ).order_by(ResearchEvidence.overall_score.desc()).limit(5).all()
        
        findings = []
        
        for i, evidence in enumerate(evidence_list):
            findings.append({
                "rank": i + 1,
                "title": evidence.title,
                "summary": evidence.summary or evidence.content[:200],
                "source": evidence.source_name,
                "confidence": evidence.overall_score,
                "relevance": evidence.relevance_score
            })
        
        return findings
    
    def generate_references(
        self,
        evidence_list: List[ResearchEvidence]
    ) -> List[Dict[str, str]]:
        """Generate formatted references."""
        references = []
        
        for i, evidence in enumerate(evidence_list):
            ref = f"[{i+1}] {evidence.title}"
            if evidence.author:
                ref += f" by {evidence.author}"
            if evidence.published_date:
                ref += f" ({evidence.published_date.year})"
            if evidence.source_name:
                ref += f". {evidence.source_name}"
            if evidence.source_url:
                ref += f". {evidence.source_url}"
            
            references.append({
                "key": f"[{i+1}]",
                "citation": ref,
                "source_url": evidence.source_url
            })
        
        return references
