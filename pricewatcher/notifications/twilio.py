"""
Twilio notification handler for PriceWatcher (SMS and WhatsApp)
"""
import os
import logging
from typing import Dict, Any

from .base import BaseNotifier

logger = logging.getLogger(__name__)

class TwilioNotifier(BaseNotifier):
    """
    Notification handler for SMS and WhatsApp via Twilio
    """
    
    def __init__(self):
        """Initialize the Twilio notifier"""
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        
        self.client = None
        if all([self.account_sid, self.auth_token, self.from_number]):
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio notifier initialized successfully")
            except ImportError:
                logger.error("Twilio package not installed. Install with: pip install twilio")
            except Exception as e:
                logger.error(f"Error initializing Twilio notifier: {str(e)}")
                self.client = None
        else:
            logger.warning("Twilio configuration incomplete, SMS/WhatsApp notifications will be disabled")
    
    def is_configured(self) -> bool:
        """
        Check if the Twilio notifier is properly configured
        
        Returns:
            bool: True if configured, False otherwise
        """
        return self.client is not None
        
    def send_notification(self, recipient: str, subject: str, message: str, data: Dict[str, Any] = None) -> bool:
        """
        Send a notification via SMS or WhatsApp
        
        Args:
            recipient (str): Phone number to send to (with country code, e.g., +1234567890)
            subject (str): Subject line (will be included in message body)
            message (str): Message body
            data (Dict[str, Any], optional): Additional data (product info, etc.)
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.error("Twilio notifier not configured")
            return False
        
        try:
            # Check if recipient is for WhatsApp (prefixed with "whatsapp:")
            is_whatsapp = recipient.startswith("whatsapp:")
            to_number = recipient
            from_number = self.from_number
            
            # If this is a WhatsApp message but recipient doesn't have the prefix, add it
            if 'whatsapp' in data and data['whatsapp'] and not is_whatsapp:
                to_number = f"whatsapp:{recipient}"
                from_number = f"whatsapp:{self.from_number}"
            # If this is a WhatsApp recipient but from_number doesn't have prefix, add it
            elif is_whatsapp and not self.from_number.startswith("whatsapp:"):
                from_number = f"whatsapp:{self.from_number}"
            
            # Format message
            formatted_message = f"{subject}\n\n{message}"
            
            # Add product information if available (keep it brief for SMS)
            if data and 'product' in data:
                product = data['product']
                
                if 'name' in product:
                    formatted_message += f"\n\nProduct: {product['name']}"
                    
                if 'current_price' in product and 'currency' in product:
                    formatted_message += f"\nPrice: {product['current_price']} {product['currency']}"
                
                if 'target_price' in product:
                    formatted_message += f"\nTarget: {product['target_price']} {product.get('currency', 'USD')}"
                
                if 'url' in product:
                    formatted_message += f"\n\nView: {product['url']}"
            
            # Send message
            message = self.client.messages.create(
                body=formatted_message,
                from_=from_number,
                to=to_number
            )
            
            logger.info(f"Twilio notification sent to {recipient}, SID: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Twilio notification: {str(e)}")
            return False
