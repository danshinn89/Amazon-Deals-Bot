#!/usr/bin/env python3
"""
Bluesky Poster - Handles posting deals to Bluesky using the AT Protocol.
This version builds a rich post record using facets to make links clickable
and an embed record to attach the deal image (if available).

Compatible with most versions of the AT Protocol client library.

Refer to: https://docs.bsky.app/docs/advanced-guides/post-richtext
"""

import os
import logging
import random
from typing import Dict, Optional, List
import requests
from atproto import Client
from dotenv import load_dotenv

logger = logging.getLogger("GoinUPDeals")
load_dotenv()

def setup_bluesky_api() -> Optional[Client]:
    """Initialize and return Bluesky API client."""
    try:
        bluesky_username = os.getenv("BLUESKY_USERNAME")
        bluesky_password = os.getenv("BLUESKY_APP_PASSWORD")
        if not bluesky_username or not bluesky_password:
            logger.error("Bluesky credentials not found in environment variables")
            return None
        client = Client()
        client.login(bluesky_username, bluesky_password)
        logger.info("Bluesky API authentication successful")
        return client
    except Exception as e:
        logger.error(f"Bluesky API authentication failed: {e}")
        return None

def create_link_facet(text: str, url: str) -> List[dict]:
    """
    Create a facet for a URL in text.
    This will make the URL clickable in the post.
    
    Args:
        text: The post text
        url: The URL to make clickable
        
    Returns:
        List of facet dictionaries
    """
    # Find where the URL appears in the text
    try:
        start = text.index(url)
        end = start + len(url)
        
        return [{
            "index": {
                "byteStart": start,
                "byteEnd": end
            },
            "features": [{
                "$type": "app.bsky.richtext.facet#link",
                "uri": url
            }]
        }]
    except ValueError:
        logger.warning(f"URL {url} not found in post text, facet will not be created")
        return []

def format_deal_post_rich(deal: Dict, client: Client) -> dict:
    """
    Build a rich post record with facets and, if available, an embed for an image.
    
    Args:
        deal: Dictionary with keys such as 'title', 'price', 'original_price',
              'discount_percent', 'url', and optionally 'image_url'.
        client: Bluesky API client used for uploading the image.
        
    Returns:
        A dictionary representing the post record.
    """
    title = deal['title']
    if len(title) > 50:
        title = title[:47] + "..."
    
    price = f"${deal['price']:.2f}"
    original = f"${deal['original_price']:.2f}"
    discount = deal['discount_percent']
    url = deal['url']
    
    # Base text including the full URL (for facet to work)
    text = (
        "🔥 PRICES GOIN UP SOON! 🔥\n\n"
        f"**{title}**\n\n"
        f"Now: {price} (was {original})\n"
        f"{discount}% OFF!\n\n"
        f"Grab it while it's hot! {url}\n\n"
        "#GoinUPDeals #AmazonDeals #DealAlert"
    )
    
    # Create facets for the URL
    facets = create_link_facet(text, url)
    
    # Handle image embeds
    embed = None
    image_url = deal.get('image_url')
    if image_url:
        try:
            resp = requests.get(image_url)
            if resp.status_code == 200:
                image_data = resp.content
                # Upload the image blob
                upload_response = client.upload_blob(image_data)
                if upload_response and hasattr(upload_response, 'blob'):
                    # Create image embed
                    embed = {
                        "$type": "app.bsky.embed.images",
                        "images": [{"alt": title, "image": upload_response.blob}]
                    }
        except Exception as e:
            logger.warning(f"Failed to process image embed: {e}")
    
    return {
        "text": text,
        "facets": facets,
        "embed": embed
    }

def post_deal_with_embed(client: Client, deal: Dict) -> bool:
    """
    Post a deal to Bluesky using rich text formatting, facets, and embed.
    """
    try:
        post_data = format_deal_post_rich(deal, client)
        
        # Using send_post method which is more commonly available in the AT Protocol client
        response = client.send_post(
            text=post_data["text"],
            facets=post_data.get("facets"),
            embed=post_data.get("embed")
        )
        
        if response and hasattr(response, 'uri'):
            logger.info(f"Successfully posted deal: {deal['title']}")
            return True
        else:
            logger.error(f"Failed to post deal, response: {response}")
            return False
    except Exception as e:
        logger.error(f"Error posting deal with embed: {e}")
        return False

def test_bluesky_connection() -> bool:
    """Test Bluesky API connection."""
    try:
        client = setup_bluesky_api()
        if not client:
            return False
        logger.info("Bluesky connection test successful")
        return True
    except Exception as e:
        logger.error(f"Bluesky connection test failed: {e}")
        return False