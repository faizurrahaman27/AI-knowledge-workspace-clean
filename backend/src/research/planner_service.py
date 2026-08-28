"""
Research Planner Service

Generates research plans from goals.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from src.research.models import (
    ResearchProject, ResearchTask, ResearchPlan, ResearchStatus, TaskStatus
)
from src.core.logging import logger


class ResearchPlannerService:
    """
    Service for generating research plans from user goals.
    
    Takes a research goal and produces:
    - Objectives
    - Research Questions
    - Subtasks
    - Expected Sources
    - Missing Information
    - Estimated Complexity
    - Execution Plan
    """
    
    def __init__(self, db: Session, llm_provider=None):
        """
        Initialize the planner service.
        
        Args:
            db: Database session
            llm_provider: Optional LLM provider for advanced planning
        """
        self.db = db
        self.llm_provider = llm_provider
    
    def create_project(
        self,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        objective: Optional[str] = None,
        scope: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        tags: Optional[List[str]] = None
    ) -> ResearchProject:
        """
        Create a new research project.
        
        Args:
            user_id: User ID
            title: Project title
            description: Optional description
            objective: Research objective
            scope: Research scope
            keywords: Research keywords
            tags: User tags
            
        Returns:
            Created research project
        """
        project = ResearchProject(
            user_id=user_id,
            title=title,
            description=description,
            objective=objective,
            scope=scope,
            keywords=keywords,
            tags=tags,
            status=ResearchStatus.PLANNING.value,
            started_at=datetime.utcnow()
        )
        
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        
        logger.info(f"Created research project {project.id}: {title}")
        
        return project
    
    def generate_plan(
        self,
        project_id: int,
        research_goal: str
    ) -> ResearchPlan:
        """
        Generate a research plan from a goal.
        
        Args:
            project_id: Project ID
            research_goal: The research goal/objective
            
        Returns:
            Generated research plan
        """
        # Get project
        project = self.db.query(ResearchProject).filter(
            ResearchProject.id == project_id
        ).first()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Generate plan using LLM or template
        if self.llm_provider:
            plan_data = self._generate_plan_with_llm(research_goal)
        else:
            plan_data = self._generate_plan_template(research_goal)
        
        # Create plan record
        plan = ResearchPlan(
            project_id=project_id,
            research_goal=research_goal,
            objectives=plan_data.get("objectives"),
            research_questions=plan_data.get("research_questions"),
            subtasks=plan_data.get("subtasks"),
            expected_sources=plan_data.get("expected_sources"),
            missing_information=plan_data.get("missing_information"),
            estimated_complexity=plan_data.get("estimated_complexity"),
            estimated_duration_hours=plan_data.get("estimated_duration_hours"),
            priority_order=plan_data.get("priority_order"),
            execution_plan=plan_data.get("execution_plan")
        )
        
        self.db.add(plan)
        
        # Create tasks from subtasks
        self._create_tasks_from_plan(project_id, plan_data.get("subtasks", []))
        
        # Update project status
        project.status = ResearchStatus.PLANNING.value
        project.total_tasks = len(plan_data.get("subtasks", []))
        
        self.db.commit()
        self.db.refresh(plan)
        
        logger.info(f"Generated research plan for project {project_id}")
        
        return plan
    
    def _generate_plan_with_llm(self, goal: str) -> Dict[str, Any]:
        """Generate plan using LLM."""
        prompt = f"""Generate a comprehensive research plan for the following goal:

Goal: {goal}

