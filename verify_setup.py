#!/usr/bin/env python3
"""
Verification script to test CRA scraper setup and configuration.
Run this before starting actual scraping to ensure everything is configured correctly.
"""

import asyncio
import os
import sys
from typing import Any

from dotenv import load_dotenv


def check_environment_file() -> bool:
    """Check if .env file exists and is readable."""
    env_path = '.env'
    
    if not os.path.exists(env_path):
        print("❌ .env file not found")
        print("   Run: cp .env.example .env")
        print("   Then edit .env with your actual credentials")
        return False
    
    if not os.access(env_path, os.R_OK):
        print("❌ .env file exists but is not readable")
        print("   Run: chmod 600 .env")
        return False
    
    print("✅ .env file found and readable")
    return True


def check_gitignore() -> bool:
    """Check if .env is properly gitignored."""
    try:
        # Check if .env is tracked by git
        import subprocess
        result = subprocess.run(['git', 'check-ignore', '.env'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ .env file is properly gitignored")
            return True
        else:
            print("⚠️  .env file might not be gitignored")
            print("   This could expose your API keys if committed")
            return False
    
    except Exception:
        print("⚠️  Could not verify git ignore status")
        return True  # Don't fail verification for git issues


def check_environment_variables() -> dict[str, bool]:
    """Check if required environment variables are set."""
    load_dotenv()
    
    required_vars = {
        'QDRANT_API_KEY': 'Your Qdrant API key',
        'QDRANT_ENDPOINT': 'Your Qdrant endpoint URL', 
        'QDRANT_CLUSTER_NAME': 'Your Qdrant cluster name',
        'QDRANT_CLUSTER_ID': 'Your Qdrant cluster ID'
    }
    
    optional_vars = {
        'CRA_LIMITS__MAX_REQUESTS_PER_MINUTE': 'Rate limiting',
        'CRA_LIMITS__REQUEST_DELAY': 'Request delay',
        'CRA_DATA_DIR': 'Data storage directory'
    }
    
    results = {}
    
    print("\n🔍 Checking required environment variables:")
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            # Show partial value for security
            masked_value = value[:8] + '...' if len(value) > 8 else '***'
            print(f"✅ {var}: {masked_value}")
            results[var] = True
        else:
            print(f"❌ {var}: Not set ({description})")
            results[var] = False
    
    print("\n📋 Optional environment variables:")
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚪ {var}: Using default ({description})")
    
    return results


async def test_qdrant_connection() -> bool:
    """Test connection to Qdrant."""
    try:
        from crawlee.cra_scraper import CRAQdrantClient, CRAConfig
        
        config = CRAConfig()
        
        if not config.qdrant.api_key:
            print("❌ Cannot test Qdrant connection - API key not set")
            return False
        
        if not config.qdrant.endpoint:
            print("❌ Cannot test Qdrant connection - endpoint not set") 
            return False
        
        print("🔌 Testing Qdrant connection...")
        
        client = CRAQdrantClient(
            endpoint=config.qdrant.endpoint,
            api_key=config.qdrant.api_key,
            collection_name=config.qdrant.collection_name,
        )
        
        # Try to initialize (this will test connection)
        await client.initialize()
        
        # Get collection info
        info = await client.get_collection_info()
        print(f"✅ Qdrant connection successful!")
        print(f"   Collection: {info['name']}")
        print(f"   Points: {info['points_count']}")
        print(f"   Vector size: {info['vector_size']}")
        
        return True
        
    except ImportError:
        print("⚠️  Qdrant client not available (missing dependencies)")
        print("   Run: uv add crawlee[cra-scraper]")
        return False
    except Exception as e:
        print(f"❌ Qdrant connection failed: {e}")
        print("   Check your API key and endpoint URL")
        return False


def test_configuration() -> bool:
    """Test configuration loading."""
    try:
        from crawlee.cra_scraper import CRAConfig
        
        print("🔧 Testing configuration loading...")
        config = CRAConfig()
        
        print(f"✅ Configuration loaded successfully")
        print(f"   Base URL: {config.base_url}")
        print(f"   Rate limit: {config.limits.max_requests_per_minute}/min")
        print(f"   Request delay: {config.limits.request_delay}s")
        print(f"   Collection: {config.qdrant.collection_name}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Cannot import CRA scraper: {e}")
        print("   Run: uv add crawlee[cra-scraper]")
        return False
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


async def main() -> None:
    """Run all verification checks."""
    print("🔍 CRA Scraper Setup Verification")
    print("=" * 40)
    
    checks_passed = 0
    total_checks = 0
    
    # File system checks
    total_checks += 1
    if check_environment_file():
        checks_passed += 1
    
    total_checks += 1  
    if check_gitignore():
        checks_passed += 1
    
    # Environment variable checks
    total_checks += 1
    env_results = check_environment_variables()
    if all(env_results.values()):
        print("✅ All required environment variables are set")
        checks_passed += 1
    else:
        missing = [var for var, ok in env_results.items() if not ok]
        print(f"❌ Missing environment variables: {missing}")
    
    # Configuration check
    total_checks += 1
    if test_configuration():
        checks_passed += 1
    
    # Qdrant connection check (if config is available)
    if all(env_results.values()):
        total_checks += 1
        if await test_qdrant_connection():
            checks_passed += 1
    
    # Summary
    print(f"\n📊 Verification Summary: {checks_passed}/{total_checks} checks passed")
    
    if checks_passed == total_checks:
        print("🎉 All checks passed! Your setup is ready for scraping.")
        print("\n🚀 Next steps:")
        print("   python examples/cra_scraper_example.py")
    else:
        print("⚠️  Some checks failed. Please fix the issues above before scraping.")
        print("\n💡 Common solutions:")
        print("   1. Copy .env.example to .env")  
        print("   2. Add your actual Qdrant credentials to .env")
        print("   3. Install dependencies: uv add crawlee[cra-scraper]")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())