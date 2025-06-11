"""
Email notification handler for PriceWatcher
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

from .base import BaseNotifier

logger = logging.getLogger(__name__)

class EmailNotifier(BaseNotifier):
    """
    Notification handler for Email
    """
    
    def __init__(self):
        """Initialize the Email notifier"""
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.email_from = os.getenv("EMAIL_FROM", self.smtp_username)
        
        if not all([self.smtp_server, self.smtp_username, self.smtp_password]):
            logger.warning("Email configuration incomplete, notifications will be disabled")
    
    def is_configured(self) -> bool:
        """
        Check if the Email notifier is properly configured
        
        Returns:
            bool: True if configured, False otherwise
        """
        return all([self.smtp_server, self.smtp_username, self.smtp_password])
        
    def send_notification(self, recipient: str, subject: str, message: str, data: Dict[str, Any] = None) -> bool:
        """
        Send a notification via Email
        
        Args:
            recipient (str): Email address to send to
            subject (str): Subject line of the email
            message (str): Message body in plain text
            data (Dict[str, Any], optional): Additional data (product info, etc.)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            logger.error("Email notifier not configured")
            return False
        
        try:
            # Create email message
            email = MIMEMultipart("alternative")
            email["Subject"] = subject
            email["From"] = self.email_from
            email["To"] = recipient
            
            # Create plain text version of the email
            text_content = message
            
            # Create HTML version with more details if product data available
            html_content = f"<html><body><p>{message}</p>"
            
            if data and 'product' in data:
                product = data['product']
                
                html_content += "<hr/><h2>Product Details</h2>"
                
                if 'name' in product:
                    html_content += f"<p><strong>Product:</strong> {product['name']}</p>"
                    
                if 'current_price' in product and 'currency' in product:
                    html_content += f"<p><strong>Current Price:</strong> {product['current_price']} {product['currency']}</p>"
                
                if 'target_price' in product:
                    html_content += f"<p><strong>Target Price:</strong> {product['target_price']} {product.get('currency', 'USD')}</p>"
                    
                if 'image_url' in product and product['image_url']:
                    html_content += f"<p><img src='{product['image_url']}' alt='Product Image' style='max-width: 300px;'/></p>"
                    
                if 'url' in product:
                    html_content += f"<p><a href='{product['url']}'>View Product</a></p>"
            
            html_content += "</body></html>"
            
            # Attach parts to the email
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            email.attach(part1)
            email.attach(part2)
            
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.email_from, recipient, email.as_string())
            
            logger.info(f"Email notification sent to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
