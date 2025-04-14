Amazon affiliate marketing bot

A Bluesky bot that automatically finds and posts Amazon snack deals to your Bluesky account.
Features

Searches Amazon for discounted snack products
Stores deals in a database to avoid duplicates
Posts deals to Bluesky with formatted text and images
Scheduled posting at configurable intervals

---------------Requirements---------------

Python 3.9+
Amazon Product Advertising API credentials
Bluesky account with app password
Supabase account for database storage

---------------Installation---------------

Clone this repository
Install dependencies:
pip install -r requirements.txt

Set up your environment variables in a .env file:
# Amazon Product Advertising API
AMAZON_ACCESS_KEY=your_access_key
AMAZON_SECRET_KEY=your_secret_key
ASSOCIATE_TAG=your_associate_tag
REGION=us-east-1

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Bluesky
BLUESKY_USERNAME=your_bluesky_username
BLUESKY_APP_PASSWORD=your_bluesky_app_password


Usage
Finding Deals Without Posting
python bluesky_main.py --find

Posting a Single Deal Manually
python bluesky_main.py --manual

Running in Scheduled Mode (posts every 6 hours)
python bluesky_main.py
Testing the Setup
python bluesky_post_test.py
Database Setup
Create a Supabase table with the following structure:
sqlCREATE TABLE deals (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) NOT NULL UNIQUE,
    title TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2) NOT NULL,
    discount_percent INTEGER NOT NULL,
    url TEXT NOT NULL,
    image_url TEXT,
    posted BOOLEAN DEFAULT FALSE,
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

License
MIT License