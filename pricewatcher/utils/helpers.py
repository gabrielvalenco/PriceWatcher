"""
Helper utilities for PriceWatcher
"""
import re
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def validate_url(url: str) -> bool:
    """
    Validate if the URL is properly formatted
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if URL is valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def get_domain_from_url(url: str) -> Optional[str]:
    """
    Extract the domain from a URL
    
    Args:
        url (str): URL to extract domain from
        
    Returns:
        Optional[str]: Domain name or None if invalid URL
    """
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Remove www. prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return domain
    except Exception as e:
        logger.error(f"Error extracting domain from URL {url}: {str(e)}")
        return None

def format_price(price: float, currency: str = "USD") -> str:
    """
    Format price with appropriate currency symbol
    
    Args:
        price (float): Price value
        currency (str): Currency code (USD, EUR, GBP, etc.)
        
    Returns:
        str: Formatted price string
    """
    currency_symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "INR": "₹"
    }
    
    symbol = currency_symbols.get(currency, "")
    
    if currency in ["JPY", "INR"]:  # No decimal places
        formatted = f"{symbol}{int(price)}"
    else:
        formatted = f"{symbol}{price:.2f}"
        
    return formatted

def calculate_price_difference(old_price: float, new_price: float) -> Dict[str, Any]:
    """
    Calculate difference between prices
    
    Args:
        old_price (float): Old price
        new_price (float): New price
        
    Returns:
        Dict[str, Any]: Dictionary with difference details:
            - absolute: Absolute difference
            - percentage: Percentage difference
            - decreased: True if price decreased, False otherwise
    """
    if old_price == 0:
        return {
            "absolute": new_price,
            "percentage": 0,
            "decreased": False
        }
        
    absolute_diff = new_price - old_price
    percentage_diff = (absolute_diff / old_price) * 100
    
    return {
        "absolute": abs(absolute_diff),
        "percentage": abs(percentage_diff),
        "decreased": absolute_diff < 0
    }

def extract_product_id_from_url(url: str, store_domain: str) -> Optional[str]:
    """
    Attempt to extract product ID from URL based on store patterns
    
    Args:
        url (str): Product URL
        store_domain (str): Store domain name
        
    Returns:
        Optional[str]: Extracted product ID or None if not found
    """
    try:
        if "amazon" in store_domain:
            # Amazon product URLs: https://www.amazon.com/dp/BXXXXXXXX or /gp/product/BXXXXXXXX
            pattern = r'/(?:dp|gp/product)/([A-Z0-9]{10})'
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        elif "ebay" in store_domain:
            # eBay product URLs: https://www.ebay.com/itm/123456789
            pattern = r'/itm/(\d+)'
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        elif "walmart" in store_domain:
            # Walmart product URLs: https://www.walmart.com/ip/123456789
            pattern = r'/ip/(?:[^/]+/)?(\d+)'
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # For other stores, return None
        return None
    except Exception as e:
        logger.error(f"Error extracting product ID from URL {url}: {str(e)}")
        return None
