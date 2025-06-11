"""
Tests for the scraper components
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import requests

from pricewatcher.scrapers.base import BaseScraper
from pricewatcher.scrapers.amazon import AmazonScraper
from pricewatcher.scrapers.ebay import EbayScraper
from pricewatcher.scrapers.walmart import WalmartScraper
from pricewatcher.scrapers.manager import ScraperManager


class BaseScraperTests(unittest.TestCase):
    """Tests for the BaseScraper class"""
    
    def test_abstract_methods(self):
        """Test that BaseScraper is abstract and can't be instantiated directly"""
        with self.assertRaises(TypeError):
            BaseScraper()
            
    def test_extract_product_id(self):
        """Test the extract_product_id method of BaseScraper"""
        with patch.object(BaseScraper, '__abstractmethods__', set()):
            # Now we can instantiate it for testing
            scraper = BaseScraper()
            
            # Test default implementation
            with self.assertRaises(NotImplementedError):
                scraper.extract_product_id("https://example.com/product/123")


class AmazonScraperTests(unittest.TestCase):
    """Tests for the AmazonScraper class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = AmazonScraper()
        
    def test_can_handle_url(self):
        """Test URL validation logic"""
        # Valid URLs
        self.assertTrue(self.scraper.can_handle_url("https://www.amazon.com/dp/B07P6Y8L3F"))
        self.assertTrue(self.scraper.can_handle_url("https://www.amazon.com/Product-Name/dp/B07P6Y8L3F"))
        self.assertTrue(self.scraper.can_handle_url("https://amazon.com/dp/B07P6Y8L3F"))
        
        # Invalid URLs
        self.assertFalse(self.scraper.can_handle_url("https://www.ebay.com/itm/123456"))
        self.assertFalse(self.scraper.can_handle_url("https://example.com"))
        
    def test_extract_product_id(self):
        """Test product ID extraction"""
        # Standard product URL
        self.assertEqual(
            self.scraper.extract_product_id("https://www.amazon.com/dp/B07P6Y8L3F"),
            "B07P6Y8L3F"
        )
        
        # URL with product name and ID
        self.assertEqual(
            self.scraper.extract_product_id("https://www.amazon.com/Product-Name/dp/B07P6Y8L3F/ref=sr_1_1"),
            "B07P6Y8L3F"
        )
        
    @patch('pricewatcher.scrapers.amazon.requests.get')
    def test_scrape_product(self, mock_get):
        """Test product scraping with a mocked response"""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Product - Amazon.com</title></head>
            <body>
                <span id="productTitle">Test Product</span>
                <span class="a-offscreen">$29.99</span>
                <span id="availability" class="a-color-success">In Stock.</span>
                <div id="feature-bullets">
                    <li>Product description 1</li>
                    <li>Product description 2</li>
                </div>
                <img id="landingImage" src="https://example.com/image.jpg" />
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Test scraping
        product_info = self.scraper.scrape_product("https://www.amazon.com/dp/B07P6Y8L3F")
        
        # Verify results
        self.assertEqual(product_info["name"], "Test Product")
        self.assertEqual(product_info["price"], 29.99)
        self.assertEqual(product_info["currency"], "USD")
        self.assertTrue(product_info["in_stock"])
        self.assertEqual(product_info["image_url"], "https://example.com/image.jpg")
        self.assertIn("Product description", product_info["description"])


class EbayScraperTests(unittest.TestCase):
    """Tests for the EbayScraper class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = EbayScraper()
        
    def test_can_handle_url(self):
        """Test URL validation logic"""
        # Valid URLs
        self.assertTrue(self.scraper.can_handle_url("https://www.ebay.com/itm/123456"))
        self.assertTrue(self.scraper.can_handle_url("https://ebay.com/itm/123456"))
        
        # Invalid URLs
        self.assertFalse(self.scraper.can_handle_url("https://www.amazon.com/dp/B07P6Y8L3F"))
        self.assertFalse(self.scraper.can_handle_url("https://example.com"))
        
    def test_extract_product_id(self):
        """Test product ID extraction"""
        self.assertEqual(
            self.scraper.extract_product_id("https://www.ebay.com/itm/123456"),
            "123456"
        )
        
    @patch('pricewatcher.scrapers.ebay.requests.get')
    def test_scrape_product(self, mock_get):
        """Test product scraping with a mocked response"""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Product | eBay</title></head>
            <body>
                <h1 class="x-item-title__mainTitle">Test Product</h1>
                <div class="x-price-primary">
                    <span>US $19.99</span>
                </div>
                <div class="d-quantity__availability">
                    <span>3 available</span>
                </div>
                <div class="tab-content-m">
                    <div>Product description for testing</div>
                </div>
                <img class="img-fluid" src="https://example.com/ebay-image.jpg" />
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        # Test scraping
        product_info = self.scraper.scrape_product("https://www.ebay.com/itm/123456")
        
        # Verify results
        self.assertEqual(product_info["name"], "Test Product")
        self.assertEqual(product_info["price"], 19.99)
        self.assertEqual(product_info["currency"], "USD")
        self.assertTrue(product_info["in_stock"])
        self.assertEqual(product_info["image_url"], "https://example.com/ebay-image.jpg")
        self.assertIn("Product description", product_info["description"])


class ScraperManagerTests(unittest.TestCase):
    """Tests for the ScraperManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.manager = ScraperManager()
        
    def test_get_scraper_for_url(self):
        """Test getting the correct scraper for a URL"""
        # Amazon URL
        scraper = self.manager.get_scraper_for_url("https://www.amazon.com/dp/B07P6Y8L3F")
        self.assertIsInstance(scraper, AmazonScraper)
        
        # eBay URL
        scraper = self.manager.get_scraper_for_url("https://www.ebay.com/itm/123456")
        self.assertIsInstance(scraper, EbayScraper)
        
        # Walmart URL
        scraper = self.manager.get_scraper_for_url("https://www.walmart.com/ip/123456")
        self.assertIsInstance(scraper, WalmartScraper)
        
        # Unsupported URL
        with self.assertRaises(ValueError):
            self.manager.get_scraper_for_url("https://example.com/product")
    
    @patch('pricewatcher.scrapers.amazon.AmazonScraper.scrape_product')
    def test_scrape_product(self, mock_scrape):
        """Test the scrape_product method"""
        # Mock the scraper's response
        mock_scrape.return_value = {
            "name": "Test Product",
            "price": 29.99,
            "currency": "USD",
            "in_stock": True,
            "image_url": "https://example.com/image.jpg",
            "description": "Test description"
        }
        
        # Test the manager's scrape_product method
        product_info = self.manager.scrape_product("https://www.amazon.com/dp/B07P6Y8L3F")
        
        # Verify results
        self.assertEqual(product_info["name"], "Test Product")
        self.assertEqual(product_info["price"], 29.99)
        self.assertEqual(product_info["currency"], "USD")
        
        # Verify the mock was called with the correct URL
        mock_scrape.assert_called_once_with("https://www.amazon.com/dp/B07P6Y8L3F")
        

if __name__ == '__main__':
    unittest.main()
