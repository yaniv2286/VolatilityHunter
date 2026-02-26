"""
Agent Factory - Factory for creating agents
"""

import logging
from typing import Dict, Any, Type, Optional, List
from ..interfaces.agent_interface import AgentInterface, AgentStatus

class AgentFactory:
    """Factory for creating agents"""
    
    def __init__(self, config_manager=None):
        self.logger = logging.getLogger("agent_factory")
        self.config_manager = config_manager
        self._agent_registry: Dict[str, Type[AgentInterface]] = {}
        self._agent_configs: Dict[str, Dict[str, Any]] = {}
        
    def register_agent(self, agent_type: str, agent_class: Type[AgentInterface]):
        """Register agent class"""
        self._agent_registry[agent_type] = agent_class
        self.logger.info(f"Registered agent type: {agent_type}")
        
    def create_agent(self, agent_type: str, agent_id: str, config: Dict[str, Any] = None) -> Optional[AgentInterface]:
        """Create agent instance"""
        try:
            # Get agent class - try both the agent_type and agent_id as keys
            agent_class = self._agent_registry.get(agent_type)
            if not agent_class:
                # Try to find by looking through configs for matching agent_id
                for config_key, config_data in self._agent_configs.items():
                    if config_data.get("agent_id") == agent_id:
                        agent_class = self._agent_registry.get(config_data.get("agent_type"))
                        if agent_class:
                            agent_type = config_data.get("agent_type")
                            break
            
            if not agent_class:
                self.logger.error(f"Unknown agent type: {agent_type}")
                return None
                
            # Get configuration
            if config is None:
                config = self._agent_configs.get(agent_id, {})
                if not config:
                    # Try to find config by agent_type
                    for config_key, config_data in self._agent_configs.items():
                        if config_data.get("agent_type") == agent_type:
                            config = config_data
                            break
                
            # Create agent instance
            agent = agent_class(agent_id, config)
            
            self.logger.info(f"Created agent {agent_id} of type {agent_type}")
            return agent
            
        except Exception as e:
            self.logger.error(f"Error creating agent {agent_id} of type {agent_type}: {e}")
            return None
            
    def create_all_agents(self, agent_configs: Dict[str, Dict[str, Any]]) -> Dict[str, AgentInterface]:
        """Create all agents from configuration"""
        agents = {}
        
        for config_key, config in agent_configs.items():
            # Use agent_id from config
            agent_id = config.get("agent_id", config_key)
            agent_type = config.get("agent_type", config_key)
            
            agent = self.create_agent(agent_type, agent_id, config)
            if agent:
                agents[agent_id] = agent
                    
        self.logger.info(f"Created {len(agents)} agents")
        return agents
        
    def load_agent_configs(self, config_path: str = None) -> Dict[str, Dict[str, Any]]:
        """Load agent configurations"""
        try:
            if config_path is None:
                config_path = "config/agents.json"
                
            if self.config_manager:
                configs = self.config_manager.load_config(config_path)
            else:
                # Fallback to direct file loading
                import json
                with open(config_path, 'r') as f:
                    configs = json.load(f)
                    
            self._agent_configs = configs
            self.logger.info(f"Loaded agent configurations from {config_path}")
            return configs
            
        except Exception as e:
            self.logger.error(f"Error loading agent configurations: {e}")
            return {}
            
    def get_available_agent_types(self) -> List[str]:
        """Get available agent types"""
        return list(self._agent_registry.keys())
        
    def get_agent_config_template(self, agent_type: str) -> Dict[str, Any]:
        """Get configuration template for agent type"""
        # This would typically load from a template file or generate based on agent class
        return {
            "agent_id": f"{agent_type}_001",
            "enabled": True,
            "log_level": "INFO",
            "retry_attempts": 3,
            "timeout": 30
        }
        
    def validate_agent_config(self, agent_type: str, config: Dict[str, Any]) -> bool:
        """Validate agent configuration"""
        try:
            # Basic validation
            if not config.get("agent_id"):
                self.logger.error(f"Agent config missing agent_id for {agent_type}")
                return False
                
            if not isinstance(config.get("enabled"), bool):
                self.logger.error(f"Agent config invalid enabled field for {agent_type}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating agent config for {agent_type}: {e}")
            return False
            
    def get_factory_info(self) -> Dict[str, Any]:
        """Get factory information"""
        return {
            "registered_agents": list(self._agent_registry.keys()),
            "loaded_configs": list(self._agent_configs.keys()),
            "total_registered": len(self._agent_registry),
            "total_configs": len(self._agent_configs)
        }
