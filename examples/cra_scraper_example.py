"""Example usage of the CRA scraper with secure environment configuration."""

import asyncio
import os
from dotenv import load_dotenv

from crawlee.cra_scraper import CRACrawler, CRAConfig

# Load environment variables from .env file
load_dotenv()


def verify_environment() -> bool:
    """Verify that required environment variables are set."""
    required_vars = [
        'QDRANT_API_KEY',
        'QDRANT_ENDPOINT', 
        'QDRANT_CLUSTER_NAME',
        'QDRANT_CLUSTER_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\n💡 Please check your .env file and ensure all required variables are set.")
        print("   See .env.example for the required format.")
        return False
    
    print("✅ Environment configuration verified")
    return True


async def main() -> None:
    """Run the CRA scraper example."""
    # Verify environment setup
    if not verify_environment():
        return
    
    # Create configuration (will load from environment variables)
    config = CRAConfig()
    
    # Optional: Override specific settings for this run
    # config.limits.max_requests_per_minute = 10  # Start conservative
    # config.limits.request_delay = 3.0  # 3 seconds between requests
    
    print(f"🎯 Target URL: {config.base_url}")
    print(f"⚡ Rate limits: {config.limits.max_requests_per_minute}/min, {config.limits.request_delay}s delay")
    print(f"🗄️  Collection: {config.qdrant.collection_name}")
    print()
    
    # Create and initialize crawler
    crawler = CRACrawler(config=config)
    
    try:
        # Initialize components
        print("🔧 Initializing crawler components...")
        await crawler.initialize()
        
        # Start crawling
        print("🚀 Starting CRA crawl...")
        results = await crawler.crawl()
        
        print("\n✅ Crawling completed!")
        print(f"📊 Pages crawled: {results['pages_crawled']}")
        print(f"✅ Pages processed: {results['pages_processed']}")
        print(f"💾 Pages stored: {results['pages_stored']}")
        print(f"❌ Validation errors: {results['validation_errors']}")
        print(f"⚠️  Processing errors: {results['processing_errors']}")
        
        # Example semantic search
        if results['pages_stored'] > 0:
            print("\n🔍 Testing semantic search...")
            search_queries = [
                "T1 personal income tax form filing instructions",
                "business tax deductions",
                "GST HST registration requirements"
            ]
            
            for query in search_queries:
                print(f"\n🔎 Query: '{query}'")
                search_results = await crawler.search_similar_content(
                    query=query,
                    limit=3
                )
                
                if search_results:
                    for i, result in enumerate(search_results, 1):
                        title = result.get('title', 'No title')[:60]
                        print(f"   {i}. {title}... (score: {result['score']:.3f})")
                else:
                    print("   No similar content found")
        
        print(f"\n🎉 Success! Your data is now searchable in Qdrant collection '{config.qdrant.collection_name}'")
    
    except Exception as e:
        print(f"❌ Error during scraping: {e}")
        print("\n💡 Tips for troubleshooting:")
        print("   - Check your internet connection")
        print("   - Verify your Qdrant API key is valid")
        print("   - Try reducing rate limits in your .env file")
        raise


if __name__ == '__main__':
    print("🕷️  CRA Crawler - Secure Environment Setup")
    print("=" * 50)
    asyncio.run(main())