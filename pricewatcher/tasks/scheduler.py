"""
Task scheduler for PriceWatcher
"""
import os
import time
import logging
import threading
import schedule
from datetime import datetime

from pricewatcher.database.connection import get_session
from pricewatcher.database.models import Product, PricePoint, PriceAlert
from pricewatcher.scrapers.manager import ScraperManager
from pricewatcher.notifications.manager import NotificationManager

logger = logging.getLogger(__name__)

class TaskScheduler:
    """
    Scheduler for periodic tasks like price checking and notifications
    """
    
    def __init__(self):
        """Initialize the task scheduler"""
        self.scraper_manager = ScraperManager()
        self.notification_manager = NotificationManager()
        self.running = False
        self.scheduler_thread = None
        
        # Set up scheduled tasks
        self._setup_schedule()
    
    def _setup_schedule(self):
        """Set up scheduled tasks"""
        # Schedule full price update every 6 hours
        schedule.every(6).hours.do(self.update_all_prices)
        
        # Schedule price alert check every hour
        schedule.every(1).hour.do(self.check_price_alerts)
        
        logger.info("Task scheduler initialized with default schedule")
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        
        # Run initial price update
        logger.info("Running initial price update")
        self.update_all_prices()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Task scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            
        logger.info("Task scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check for pending tasks every minute
    
    def update_all_prices(self):
        """Update prices for all active products"""
        logger.info("Starting price update for all products")
        
        session = get_session()
        try:
            products = session.query(Product).filter(Product.active == True).all()
            logger.info(f"Updating prices for {len(products)} products")
            
            for product in products:
                try:
                    product_info = self.scraper_manager.scrape_product(product.url)
                    
                    if not product_info or 'price' not in product_info:
                        logger.warning(f"Failed to get price for product {product.id}: {product.name}")
                        continue
                    
                    # Create a new price point
                    price_point = PricePoint(
                        product_id=product.id,
                        price=product_info['price'],
                        currency=product_info.get('currency', 'USD'),
                        in_stock=product_info.get('in_stock', True)
                    )
                    
                    session.add(price_point)
                    session.commit()
                    
                    logger.info(f"Updated price for product {product.id}: {product_info['price']} {product_info.get('currency', 'USD')}")
                    
                except Exception as e:
                    logger.error(f"Error updating price for product {product.id}: {str(e)}")
                    session.rollback()
            
            logger.info("Price update completed")
            
        except Exception as e:
            logger.error(f"Error in update_all_prices: {str(e)}")
        finally:
            session.close()
    
    def check_price_alerts(self):
        """Check active price alerts and send notifications if triggered"""
        logger.info("Checking price alerts")
        
        session = get_session()
        try:
            alerts = session.query(PriceAlert).filter(PriceAlert.is_active == True).all()
            logger.info(f"Checking {len(alerts)} active price alerts")
            
            for alert in alerts:
                try:
                    # Get latest price point
                    latest_price = session.query(PricePoint).filter(
                        PricePoint.product_id == alert.product_id
                    ).order_by(PricePoint.timestamp.desc()).first()
                    
                    if not latest_price:
                        continue
                    
                    # Get product
                    product = session.query(Product).filter(Product.id == alert.product_id).first()
                    if not product:
                        continue
                    
                    # Check if price has dropped below target
                    if latest_price.price <= alert.target_price:
                        # Only send notification if we haven't sent one recently
                        should_notify = True
                        if alert.last_notified_at:
                            # Don't send notifications more than once per day
                            time_since_last = datetime.utcnow() - alert.last_notified_at
                            if time_since_last.total_seconds() < 24 * 60 * 60:
                                should_notify = False
                        
                        if should_notify:
                            logger.info(f"Price alert triggered for product {product.id}: {product.name}")
                            # Send notifications
                            results = self.notification_manager.send_price_alert(alert, product, latest_price)
                            
                            # Update last notified timestamp
                            alert.last_notified_at = datetime.utcnow()
                            session.commit()
                            
                            logger.info(f"Notifications sent: {results}")
                
                except Exception as e:
                    logger.error(f"Error processing alert {alert.id}: {str(e)}")
            
            logger.info("Price alert check completed")
            
        except Exception as e:
            logger.error(f"Error in check_price_alerts: {str(e)}")
        finally:
            session.close()

# Global scheduler instance
_scheduler = None

def start_scheduler():
    """Start the task scheduler"""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    
    _scheduler.start()
    
def stop_scheduler():
    """Stop the task scheduler"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()
