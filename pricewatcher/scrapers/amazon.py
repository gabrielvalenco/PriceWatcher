"""
Amazon scraper for PriceWatcher
"""
import logging
import re
from typing import Dict, Any
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper

logger = logging.getLogger(__name__)

class AmazonScraper(BaseScraper):
    """Scraper for Amazon product pages"""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    @staticmethod
    def get_store_name() -> str:
        """Return the store name"""
        return "Amazon"
    
    def is_valid_url(self) -> bool:
        """Check if the URL is a valid Amazon product URL"""
        amazon_pattern = r'https?://(www\.)?amazon\.(com|ca|co\.uk|de|fr|es|it|co\.jp|in)/.*'
        return bool(re.match(amazon_pattern, self.url))
    
    def extract_product_info(self) -> Dict[str, Any]:
        """
        Extract product information from Amazon product page
        
        Returns:
            Dict containing the product information
        """
        try:
            response = requests.get(self.url, headers=self.HEADERS, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch Amazon page: {response.status_code}")
                return {}
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product name
            product_name = None
            product_title = soup.find('span', id='productTitle')
            if product_title:
                product_name = product_title.text.strip()
            
            # Extract price
            price = None
            price_elem = soup.find('span', class_='a-offscreen')
            if price_elem:
                price_str = price_elem.text.strip()
                price = self.clean_price(price_str)
                
            # Determine currency
            currency = 'USD'  # Default
            if price_elem:
                price_text = price_elem.text.strip()
                if '€' in price_text:
                    currency = 'EUR'
                elif '£' in price_text:
                    currency = 'GBP'
                elif '¥' in price_text:
                    currency = 'JPY'
                elif '₹' in price_text:
                    currency = 'INR'
                    
            # Check stock status
            in_stock = True
            availability = soup.find('div', id='availability')
            if availability:
                availability_text = availability.text.strip().lower()
                in_stock = 'in stock' in availability_text
                
            # Get image URL
            image_url = None
            img_elem = soup.find('img', id='landingImage')
            if img_elem and 'src' in img_elem.attrs:
                image_url = img_elem['src']
                
            # Get description
            description = None
            desc_elem = soup.find('div', id='productDescription')
            if desc_elem:
                description = desc_elem.text.strip()
                
            return {
                'name': product_name,
                'price': price,
                'currency': currency,
                'in_stock': in_stock,
                'image_url': image_url,
                'description': description
            }
            
        except Exception as e:
            logger.error(f"Error scraping Amazon product: {str(e)}")
            return {}
