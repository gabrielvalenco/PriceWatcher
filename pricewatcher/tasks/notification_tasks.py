"""
Celery tasks for sending notifications
"""
import logging
from typing import List, Dict, Any

from celery.utils.log import get_task_logger

from pricewatcher.database.connection import get_session
from pricewatcher.database.models import Product, PriceAlert
from pricewatcher.notifications.manager import NotificationManager
from .celery_app import app

logger = get_task_logger(__name__)

@app.task(name='pricewatcher.tasks.notification_tasks.send_price_alert_notifications')
def send_price_alert_notifications(alert_ids: List[int], product_id: int, price_data: Dict[str, Any]):
    """
    Send notifications for triggered price alerts
    
    Args:
        alert_ids: List of alert IDs to send notifications for
        product_id: ID of the product that triggered the alerts
        price_data: Dictionary with current price information
        
    Returns:
        dict: Summary of notification results
    """
    if not alert_ids:
        logger.warning("No alert IDs provided")
        return {'error': 'No alert IDs provided'}
    
    session = get_session()
    notification_manager = NotificationManager()
    results = {}
    
    try:
        # Get product info
        product = session.query(Product).filter(Product.id == product_id).first()
        if not product:
            logger.error(f"Product {product_id} not found")
            return {'error': f"Product {product_id} not found"}
        
        # Get alerts
        alerts = session.query(PriceAlert).filter(PriceAlert.id.in_(alert_ids)).all()
        if not alerts:
            logger.error(f"No alerts found for IDs: {alert_ids}")
            return {'error': 'No alerts found'}
        
        # Prepare product data for notifications
        product_data = {
            'name': product.name,
            'url': product.url,
            'image_url': product.image_url,
            'current_price': price_data.get('price'),
            'currency': price_data.get('currency', 'USD'),
            'in_stock': price_data.get('in_stock', True)
        }
        
        # Send notifications for each alert
        for alert in alerts:
            alert_results = {}
            
            # Prepare notification text
            subject = f"Price Alert: {product.name}"
            message = (f"The price for {product.name} has dropped to "
                      f"{price_data.get('price')} {price_data.get('currency', 'USD')}, "
                      f"below your target price of {alert.target_price} {price_data.get('currency', 'USD')}!")
            
            product_data['target_price'] = alert.target_price
            
            # Send email notification if configured
            if alert.notification_email:
                alert_results['email'] = notification_manager.send_test_notification(
                    'Email',
                    alert.notification_email,
                    message
                )
            
            # Send Telegram notification if configured
            if alert.notification_telegram:
                alert_results['telegram'] = notification_manager.send_test_notification(
                    'Telegram',
                    alert.notification_telegram,
                    message
                )
            
            # Send SMS/WhatsApp notification if configured
            if alert.notification_phone:
                alert_results['sms'] = notification_manager.send_test_notification(
                    'Twilio',
                    alert.notification_phone,
                    message
                )
            
            # Store results
            results[alert.id] = alert_results
            
            # Log the notification status
            notification_sent = any(alert_results.values())
            logger.info(
                f"Price alert {alert.id} notification for product {product.name}: "
                f"{'sent successfully' if notification_sent else 'failed'}"
            )
        
        return {
            'alerts_processed': len(alerts),
            'product_name': product.name,
            'price': price_data.get('price'),
            'currency': price_data.get('currency', 'USD'),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error sending price alert notifications: {str(e)}")
        return {'error': str(e)}
        
    finally:
        session.close()

@app.task(name='pricewatcher.tasks.notification_tasks.send_test_notification')
def send_test_notification(notification_type: str, recipient: str, message: str = None):
    """
    Send a test notification
    
    Args:
        notification_type: Type of notification (Email, Telegram, Twilio)
        recipient: Recipient address/number
        message: Custom test message (optional)
        
    Returns:
        bool: Whether the notification was sent successfully
    """
    if not message:
        message = "This is a test notification from PriceWatcher"
    
    notification_manager = NotificationManager()
    
    try:
        result = notification_manager.send_test_notification(
            notification_type, 
            recipient, 
            message
        )
        
        logger.info(
            f"Test {notification_type} notification to {recipient}: "
            f"{'sent successfully' if result else 'failed'}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error sending test notification: {str(e)}")
        return False
