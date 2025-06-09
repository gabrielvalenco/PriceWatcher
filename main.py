#!/usr/bin/env python3
"""
PriceWatcher - Main entry point
"""
import os
import argparse
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import core modules
from pricewatcher.api.server import start_api
from pricewatcher.scrapers.manager import start_scraping
from pricewatcher.tasks.scheduler import start_scheduler
from pricewatcher.dashboard.app import start_dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/pricewatcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main function that starts the PriceWatcher application."""
    parser = argparse.ArgumentParser(description="PriceWatcher - Track e-commerce product prices")
    parser.add_argument('--api-only', action='store_true', help="Run only the API server")
    parser.add_argument('--scrape-only', action='store_true', help="Run only the scraper")
    parser.add_argument('--dashboard', action='store_true', help="Start the web dashboard")
    args = parser.parse_args()

    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        if args.api_only:
            start_api()
        elif args.scrape_only:
            start_scraping()
        elif args.dashboard:
            start_dashboard()
        else:
            # Start all components
            start_scheduler()
            start_api()
    except Exception as e:
        logger.error(f"Error starting PriceWatcher: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
