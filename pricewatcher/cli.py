"""
Command-line interface for PriceWatcher
"""
import os
import sys
import argparse
import logging
import json
from datetime import datetime
from tabulate import tabulate

from pricewatcher.database.connection import get_session, init_db
from pricewatcher.database.models import Product, Store, PricePoint, PriceAlert
from pricewatcher.scrapers.manager import ScraperManager
from pricewatcher.notifications.manager import NotificationManager
from pricewatcher.utils.helpers import format_price

logger = logging.getLogger(__name__)

class PriceWatcherCLI:
    """Command-line interface for PriceWatcher"""
    
    def __init__(self):
        """Initialize the CLI"""
        self.session = get_session()
        self.scraper_manager = ScraperManager()
        self.notification_manager = NotificationManager()
        
    def close(self):
        """Close database session"""
        self.session.close()
        
    def setup_parser(self):
        """Set up command-line argument parser"""
        parser = argparse.ArgumentParser(
            description="PriceWatcher - Track e-commerce product prices",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # Add product command
        add_parser = subparsers.add_parser("add", help="Add a product to track")
        add_parser.add_argument("url", help="URL of the product to track")
        
        # List products command
        list_parser = subparsers.add_parser("list", help="List tracked products")
        list_parser.add_argument("--json", action="store_true", help="Output in JSON format")
        
        # Price history command
        history_parser = subparsers.add_parser("history", help="Show price history for a product")
        history_parser.add_argument("product_id", type=int, help="ID of the product")
        history_parser.add_argument("--limit", type=int, default=10, help="Number of price points to show")
        history_parser.add_argument("--json", action="store_true", help="Output in JSON format")
        
        # Update product command
        update_parser = subparsers.add_parser("update", help="Update price for a product")
        update_parser.add_argument("product_id", type=int, nargs="?", help="ID of the product (omit to update all)")
        
        # Set price alert command
        alert_parser = subparsers.add_parser("alert", help="Set a price alert")
        alert_parser.add_argument("product_id", type=int, help="ID of the product")
        alert_parser.add_argument("target_price", type=float, help="Target price to alert on")
        alert_parser.add_argument("--email", help="Email address for notification")
        alert_parser.add_argument("--phone", help="Phone number for SMS notification")
        alert_parser.add_argument("--telegram", help="Telegram chat ID for notification")
        
        # List alerts command
        alerts_parser = subparsers.add_parser("alerts", help="List active price alerts")
        alerts_parser.add_argument("--json", action="store_true", help="Output in JSON format")
        
        # Test notification command
        notify_parser = subparsers.add_parser("notify", help="Send a test notification")
        notify_parser.add_argument("type", choices=["email", "sms", "telegram"], help="Notification type")
        notify_parser.add_argument("recipient", help="Notification recipient (email, phone, or chat ID)")
        notify_parser.add_argument("message", nargs="?", help="Message to send (optional)")
        
        # Initialize database command
        init_parser = subparsers.add_parser("init", help="Initialize the database")
        
        return parser
        
    def run(self):
        """Run the CLI"""
        parser = self.setup_parser()
        args = parser.parse_args()
        
        if not args.command:
            parser.print_help()
            return 0
            
        try:
            # Call the appropriate method based on the command
            method_name = f"cmd_{args.command}"
            if hasattr(self, method_name):
                method = getattr(self, method_name)
                return method(args)
            else:
                print(f"Unknown command: {args.command}")
                return 1
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            print(f"Error: {str(e)}")
            return 1
        finally:
            self.close()
    
    def cmd_add(self, args):
        """Add a product to track"""
        print(f"Adding product from URL: {args.url}")
        product_info = self.scraper_manager.scrape_product(args.url)
        
        if not product_info or 'name' not in product_info:
            print("Failed to fetch product information from the URL.")
            return 1
            
        # Find or create store
        store = self.session.query(Store).filter(Store.name == product_info['store_name']).first()
        if not store:
            store = Store(
                name=product_info['store_name'],
                url=f"https://{product_info['store_name'].lower()}.com",  # Default URL
                scraper_class=f"{product_info['store_name']}Scraper"
            )
            self.session.add(store)
            self.session.flush()
            
        # Create product
        product = Product(
            name=product_info['name'],
            url=args.url,
            image_url=product_info.get('image_url'),
            description=product_info.get('description'),
            store_id=store.id
        )
        self.session.add(product)
        self.session.flush()
        
        # Create initial price point
        price_point = None
        if 'price' in product_info:
            price_point = PricePoint(
                product_id=product.id,
                price=product_info['price'],
                currency=product_info.get('currency', 'USD'),
                in_stock=product_info.get('in_stock', True)
            )
            self.session.add(price_point)
            
        self.session.commit()
        
        print(f"Product added successfully with ID: {product.id}")
        print(f"Name: {product.name}")
        print(f"Store: {store.name}")
        
        if price_point:
            print(f"Current price: {format_price(price_point.price, price_point.currency)}")
            print(f"In stock: {'Yes' if price_point.in_stock else 'No'}")
            
        return 0
    
    def cmd_list(self, args):
        """List tracked products"""
        products = self.session.query(Product).filter(Product.active == True).all()
        
        if not products:
            print("No products being tracked.")
            return 0
            
        if args.json:
            # JSON output
            result = []
            for product in products:
                # Get latest price
                latest_price = self.session.query(PricePoint).filter(
                    PricePoint.product_id == product.id
                ).order_by(PricePoint.timestamp.desc()).first()
                
                # Get store
                store = self.session.query(Store).filter(Store.id == product.store_id).first()
                
                result.append({
                    "id": product.id,
                    "name": product.name,
                    "url": product.url,
                    "store": store.name if store else "Unknown",
                    "price": latest_price.price if latest_price else None,
                    "currency": latest_price.currency if latest_price else "USD",
                    "in_stock": latest_price.in_stock if latest_price else None,
                    "last_updated": latest_price.timestamp.isoformat() if latest_price else None
                })
                
            print(json.dumps(result, indent=2))
        else:
            # Table output
            table_data = []
            headers = ["ID", "Name", "Store", "Price", "In Stock", "Last Updated"]
            
            for product in products:
                # Get latest price
                latest_price = self.session.query(PricePoint).filter(
                    PricePoint.product_id == product.id
                ).order_by(PricePoint.timestamp.desc()).first()
                
                # Get store
                store = self.session.query(Store).filter(Store.id == product.store_id).first()
                
                price_formatted = format_price(latest_price.price, latest_price.currency) if latest_price else "N/A"
                in_stock = "Yes" if latest_price and latest_price.in_stock else "No"
                last_updated = latest_price.timestamp.strftime("%Y-%m-%d %H:%M") if latest_price else "Never"
                
                table_data.append([
                    product.id,
                    product.name[:40] + "..." if len(product.name) > 40 else product.name,
                    store.name if store else "Unknown",
                    price_formatted,
                    in_stock,
                    last_updated
                ])
                
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            
        return 0
    
    def cmd_history(self, args):
        """Show price history for a product"""
        # Check if product exists
        product = self.session.query(Product).filter(Product.id == args.product_id).first()
        if not product:
            print(f"Product with ID {args.product_id} not found.")
            return 1
            
        # Get price history
        price_points = self.session.query(PricePoint).filter(
            PricePoint.product_id == args.product_id
        ).order_by(PricePoint.timestamp.desc()).limit(args.limit).all()
        
        if not price_points:
            print(f"No price history available for product {args.product_id}.")
            return 0
            
        if args.json:
            # JSON output
            result = {
                "product_id": product.id,
                "name": product.name,
                "prices": [
                    {
                        "price": pp.price,
                        "currency": pp.currency,
                        "in_stock": pp.in_stock,
                        "timestamp": pp.timestamp.isoformat()
                    }
                    for pp in price_points
                ]
            }
            
            print(json.dumps(result, indent=2))
        else:
            # Table output
            print(f"Price history for: {product.name} (ID: {product.id})")
            print("-" * 50)
            
            table_data = []
            headers = ["Date", "Price", "Currency", "In Stock"]
            
            for pp in price_points:
                table_data.append([
                    pp.timestamp.strftime("%Y-%m-%d %H:%M"),
                    f"{pp.price:.2f}",
                    pp.currency,
                    "Yes" if pp.in_stock else "No"
                ])
                
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            
        return 0
    
    def cmd_update(self, args):
        """Update price for a product or all products"""
        if args.product_id:
            # Update single product
            product = self.session.query(Product).filter(
                Product.id == args.product_id, 
                Product.active == True
            ).first()
            
            if not product:
                print(f"Product with ID {args.product_id} not found or not active.")
                return 1
                
            print(f"Updating price for product {product.id}: {product.name}")
            product_info = self.scraper_manager.scrape_product(product.url)
            
            if not product_info or 'price' not in product_info:
                print("Failed to fetch updated price information.")
                return 1
                
            # Create new price point
            price_point = PricePoint(
                product_id=product.id,
                price=product_info['price'],
                currency=product_info.get('currency', 'USD'),
                in_stock=product_info.get('in_stock', True)
            )
            
            self.session.add(price_point)
            self.session.commit()
            
            print(f"Updated price: {format_price(price_point.price, price_point.currency)}")
            print(f"In stock: {'Yes' if price_point.in_stock else 'No'}")
            
        else:
            # Update all products
            products = self.session.query(Product).filter(Product.active == True).all()
            
            if not products:
                print("No products to update.")
                return 0
                
            print(f"Updating prices for {len(products)} products...")
            
            success_count = 0
            for product in products:
                try:
                    product_info = self.scraper_manager.scrape_product(product.url)
                    
                    if not product_info or 'price' not in product_info:
                        print(f"Failed to update product {product.id}: {product.name}")
                        continue
                        
                    # Create new price point
                    price_point = PricePoint(
                        product_id=product.id,
                        price=product_info['price'],
                        currency=product_info.get('currency', 'USD'),
                        in_stock=product_info.get('in_stock', True)
                    )
                    
                    self.session.add(price_point)
                    success_count += 1
                    
                    print(f"Updated product {product.id}: {product.name} - "
                          f"{format_price(price_point.price, price_point.currency)}")
                          
                except Exception as e:
                    print(f"Error updating product {product.id}: {str(e)}")
                    
            self.session.commit()
            print(f"Successfully updated {success_count} of {len(products)} products.")
            
        return 0
    
    def cmd_alert(self, args):
        """Set a price alert"""
        # Check if product exists
        product = self.session.query(Product).filter(Product.id == args.product_id).first()
        if not product:
            print(f"Product with ID {args.product_id} not found.")
            return 1
            
        # Check if at least one notification method is specified
        if not any([args.email, args.phone, args.telegram]):
            print("Error: At least one notification method (email, phone, or telegram) must be specified.")
            return 1
            
        # Create alert
        alert = PriceAlert(
            product_id=args.product_id,
            target_price=args.target_price,
            notification_email=args.email,
            notification_phone=args.phone,
            notification_telegram=args.telegram
        )
        
        self.session.add(alert)
        self.session.commit()
        
        print(f"Price alert created with ID: {alert.id}")
        print(f"Product: {product.name}")
        print(f"Target price: {format_price(alert.target_price, 'USD')}")
        
        if args.email:
            print(f"Email notification: {args.email}")
        if args.phone:
            print(f"SMS notification: {args.phone}")
        if args.telegram:
            print(f"Telegram notification: {args.telegram}")
            
        # Get latest price
        latest_price = self.session.query(PricePoint).filter(
            PricePoint.product_id == args.product_id
        ).order_by(PricePoint.timestamp.desc()).first()
        
        if latest_price:
            current_price = format_price(latest_price.price, latest_price.currency)
            print(f"Current price: {current_price}")
            
            if latest_price.price <= args.target_price:
                print("Note: Current price is already at or below your target price!")
                
        return 0
    
    def cmd_alerts(self, args):
        """List active price alerts"""
        alerts = self.session.query(PriceAlert).filter(PriceAlert.is_active == True).all()
        
        if not alerts:
            print("No active price alerts.")
            return 0
            
        if args.json:
            # JSON output
            result = []
            for alert in alerts:
                # Get product
                product = self.session.query(Product).filter(Product.id == alert.product_id).first()
                
                # Get latest price
                latest_price = self.session.query(PricePoint).filter(
                    PricePoint.product_id == alert.product_id
                ).order_by(PricePoint.timestamp.desc()).first()
                
                result.append({
                    "id": alert.id,
                    "product_id": alert.product_id,
                    "product_name": product.name if product else "Unknown",
                    "target_price": alert.target_price,
                    "current_price": latest_price.price if latest_price else None,
                    "currency": latest_price.currency if latest_price else "USD",
                    "email": alert.notification_email,
                    "phone": alert.notification_phone,
                    "telegram": alert.notification_telegram,
                    "last_notified": alert.last_notified_at.isoformat() if alert.last_notified_at else None
                })
                
            print(json.dumps(result, indent=2))
        else:
            # Table output
            table_data = []
            headers = ["ID", "Product", "Target", "Current", "Notification Methods", "Last Notified"]
            
            for alert in alerts:
                # Get product
                product = self.session.query(Product).filter(Product.id == alert.product_id).first()
                
                # Get latest price
                latest_price = self.session.query(PricePoint).filter(
                    PricePoint.product_id == alert.product_id
                ).order_by(PricePoint.timestamp.desc()).first()
                
                product_name = product.name[:30] + "..." if product and len(product.name) > 30 else (product.name if product else "Unknown")
                target_price = format_price(alert.target_price, latest_price.currency if latest_price else "USD")
                current_price = format_price(latest_price.price, latest_price.currency) if latest_price else "N/A"
                
                # Notification methods
                methods = []
                if alert.notification_email:
                    methods.append("Email")
                if alert.notification_phone:
                    methods.append("SMS")
                if alert.notification_telegram:
                    methods.append("Telegram")
                    
                last_notified = alert.last_notified_at.strftime("%Y-%m-%d %H:%M") if alert.last_notified_at else "Never"
                
                table_data.append([
                    alert.id,
                    product_name,
                    target_price,
                    current_price,
                    ", ".join(methods),
                    last_notified
                ])
                
            print(tabulate(table_data, headers=headers, tablefmt="pretty"))
            
        return 0
    
    def cmd_notify(self, args):
        """Send a test notification"""
        notification_type = args.type.capitalize()
        recipient = args.recipient
        message = args.message or "This is a test notification from PriceWatcher CLI"
        
        print(f"Sending test {notification_type} notification to {recipient}...")
        
        result = self.notification_manager.send_test_notification(
            notification_type, 
            recipient, 
            message
        )
        
        if result:
            print("Notification sent successfully!")
        else:
            print("Failed to send notification. Check your configuration and try again.")
            return 1
            
        return 0
    
    def cmd_init(self, args):
        """Initialize the database"""
        print("Initializing database...")
        init_db()
        print("Database initialized successfully.")
        return 0

def main():
    """Command-line entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run CLI
    cli = PriceWatcherCLI()
    return cli.run()

if __name__ == "__main__":
    sys.exit(main())
