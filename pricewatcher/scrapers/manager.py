"""
Scraper manager for PriceWatcher
"""
import logging
import importlib
import pkgutil
from typing import Dict, Any, List, Type, Optional
import pricewatcher.scrapers as scrapers_package
from pricewatcher.database.connection import get_session
from pricewatcher.database.models import Product, PricePoint, Store

from .base import BaseScraper

logger = logging.getLogger(__name__)

class ScraperManager:
    """
    Manager class for handling different scrapers and scraping operations
    """
    
    def __init__(self):
        """Initialize the scraper manager"""
        self.scrapers = {}
        self._discover_scrapers()
        
    def _discover_scrapers(self):
        """
        Dynamically discover all available scrapers in the package
        """
        for _, name, is_pkg in pkgutil.iter_modules(scrapers_package.__path__):
            if name != 'base' and name != 'manager':
                try:
                    module = importlib.import_module(f'pricewatcher.scrapers.{name}')
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        # Check if it's a class and a subclass of BaseScraper (but not BaseScraper itself)
                        if (isinstance(attr, type) and 
                            issubclass(attr, BaseScraper) and 
                            attr is not BaseScraper):
                            store_name = attr.get_store_name()
                            self.scrapers[store_name] = attr
                            logger.info(f"Found scraper for {store_name}: {attr.__name__}")
                except Exception as e:
                    logger.error(f"Error loading scraper module {name}: {str(e)}")
    
    def get_scraper_for_url(self, url: str) -> Optional[BaseScraper]:
        """
        Find the appropriate scraper for a given URL
        
        Args:
            url (str): URL to find scraper for
            
        Returns:
            BaseScraper or None: A scraper instance if found, None otherwise
        """
        for scraper_class in self.scrapers.values():
            temp_scraper = scraper_class(url)
            if temp_scraper.is_valid_url():
                logger.info(f"Found scraper {scraper_class.__name__} for URL: {url}")
                return temp_scraper
        
        logger.warning(f"No scraper found for URL: {url}")
        return None
    
    def scrape_product(self, url: str) -> Dict[str, Any]:
        """
        Scrape product information from a URL
        
        Args:
            url (str): URL to scrape
            
        Returns:
            Dict[str, Any]: Product information or empty dict if scraping failed
        """
        scraper = self.get_scraper_for_url(url)
        if scraper:
            try:
                logger.info(f"Scraping URL: {url}")
                product_info = scraper.extract_product_info()
                if product_info:
                    # Add the store name to the product info
                    product_info['store_name'] = scraper.get_store_name()
                return product_info
            except Exception as e:
                logger.error(f"Error scraping URL {url}: {str(e)}")
        
        return {}
    
    def update_all_products(self):
        """
        Update all active products in the database
        """
        session = get_session()
        try:
            products = session.query(Product).filter(Product.active == True).all()
            logger.info(f"Updating prices for {len(products)} products")
            
            for product in products:
                product_info = self.scrape_product(product.url)
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
            logger.info("Price updates completed successfully")
        
        except Exception as e:
            logger.error(f"Error updating products: {str(e)}")
            session.rollback()
        finally:
            session.close()

def start_scraping():
    """
    Start the scraping process for all products
    """
    logger.info("Starting scraper service")
    manager = ScraperManager()
    manager.update_all_products()
    logger.info("Scraper service completed")
