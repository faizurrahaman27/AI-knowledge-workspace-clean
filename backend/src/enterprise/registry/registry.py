"""
Agent Registry

Registry for discovering, registering, and managing agents.
Supports capability-based lookup and load balancing across agent instances.
"""

from typing import Optional
from collections import defaultdict

from src.enterprise.orchestrator.base import BaseAgent, AgentCapability, AgentStatus


class AgentRegistry:
    """
    Registry for managing agent instances.
    
    Provides:
    - Agent registration and unregistration
    - Capability-based agent discovery
    - Load balancing across multiple agents with same capability
    - Agent metadata queries
    
    Usage:
        registry = AgentRegistry()
        registry.register(my_agent)
        
        # Find agent for capability
        agent = registry.get_agent_for_capability(AgentCapability.QA)
        
        # Get all agents with capability
        agents = registry.get_agents_with_capability(AgentCapability.QA)
    """
    
    def __init__(self):
        # agent_id -> BaseAgent
        self._agents_by_id: dict[str, BaseAgent] = {}
        # AgentCapability -> list of agent_ids (for lookup order)
        self._agents_by_capability: dict[AgentCapability, list[str]] = defaultdict(list)
        # agent_id -> list of capabilities
        self._capabilities_by_agent: dict[str, list[AgentCapability]] = defaultdict(list)
    
    def register(self, agent: BaseAgent) -> None:
        """
        Register an agent in the registry.
        
        Args:
            agent: The agent instance to register
            
        Raises:
            ValueError: If agent is already registered
        """
        agent_id = agent.metadata.agent_id
        
        if agent_id in self._agents_by_id:
            raise ValueError(f"Agent {agent_id} is already registered")
        
        self._agents_by_id[agent_id] = agent
        
        # Index by capabilities
        for capability in agent.metadata.capabilities:
            self._capabilities_by_agent[agent_id].append(capability)
            if agent_id not in self._agents_by_capability[capability]:
                self._agents_by_capability[capability].append(agent_id)
    
    def unregister(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            True if the agent was found and removed, False otherwise
        """
        if agent_id not in self._agents_by_id:
            return False
        
        agent = self._agents_by_id.pop(agent_id)
        
        # Remove from capability indexes
        for capability in agent.metadata.capabilities:
            if agent_id in self._agents_by_capability[capability]:
                self._agents_by_capability[capability].remove(agent_id)
        
        del self._capabilities_by_agent[agent_id]
        
        return True
    
    def get_agent_by_id(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get an agent by its ID.
        
        Args:
            agent_id: The unique agent identifier
            
        Returns:
            The agent if found, None otherwise
        """
        return self._agents_by_id.get(agent_id)
    
    def get_agent_for_capability(
        self,
        capability: AgentCapability,
        prefer_available: bool = True
    ) -> Optional[BaseAgent]:
        """
        Get the best available agent for a capability.
        
        Uses round-robin among available agents with the same capability
        to distribute load evenly.
        
        Args:
            capability: The required capability
            prefer_available: If True, prefer agents that are available
                              (not at max capacity). If False, return any agent.
            
        Returns:
            The best available agent for the capability, or None if no agent exists
        """
        agent_ids = self._agents_by_capability.get(capability, [])
        
        if not agent_ids:
            return None
        
        # Try to find an available agent first
        if prefer_available:
            for agent_id in agent_ids:
                agent = self._agents_by_id.get(agent_id)
                if agent and agent.is_available:
                    return agent
        
        # Fall back to any agent with the capability
        for agent_id in agent_ids:
            agent = self._agents_by_id.get(agent_id)
            if agent and agent.status != AgentStatus.DISABLED:
                return agent
        
        return None
    
    def get_agents_with_capability(self, capability: AgentCapability) -> list[BaseAgent]:
        """
        Get all agents that have a specific capability.
        
        Args:
            capability: The capability to filter by
            
        Returns:
            List of agents with the capability
        """
        agent_ids = self._agents_by_capability.get(capability, [])
        return [
            self._agents_by_id[aid]
            for aid in agent_ids
            if aid in self._agents_by_id
        ]
    
    def get_agents_by_tag(self, tag: str) -> list[BaseAgent]:
        """
        Get all agents with a specific tag.
        
        Args:
            tag: The tag to filter by
            
        Returns:
            List of agents with the tag
        """
        return [
            agent for agent in self._agents_by_id.values()
            if tag in agent.metadata.tags
        ]
    
    def get_all_agents(self) -> list[BaseAgent]:
        """
        Get all registered agents.
        
        Returns:
            List of all agents
        """
        return list(self._agents_by_id.values())
    
    def get_agents_by_status(self, status: AgentStatus) -> list[BaseAgent]:
        """
        Get all agents with a specific status.
        
        Args:
            status: The status to filter by
            
        Returns:
            List of agents with the status
        """
        return [
            agent for agent in self._agents_by_id.values()
            if agent.status == status
        ]
    
    def search_agents(self, query: str) -> list[BaseAgent]:
        """
        Search agents by name, description, or tags.
        
        Case-insensitive partial matching.
        
        Args:
            query: Search query
            
        Returns:
            List of matching agents
        """
        query_lower = query.lower()
        results = []
        
        for agent in self._agents_by_id.values():
            metadata = agent.metadata
            
            # Check name
            if query_lower in metadata.name.lower():
                results.append(agent)
                continue
            
            # Check description
            if query_lower in metadata.description.lower():
                results.append(agent)
                continue
            
            # Check tags
            if any(query_lower in tag.lower() for tag in metadata.tags):
                results.append(agent)
                continue
        
        return results
    
    def get_capability_summary(self) -> dict[str, int]:
        """
        Get a summary of available capabilities and agent counts.
        
        Returns:
            Dict mapping capability names to agent counts
        """
        return {
            capability.value: len(agents)
            for capability, agents in self._agents_by_capability.items()
        }
    
    def __len__(self) -> int:
        """Return the number of registered agents."""
        return len(self._agents_by_id)
    
    def __contains__(self, agent_id: str) -> bool:
        """Check if an agent is registered."""
        return agent_id in self._agents_by_id
