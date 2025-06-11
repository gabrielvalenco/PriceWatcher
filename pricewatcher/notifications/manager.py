"""
Notification manager for PriceWatcher
"""
import logging
import importlib
import pkgutil
from typing import Dict, Any, List

import pricewatcher.notifications as notifications_package
from .base import BaseNotifier

logger = logging.getLogger(__name__)

class NotificationManager:
    """
    Manager class for handling different notification methods
    """
    
    def __init__(self):
        """Initialize the notification manager"""
        self.notifiers = {}
        self._discover_notifiers()
    
    def _discover_notifiers(self):
        """
        Dynamically discover all available notifier classes in the package
        """
        for _, name, is_pkg in pkgutil.iter_modules(notifications_package.__path__):
            if name != 'base' and name != 'manager':
                try:
                    module = importlib.import_module(f'pricewatcher.notifications.{name}')
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        # Check if it's a class and a subclass of BaseNotifier (but not BaseNotifier itself)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseNotifier) and 
                            attr is not BaseNotifier):
                            notifier_name = name.capitalize()
                            self.notifiers[notifier_name] = attr()
                            logger.info(f"Found notifier: {notifier_name}")
                except Exception as e:
                    logger.error(f"Error loading notifier module {name}: {str(e)}")
    
    def send_price_alert(self, alert, product, price_point) -> Dict[str, bool]:
        """
        Send price alert notifications through all configured channels
        
        Args:
            alert: PriceAlert model instance
            product: Product model instance
            price_point: PricePoint model instance
            
        Returns:
            Dict[str, bool]: Results for each notification method
        """
        results = {}
        product_data = {
            'name': product.name,
            'url': product.url,
            'image_url': product.image_url,
            'current_price': price_point.price,
            'currency': price_point.currency,
            'target_price': alert.target_price
        }
        
        subject = f"Price Alert: {product.name}"
        message = (f"The price for {product.name} has dropped to "
                  f"{price_point.price} {price_point.currency}, "
                  f"below your target price of {alert.target_price} {price_point.currency}!")
        
        # Send email notification if configured
        if alert.notification_email and 'Email' in self.notifiers:
            notifier = self.notifiers['Email']
            if notifier.is_configured():
                results['email'] = notifier.send_notification(
                    alert.notification_email,
                    subject,
                    message,
                    {'product': product_data}
                )
        
        # Send Telegram notification if configured
        if alert.notification_telegram and 'Telegram' in self.notifiers:
            notifier = self.notifiers['Telegram']
            if notifier.is_configured():
                results['telegram'] = notifier.send_notification(
                    alert.notification_telegram,
                    subject,
                    message,
                    {'product': product_data}
                )
        
        # Send WhatsApp/SMS notification if configured
        if alert.notification_phone and 'Twilio' in self.notifiers:
            notifier = self.notifiers['Twilio'] 
            if notifier.is_configured():
                results['sms'] = notifier.send_notification(
                    alert.notification_phone,
                    subject,
                    message,
                    {'product': product_data}
                )
        
        return results
    
    def send_test_notification(self, notification_type, recipient, message="This is a test notification from PriceWatcher") -> bool:
        """
        Send a test notification
        
        Args:
            notification_type (str): Type of notification ('Email', 'Telegram', 'Twilio')
            recipient (str): Recipient identifier (email, chat ID, phone number)
            message (str): Custom test message
            
        Returns:
            bool: True if test notification sent successfully
        """
        if notification_type not in self.notifiers:
            logger.error(f"Unknown notification type: {notification_type}")
            return False
        
        notifier = self.notifiers[notification_type]
        if not notifier.is_configured():
            logger.error(f"{notification_type} notifier not properly configured")
            return False
        
        return notifier.send_notification(
            recipient,
            "PriceWatcher Test Notification",
            message,
            {'test': True}
        )
