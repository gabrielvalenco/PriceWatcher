"""
Walmart scraper for PriceWatcher
"""
import logging
import re
import json
from typing import Dict, Any
import requests
from bs4 import BeautifulSoup
from .base import BaseScraper

logger = logging.getLogger(__name__)

class WalmartScraper(BaseScraper):
    """Scraper for Walmart product pages"""
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    
    @staticmethod
    def get_store_name() -> str:
        """Return the store name"""
        return "Walmart"
    
    def is_valid_url(self) -> bool:
        """Check if the URL is a valid Walmart product URL"""
        walmart_pattern = r'https?://(www\.)?walmart\.(com|ca)/ip/.*'
        return bool(re.match(walmart_pattern, self.url))
    
    def extract_product_info(self) -> Dict[str, Any]:
        """
        Extract product information from Walmart product page
        
        Returns:
            Dict containing the product information
        """
        try:
            response = requests.get(self.url, headers=self.HEADERS, timeout=10)
            if response.status_code != 200:
                logger.error(f"Failed to fetch Walmart page: {response.status_code}")
                return {}
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Walmart often includes product data in a JSON script
            product_data = {}
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and '@type' in data and data['@type'] == 'Product':
                        product_data = data
                        break
                except (json.JSONDecodeError, AttributeError):
                    continue
            
            # Extract product name
            product_name = None
            if product_data and 'name' in product_data:
                product_name = product_data['name']
            else:
                name_elem = soup.find('h1', {'itemprop': 'name'}) or soup.find('h1', class_='prod-ProductTitle')
                if name_elem:
                    product_name = name_elem.text.strip()
            
            # Extract price
            price = None
            if product_data and 'offers' in product_data and 'price' in product_data['offers']:
                price = float(product_data['offers']['price'])
            else:
                price_elem = soup.find('span', {'itemprop': 'price'}) or soup.find('span', class_='price-characteristic')
                if price_elem:
                    price_str = price_elem.text.strip()
                    price = self.clean_price(price_str)
                
            # Determine currency
            currency = 'USD'  # Default for Walmart US
            if '.ca' in self.url:
                currency = 'CAD'
            
            if product_data and 'offers' in product_data and 'priceCurrency' in product_data['offers']:
                currency = product_data['offers']['priceCurrency']
                    
            # Check stock status
            in_stock = True
            if product_data and 'offers' in product_data and 'availability' in product_data['offers']:
                availability = product_data['offers']['availability']
                in_stock = 'InStock' in availability
            else:
                # Try to find stock information in the HTML
                availability = soup.find('div', {'id': 'availability'}) or soup.find('span', class_='product-availability-message')
                if availability:
                    availability_text = availability.text.strip().lower()
                    in_stock = not ('out of stock' in availability_text or 'unavailable' in availability_text)
                
            # Get image URL
            image_url = None
            if product_data and 'image' in product_data:
                image_url = product_data['image']
            else:
                img_elem = soup.find('img', {'id': 'product-details-main-image'}) or soup.find('img', class_='prod-hero-image')
                if img_elem and 'src' in img_elem.attrs:
                    image_url = img_elem['src']
                
            # Get description
            description = None
            if product_data and 'description' in product_data:
                description = product_data['description']
            else:
                desc_elem = soup.find('div', {'id': 'product-description'}) or soup.find('div', class_='about-product')
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
            logger.error(f"Error scraping Walmart product: {str(e)}")
            return {}