Create a JSON response with the following structure:
{{
    "objectives": ["objective 1", "objective 2", ...],
    "research_questions": ["question 1", "question 2", ...],
    "subtasks": [
        {{"title": "task title", "description": "...", "priority": 1-10, "task_type": "gather|analyze|compare|synthesize"}},
        ...
    ],
    "expected_sources": ["workspace", "web", "documentation", "arxiv", ...],
    "missing_information": ["gap 1", "gap 2", ...],
    "estimated_complexity": "low|medium|high",
    "estimated_duration_hours": number,
    "priority_order": ["task 1 title", "task 2 title", ...],
    "execution_plan": ["step 1", "step 2", ...]
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
            logger.error(f"LLM planning failed: {e}")
            return self._generate_plan_template(goal)
    
    def _generate_plan_template(self, goal: str) -> Dict[str, Any]:
        """Generate plan using template (fallback)."""
        # Template-based plan generation
        return {
            "objectives": [
                f"Understand the fundamentals of {goal}",
                f"Gather evidence and examples related to {goal}",
                f"Analyze different perspectives on {goal}",
                f"Identify key concepts and relationships",
                f"Synthesize findings into conclusions"
            ],
            "research_questions": [
                f"What is {goal}?",
                f"What are the key components of {goal}?",
                f"What are the main applications of {goal}?",
                f"What are the advantages and disadvantages?",
                f"What is the current state of research?"
            ],
            "subtasks": [
                {
                    "title": f"Research background of {goal}",
                    "description": f"Investigate the history and background of {goal}",
                    "priority": 1,
                    "task_type": "gather"
                },
                {
                    "title": f"Gather evidence on {goal}",
                    "description": f"Collect evidence and examples related to {goal}",
                    "priority": 2,
                    "task_type": "gather"
                },
                {
                    "title": f"Analyze perspectives on {goal}",
                    "description": f"Compare different viewpoints and approaches",
                    "priority": 3,
                    "task_type": "analyze"
                },
                {
                    "title": f"Compare related concepts",
                    "description": "Compare with similar or related concepts",
                    "priority": 4,
                    "task_type": "compare"
                },
                {
                    "title": "Synthesize findings",
                    "description": "Combine findings into coherent conclusions",
                    "priority": 5,
                    "task_type": "synthesize"
                }
            ],
            "expected_sources": ["workspace", "web", "documentation"],
            "missing_information": [],
            "estimated_complexity": "medium",
            "estimated_duration_hours": 2.0,
            "priority_order": [
                f"Research background of {goal}",
                f"Gather evidence on {goal}",
                f"Analyze perspectives on {goal}",
                "Compare related concepts",
                "Synthesize findings"
            ],
            "execution_plan": [
                "Start with background research",
                "Collect evidence from multiple sources",
                "Analyze and compare findings",
                "Identify conflicts and consensus",
                "Generate final synthesis"
            ]
        }
    
    def _create_tasks_from_plan(
        self,
        project_id: int,
        subtasks: List[Dict[str, Any]]
    ):
        """Create research tasks from subtasks."""
        for i, subtask in enumerate(subtasks):
            task = ResearchTask(
                project_id=project_id,
                title=subtask.get("title", f"Task {i+1}"),
                description=subtask.get("description"),
                task_type=subtask.get("task_type", "gather"),
                priority=subtask.get("priority", i + 1),
                status=TaskStatus.PENDING.value
            )
            self.db.add(task)
    
    def decompose_task(
        self,
        task_id: int
    ) -> List[ResearchTask]:
        """
        Decompose a task into subtasks.
        
        Args:
            task_id: Task to decompose
            
        Returns:
            List of created subtasks
        """
        task = self.db.query(ResearchTask).filter(
            ResearchTask.id == task_id
        ).first()
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Generate subtasks
        if self.llm_provider:
            subtasks = self._decompose_with_llm(task.title, task.description)
        else:
            subtasks = self._decompose_template(task.title)
        
        # Create subtasks
        created_tasks = []
        for subtask_data in subtasks:
            subtask = ResearchTask(
                project_id=task.project_id,
                parent_task_id=task_id,
                title=subtask_data.get("title"),
                description=subtask_data.get("description"),
                task_type=subtask_data.get("task_type", "gather"),
                priority=subtask_data.get("priority", 5),
                status=TaskStatus.PENDING.value
            )
            self.db.add(subtask)
            created_tasks.append(subtask)
        
        # Mark parent as having subtasks
        task.status = TaskStatus.IN_PROGRESS.value
        
        self.db.commit()
        
        return created_tasks
    
    def _decompose_with_llm(self, title: str, description: str) -> List[Dict]:
        """Decompose task using LLM."""
        prompt = f"""Break down this research task into subtasks:

Title: {title}
Description: {description}

Return a JSON array of subtasks:
[
    {{"title": "subtask title", "description": "...", "priority": 1-10, "task_type": "gather|analyze|compare|synthesize"}}
]
"""
        
        try:
            response = self.llm_provider.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="llama3"
            )
            
            import json
            return json.loads(response)
        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}")
            return self._decompose_template(title)
    
    def _decompose_template(self, title: str) -> List[Dict]:
        """Decompose task using template."""
        return [
            {
                "title": f"Gather information for: {title}",
                "description": "Collect relevant evidence and sources",
                "priority": 1,
                "task_type": "gather"
            },
            {
                "title": f"Analyze: {title}",
                "description": "Analyze the gathered information",
                "priority": 2,
                "task_type": "analyze"
            },
            {
                "title": f"Document findings for: {title}",
                "description": "Document key findings",
                "priority": 3,
                "task_type": "synthesize"
            }
        ]
    
    def update_task_status(
        self,
        task_id: int,
        status: str,
        findings: Optional[Dict] = None,
        blockers: Optional[str] = None
    ) -> ResearchTask:
        """Update task status."""
        task = self.db.query(ResearchTask).filter(
            ResearchTask.id == task_id
        ).first()
        
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = status
        
        if status == TaskStatus.IN_PROGRESS.value and not task.started_at:
            task.started_at = datetime.utcnow()
        elif status == TaskStatus.COMPLETED.value:
            task.completed_at = datetime.utcnow()
        
        if findings:
            task.findings = findings
        
        if blockers:
            task.blockers = blockers
        
        # Update project progress
        self._update_project_progress(task.project_id)
        
        self.db.commit()
        self.db.refresh(task)
        
        return task
    
    def _update_project_progress(self, project_id: int):
        """Update project progress based on task completion."""
        project = self.db.query(ResearchProject).filter(
            ResearchProject.id == project_id
        ).first()
        
        if not project:
            return
        
        tasks = self.db.query(ResearchTask).filter(
            ResearchTask.project_id == project_id
        ).all()
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED.value)
        
        project.total_tasks = total
        project.completed_tasks = completed
        project.progress_percentage = (completed / total * 100) if total > 0 else 0
        
        if completed == total and total > 0:
            project.status = ResearchStatus.COMPLETED.value
            project.completed_at = datetime.utcnow()
    
    def get_project(self, project_id: int, user_id: int) -> Optional[ResearchProject]:
        """Get a research project."""
        return self.db.query(ResearchProject).filter(
            ResearchProject.id == project_id,
            ResearchProject.user_id == user_id
        ).first()
    
    def get_projects(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[ResearchProject]:
        """Get user's research projects."""
        query = self.db.query(ResearchProject).filter(
            ResearchProject.user_id == user_id
        )
        
        if status:
            query = query.filter(ResearchProject.status == status)
        
        return query.order_by(
            ResearchProject.updated_at.desc()
        ).limit(limit).all()
