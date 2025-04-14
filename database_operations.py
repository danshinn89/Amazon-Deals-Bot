"""
Database operations for SnackDeals using Supabase
Handles all database interactions including storing and retrieving deals
"""

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict
from supabase import create_client, Client
from dotenv import load_dotenv

logger = logging.getLogger("SnackDeals")

class DealsDatabase:
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.client = self._init_client()

    def _init_client(self) -> Client:
        """Initialize and return Supabase client"""
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        return create_client(self.supabase_url, self.supabase_key)

    def save_deal(self, deal_data: Dict) -> bool:
        """
        Save a new deal to the database
        
        Args:
            deal_data: Dictionary containing deal information
        """
        try:
            # Ensure all required fields exist (even if NULL)
            deal_fields = {
                'asin': deal_data.get('asin', ''),
                'title': deal_data.get('title', ''),
                'price': float(deal_data.get('price', 0)),
                'original_price': float(deal_data.get('original_price', 0)),
                'discount_percent': int(deal_data.get('discount_percent', 0)),
                'url': deal_data.get('url', ''),
                'image_url': deal_data.get('image_url'),
                'posted': False,
                'created_at': datetime.utcnow().isoformat()
            }

            # Check if deal already exists
            existing = self.client.table('deals').select('id').eq('asin', deal_fields['asin']).execute()
            if existing.data:
                logger.info(f"Deal with ASIN {deal_fields['asin']} already exists")
                return False

            # Insert new deal
            response = self.client.table('deals').insert(deal_fields).execute()

            logger.info(f"Saved deal: {deal_fields['title']}")
            return True

        except Exception as e:
            logger.error(f"Error saving deal: {e}")
            return False

    def get_posted_deals(self, days: int = 7) -> List[str]:
        """Get ASINs of deals posted in the last X days"""
        try:
            response = self.client.table('deals')\
                .select('asin')\
                .eq('posted', True)\
                .gte('created_at', f'now()-interval \'{days} days\'')\
                .execute()
            return [record['asin'] for record in response.data]
        except Exception as e:
            logger.error(f"Error getting posted deals: {e}")
            return []

    def mark_deal_as_posted(self, asin: str) -> bool:
        """Mark a deal as posted"""
        try:
            self.client.table('deals')\
                .update({
                    'posted': True,
                    'posted_at': datetime.utcnow().isoformat()
                })\
                .eq('asin', asin)\
                .execute()
            logger.info(f"Marked deal {asin} as posted")
            return True
        except Exception as e:
            logger.error(f"Error marking deal as posted: {e}")
            return False

    def get_best_unposted_deal(self) -> Optional[Dict]:
        """Get the best unposted deal"""
        try:
            response = self.client.table('deals')\
                .select('*')\
                .eq('posted', False)\
                .order('discount_percent', desc=True)\
                .limit(1)\
                .execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting best unposted deal: {e}")
            return None 