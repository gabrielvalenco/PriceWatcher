"""
Base scraper class for PriceWatcher
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    """
    Abstract base class for all website scrapers.
    All specific website scrapers should inherit from this class.
    """
    
    def __init__(self, url: str):
        """
        Initialize the scraper with the product URL
        
        Args:
            url (str): URL of the product to scrape
        """
        self.url = url
        
    @abstractmethod
    def extract_product_info(self) -> Dict[str, Any]:
        """
        Extract product information from the website.
        
        Returns:
            Dict[str, Any]: Dictionary containing product information:
                - name: Product name
                - price: Current price (float)
                - currency: Currency code (str, e.g., 'USD')
                - in_stock: Whether the product is in stock (bool)
                - image_url: URL of the product image (Optional[str])
                - description: Product description (Optional[str])
        """
        pass
    
    @abstractmethod
    def is_valid_url(self) -> bool:
        """
        Check if the URL is valid for this scraper.
        
        Returns:
            bool: True if the URL is valid, False otherwise
        """
        pass
    
    @staticmethod
    @abstractmethod
    def get_store_name() -> str:
        """
        Get the name of the store this scraper is designed for.
        
        Returns:
            str: Name of the store
        """
        pass
        
    def clean_price(self, price_str: str) -> float:
        """
        Clean and convert price string to float.
        
        Args:
            price_str (str): Price string (e.g., '$10.99', '10,99 €')
            
        Returns:
            float: Cleaned price value
        """
        # Remove currency symbols and spaces
        cleaned = price_str.replace('$', '').replace('€', '').replace('£', '').strip()
        # Replace comma with dot for decimal separator
        cleaned = cleaned.replace(',', '.')
        # Extract the first valid number (in case there are multiple prices)
        import re
        match = re.search(r'\d+\.\d+|\d+', cleaned)
        if match:
            return float(match.group())
        # If no valid number found, return 0
        return 0.0
