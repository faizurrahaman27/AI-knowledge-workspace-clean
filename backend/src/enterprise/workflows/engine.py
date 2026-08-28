"""
Workflow Engine

Defines and executes multi-step workflows using the agent orchestration system.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from src.enterprise.orchestrator.base import AgentCapability


class WorkflowStatus(Enum):
    """Workflow execution states."""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """
    A single step within a workflow.
    
    Steps are executed sequentially and can have:
    - Conditional execution based on previous step results
    - Retry policies
    - Timeout settings
    """
    step_id: str
    name: str
    description: str = ""
    capability: str = ""                    # AgentCapability value or custom type
    parameters: dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None         # Expression to evaluate for conditional execution
    timeout_seconds: int = 300
    retry_count: int = 0
    on_success: Optional[str] = None        # Next step_id on success
    on_failure: Optional[str] = None       # Next step_id on failure (else: end)


@dataclass
class Workflow:
    """
    Workflow definition with steps and metadata.
    
    Workflows define reusable sequences of agent calls that can be
    executed with different inputs.
    """
    workflow_id: str
    name: str
    description: str
    version: str = "1.0.0"
    category: str = "general"               # e.g., "research", "study", "job_hunting"
    steps: list[WorkflowStep] = field(default_factory=list)
    default_timeout: int = 3600            # Overall workflow timeout
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        # Build step lookup map
        self._step_map = {step.step_id: step for step in self.steps}
    
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by its ID."""
        return self._step_map.get(step_id)
    
    def to_executable_steps(self) -> list[dict]:
        """
        Convert workflow to a list of executable step dicts.
        
        Returns:
            List of step dicts for the MasterOrchestrator
        """
        return [
            {
                "name": step.name,
                "capability": step.capability,
                "parameters": step.parameters
            }
            for step in self.steps
        ]


