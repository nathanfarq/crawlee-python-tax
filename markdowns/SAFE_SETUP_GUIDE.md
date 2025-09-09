# 🚀 Safe Setup Guide - Running CRA Crawler

## Step-by-Step Configuration

### 1. Create Your Environment File

```bash
# Copy the template
cp .env.example .env
```

### 2. Add Your Qdrant Credentials

Edit the `.env` file (this file is gitignored and safe):

```env
# Your actual Qdrant configuration
QDRANT_API_KEY=qdr_your_actual_api_key_here
QDRANT_ENDPOINT=https://fa649b5c-edf6-4a53-9a6f-2925da2e5d29.eu-west-1-0.aws.cloud.qdrant.io
QDRANT_CLUSTER_NAME=nathanfarq_free_cluster
QDRANT_CLUSTER_ID=fa649b5c-edf6-4a53-9a6f-2925da2e5d29

# Optional: Customize scraping behavior
CRA_LIMITS__MAX_REQUESTS_PER_MINUTE=10
CRA_LIMITS__REQUEST_DELAY=3.0
CRA_DATA_DIR=./my_cra_data
```

### 3. Install Dependencies

```bash
# Make sure you have the CRA scraper extras
uv add crawlee[cra-scraper]

# Or if using pip:
# pip install crawlee[cra-scraper]
```

### 4. Verify Your Setup

Run the verification script to test your configuration:

```bash
# Test your environment configuration
python verify_setup.py
```

### 5. Run the Crawler

```bash
# Run the example crawler
python examples/cra_scraper_example.py
```

## Alternative: Direct Python Usage

You can also configure and run the crawler directly in Python:

```python
import os
from crawlee.cra_scraper import CRACrawler, CRAConfig

async def main():
    # Verify environment variables are set
    required_vars = ['QDRANT_API_KEY', 'QDRANT_ENDPOINT']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        print("Please check your .env file")
        return
    
    # Create crawler with environment-based config
    config = CRAConfig()
    crawler = CRACrawler(config=config)
    
    # Initialize and run
    await crawler.initialize()
    results = await crawler.crawl()
    
    print(f"Crawling completed: {results}")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

## Security Checklist

Before running:

- [ ] `.env` file exists and contains your credentials
- [ ] `.env` file is NOT staged for git commit
- [ ] All required environment variables are set
- [ ] You're testing with conservative rate limits first

## Troubleshooting

### Configuration Issues
```bash
# Check if your .env file is being loaded
python -c "from crawlee.cra_scraper import CRAConfig; c=CRAConfig(); print('API key set:', bool(c.qdrant.api_key))"
```

### Permission Issues
```bash
# Make sure .env file has correct permissions
chmod 600 .env
```

### Rate Limiting
Start with conservative settings:
- `MAX_REQUESTS_PER_MINUTE=5`  
- `REQUEST_DELAY=5.0`

Then adjust based on results and server response.

## What Gets Stored

The crawler will:
1. **Extract** tax-related content from CRA pages
2. **Validate** content relevance and domain
3. **Vectorize** text using sentence transformers
4. **Store** in your Qdrant collection for semantic search

Your data will be available for similarity searches immediately after scraping.
