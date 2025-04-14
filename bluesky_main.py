#!/usr/bin/env python3
"""
Goin UP Deals Bot - A Bluesky bot that posts deals on snacks from Amazon.
Similar to the Twitter bot but posting to Bluesky instead.
"""

import os
import logging
import sys
import argparse
import time
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("goinupdeals_bluesky.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("GoinUPDeals")

# Load environment variables
load_dotenv()

# Import necessary modules
from database_operations import DealsDatabase
from amazon_deal_finder import find_best_deals
# IMPORTANT: Import the updated function post_deal_with_embed.
from bluesky_poster import setup_bluesky_api, test_bluesky_connection, post_deal_with_embed

def bluesky_post_from_database(db: DealsDatabase) -> bool:
    """
    Post a deal from the database to Bluesky.

    This function does the following:
      1. Retrieves a Bluesky API client.
      2. Looks up the best unposted deal from the database.
      3. Uses the rich post function (post_deal_with_embed) to send the deal.
      4. Marks the deal as posted in the database if successful.
    
    Args:
        db: An instance of DealsDatabase.
    
    Returns:
        True if the deal was posted successfully; False otherwise.
    """
    try:
        # Get Bluesky API client using the updated function.
        client = setup_bluesky_api()
        if not client:
            logger.error("Bluesky API setup failed")
            return False

        logger.info("Looking for deals before prices go UP!")
        # Retrieve the best unposted deal from the database.
        deal = db.get_best_unposted_deal()
        if not deal:
            logger.info("No unposted deals found in database")
            return False

        # Post to Bluesky using the rich posting function.
        if post_deal_with_embed(client, deal):
            # Mark the deal as posted in the database.
            db.mark_deal_as_posted(deal['asin'])
            logger.info(f"Posted deal from database to Bluesky: {deal['title']}")
            return True
        else:
            logger.error(f"Failed to post deal to Bluesky: {deal['title']}")
            return False

    except Exception as e:
        logger.error(f"Error posting deal from database to Bluesky: {e}")
        return False

def main():
    """Main function to run the Goin UP Deals Bluesky bot."""
    parser = argparse.ArgumentParser(description='Goin UP Deals Bluesky Bot')
    parser.add_argument('--test', action='store_true', help='Post a single deal for testing')
    parser.add_argument('--setup', action='store_true', help='Set up the database and exit')
    parser.add_argument('--find', action='store_true', help='Find deals without posting and print them')
    parser.add_argument('--manual', action='store_true', help='Manually post a single deal from the database')
    
    args = parser.parse_args()
    
    try:
        # Initialize the database service
        db = DealsDatabase()  # Raises error if credentials are missing
        
        if args.setup:
            logger.info("Database setup complete")
            return
        
        elif args.find:
            logger.info("Finding deals without posting...")
            deals = find_best_deals(num_deals=5)
            if deals:
                logger.info(f"Found {len(deals)} deals:")
                for i, deal in enumerate(deals, 1):
                    db.save_deal(deal)
                    logger.info(f"{i}. {deal['title']} - {deal['price']} (was {deal['original_price']}) - {deal['discount_percent']}% off")
            else:
                logger.info("No deals found")
            return
        
        elif args.test:
            if not test_bluesky_connection():
                logger.error("Bluesky connection test failed")
                return
            logger.info("Running in test mode - running bluesky_post_test.py")
            import subprocess
            subprocess.run([sys.executable, "bluesky_post_test.py"])
            return
            
        elif args.manual:
            if not test_bluesky_connection():
                logger.error("Bluesky connection test failed")
                return
            logger.info("Manually posting a single deal from the database")
            success = bluesky_post_from_database(db)
            if success:
                print("✅ Successfully posted a deal to Bluesky")
            else:
                print("❌ Failed to post deal to Bluesky")
            return
        
        else:
            if not test_bluesky_connection():
                logger.error("Bluesky connection test failed")
                return
            logger.info("Starting Goin UP Deals Bluesky Bot in scheduled mode")
            print("Press Ctrl+C to exit")
            
            # Immediately post one deal.
            bluesky_post_from_database(db)
            
            # Then schedule future posts using a simple loop.
            while True:
                # Wait 6 hours between posts (14400 seconds).
                logger.info("Waiting 6 hours until next post...")
                time.sleep(14400)
                bluesky_post_from_database(db)

    except Exception as e:
        logger.exception(f"Unhandled exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