class WorkflowEngine:
    """
    Engine for defining and executing workflows.
    
    Provides:
    - Predefined workflow templates
    - Workflow validation
    - Execution via MasterOrchestrator
    
    Usage:
        engine = WorkflowEngine()
        
        # Get a predefined workflow
        workflow = engine.get_workflow("study_pack")
        
        # Execute it
        result = await engine.execute(workflow, context)
    """
    
    # Predefined workflow templates
    WORKFLOW_TEMPLATES: dict[str, Workflow] = {}
    
    def __init__(self):
        self._workflows: dict[str, Workflow] = {}
        self._register_default_workflows()
    
    def _register_default_workflows(self) -> None:
        """Register built-in workflow templates."""
        
        # Study Pack Workflow: Summary -> Questions -> Flashcards -> Quiz -> Mind Map
        self.register(Workflow(
            workflow_id="study_pack",
            name="Complete Study Pack",
            description="Generate a comprehensive study pack from a document",
            category="study",
            steps=[
                WorkflowStep(
                    step_id="summarize",
                    name="Generate Summary",
                    description="Create a structured summary of the document",
                    capability=AgentCapability.DOCUMENT_SUMMARIZATION.value,
                    parameters={}
                ),
                WorkflowStep(
                    step_id="questions",
                    name="Generate Questions",
                    description="Create important exam/interview questions",
                    capability=AgentCapability.QUIZ_GENERATION.value,
                    parameters={"count": 10}
                ),
                WorkflowStep(
                    step_id="flashcards",
                    name="Generate Flashcards",
                    description="Create Q&A flashcards for memorization",
                    capability=AgentCapability.FLASHCARD_GENERATION.value,
                    parameters={"count": 15}
                ),
                WorkflowStep(
                    step_id="quiz",
                    name="Generate Quiz",
                    description="Create a practice quiz with multiple choice",
                    capability=AgentCapability.QUIZ_GENERATION.value,
                    parameters={"count": 5, "format": "multiple_choice"}
                ),
                WorkflowStep(
                    step_id="mindmap",
                    name="Generate Mind Map",
                    description="Create a visual concept map",
                    capability=AgentCapability.MINDMAP_GENERATION.value,
                    parameters={}
                )
            ]
        ))
        
        # Research Synthesis Workflow
        self.register(Workflow(
            workflow_id="research_synthesis",
            name="Research Synthesis",
            description="Analyze multiple sources and synthesize findings",
            category="research",
            steps=[
                WorkflowStep(
                    step_id="extract",
                    name="Extract Key Information",
                    description="Extract key claims and evidence from sources",
                    capability=AgentCapability.SEMANTIC_SEARCH.value,
                    parameters={"mode": "detailed"}
                ),
                WorkflowStep(
                    step_id="compare",
                    name="Compare Sources",
                    description="Compare and contrast findings across sources",
                    capability=AgentCapability.COMPARATIVE_ANALYSIS.value,
                    parameters={}
                ),
                WorkflowStep(
                    step_id="synthesize",
                    name="Synthesize Findings",
                    description="Combine findings into coherent synthesis",
                    capability=AgentCapability.RESEARCH_SYNTHESIS.value,
                    parameters={}
                ),
                WorkflowStep(
                    step_id="cite",
                    name="Generate Citations",
                    description="Create proper citations for all sources",
                    capability=AgentCapability.SOURCE_CITATION.value,
                    parameters={"style": "apa"}
                )
            ]
        ))
        
        # Exam Preparation Workflow
        self.register(Workflow(
            workflow_id="exam_prep",
            name="Exam Preparation",
            description="Comprehensive exam preparation from study materials",
            category="exam",
            steps=[
                WorkflowStep(
                    step_id="overview",
                    name="Generate Overview",
                    description="Create topic overview and key concepts",
                    capability=AgentCapability.DOCUMENT_SUMMARIZATION.value,
                    parameters={"level": "detailed"}
                ),
                WorkflowStep(
                    step_id="topics",
                    name="Identify Topics",
                    description="Break down into study topics",
                    capability=AgentCapability.SEMANTIC_SEARCH.value,
                    parameters={"mode": "topic_clustering"}
                ),
                WorkflowStep(
                    step_id="practice_questions",
                    name="Create Practice Questions",
                    description="Generate likely exam questions",
                    capability=AgentCapability.QUIZ_GENERATION.value,
                    parameters={"count": 20, "types": ["multiple_choice", "short_answer"]}
                ),
                WorkflowStep(
                    step_id="flashcards",
                    name="Create Flashcards",
                    description="Generate flashcards for key terms and concepts",
                    capability=AgentCapability.FLASHCARD_GENERATION.value,
                    parameters={"count": 25}
                ),
                WorkflowStep(
                    step_id="notes",
                    name="Generate Study Notes",
                    description="Create condensed study notes",
                    capability=AgentCapability.NOTES_GENERATION.value,
                    parameters={}
                )
            ]
        ))
        
        # Job Application Workflow
        self.register(Workflow(
            workflow_id="job_application",
            name="Job Application Assistant",
            description="Help prepare for job applications",
            category="jobs",
            steps=[
                WorkflowStep(
                    step_id="analyze_jd",
                    name="Analyze Job Description",
                    description="Extract key requirements and skills",
                    capability=AgentCapability.SEMANTIC_SEARCH.value,
                    parameters={"mode": "job_analysis"}
                ),
                WorkflowStep(
                    step_id="match_resume",
                    name="Match Resume to Job",
                    description="Compare resume against job requirements",
                    capability=AgentCapability.COMPARATIVE_ANALYSIS.value,
                    parameters={}
                ),
                WorkflowStep(
                    step_id="cover_letter",
                    name="Draft Cover Letter",
                    description="Generate tailored cover letter",
                    capability=AgentCapability.ESSAY_WRITING.value,
                    parameters={"type": "cover_letter"}
                ),
                WorkflowStep(
                    step_id="interview_prep",
                    name="Interview Preparation",
                    description="Generate likely interview questions and answers",
                    capability=AgentCapability.EXAM_PREPARATION.value,
                    parameters={"domain": "interview"}
                )
            ]
        ))
        
        # Document Analysis Workflow
        self.register(Workflow(
            workflow_id="document_analysis",
            name="Document Analysis",
            description="Comprehensive analysis of a document",
            category="general",
            steps=[
                WorkflowStep(
                    step_id="extract",
                    name="Extract Content",
                    description="Extract and structure document content",
                    capability=AgentCapability.SEMANTIC_SEARCH.value,
                    parameters={"mode": "full_extraction"}
                ),
                WorkflowStep(
                    step_id="summarize",
                    name="Summarize",
                    description="Create concise summary",
                    capability=AgentCapability.DOCUMENT_SUMMARIZATION.value,
                    parameters={}
                ),
                WorkflowStep(
                    step_id="key_concepts",
                    name="Identify Key Concepts",
                    description="Extract key terms and definitions",
                    capability=AgentCapability.SEMANTIC_SEARCH.value,
                    parameters={"mode": "entities"}
                ),
                WorkflowStep(
                    step_id="questions",
                    name="Generate Questions",
                    description="Create comprehension questions",
                    capability=AgentCapability.QUIZ_GENERATION.value,
                    parameters={"count": 5}
                )
            ]
        ))
    
    def register(self, workflow: Workflow) -> None:
        """
        Register a workflow.
        
        Args:
            workflow: The workflow to register
        """
        self._workflows[workflow.workflow_id] = workflow
        self.WORKFLOW_TEMPLATES[workflow.workflow_id] = workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)
    
    def get_workflows_by_category(self, category: str) -> list[Workflow]:
        """Get all workflows in a category."""
        return [
            w for w in self._workflows.values()
            if w.category == category
        ]
    
    def get_all_workflows(self) -> list[Workflow]:
        """Get all registered workflows."""
        return list(self._workflows.values())
    
    def create_custom_workflow(
        self,
        name: str,
        description: str,
        steps: list[WorkflowStep],
        category: str = "custom"
    ) -> Workflow:
        """
        Create and register a custom workflow.
        
        Args:
            name: Workflow name
            description: Description
            steps: List of workflow steps
            category: Category (default: "custom")
            
        Returns:
            The created workflow
        """
        workflow = Workflow(
            workflow_id=f"custom_{uuid.uuid4().hex[:8]}",
            name=name,
            description=description,
            category=category,
            steps=steps
        )
        self.register(workflow)
        return workflow
    
    def validate_workflow(self, workflow: Workflow) -> list[str]:
        """
        Validate a workflow for execution readiness.
        
        Args:
            workflow: The workflow to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not workflow.steps:
            errors.append("Workflow has no steps")
            return errors
        
        # Check for duplicate step IDs
        step_ids = [s.step_id for s in workflow.steps]
        if len(step_ids) != len(set(step_ids)):
            errors.append("Duplicate step IDs found")
        
        # Validate step references
        for step in workflow.steps:
            if step.on_success and step.on_success not in step_ids:
                errors.append(f"Step '{step.step_id}' references non-existent success step '{step.on_success}'")
            if step.on_failure and step.on_failure not in step_ids:
                errors.append(f"Step '{step.step_id}' references non-existent failure step '{step.on_failure}'")
        
        # Check capabilities are valid
        for step in workflow.steps:
            if step.capability:
                try:
                    AgentCapability(step.capability)
                except ValueError:
                    # Not a standard capability, might be custom - that's OK
                    pass
        
        return errors
    
    async def execute(
        self,
        workflow: Workflow,
        orchestrator,
        context,
        step_callback: Optional[callable] = None
    ):
        """
        Execute a workflow using the orchestrator.
        
        Args:
            workflow: The workflow to execute
            orchestrator: MasterOrchestrator instance
            context: AgentContext for execution
            step_callback: Optional callback for step completion
            
        Returns:
            OrchestrationResult from the workflow execution
        """
        # Validate
        errors = self.validate_workflow(workflow)
        if errors:
            raise ValueError(f"Invalid workflow: {', '.join(errors)}")
        
        # Convert to executable format
        executable_steps = workflow.to_executable_steps()
        
        # Execute via orchestrator
        result = await orchestrator.execute_workflow(executable_steps, context)
        
        return result
    
    def get_available_workflows(self) -> list[dict]:
        """Get summary of all available workflows for API documentation."""
        return [
            {
                "workflow_id": w.workflow_id,
                "name": w.name,
                "description": w.description,
                "category": w.category,
                "version": w.version,
                "step_count": len(w.steps),
                "steps": [
                    {
                        "name": s.name,
                        "description": s.description,
                        "capability": s.capability
                    }
                    for s in w.steps
                ]
            }
            for w in self._workflows.values()
        ]
