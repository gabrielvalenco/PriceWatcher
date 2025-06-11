"""
Base notification handler for PriceWatcher
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BaseNotifier(ABC):
    """
    Abstract base class for all notification methods
    """
    
    @abstractmethod
    def send_notification(self, recipient: str, subject: str, message: str, data: Dict[str, Any] = None) -> bool:
        """
        Send a notification to the recipient
        
        Args:
            recipient (str): Recipient identifier (email, phone, chat ID, etc.)
            subject (str): Subject or title of the notification
            message (str): Main message content
            data (Dict[str, Any], optional): Additional data to include
            
        Returns:
            bool: True if notification was sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        """
        Check if the notifier is properly configured
        
        Returns:
            bool: True if configured, False otherwise
        """
        pass
