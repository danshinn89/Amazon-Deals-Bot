#!/usr/bin/env python3
"""
Bluesky Post - Alternate module for posting deals to Bluesky with rich text formatting.
This version uses facets to create a clickable "View Deal" link and an embed for images.
"""

import os
import logging
import random
from typing import Dict, Optional
import requests
from atproto import Client
from dotenv import load_dotenv

logger = logging.getLogger("GoinUPDeals")
load_dotenv()

def setup_bluesky_api() -> Optional[Client]:
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

def create_link_facet(text: str, link_label: str, url: str) -> dict:
    try:
        start = text.index(link_label)
        end = start + len(link_label)
    except ValueError:
        start = 0
        end = 0
    return {
        "$type": "app.bsky.richtext.facet",
        "index": {"byteStart": start, "byteEnd": end},
        "features": [{
            "$type": "app.bsky.richtext.facet.view",
            "uri": url
        }]
    }

def format_deal_post_rich(deal: Dict, client: Client) -> dict:
    title = deal['title']
    if len(title) > 50:
        title = title[:47] + "..."
    price = f"${deal['price']:.2f}"
    original = f"${deal['original_price']:.2f}"
    discount = deal['discount_percent']
    url = deal['url']
    text = (
        "🔥 PRICES GOIN UP SOON! 🔥\n\n"
        f"**{title}**\n\n"
        f"Now: {price} (was {original})\n"
        f"{discount}% OFF!\n\n"
        "Grab it while it's hot! View Deal\n\n"
        "#GoinUPDeals #AmazonDeals #DealAlert"
    )
    facets = [create_link_facet(text, "View Deal", url)]
    embed = None
    image_url = deal.get('image_url')
    if image_url:
        try:
            resp = requests.get(image_url)
            if resp.status_code == 200:
                image_data = resp.content
                upload_response = client.upload_blob(image_data, "image/jpeg")
                if upload_response and hasattr(upload_response, 'blob'):
                    embed = {
                        "$type": "app.bsky.embed.images",
                        "images": [{"image": {"ref": upload_response.blob}}]
                    }
        except Exception as e:
            logger.warning(f"Failed to process image embed: {e}")
    record = {
        "text": text,
        "facets": facets
    }
    if embed:
        record["embed"] = embed
    max_length = 300
    if len(record["text"]) > max_length:
        record["text"] = record["text"][:max_length-3] + "..."
    return record

def post_deal_with_embed(client: Client, deal: Dict) -> bool:
    try:
        record = format_deal_post_rich(deal, client)
        response = client.createRecord("app.bsky.feed.post", record=record)
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
    try:
        client = setup_bluesky_api()
        if not client:
            return False
        logger.info("Bluesky connection test successful")
        return True
    except Exception as e:
        logger.error(f"Bluesky connection test failed: {e}")
        return False
