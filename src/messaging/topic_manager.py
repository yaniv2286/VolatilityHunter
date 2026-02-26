"""
Topic Manager - Topic management for message bus
"""

import logging
from typing import Dict, List, Set
from ..interfaces.message_interface import TopicManagerInterface

class TopicManager(TopicManagerInterface):
    """Topic manager implementation"""
    
    def __init__(self):
        self.logger = logging.getLogger("topic_manager")
        self.topics: Dict[str, Set[str]] = {}
        self.topic_metadata: Dict[str, Dict[str, any]] = {}
        
    def create_topic(self, topic_name: str) -> bool:
        """Create new topic"""
        try:
            if topic_name in self.topics:
                self.logger.warning(f"Topic {topic_name} already exists")
                return False
                
            self.topics[topic_name] = set()
            self.topic_metadata[topic_name] = {
                "created_at": self._get_timestamp(),
                "subscriber_count": 0,
                "message_count": 0
            }
            
            self.logger.info(f"Created topic: {topic_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating topic {topic_name}: {e}")
            return False
            
    def delete_topic(self, topic_name: str) -> bool:
        """Delete topic"""
        try:
            if topic_name not in self.topics:
                self.logger.warning(f"Topic {topic_name} does not exist")
                return False
                
            del self.topics[topic_name]
            del self.topic_metadata[topic_name]
            
            self.logger.info(f"Deleted topic: {topic_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting topic {topic_name}: {e}")
            return False
            
    def list_topics(self) -> List[str]:
        """List all topics"""
        return list(self.topics.keys())
        
    def get_topic_subscribers(self, topic_name: str) -> List[str]:
        """Get subscribers for topic"""
        return list(self.topics.get(topic_name, set()))
        
    def add_subscriber(self, topic_name: str, subscriber_id: str) -> bool:
        """Add subscriber to topic"""
        try:
            if topic_name not in self.topics:
                self.create_topic(topic_name)
                
            self.topics[topic_name].add(subscriber_id)
            self.topic_metadata[topic_name]["subscriber_count"] = len(self.topics[topic_name])
            
            self.logger.debug(f"Added subscriber {subscriber_id} to topic {topic_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding subscriber to topic {topic_name}: {e}")
            return False
            
    def remove_subscriber(self, topic_name: str, subscriber_id: str) -> bool:
        """Remove subscriber from topic"""
        try:
            if topic_name not in self.topics:
                return False
                
            self.topics[topic_name].discard(subscriber_id)
            self.topic_metadata[topic_name]["subscriber_count"] = len(self.topics[topic_name])
            
            self.logger.debug(f"Removed subscriber {subscriber_id} from topic {topic_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing subscriber from topic {topic_name}: {e}")
            return False
            
    def get_topic_metadata(self, topic_name: str) -> Dict[str, any]:
        """Get topic metadata"""
        return self.topic_metadata.get(topic_name, {})
        
    def increment_message_count(self, topic_name: str):
        """Increment message count for topic"""
        if topic_name in self.topic_metadata:
            self.topic_metadata[topic_name]["message_count"] += 1
            
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
        
    def get_statistics(self) -> Dict[str, any]:
        """Get topic manager statistics"""
        return {
            "total_topics": len(self.topics),
            "total_subscribers": sum(len(subscribers) for subscribers in self.topics.values()),
            "topics": list(self.topics.keys())
        }
