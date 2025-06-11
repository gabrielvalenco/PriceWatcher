"""
Telegram notification handler for PriceWatcher
"""
import os
import logging
from typing import Dict, Any, Optional

import telegram
from telegram.error import TelegramError

from .base import BaseNotifier

logger = logging.getLogger(__name__)

class TelegramNotifier(BaseNotifier):
    """
    Notification handler for Telegram
    """
    
    def __init__(self):
        """Initialize the Telegram notifier"""
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.bot = None
        if self.token:
            try:
                self.bot = telegram.Bot(token=self.token)
                logger.info("Telegram notifier initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Telegram notifier: {str(e)}")
                self.bot = None
        else:
            logger.warning("TELEGRAM_BOT_TOKEN not set, Telegram notifications will be disabled")
    
    def is_configured(self) -> bool:
        """
        Check if the Telegram notifier is properly configured
        
        Returns:
            bool: True if configured, False otherwise
        """
        return self.bot is not None
        
    def send_notification(self, recipient: str, subject: str, message: str, data: Dict[str, Any] = None) -> bool:
        """
        Send a notification via Telegram
        
        Args:
            recipient (str): Telegram chat ID to send message to
            subject (str): Subject line (will be used as message title)
            message (str): Message body
            data (Dict[str, Any], optional): Additional data (product info, etc.)
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.error("Telegram notifier not configured")
            return False
        
        try:
            # Format message with Markdown
            formatted_message = f"*{subject}*\n\n{message}"
            
            # Add product information if available
            if data and 'product' in data:
                product = data['product']
                formatted_message += f"\n\n*Product:* {product.get('name', 'N/A')}"
                
                if 'current_price' in product and 'currency' in product:
                    formatted_message += f"\n*Current Price:* {product['current_price']} {product['currency']}"
                
                if 'target_price' in product:
                    formatted_message += f"\n*Target Price:* {product['target_price']} {product.get('currency', 'USD')}"
                
                if 'url' in product:
                    formatted_message += f"\n\n[View Product]({product['url']})"
            
            # Send message
            self.bot.send_message(
                chat_id=recipient,
                text=formatted_message,
                parse_mode=telegram.ParseMode.MARKDOWN,
                disable_web_page_preview=False
            )
            
            logger.info(f"Telegram notification sent to {recipient}")
            return True
            
        except TelegramError as e:
            logger.error(f"Telegram error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
            return False
