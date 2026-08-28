"""
Report Generation Service

Generates structured research reports.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.research.models import (
    ResearchReport, ResearchProject, ResearchEvidence, ResearchConflict
)
from src.research.synthesis_service import SynthesisService
from src.core.logging import logger


class ReportGenerationService:
    """
    Service for generating research reports.
    """
    
    def __init__(self, db: Session, llm_provider=None):
        """Initialize the report service."""
        self.db = db
        self.llm_provider = llm_provider
        self.synthesis_service = SynthesisService(db, llm_provider)
    
    def generate_report(
        self,
        project_id: int,
        report_type: str = "comprehensive",
        title: Optional[str] = None
    ) -> ResearchReport:
        """
        Generate a research report.
        
        Args:
            project_id: Project ID
            report_type: Type of report (comprehensive, executive, technical)
            title: Optional custom title
            
        Returns:
            Generated report
        """
        # Get project
        project = self.db.query(ResearchProject).filter(
            ResearchProject.id == project_id
        ).first()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Get evidence and conflicts
        evidence_list = self.db.query(ResearchEvidence).filter(
            ResearchEvidence.project_id == project_id,
            ResearchEvidence.is_pertinent == True
        ).order_by(ResearchEvidence.overall_score.desc()).all()
        
        conflicts = self.db.query(ResearchConflict).filter(
            ResearchConflict.project_id == project_id
        ).all()
        
        # Synthesize knowledge
        synthesis = self.synthesis_service.synthesize(
            project_id, project.objective or project.title
        )
        
        # Generate references
        references = self.synthesis_service.generate_references(evidence_list)
        
        # Calculate research confidence
        confidence = self._calculate_research_confidence(evidence_list, conflicts)
        
        # Create report
        report = ResearchReport(
            project_id=project_id,
            title=title or f"Research Report: {project.title}",
            report_type=report_type,
            executive_summary=synthesis.get("executive_summary"),
            technical_summary=synthesis.get("technical_summary"),
            beginner_explanation=synthesis.get("beginner_explanation"),
            comparison_table=synthesis.get("comparison_table"),
            pros_cons=synthesis.get("pros_cons"),
            consensus=synthesis.get("consensus"),
            disagreements=synthesis.get("disagreements"),
            open_questions=synthesis.get("open_questions"),
            future_research=synthesis.get("future_research"),
            evidence_used=[e.id for e in evidence_list],
            conflicts_addressed=[c.id for c in conflicts if c.resolution_status == "resolved"],
            key_findings=self.synthesis_service.generate_key_findings(project_id),
            research_confidence=confidence,
            references=references,
            generated_at=datetime.utcnow()
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        logger.info(f"Generated report {report.id} for project {project_id}")
        
        return report
    
    def _calculate_research_confidence(
        self,
        evidence_list: List[ResearchEvidence],
        conflicts: List[ResearchConflict]
    ) -> float:
        """Calculate overall research confidence."""
        if not evidence_list:
            return 0.0
        
        # Average evidence confidence
        avg_evidence = sum(e.overall_score for e in evidence_list) / len(evidence_list)
        
        # Penalize for unresolved conflicts
        unresolved = sum(1 for c in conflicts if c.resolution_status == "unresolved")
        conflict_penalty = min(unresolved * 0.05, 0.3)
        
        # Calculate final confidence
        confidence = max(avg_evidence - conflict_penalty, 0.0)
        
        return round(confidence, 3)
    
    def get_report(self, report_id: int) -> Optional[ResearchReport]:
        """Get a report by ID."""
        return self.db.query(ResearchReport).filter(
            ResearchReport.id == report_id
        ).first()
    
    def get_reports_for_project(
        self,
        project_id: int
    ) -> List[ResearchReport]:
        """Get all reports for a project."""
        return self.db.query(ResearchReport).filter(
            ResearchReport.project_id == project_id
        ).order_by(ResearchReport.generated_at.desc()).all()
    
    def export_as_markdown(self, report_id: int) -> str:
        """Export report as Markdown."""
        report = self.get_report(report_id)
        
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        md = f"# {report.title}\n\n"
        md += f"**Type:** {report.report_type}\n"
        md += f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M') if report.generated_at else 'N/A'}\n"
        md += f"**Confidence:** {report.research_confidence:.1%}\n\n"
        
        if report.executive_summary:
            md += f"## Executive Summary\n\n{report.executive_summary}\n\n"
        
        if report.technical_summary:
            md += f"## Technical Summary\n\n{report.technical_summary}\n\n"
        
        if report.key_findings:
            md += "## Key Findings\n\n"
            for finding in report.key_findings:
                md += f"- **{finding.get('title', 'Finding')}**: {finding.get('summary', '')}\n"
            md += "\n"
        
        if report.pros_cons:
            md += "## Pros & Cons\n\n"
            md += "### Pros\n"
            for pro in report.pros_cons.get("pros", []):
                md += f"- {pro}\n"
            md += "\n### Cons\n"
            for con in report.pros_cons.get("cons", []):
                md += f"- {con}\n"
            md += "\n"
        
        if report.open_questions:
            md += "## Open Questions\n\n"
            for q in report.open_questions:
                md += f"- {q.get('question', '')}\n"
            md += "\n"
        
        if report.references:
            md += "## References\n\n"
            for ref in report.references:
                md += f"- {ref.get('citation', '')}\n"
        
        return md
    
    def export_as_html(self, report_id: int) -> str:
        """Export report as HTML."""
        md = self.export_as_markdown(report_id)
        
        # Simple Markdown to HTML conversion
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{self.get_report(report_id).title if report_id else 'Report'}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        code {{ background: #f4f4f4; padding: 2px 6px; }}
        pre {{ background: #f4f4f4; padding: 10px; overflow-x: auto; }}
    </style>
</head>
<body>
{self._markdown_to_html(md)}
</body>
</html>"""
        return html
    
    def _markdown_to_html(self, md: str) -> str:
        """Convert Markdown to HTML."""
        import re
        
        html = md
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'^- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'\n\n', '</p><p>', html)
        html = f'<p>{html}</p>'
        html = re.sub(r'<p><(h[123])', r'<\1', html)
        html = re.sub(r'</(h[123])></p>', r'</\1>', html)
        
        return html
    
    def integrate_with_notebook(
        self,
        report_id: int,
        user_id: int,
        collection_id: Optional[int] = None
    ) -> int:
        """
        Integrate report into notebook.
        
        Args:
            report_id: Report ID
            user_id: User ID
            collection_id: Optional collection ID
            
        Returns:
            Created note ID
        """
        from src.knowledge.interaction_models import KnowledgeNote
        
        report = self.get_report(report_id)
        if not report:
            raise ValueError(f"Report {report_id} not found")
        
        # Create note from report
        note = KnowledgeNote(
            user_id=user_id,
            title=report.title,
            content=self.export_as_markdown(report_id),
            note_type="summary",
            source_document_id=None,
            ai_generated=True,
            collection_id=collection_id
        )
        
        self.db.add(note)
        
        # Link note to report
        report.notebook_note_id = note.id
        report.collection_id = collection_id
        
        self.db.commit()
        self.db.refresh(note)
        
        return note.id
