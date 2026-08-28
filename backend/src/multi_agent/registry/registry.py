"""
Agent Registry

Dynamic plugin architecture for agent registration and discovery.
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class AgentCapabilities:
    """Agent capabilities definition."""
    research: bool = False
    math: bool = False
    notebook: bool = False
    web_search: bool = False
    github: bool = False
    document_analysis: bool = False
    flashcard_generation: bool = False
    quiz_generation: bool = False
    code_execution: bool = False
    visualization: bool = False
    analytics: bool = False
    job_hunting: bool = False
    data_processing: bool = False


@dataclass
class AgentMetadata:
    """Agent metadata for registry."""
    agent_id: str
    name: str
    description: str
    version: str = "1.0.0"
    capabilities: AgentCapabilities = field(default_factory=AgentCapabilities)
    priority: int = 5
    required_dependencies: List[str] = field(default_factory=list)
    supported_tools: List[str] = field(default_factory=list)
    estimated_cost: float = 1.0
    estimated_latency_ms: int = 5000
    max_retries: int = 3
    timeout_seconds: int = 300
    health_status: str = "healthy"
    last_heartbeat: Optional[datetime] = None


class AgentRegistry:
    """
    Dynamic agent registry with plugin architecture.
    
    Agents register themselves with capabilities.
    The registry matches requests to capable agents.
    """
    
    def __init__(self):
        """Initialize the agent registry."""
        self._agents: Dict[str, AgentMetadata] = {}
        self._capability_index: Dict[str, List[str]] = {}  # capability -> [agent_ids]
        self._hooks: Dict[str, List[Callable]] = {
            "agent_registered": [],
            "agent_unregistered": [],
            "agent_invoked": [],
            "agent_completed": [],
        }
    
    def register(self, metadata: AgentMetadata) -> bool:
        """
        Register an agent.
        
        Args:
            metadata: Agent metadata
            
        Returns:
            True if registered successfully
        """
        if metadata.agent_id in self._agents:
            logger.warning(f"Agent {metadata.agent_id} already registered, updating")
        
        self._agents[metadata.agent_id] = metadata
        
        # Update capability index
        for capability, enabled in self._capabilities_to_dict(metadata.capabilities).items():
            if enabled:
                if capability not in self._capability_index:
                    self._capability_index[capability] = []
                if metadata.agent_id not in self._capability_index[capability]:
                    self._capability_index[capability].append(metadata.agent_id)
        
        # Trigger hooks
        for hook in self._hooks.get("agent_registered", []):
            try:
                hook(metadata)
            except Exception as e:
                logger.error(f"Hook failed: {e}")
        
        logger.info(f"Registered agent: {metadata.agent_id} ({metadata.name})")
        return True
    
    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if unregistered successfully
        """
        if agent_id not in self._agents:
            return False
        
        metadata = self._agents[agent_id]
        
        # Remove from capability index
        for capability, enabled in self._capabilities_to_dict(metadata.capabilities).items():
            if enabled and capability in self._capability_index:
                if agent_id in self._capability_index[capability]:
                    self._capability_index[capability].remove(agent_id)
        
        # Remove agent
        del self._agents[agent_id]
        
        # Trigger hooks
        for hook in self._hooks.get("agent_unregistered", []):
            try:
                hook(metadata)
            except Exception as e:
                logger.error(f"Hook failed: {e}")
        
        logger.info(f"Unregistered agent: {agent_id}")
        return True
    
    def get(self, agent_id: str) -> Optional[AgentMetadata]:
        """Get agent by ID."""
        return self._agents.get(agent_id)
    
    def get_all(self) -> List[AgentMetadata]:
        """Get all registered agents."""
        return list(self._agents.values())
    
    def find_by_capability(
        self,
        capabilities: List[str],
        match_all: bool = False
    ) -> List[AgentMetadata]:
        """
        Find agents by capabilities.
        
        Args:
            capabilities: List of required capabilities
            match_all: If True, agent must have ALL capabilities
            
        Returns:
            List of matching agents
        """
        if match_all:
            # Agent must have all capabilities
            matching = []
            for agent in self._agents.values():
                agent_caps = self._capabilities_to_dict(agent.capabilities)
                if all(cap in agent_caps and agent_caps[cap] for cap in capabilities):
                    matching.append(agent)
            return sorted(matching, key=lambda a: a.priority)
        else:
            # Agent must have ANY capability
            matching_ids = set()
            for cap in capabilities:
                if cap in self._capability_index:
                    matching_ids.update(self._capability_index[cap])
            
            matching = [self._agents[aid] for aid in matching_ids if aid in self._agents]
            return sorted(matching, key=lambda a: a.priority)
    
    def find_best(
        self,
        capabilities: List[str],
        exclude_ids: Optional[List[str]] = None
    ) -> Optional[AgentMetadata]:
        """
        Find the best agent for capabilities.
        
        Args:
            capabilities: Required capabilities
            exclude_ids: Agent IDs to exclude
            
        Returns:
            Best matching agent or None
        """
        candidates = self.find_by_capability(capabilities)
        
        if exclude_ids:
            candidates = [a for a in candidates if a.agent_id not in exclude_ids]
        
        return candidates[0] if candidates else None
    
    def update_health(self, agent_id: str, status: str) -> bool:
        """Update agent health status."""
        if agent_id not in self._agents:
            return False
        
        self._agents[agent_id].health_status = status
        self._agents[agent_id].last_heartbeat = datetime.utcnow()
        return True
    
    def get_healthy_agents(self) -> List[AgentMetadata]:
        """Get all healthy agents."""
        return [
            a for a in self._agents.values()
            if a.health_status == "healthy"
        ]
    
    def register_hook(self, event: str, hook: Callable) -> None:
        """Register a hook for events."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(hook)
    
    def _capabilities_to_dict(self, capabilities: AgentCapabilities) -> Dict[str, bool]:
        """Convert capabilities to dictionary."""
        return {
            "research": capabilities.research,
            "math": capabilities.math,
            "notebook": capabilities.notebook,
            "web_search": capabilities.web_search,
            "github": capabilities.github,
            "document_analysis": capabilities.document_analysis,
            "flashcard_generation": capabilities.flashcard_generation,
            "quiz_generation": capabilities.quiz_generation,
            "code_execution": capabilities.code_execution,
            "visualization": capabilities.visualization,
            "analytics": capabilities.analytics,
            "job_hunting": capabilities.job_hunting,
            "data_processing": capabilities.data_processing,
        }


# Global registry instance
_agent_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry."""
    global _agent_registry
    if _agent_registry is None:
        _agent_registry = AgentRegistry()
    return _agent_registry
