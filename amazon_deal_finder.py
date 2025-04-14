"""
Amazon Deal Finder - Finds snack deals using Amazon's Product Advertising API
"""

import os
import logging
import time
from decimal import Decimal
from typing import List, Dict, Optional
from amazon_paapi import AmazonApi
from amazon_paapi.sdk.models.condition import Condition

logger = logging.getLogger("GoinUPDeals")

class AmazonDealFinder:
    def __init__(self):
        """Initialize Amazon PA-API client"""
        self.client = self._setup_client()
        self.last_request_time = 0
        self.min_request_interval = 10.0  # 10 seconds between requests
        self.max_retries = 3

    def _setup_client(self) -> Optional[AmazonApi]:
        """Set up Amazon PA-API client with error handling"""
        try:
            required_vars = ["AMAZON_ACCESS_KEY", "AMAZON_SECRET_KEY", "ASSOCIATE_TAG", "REGION"]
            missing_vars = [var for var in required_vars if not os.getenv(var)]
            
            if missing_vars:
                raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

            # Get the country code from region (e.g., "us-east-1" -> "US")
            region = os.getenv("REGION", "us-east-1")
            country_code = region.split('-')[0].upper()

            return AmazonApi(
                key=os.getenv("AMAZON_ACCESS_KEY"),
                secret=os.getenv("AMAZON_SECRET_KEY"),
                tag=os.getenv("ASSOCIATE_TAG"),
                country=country_code
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Amazon client: {e}")
            raise

    def _throttled_request(self, func, *args, **kwargs):
        """Execute a request with throttling to avoid rate limits"""
        # Calculate time since last request
        now = time.time()
        time_since_last = now - self.last_request_time
        
        # If we need to wait to meet the minimum interval
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.info(f"Throttling: Waiting {sleep_time:.2f} seconds before next request")
            time.sleep(sleep_time)
        
        # Make the request with retries
        retries = 0
        while retries <= self.max_retries:
            try:
                self.last_request_time = time.time()
                return func(*args, **kwargs)
            except Exception as e:
                if "TooManyRequests" in str(e) or "Too Many Requests" in str(e):
                    retries += 1
                    if retries > self.max_retries:
                        logger.error(f"Max retries reached. Last error: {e}")
                        raise
                    
                    # Exponential backoff: wait longer with each retry
                    wait_time = 30 * (2 ** retries)  # 60s, 120s, 240s
                    logger.warning(f"Hit rate limits, retrying in {wait_time} seconds (attempt {retries}/{self.max_retries})")
                    time.sleep(wait_time)
                    self.min_request_interval += 5.0  # Increase interval for future requests
                else:
                    raise

    def calculate_discount(self, current_price: Decimal, original_price: Decimal) -> int:
        """Calculate discount percentage"""
        try:
            if original_price <= 0 or current_price <= 0:
                return 0
            return int((original_price - current_price) / original_price * 100)
        except Exception as e:
            logger.warning(f"Error calculating discount: {e}")
            return 0

    def find_deals_by_keyword(self, keyword, min_discount=20, min_price=5.0):
        """Find deals for a specific keyword with extended throttling"""
        deals = []
        
        try:
            logger.info(f"Searching for '{keyword}' deals")
            
            # Convert min_price from dollars to cents (API expects lowest denomination)
            min_price_cents = int(min_price * 100)
            
            # Use only parameters that work with your API version
            # Based on test results: keywords, item_count, min_price, condition, min_saving_percent
            response = self._throttled_request(
                self.client.search_items,
                keywords=keyword,
                item_count=10,  # Maximum items per request
                min_price=min_price_cents,
                condition=Condition.NEW,
                min_saving_percent=min_discount  # Use this to filter by discount directly
            )
            
            if not hasattr(response, 'items') or not response.items:
                logger.warning(f"No items found for '{keyword}'")
                return []
            
            logger.info(f"Found {len(response.items)} items for '{keyword}'")
            
            for item in response.items:
                try:
                    # Check if the item has offers and listings
                    if not hasattr(item, 'offers') or not item.offers or not hasattr(item.offers, 'listings') or not item.offers.listings:
                        continue
                        
                    listing = item.offers.listings[0]
                    
                    # Check if price exists
                    if not hasattr(listing, 'price') or not hasattr(listing.price, 'amount'):
                        continue
                        
                    current_price = Decimal(str(listing.price.amount))
                    
                    # Check if saving_basis exists for original price
                    original_price = None
                    if hasattr(listing, 'saving_basis') and hasattr(listing.saving_basis, 'amount'):
                        original_price = Decimal(str(listing.saving_basis.amount))
                    else:
                        # Skip if no original price (not a discount)
                        continue
                    
                    # Double-check discount percentage (should already be filtered by min_saving_percent)
                    discount = self.calculate_discount(current_price, original_price)
                    
                    if discount >= min_discount:
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
                            'price': float(current_price),
                            'original_price': float(original_price),
                            'discount_percent': discount,
                            'url': f"https://www.amazon.com/dp/{asin}?tag={os.getenv('ASSOCIATE_TAG')}",
                            'image_url': image_url,
                            'posted': False
                        })
                except Exception as e:
                    logger.warning(f"Error processing item {getattr(item, 'asin', 'unknown')}: {e}")
                    continue
                    
            # Sort by discount percentage
            deals.sort(key=lambda x: x['discount_percent'], reverse=True)
            return deals
            
        except Exception as e:
            logger.error(f"Error searching for {keyword}: {e}")
            return []

    def find_best_deals(self, num_deals: int = 5, min_discount: int = 20, min_price: float = 5.0) -> List[Dict]:
        """Find the best snack deals on Amazon"""
        if not self.client:
            logger.error("Amazon client not initialized")
            return []

        # Use specific snack-related keywords
        keywords = [
            "snack box", 
            "rice krispies treats", 
            "granola bars",
            "chips snacks",
            "cookies snacks",
            "trail mix"
        ]
        deals = []
        
        for keyword in keywords:
            try:
                logger.info(f"Searching for '{keyword}'")
                
                # Convert min_price from dollars to cents (API expects lowest denomination)
                min_price_cents = int(min_price * 100)
                
                # Use only parameters that work with your API version
                response = self._throttled_request(
                    self.client.search_items,
                    keywords=keyword,
                    item_count=10,
                    min_price=min_price_cents,
                    condition=Condition.NEW,
                    min_saving_percent=min_discount
                )
                
                if not hasattr(response, 'items') or not response.items:
                    logger.warning(f"No items found for '{keyword}'")
                    continue
                
                logger.info(f"Found {len(response.items)} items for '{keyword}'")
                
                for item in response.items:
                    try:
                        # Check if the item has offers and listings
                        if not hasattr(item, 'offers') or not item.offers or not hasattr(item.offers, 'listings') or not item.offers.listings:
                            continue
                            
                        listing = item.offers.listings[0]
                        
                        # Check if price exists
                        if not hasattr(listing, 'price') or not hasattr(listing.price, 'amount'):
                            continue
                            
                        current_price = Decimal(str(listing.price.amount))
                        
                        # Check if saving_basis exists for original price
                        original_price = None
                        if hasattr(listing, 'saving_basis') and hasattr(listing.saving_basis, 'amount'):
                            original_price = Decimal(str(listing.saving_basis.amount))
                        else:
                            # Skip if no original price (not a discount)
                            continue
                        
                        # Double-check discount percentage
                        discount = self.calculate_discount(current_price, original_price)
                        
                        if discount >= min_discount:
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
                                'price': float(current_price),
                                'original_price': float(original_price),
                                'discount_percent': discount,
                                'url': f"https://www.amazon.com/dp/{asin}?tag={os.getenv('ASSOCIATE_TAG')}",
                                'image_url': image_url,
                                'posted': False
                            })
                    except Exception as e:
                        logger.warning(f"Error processing item {getattr(item, 'asin', 'unknown')}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error searching for {keyword}: {e}")
                continue
        
        # Sort by discount percentage and return top deals
        deals.sort(key=lambda x: x['discount_percent'], reverse=True)
        return deals[:num_deals]

# Function to get the best deals (to be used directly without class)
def find_best_deals(num_deals: int = 5, min_discount: int = 20, min_price: float = 5.0) -> List[Dict]:
    """Find the best snack deals on Amazon"""
    finder = AmazonDealFinder()
    return finder.find_best_deals(num_deals, min_discount, min_price)