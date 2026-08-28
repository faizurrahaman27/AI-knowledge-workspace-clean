"""
Multi-Agent System Services

Backend services for multi-agent orchestration.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.multi_agent.models import (
    Agent, WorkflowExecution, TaskExecution, AgentMemory, 
    AgentMetrics, AgentEvent, WorkflowStatus, TaskStatus, AgentStatus
)
from src.multi_agent.registry.registry import (
    AgentRegistry, get_agent_registry, AgentMetadata, AgentCapabilities
)
from src.core.logging import logger


class AgentManagerService:
    """
    Service for managing registered agents.
    """
    
    def __init__(self, db: Session, registry: Optional[AgentRegistry] = None):
        self.db = db
        self.registry = registry or get_agent_registry()
    
    def register_agent(
        self,
        agent_id: str,
        name: str,
        description: str,
        capabilities: Dict[str, bool],
        version: str = "1.0.0",
        priority: int = 5,
        supported_tools: Optional[List[str]] = None,
        estimated_latency_ms: int = 5000,
        max_retries: int = 3,
        timeout_seconds: int = 300
    ) -> Agent:
        """Register an agent in both DB and registry."""
        # Create DB record
        agent = Agent(
            agent_id=agent_id,
            name=name,
            description=description,
            version=version,
            capabilities=capabilities,
            priority=priority,
            supported_tools=supported_tools,
            estimated_latency_ms=estimated_latency_ms,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            status=AgentStatus.IDLE.value,
            health_status="healthy",
            last_heartbeat=datetime.utcnow()
        )
        
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        
        # Register in memory registry
        caps = AgentCapabilities(**{k: v for k, v in capabilities.items() if k in AgentCapabilities.__annotations__})
        metadata = AgentMetadata(
            agent_id=agent_id,
            name=name,
            description=description,
            version=version,
            capabilities=caps,
            priority=priority,
            supported_tools=supported_tools or [],
            estimated_latency_ms=estimated_latency_ms,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        
        self.registry.register(metadata)
        
        logger.info(f"Registered agent: {agent_id}")
        
        return agent
    
    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        agent = self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
        
        if not agent:
            return False
        
        self.registry.unregister(agent_id)
        self.db.delete(agent)
        self.db.commit()
        
        return True
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self.db.query(Agent).filter(Agent.agent_id == agent_id).first()
    
    def get_all_agents(self) -> List[Agent]:
        """Get all registered agents."""
        return self.db.query(Agent).all()
    
    def get_agents_by_capability(self, capability: str) -> List[Agent]:
        """Get agents by capability."""
        agents = self.db.query(Agent).filter(
            Agent.capabilities[capability].astext == True
        ).all()
        return agents
    
    def update_health(self, agent_id: str, status: str) -> Optional[Agent]:
        """Update agent health status."""
        agent = self.get_agent(agent_id)
        
        if not agent:
            return None
        
        agent.health_status = status
        agent.last_heartbeat = datetime.utcnow()
        self.db.commit()
        
        self.registry.update_health(agent_id, status)
        
        return agent
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        total = self.db.query(Agent).count()
        healthy = self.db.query(Agent).filter(Agent.health_status == "healthy").count()
        error = self.db.query(Agent).filter(Agent.health_status == "error").count()
        
        return {
            "total_agents": total,
            "healthy": healthy,
            "error": error,
            "unhealthy": total - healthy - error
        }


class WorkflowService:
    """
    Service for workflow execution management.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowExecution]:
        """Get workflow by ID."""
        return self.db.query(WorkflowExecution).filter(
            WorkflowExecution.workflow_id == workflow_id
        ).first()
    
    def get_user_workflows(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[WorkflowExecution]:
        """Get user's workflows."""
        query = self.db.query(WorkflowExecution).filter(
            WorkflowExecution.user_id == user_id
        )
        
        if status:
            query = query.filter(WorkflowExecution.status == status)
        
        return query.order_by(
            WorkflowExecution.created_at.desc()
        ).limit(limit).all()
    
    def get_workflow_tasks(self, workflow_id: str) -> List[TaskExecution]:
        """Get tasks for a workflow."""
        workflow = self.get_workflow(workflow_id)
        if not workflow:
            return []
        
        return self.db.query(TaskExecution).filter(
            TaskExecution.workflow_id == workflow.id
        ).order_by(TaskExecution.execution_order).all()
    
    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a workflow."""
        workflow = self.get_workflow(workflow_id)
        
        if not workflow:
            return False
        
        workflow.status = WorkflowStatus.CANCELLED.value
        workflow.completed_at = datetime.utcnow()
        
        # Cancel pending tasks
        self.db.query(TaskExecution).filter(
            TaskExecution.workflow_id == workflow.id,
            TaskExecution.status == TaskStatus.PENDING.value
        ).update({TaskExecution.status: TaskStatus.SKIPPED.value})
        
        self.db.commit()
        
        return True


class MemoryService:
    """
    Service for agent memory management.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def store(
        self,
        key: str,
        value: Any,
        memory_type: str,
        workflow_id: Optional[int] = None,
        task_id: Optional[str] = None,
        scope: str = "workflow"
    ) -> AgentMemory:
        """Store memory."""
        memory = AgentMemory(
            workflow_id=workflow_id,
            task_id=task_id,
            memory_type=memory_type,
            key=key,
            value=value if isinstance(value, (dict, list)) else {"value": value},
            scope=scope
        )
        
        self.db.add(memory)
        self.db.commit()
        
        return memory
    
    def get(
        self,
        key: str,
        memory_type: Optional[str] = None,
        workflow_id: Optional[int] = None,
        scope: str = "workflow"
    ) -> Optional[Any]:
        """Get memory by key."""
        query = self.db.query(AgentMemory).filter(
            AgentMemory.key == key,
            AgentMemory.scope == scope
        )
        
        if workflow_id:
            query = query.filter(AgentMemory.workflow_id == workflow_id)
        
        if memory_type:
            query = query.filter(AgentMemory.memory_type == memory_type)
        
        memory = query.first()
        
        if memory:
            return memory.value
        
        return None
    
    def get_workflow_memory(
        self,
        workflow_id: int,
        memory_type: Optional[str] = None
    ) -> List[AgentMemory]:
        """Get all memory for a workflow."""
        query = self.db.query(AgentMemory).filter(
            AgentMemory.workflow_id == workflow_id
        )
        
        if memory_type:
            query = query.filter(AgentMemory.memory_type == memory_type)
        
        return query.all()
    
    def clear_workflow_memory(self, workflow_id: int) -> int:
        """Clear all memory for a workflow."""
        count = self.db.query(AgentMemory).filter(
            AgentMemory.workflow_id == workflow_id
        ).delete()
        
        self.db.commit()
        return count


class MetricsService:
    """
    Service for agent metrics.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def record_execution(
        self,
        agent_id: int,
        execution_id: Optional[int] = None,
        task_id: Optional[str] = None,
        execution_time_ms: int = 0,
        queue_time_ms: int = 0,
        token_count: int = 0,
        success: bool = True,
        error_type: Optional[str] = None
    ) -> AgentMetrics:
        """Record execution metrics."""
        metrics = AgentMetrics(
            agent_id=agent_id,
            execution_id=execution_id,
            task_id=task_id,
            execution_time_ms=execution_time_ms,
            queue_time_ms=queue_time_ms,
            total_time_ms=execution_time_ms + queue_time_ms,
            token_count=token_count,
            success=success,
            error_type=error_type
        )
        
        self.db.add(metrics)
        self.db.commit()
        
        return metrics
    
    def get_agent_stats(self, agent_id: int) -> Dict[str, Any]:
        """Get statistics for an agent."""
        stats = self.db.query(
            func.count(AgentMetrics.id).label('total_executions'),
            func.avg(AgentMetrics.total_time_ms).label('avg_time_ms'),
            func.sum(AgentMetrics.token_count).label('total_tokens'),
            func.sum(
                func.case(
                    (AgentMetrics.success == True, 1),
                    else_=0
                )
            ).label('successful_executions')
        ).filter(AgentMetrics.agent_id == agent_id).first()
        
        total = stats.total_executions or 0
        successful = stats.successful_executions or 0
        
        return {
            "total_executions": total,
            "successful_executions": successful,
            "failed_executions": total - successful,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "avg_execution_time_ms": round(stats.avg_time_ms or 0, 2),
            "total_tokens": stats.total_tokens or 0
        }
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall system statistics."""
        total_executions = self.db.query(func.count(AgentMetrics.id)).scalar()
        total_agents = self.db.query(func.count(Agent.id)).scalar()
        total_workflows = self.db.query(func.count(WorkflowExecution.id)).scalar()
        
        completed_workflows = self.db.query(func.count(WorkflowExecution.id)).filter(
            WorkflowExecution.status == WorkflowStatus.COMPLETED.value
        ).scalar()
        
        return {
            "total_executions": total_executions or 0,
            "total_agents": total_agents or 0,
            "total_workflows": total_workflows or 0,
            "completed_workflows": completed_workflows or 0,
            "workflow_success_rate": (
                (completed_workflows / total_workflows * 100) 
                if total_workflows > 0 else 0
            )
        }
