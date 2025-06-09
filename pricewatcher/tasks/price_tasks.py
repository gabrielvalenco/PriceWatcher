"""
Celery tasks for price updates and alerts
"""
import logging
from datetime import datetime, timedelta

from celery import chain
from celery.utils.log import get_task_logger

from pricewatcher.database.connection import get_session
from pricewatcher.database.models import Product, PricePoint, PriceAlert
from pricewatcher.scrapers.manager import ScraperManager
from .celery_app import app
from .notification_tasks import send_price_alert_notifications

logger = get_task_logger(__name__)

@app.task(name='pricewatcher.tasks.price_tasks.update_product_price')
def update_product_price(product_id):
    """
    Update price for a specific product
    
    Args:
        product_id: ID of the product to update
    
    Returns:
        bool: True if price was updated successfully, False otherwise
    """
    session = get_session()
    scraper_manager = ScraperManager()
    
    try:
        product = session.query(Product).filter(Product.id == product_id, Product.active == True).first()
        if not product:
            logger.warning(f"Product {product_id} not found or not active")
            return False
        
        # Get latest product info
        product_info = scraper_manager.scrape_product(product.url)
        
        if not product_info or 'price' not in product_info:
            logger.warning(f"Failed to get price for product {product_id}: {product.name}")
            return False
        
        # Create new price point
        price_point = PricePoint(
            product_id=product.id,
            price=product_info['price'],
            currency=product_info.get('currency', 'USD'),
            in_stock=product_info.get('in_stock', True)
        )
        
        session.add(price_point)
        session.commit()
        
        logger.info(f"Updated price for product {product_id}: {product_info['price']} {product_info.get('currency', 'USD')}")
        
        # Return price point ID and other info needed for alert checking
        return {
            'product_id': product.id,
            'price_point_id': price_point.id,
            'price': price_point.price,
            'currency': price_point.currency,
            'in_stock': price_point.in_stock
        }
    
    except Exception as e:
        logger.error(f"Error updating price for product {product_id}: {str(e)}")
        session.rollback()
        return False
    
    finally:
        session.close()

@app.task(name='pricewatcher.tasks.price_tasks.update_all_prices')
def update_all_prices():
    """
    Update prices for all active products
    
    Returns:
        dict: Summary of update results
    """
    session = get_session()
    updated_count = 0
    error_count = 0
    
    try:
        products = session.query(Product).filter(Product.active == True).all()
        product_ids = [product.id for product in products]
        logger.info(f"Scheduling price updates for {len(product_ids)} products")
        
        # Start individual update tasks
        for product_id in product_ids:
            # Chain price update with alert checking
            chain(
                update_product_price.s(product_id),
                check_product_alerts.s()
            ).apply_async()
        
        return {
            'scheduled_products': len(product_ids),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error scheduling product updates: {str(e)}")
        return {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    finally:
        session.close()

@app.task(name='pricewatcher.tasks.price_tasks.check_product_alerts')
def check_product_alerts(price_update_result):
    """
    Check alerts for a product after price update
    
    Args:
        price_update_result: Result from update_product_price task
        
    Returns:
        dict: Summary of alert check results
    """
    if not price_update_result:
        logger.warning("No price update result provided")
        return {'error': 'No price update result provided'}
    
    product_id = price_update_result.get('product_id')
    if not product_id:
        logger.warning("No product ID in price update result")
        return {'error': 'No product ID in price update result'}
    
    session = get_session()
    triggered_alerts = []
    
    try:
        # Find all active alerts for this product where the price is at or below target
        alerts = session.query(PriceAlert).filter(
            PriceAlert.product_id == product_id,
            PriceAlert.is_active == True,
            PriceAlert.target_price >= price_update_result['price']
        ).all()
        
        now = datetime.utcnow()
        
        for alert in alerts:
            # Only trigger if we haven't sent a notification recently (within 24 hours)
            should_notify = True
            if alert.last_notified_at:
                time_since_last = now - alert.last_notified_at
                if time_since_last.total_seconds() < 24 * 60 * 60:
                    should_notify = False
            
            if should_notify:
                # Update last notified time
                alert.last_notified_at = now
                triggered_alerts.append(alert.id)
        
        # Commit updates to last_notified_at
        if triggered_alerts:
            session.commit()
            
            # Schedule notification task
            send_price_alert_notifications.delay(
                alert_ids=triggered_alerts, 
                product_id=product_id,
                price_data={
                    'price': price_update_result['price'],
                    'currency': price_update_result['currency'],
                    'in_stock': price_update_result['in_stock']
                }
            )
        
        return {
            'product_id': product_id,
            'alerts_triggered': len(triggered_alerts),
            'alert_ids': triggered_alerts
        }
    
    except Exception as e:
        logger.error(f"Error checking alerts for product {product_id}: {str(e)}")
        session.rollback()
        return {'error': str(e), 'product_id': product_id}
    
    finally:
        session.close()

@app.task(name='pricewatcher.tasks.price_tasks.check_price_alerts')
def check_price_alerts():
    """
    Check all active price alerts against latest prices
    
    Returns:
        dict: Summary of alert checks
    """
    session = get_session()
    triggered_count = 0
    
    try:
        # Get all active alerts
        alerts = session.query(PriceAlert).filter(PriceAlert.is_active == True).all()
        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        
        for alert in alerts:
            # Skip if we've notified in the last 24 hours
            if alert.last_notified_at and alert.last_notified_at > yesterday:
                continue
                
            # Get the latest price for this product
            latest_price = session.query(PricePoint).filter(
                PricePoint.product_id == alert.product_id
            ).order_by(PricePoint.timestamp.desc()).first()
            
            if not latest_price:
                continue
                
            # Check if price is at or below target
            if latest_price.price <= alert.target_price:
                # Update last notified time
                alert.last_notified_at = now
                triggered_count += 1
                
                # Schedule notification
                send_price_alert_notifications.delay(
                    alert_ids=[alert.id],
                    product_id=alert.product_id,
                    price_data={
                        'price': latest_price.price,
                        'currency': latest_price.currency,
                        'in_stock': latest_price.in_stock
                    }
                )
        
        # Commit updates to last_notified_at timestamps
        if triggered_count > 0:
            session.commit()
            
        return {
            'alerts_checked': len(alerts),
            'alerts_triggered': triggered_count,
            'timestamp': now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in check_price_alerts: {str(e)}")
        session.rollback()
        return {'error': str(e)}
        
    finally:
        session.close()
