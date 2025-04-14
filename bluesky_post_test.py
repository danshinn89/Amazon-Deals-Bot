#!/usr/bin/env python3
'''
Single post test for Goin UP Deals (Bluesky version)
Tests finding one deal and posting it to Bluesky.
'''

import os
import logging
import sys
from dotenv import load_dotenv
from amazon_paapi.sdk.models.condition import Condition

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("goinupdeals_bluesky_test.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("GoinUPDeals")

# Load environment variables
load_dotenv()

# Import the database module
try:
    from database_operations import DealsDatabase
    db = DealsDatabase()
    logger.info("Database connection established")
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    db = None

def find_single_deal():
    '''Find a single good deal using the parameters that work with your API'''
    from amazon_deal_finder import AmazonDealFinder
    
    try:
        logger.info("Looking for a good deal...")
        
        # Create AmazonDealFinder instance
        finder = AmazonDealFinder()
        
        # Set up specific keywords for snacks
        keywords = [
            "rice krispies treats", 
            "snack box", 
            "granola bars",
            "chips snacks"
        ]
        
        # Try each keyword until we find a deal
        for keyword in keywords:
            logger.info(f"Searching for '{keyword}'")
            
            min_price_cents = int(5.0 * 100)  # $5 minimum price
            
            try:
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
                
                deals = []
                for item in response.items:
                    try:
                        if not hasattr(item, 'offers') or not item.offers or not hasattr(item.offers, 'listings') or not item.offers.listings:
                            continue
                            
                        listing = item.offers.listings[0]
                        
                        if not hasattr(listing, 'price') or not hasattr(listing.price, 'amount'):
                            continue
                        
                        current_price = float(listing.price.amount)
                        
                        if not hasattr(listing, 'saving_basis') or not hasattr(listing.saving_basis, 'amount'):
                            continue
                        
                        original_price = float(listing.saving_basis.amount)
                        discount = int((original_price - current_price) / original_price * 100)
                        
                        if discount >= 15:
                            title = "Unknown Product"
                            if hasattr(item, 'item_info') and hasattr(item.item_info, 'title') and hasattr(item.item_info.title, 'display_value'):
                                title = item.item_info.title.display_value
                            
                            asin = getattr(item, 'asin', 'unknown')
                            
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
                    deals.sort(key=lambda x: x['discount_percent'], reverse=True)
                    return deals[0]
                
            except Exception as e:
                logger.error(f"Error searching for '{keyword}': {e}")
                continue
        
        logger.warning("No deals found across all keywords")
        return None
        
    except Exception as e:
        logger.error(f"Error finding deal: {e}")
        return None

def post_single_deal(deal):
    '''Post a single deal to Bluesky'''
    try:
        # IMPORTANT: Update the import here to use post_deal_with_embed.
        from bluesky_poster import setup_bluesky_api, post_deal_with_embed
        
        if not deal:
            logger.error("No deal to post")
            return False
        
        logger.info("Setting up Bluesky API...")
        client = setup_bluesky_api()
        if not client:
            logger.error("Bluesky API setup failed")
            return False
        
        logger.info(f"Posting deal to Bluesky: {deal['title']}")
        success = post_deal_with_embed(client, deal)
        if success:
            logger.info("Deal posted successfully to Bluesky!")
            if db:
                db.save_deal(deal)
                db.mark_deal_as_posted(deal['asin'])
            return True
        else:
            logger.error("Failed to post deal to Bluesky")
            return False
            
    except Exception as e:
        logger.error(f"Error posting deal to Bluesky: {e}")
        return False

def run_single_post_test():
    '''Run a complete test of finding and posting a single deal'''
    logger.info("====== FINDING A DEAL ======")
    deal = find_single_deal()
    if not deal:
        logger.error("Could not find any deals, aborting")
        return False
        
    print("\nFound the following deal:")
    print(f"Title: {deal['title']}")
    print(f"Price: ${deal['price']} (was ${deal['original_price']})")
    print(f"Discount: {deal['discount_percent']}% off")
    print(f"URL: {deal['url']}")
    print(f"Has image: {'Yes' if deal.get('image_url') else 'No'}")
    
    confirm = input("\nPost this deal to Bluesky? (y/n): ")
    if confirm.lower() == 'y':
        if post_single_deal(deal):
            logger.info("Test completed successfully!")
            return True
        else:
            logger.error("Failed to post deal")
            return False
    else:
        logger.info("Post cancelled by user")
        return False

if __name__ == "__main__":
    print("=== Goin UP Deals - Bluesky Post Test ===\n")
    print("This script will:")
    print("1. Find a single good deal")
    print("2. Show you the deal")
    print("3. Ask for confirmation before posting")
    print("4. Post the deal to Bluesky\n")
    
    input("Press Enter to begin or Ctrl+C to cancel...")
    
    success = run_single_post_test()
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed. Check the logs for details.")
        
    sys.exit(0 if success else 1)
