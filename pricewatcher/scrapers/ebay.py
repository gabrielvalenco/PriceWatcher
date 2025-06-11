"""
eBay scraper for PriceWatcher
"""
import logging
import re
from typing import Dict, Any
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper

logger = logging.getLogger(__name__)

class EbayScraper(BaseScraper):
    """Scraper for eBay product pages"""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    @staticmethod
    def get_store_name() -> str:
        """Return the store name"""
        return "eBay"
    
    def is_valid_url(self) -> bool:
        """Check if the URL is a valid eBay product URL"""
        ebay_pattern = r'https?://(www\.)?ebay\.(com|co\.uk|de|fr|es|it|com\.au|ca)/itm/.*'
        return bool(re.match(ebay_pattern, self.url))
    
    def extract_product_info(self) -> Dict[str, Any]:
        """
        Extract product information from eBay product page
        
        Returns:
            Dict containing the product information
        """
        try:
            response = requests.get(self.url, headers=self.HEADERS, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch eBay page: {response.status_code}")
                return {}
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract product name
            product_name = None
            product_title = soup.find('h1', id='itemTitle')
            if product_title:
                # Remove "Details about" prefix that eBay sometimes adds
                title_text = product_title.text.strip()
                if "Details about" in title_text:
                    title_text = title_text.split("Details about", 1)[1].strip()
                product_name = title_text
            
            # Extract price
            price = None
            price_elem = soup.find('span', id='prcIsum')
            if not price_elem:
                # Try alternate price element
                price_elem = soup.find('span', id='mm-saleDscPrc')
            
            if price_elem:
                price_str = price_elem.text.strip()
                price = self.clean_price(price_str)
                
            # Determine currency
            currency = 'USD'  # Default
            if price_elem and 'content' in price_elem.attrs:
                # Sometimes eBay provides currency in content attribute
                content_parts = price_elem['content'].split(' ')
                if len(content_parts) >= 2:
                    currency = content_parts[0]
            else:
                # Try to detect currency from price string
                if price_elem:
                    price_text = price_elem.text.strip()
                    if '€' in price_text:
                        currency = 'EUR'
                    elif '£' in price_text:
                        currency = 'GBP'
                    elif 'AU$' in price_text:
                        currency = 'AUD'
                    elif 'C $' in price_text:
                        currency = 'CAD'
                        
            # Check stock status
            in_stock = True
            availability = soup.find('span', id='qtySubTxt')
            if availability:
                availability_text = availability.text.strip().lower()
                in_stock = not ('out of stock' in availability_text or 'sold out' in availability_text)
                
            # Get image URL
            image_url = None
            img_elem = soup.find('img', id='icImg')
            if img_elem and 'src' in img_elem.attrs:
                image_url = img_elem['src']
                
            # Get description
            description = None
            desc_elem = soup.find('div', id='descItemNumber')
            if desc_elem:
                parent_div = desc_elem.find_parent('div', class_='section')
                if parent_div:
                    description = parent_div.text.strip()
                
            return {
                'name': product_name,
                'price': price,
                'currency': currency,
                'in_stock': in_stock,
                'image_url': image_url,
                'description': description
            }
            
        except Exception as e:
            logger.error(f"Error scraping eBay product: {str(e)}")
            return {}
