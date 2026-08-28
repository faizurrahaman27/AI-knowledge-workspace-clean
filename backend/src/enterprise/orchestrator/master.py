"""
Master Orchestrator

Central coordinator for all agents in the enterprise architecture.
Manages agent lifecycle, routes requests to appropriate agents,
and orchestrates complex multi-agent workflows.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from src.enterprise.orchestrator.base import (
    BaseAgent, AgentCapability, AgentContext, AgentMetadata,
    AgentResult, AgentStatus
)
from src.enterprise.registry.registry import AgentRegistry
from src.enterprise.dispatcher.task_dispatcher import TaskDispatcher, Task, TaskPriority
from src.enterprise.events.manager import EnterpriseEventManager, EventType, WorkflowEvent
from src.core.logging import logger


@dataclass
class OrchestrationResult:
    """Result from orchestrating a complex workflow."""
    workflow_id: str
    success: bool
    primary_output: Any = None
    agent_results: dict[str, AgentResult] = field(default_factory=dict)
    total_execution_time_ms: int = 0
    errors: list[str] = field(default_factory=list)


class MasterOrchestrator:
    """
    Central orchestrator for agent coordination and workflow execution.
    
    Responsibilities:
    - Agent lifecycle management (register, initialize, shutdown)
    - Request routing to appropriate agents based on capabilities
    - Multi-agent workflow orchestration
    - Event emission for real-time progress updates
    - Error handling and recovery
    
    Usage:
        orchestrator = MasterOrchestrator()
        
        # Register agents
        orchestrator.register_agent(my_agent)
        
        # Execute a task with the best available agent
        result = await orchestrator.route_request(
            capability=AgentCapability.QUESTION_ANSWERING,
            context=AgentContext(task_id="123", user_id=1)
        )
        
        # Execute a multi-agent workflow
        workflow_result = await orchestrator.execute_workflow(
            steps=[...],
            context=AgentContext(task_id="456", user_id=1)
        )
    """
    
    def __init__(
        self,
        registry: Optional[AgentRegistry] = None,
        dispatcher: Optional[TaskDispatcher] = None,
        event_manager: Optional[EnterpriseEventManager] = None
    ):
        self._registry = registry or AgentRegistry()
        self._dispatcher = dispatcher or TaskDispatcher()
        self._event_manager = event_manager or EnterpriseEventManager()
        self._initialized = False
        self._active_workflows: dict[str, dict] = {}
    
    @property
    def registry(self) -> AgentRegistry:
        """Access the agent registry."""
        return self._registry
    
    async def initialize(self) -> None:
        """
        Initialize the orchestrator and all registered agents.
        Should be called once at application startup.
        """
        if self._initialized:
            return
        
        logger.info("Initializing Master Orchestrator...")
        
        # Initialize all registered agents
        for agent in self._registry.get_all_agents():
            try:
                await agent.initialize()
                logger.info(f"Initialized agent: {agent.metadata.name}")
            except Exception as e:
                logger.error(f"Failed to initialize agent {agent.metadata.agent_id}: {e}")
        
        self._initialized = True
        logger.info(f"Master Orchestrator initialized with {len(self._registry)} agents")
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown all agents and release resources.
        """
        logger.info("Shutting down Master Orchestrator...")
        
        for agent in self._registry.get_all_agents():
            try:
                await agent.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down agent {agent.metadata.agent_id}: {e}")
        
        self._initialized = False
        logger.info("Master Orchestrator shutdown complete")
    
    def register_agent(self, agent: BaseAgent) -> str:
        """
        Register an agent with the orchestrator.
        
        Args:
            agent: The agent instance to register
            
        Returns:
            The agent_id of the registered agent
        """
        self._registry.register(agent)
        logger.info(f"Registered agent: {agent.metadata.name} ({agent.metadata.agent_id})")
        return agent.metadata.agent_id
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the orchestrator.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            True if the agent was found and removed
        """
        return self._registry.unregister(agent_id)
    
    async def route_request(
        self,
        capability: AgentCapability,
        context: AgentContext,
        prefer_agent_id: Optional[str] = None
    ) -> AgentResult:
        """
        Route a request to the best available agent for the capability.
        
        Args:
            capability: Required capability for the task
            context: Execution context with task details
            prefer_agent_id: Optional agent ID to prefer (e.g., user selection)
            
        Returns:
            AgentResult from the executed agent
            
        Raises:
            ValueError: If no suitable agent is found
        """
        # Find the best agent for the capability
        if prefer_agent_id:
            agent = self._registry.get_agent_by_id(prefer_agent_id)
            if agent and capability in agent.metadata.capabilities:
                return await self._execute_with_agent(agent, context)
        
        agent = self._registry.get_agent_for_capability(capability)
        if not agent:
            raise ValueError(f"No agent available for capability: {capability.value}")
        
        return await self._execute_with_agent(agent, context)
    
    async def route_request_with_fallback(
        self,
        capabilities: list[AgentCapability],
        context: AgentContext
    ) -> AgentResult:
        """
        Route a request, trying multiple capabilities in order.
        
        Args:
            capabilities: Ordered list of capabilities to try
            context: Execution context with task details
            
        Returns:
            AgentResult from the first successful agent
        """
        for capability in capabilities:
            try:
                return await self.route_request(capability, context)
            except ValueError:
                continue
        
        raise ValueError(f"No agent found for any of: {[c.value for c in capabilities]}")
    
    async def execute_workflow(
        self,
        steps: list[dict],
        context: AgentContext
    ) -> OrchestrationResult:
        """
        Execute a multi-step workflow using appropriate agents.
        
        Args:
            steps: List of workflow steps, each with:
                - capability: Required agent capability
                - name: Step name
                - parameters: Additional parameters for the step
            context: Base execution context
            
        Returns:
            OrchestrationResult with all agent outputs
        """
        workflow_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Starting workflow {workflow_id} with {len(steps)} steps")
        
        # Emit workflow start event
        await self._event_manager.emit(WorkflowEvent(
            event_type=EventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            user_id=context.user_id,
            workspace_id=context.workspace_id,
            data={"total_steps": len(steps)}
        ))
        
        result = OrchestrationResult(
            workflow_id=workflow_id,
            success=True,
            agent_results={}
        )
        
        # Execute each step in sequence
        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i}")
            capability = step.get("capability")
            parameters = step.get("parameters", {})
            
            if not capability:
                result.errors.append(f"Step {i}: Missing capability")
                result.success = False
                continue
            
            # Update context for this step
            step_context = AgentContext(
                task_id=f"{context.task_id}_step_{i}",
                user_id=context.user_id,
                workspace_id=context.workspace_id,
                document_ids=context.document_ids,
                parameters={**context.parameters, **parameters},
                metadata={**context.metadata, "workflow_id": workflow_id, "step_index": i},
                trace_enabled=context.trace_enabled
            )
            
            # Emit step start event
            await self._event_manager.emit(WorkflowEvent(
                event_type=EventType.WORKFLOW_STEP_STARTED,
                workflow_id=workflow_id,
                user_id=context.user_id,
                workspace_id=context.workspace_id,
                data={"step": step_name, "step_index": i, "capability": capability.value if isinstance(capability, AgentCapability) else capability}
            ))
            
            try:
                agent_result = await self.route_request(capability, step_context)
                result.agent_results[step_name] = agent_result
                
                if not agent_result.success:
                    result.errors.append(f"Step {step_name} failed: {agent_result.error}")
                    result.success = False
                    break
                
                # Pass artifacts to next step context
                if agent_result.artifacts:
                    context.metadata[f"{step_name}_artifacts"] = agent_result.artifacts
                
                # Emit step complete event
                await self._event_manager.emit(WorkflowEvent(
                    event_type=EventType.WORKFLOW_STEP_COMPLETED,
                    workflow_id=workflow_id,
                    user_id=context.user_id,
                    workspace_id=context.workspace_id,
                    data={
                        "step": step_name,
                        "step_index": i,
                        "execution_time_ms": agent_result.execution_time_ms,
                        "artifacts": list(agent_result.artifacts.keys()) if agent_result.artifacts else []
                    }
                ))
                
            except Exception as e:
                result.errors.append(f"Step {step_name} exception: {str(e)}")
                result.success = False
                break
        
        result.total_execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Emit workflow complete event
        await self._event_manager.emit(WorkflowEvent(
            event_type=EventType.WORKFLOW_COMPLETED if result.success else EventType.WORKFLOW_FAILED,
            workflow_id=workflow_id,
            user_id=context.user_id,
            workspace_id=context.workspace_id,
            data={
                "success": result.success,
                "total_execution_time_ms": result.total_execution_time_ms,
                "steps_completed": len(result.agent_results),
                "errors": result.errors
            }
        ))
        
        logger.info(f"Workflow {workflow_id} completed in {result.total_execution_time_ms}ms: success={result.success}")
        
        return result
    
    async def _execute_with_agent(self, agent: BaseAgent, context: AgentContext) -> AgentResult:
        """Execute a task with a specific agent, handling errors and events."""
        start_time = time.time()
        
        # Emit agent start event
        await self._event_manager.emit(WorkflowEvent(
            event_type=EventType.AGENT_STARTED,
            workflow_id=context.metadata.get("workflow_id", ""),
            user_id=context.user_id,
            workspace_id=context.workspace_id,
            data={
                "agent_id": agent.metadata.agent_id,
                "agent_name": agent.metadata.name,
                "task_id": context.task_id
            }
        ))
        
        try:
            agent._mark_busy()
            result = await agent.execute(context)
            result.execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Emit agent complete event
            await self._event_manager.emit(WorkflowEvent(
                event_type=EventType.AGENT_COMPLETED,
                workflow_id=context.metadata.get("workflow_id", ""),
                user_id=context.user_id,
                workspace_id=context.workspace_id,
                data={
                    "agent_id": agent.metadata.agent_id,
                    "task_id": context.task_id,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms
                }
            ))
            
            return result
            
        except Exception as e:
            error_result = AgentResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000)
            )
            agent._set_error(str(e))
            
            # Emit agent error event
            await self._event_manager.emit(WorkflowEvent(
                event_type=EventType.AGENT_ERROR,
                workflow_id=context.metadata.get("workflow_id", ""),
                user_id=context.user_id,
                workspace_id=context.workspace_id,
                data={
                    "agent_id": agent.metadata.agent_id,
                    "task_id": context.task_id,
                    "error": str(e)
                }
            ))
            
            return error_result
            
        finally:
            agent._mark_idle()
    
    def get_system_status(self) -> dict:
        """Get overall system status for health checks."""
        agents = self._registry.get_all_agents()
        
        status_by_capability = {}
        for agent in agents:
            for cap in agent.metadata.capabilities:
                if cap.value not in status_by_capability:
                    status_by_capability[cap.value] = []
                status_by_capability[cap.value].append({
                    "agent_id": agent.metadata.agent_id,
                    "name": agent.metadata.name,
                    "status": agent.status.value,
                    "available": agent.is_available
                })
        
        return {
            "initialized": self._initialized,
            "total_agents": len(agents),
            "ready_agents": sum(1 for a in agents if a.status == AgentStatus.READY),
            "busy_agents": sum(1 for a in agents if a.status == AgentStatus.BUSY),
            "error_agents": sum(1 for a in agents if a.status == AgentStatus.ERROR),
            "capabilities": status_by_capability,
            "active_workflows": len(self._active_workflows)
        }
