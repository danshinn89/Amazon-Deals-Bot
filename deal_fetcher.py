#!/usr/bin/env python3
"""
Deal Fetcher - Collects deals from Amazon PA-API once daily
and stores them in the database for later posting
"""

import os
import logging
import sys
import time
from dotenv import load_dotenv
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("deal_fetcher.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("GoinUPDeals")

# Load environment variables
load_dotenv()

# Import modules
from database_operations import DealsDatabase
from amazon_deal_finder import AmazonDealFinder
from amazon_paapi.sdk.models.condition import Condition

def fetch_daily_deals():
    """Fetch deals from Amazon and store them in the database"""
    try:
        # Connect to database
        db = DealsDatabase()
        
        # Initialize deal finder with extended throttling
        finder = AmazonDealFinder()
        finder.min_request_interval = 15.0  # 15 seconds between requests
        
        logger.info("Starting daily deal fetch")
        
        # Get list of specific snack keywords to search
        keywords = [
            "snack box", 
            "rice krispies treats", 
            "granola bars",
            "chips snacks",
            "cookies snacks",
            "trail mix",
            "popcorn snacks",
            "pretzels snacks",
            "crackers snacks",
            "fruit snacks"
        ]
        
        deals_found = 0
        deals_saved = 0
        
        # Search each keyword one at a time with significant delays
        for keyword in keywords:
            try:
                logger.info(f"Searching for '{keyword}'")
                
                # Convert min_price from dollars to cents (API expects lowest denomination)
                min_price_cents = int(5.0 * 100)  # $5 minimum price
                
                # Use only parameters that work with your API version
                # Get deals for this keyword using the parameters we know work
                # Use the AmazonDealFinder instance directly instead of the find_deals_by_keyword method
                response = finder._throttled_request(
                    finder.client.search_items,
                    keywords=keyword,
                    item_count=10,
                    min_price=min_price_cents,
                    condition=Condition.NEW,
                    min_saving_percent=15  # 15% minimum discount
                )
                
                if not hasattr(response, 'items') or not response.items:
                    logger.warning(f"No items found for '{keyword}'")
                    continue
                
                logger.info(f"Found {len(response.items)} items for '{keyword}'")
                
                # Process the items to find deals
                deals = []
                for item in response.items:
                    try:
                        # Check if the item has offers and listings
                        if not hasattr(item, 'offers') or not item.offers or not hasattr(item.offers, 'listings') or not item.offers.listings:
                            continue
                            
                        listing = item.offers.listings[0]
                        
                        # Check if price exists
                        if not hasattr(listing, 'price') or not hasattr(listing.price, 'amount'):
                            continue
                            
                        current_price = float(listing.price.amount)
                        
                        # Check if saving_basis exists for original price
                        if not hasattr(listing, 'saving_basis') or not hasattr(listing.saving_basis, 'amount'):
                            continue
                            
                        original_price = float(listing.saving_basis.amount)
                        
                        # Calculate discount percentage
                        discount = int((original_price - current_price) / original_price * 100)
                        
                        if discount >= 15:  # 15% minimum discount
                            # Check for item_info and title
                            title = "Unknown Product"
                            if hasattr(item, 'item_info') and hasattr(item.item_info, 'title') and hasattr(item.item_info.title, 'display_value'):
                                title = item.item_info.title.display_value
                                
                            # Check for ASIN
                            asin = getattr(item, 'asin', 'unknown')
                            
                            # Check for image URL
                            image_url = None
                            if hasattr(item, 'images') and hasattr(item.images, 'primary') and hasattr(item.images.primary, 'medium'):
                                image_url = getattr(item.images.primary.medium, 'url', None)
                            
                            deals.append({
                                'asin': asin,
                                'title': title,
                                'price': current_price,
                                'original_price': original_price,
                                'discount_percent': discount,
                                'url': f"https://www.amazon.com/dp/{asin}?tag={os.getenv('ASSOCIATE_TAG')}",
                                'image_url': image_url,
                                'posted': False
                            })
                    except Exception as e:
                        logger.warning(f"Error processing item {getattr(item, 'asin', 'unknown')}: {e}")
                        continue
                
                if deals:
                    deals_found += len(deals)
                    
                    # Save each deal to database
                    for deal in deals:
                        if db.save_deal(deal):
                            deals_saved += 1
                
                # Wait 45 seconds between keywords to avoid rate limits
                logger.info(f"Waiting 45 seconds before next search...")
                time.sleep(45)
                
            except Exception as e:
                logger.error(f"Error searching for '{keyword}': {e}")
                # Wait longer after an error
                logger.info(f"Waiting 3 minutes after error...")
                time.sleep(180)
        
        logger.info(f"Deal fetch complete. Found {deals_found} deals, saved {deals_saved} new deals.")
        return True
        
    except Exception as e:
        logger.error(f"Error in fetch_daily_deals: {e}")
        return False

if __name__ == "__main__":
    logger.info("=== Deal Fetcher Started ===")
    success = fetch_daily_deals()
    if success:
        logger.info("Deal fetching completed successfully")
    else:
        logger.error("Deal fetching failed")
    logger.info("=== Deal Fetcher Finished ===")