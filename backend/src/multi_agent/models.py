"""
Multi-Agent System Models

Database models for autonomous agent orchestration.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, 
    Boolean, JSON, Float, Index
)
from sqlalchemy.orm import relationship

from src.db.database import Base


class AgentStatus(str, Enum):
    """Agent status values."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class ExecutionStatus(str, Enum):
    """Execution status values."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class TaskStatus(str, Enum):
    """Task status values."""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowStatus(str, Enum):
    """Workflow status values."""
    PLANNING = "planning"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Agent Registry
# ============================================================================

class Agent(Base):
    """
    Registered agent in the system.
    """
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    agent_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(50), default="1.0.0")
    
    # Capabilities
    capabilities = Column(JSON, nullable=False)  # ["research", "math", "notebook"]
    supported_tools = Column(JSON, nullable=True)  # List of tool names
    
    # Metadata
    priority = Column(Integer, default=5)  # 1-10, lower = higher priority
    required_dependencies = Column(JSON, nullable=True)  # ["other_agent_id"]
    
    # Performance
    estimated_cost = Column(Float, nullable=True)  # Estimated compute cost
    estimated_latency_ms = Column(Integer, nullable=True)
    
    # Status
    status = Column(String(20), default=AgentStatus.IDLE.value)
    health_status = Column(String(20), default="healthy")
    last_heartbeat = Column(DateTime, nullable=True)
    
    # Configuration
    config = Column(JSON, nullable=True)  # Agent-specific configuration
    max_retries = Column(Integer, default=3)
    timeout_seconds = Column(Integer, default=300)
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    # executions = relationship("AgentExecution", back_populates="agent")

    __table_args__ = (
        Index('ix_agents_agent_id', 'agent_id', unique=True),
        Index('ix_agents_capabilities', 'capabilities', postgresql_using='gin'),
    )


# ============================================================================
# Workflow Execution
# ============================================================================

class WorkflowExecution(Base):
    """
    Complete workflow execution instance.
    """
    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identity
    workflow_id = Column(String(100), nullable=False)  # UUID
    title = Column(String(500), nullable=True)
    
    # User
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Goal
    goal = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)  # User context
    
    # Execution plan (DAG)
    execution_plan = Column(JSON, nullable=False)  # DAG structure
    
    # Status
    status = Column(String(20), default=WorkflowStatus.PLANNING.value)
    
    # Results
    final_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metrics
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    user = relationship("User")
    task_executions = relationship("TaskExecution", back_populates="workflow", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_workflow_user', 'user_id'),
        Index('ix_workflow_status', 'status'),
    )


# ============================================================================
# Task Execution
# ============================================================================

class TaskExecution(Base):
    """
    Individual task within a workflow.
    """
    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    
    # Workflow
    workflow_id = Column(Integer, ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False)
    
    # Task details
    task_id = Column(String(100), nullable=False)  # UUID for task
    task_name = Column(String(200), nullable=False)
    task_type = Column(String(50), nullable=True)  # research, math, notebook, etc.
    
    # Agent
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    
    # Dependencies
    depends_on = Column(JSON, nullable=True)  # List of task_ids this depends on
    
    # Execution
    status = Column(String(20), default=TaskStatus.PENDING.value)
    execution_order = Column(Integer, default=0)  # Execution order in DAG
    is_parallel = Column(Boolean, default=True)
    
    # Input/Output
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    
    # Error handling
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    fallback_agent_id = Column(Integer, ForeignKey("agents.id"), nullable=True)
    
    # Metrics
    execution_time_ms = Column(Integer, nullable=True)
    estimated_time_ms = Column(Integer, nullable=True)
    
    # Timestamps
    ready_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="task_executions")
    agent = relationship("Agent", foreign_keys=[agent_id])

    __table_args__ = (
        Index('ix_task_workflow', 'workflow_id'),
        Index('ix_task_status', 'status'),
        Index('ix_task_agent', 'agent_id'),
    )


# ============================================================================
# Agent Memory
# ============================================================================

class AgentMemory(Base):
    """
    Agent memory store for shared context.
    """
    __tablename__ = "agent_memory"

    id = Column(Integer, primary_key=True, index=True)
    
    # Workflow/Execution context
    workflow_id = Column(Integer, ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=True)
    task_id = Column(String(100), nullable=True)
    
    # Memory type
    memory_type = Column(String(50), nullable=False)  # conversation, workspace, research, task, execution
    
    # Content
    key = Column(String(200), nullable=False)
    value = Column(JSON, nullable=False)
    
    # Scope
    scope = Column(String(20), default="workflow")  # workflow, agent, user, global
    
    # TTL
    expires_at = Column(DateTime, nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    __table_args__ = (
        Index('ix_memory_workflow', 'workflow_id'),
        Index('ix_memory_task', 'task_id'),
        Index('ix_memory_type', 'memory_type'),
        Index('ix_memory_scope', 'scope'),
    )


# ============================================================================
# Agent Metrics
# ============================================================================

class AgentMetrics(Base):
    """
    Agent performance metrics.
    """
    __tablename__ = "agent_metrics"

    id = Column(Integer, primary_key=True, index=True)
    
    # Agent
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    # Execution context
    execution_id = Column(Integer, ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(String(100), nullable=True)
    
    # Metrics
    execution_time_ms = Column(Integer, nullable=True)
    queue_time_ms = Column(Integer, nullable=True)
    total_time_ms = Column(Integer, nullable=True)
    
    # Counts
    token_count = Column(Integer, nullable=True)
    api_calls = Column(Integer, default=1)
    
    # Status
    success = Column(Boolean, default=True)
    error_type = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    # Relationships
    agent = relationship("Agent")

    __table_args__ = (
        Index('ix_metrics_agent', 'agent_id'),
        Index('ix_metrics_execution', 'execution_id'),
    )


# ============================================================================
# Agent Communication
# ============================================================================

class AgentEvent(Base):
    """
    Event log for agent communication.
    """
    __tablename__ = "agent_events"

    id = Column(Integer, primary_key=True, index=True)
    
    # Event context
    workflow_id = Column(Integer, ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=True)
    task_id = Column(String(100), nullable=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # TaskCreated, TaskStarted, etc.
    message = Column(Text, nullable=True)
    data = Column(JSON, nullable=True)
    
    # Actor
    actor_type = Column(String(20), nullable=True)  # system, agent, user
    actor_id = Column(String(100), nullable=True)
    
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
        nullable=False
    )

    __table_args__ = (
        Index('ix_events_workflow', 'workflow_id'),
        Index('ix_events_task', 'task_id'),
        Index('ix_events_type', 'event_type'),
    )
