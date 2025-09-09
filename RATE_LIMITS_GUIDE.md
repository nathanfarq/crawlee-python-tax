# 🚦 Rate Limits Guide for CRA Scraping

## Current vs Recommended Settings

### ❌ Current Defaults (Too Aggressive for Government Sites)
```env
CRA_LIMITS__MAX_REQUESTS_PER_MINUTE=30    # Too fast for gov sites
CRA_LIMITS__MAX_REQUESTS_PER_HOUR=500     # Could trigger monitoring
CRA_LIMITS__MAX_REQUESTS_PER_DAY=5000     # High volume
CRA_LIMITS__REQUEST_DELAY=2.0             # Too short intervals
```

### ✅ Recommended Conservative Settings
```env
# Start with these conservative settings
CRA_LIMITS__MAX_REQUESTS_PER_MINUTE=10
CRA_LIMITS__MAX_REQUESTS_PER_HOUR=200
CRA_LIMITS__MAX_REQUESTS_PER_DAY=1000
CRA_LIMITS__REQUEST_DELAY=3.0
CRA_LIMITS__MAX_RETRIES=3
CRA_LIMITS__RETRY_DELAY=10.0
```

## Rate Limit Comparison

| Setting | Requests/Min | Pages/Hour | Pages/Day | Interval | Assessment |
|---------|--------------|------------|-----------|----------|------------|
| **Conservative** | 10 | 600 | 1,000 | 6s | 🟢 Recommended |
| **Moderate** | 20 | 1,200 | 2,000 | 3s | 🟡 Test first |
| **Current Default** | 30 | 1,800 | 5,000 | 2s | 🔴 Too aggressive |

## Why Conservative for Canada.ca?

### 🏛️ Government Site Considerations
- **Public service infrastructure** - shared with citizen access
- **Stricter monitoring** - government sites often have sophisticated bot detection
- **Legal/ethical considerations** - respect for public resources
- **Data sensitivity** - tax information requires careful handling

### 📊 Performance Impact
- **1,000 pages/day** is still substantial for tax data collection
- **Quality over quantity** - thorough processing of each page
- **Reduced server load** - respectful of shared infrastructure
- **Lower detection risk** - stays under typical monitoring thresholds

## Gradual Scaling Strategy

### Phase 1: Start Conservative (Week 1)
```env
CRA_LIMITS__MAX_REQUESTS_PER_MINUTE=5
CRA_LIMITS__REQUEST_DELAY=5.0
```
- Monitor for any blocking or errors
- Verify data quality and completeness
- Check server response times

### Phase 2: Moderate Testing (Week 2)
```env
CRA_LIMITS__MAX_REQUESTS_PER_MINUTE=10
CRA_LIMITS__REQUEST_DELAY=3.0
```
- Only if Phase 1 works perfectly
- Watch for any changes in response patterns
- Monitor error rates

### Phase 3: Optimized (Ongoing)
```env
CRA_LIMITS__MAX_REQUESTS_PER_MINUTE=15
CRA_LIMITS__REQUEST_DELAY=2.5
```
- Maximum recommended for government sites
- Continue monitoring indefinitely
- Scale back if issues arise

## Warning Signs to Watch For

🚨 **Immediately reduce limits if you see:**
- HTTP 429 (Too Many Requests) errors
- Increased response times (>5 seconds typical)
- CAPTCHA challenges appearing
- Connection timeouts or refused connections
- Any blocking or access denied messages

## Environment Configuration

Add these to your `.env` file:

```env
# Conservative settings for canada.ca
CRA_LIMITS__MAX_REQUESTS_PER_MINUTE=10
CRA_LIMITS__MAX_REQUESTS_PER_HOUR=200
CRA_LIMITS__MAX_REQUESTS_PER_DAY=1000
CRA_LIMITS__REQUEST_DELAY=3.0
CRA_LIMITS__MAX_RETRIES=3
CRA_LIMITS__RETRY_DELAY=10.0

# Optional: Enable verbose logging to monitor behavior
CRA_LOG_LEVEL=INFO
```

## Best Practices

### ✅ Do:
- Start conservative and scale gradually
- Monitor server responses continuously  
- Respect robots.txt (automatically handled)
- Run during off-peak hours (nights/weekends)
- Use descriptive User-Agent strings
- Handle errors gracefully with backoff

### ❌ Don't:
- Start with aggressive rates on government sites
- Ignore error responses or warnings
- Scrape during business hours without testing first
- Use concurrent connections (keep max_concurrent_requests=1)
- Retry failed requests immediately

## Monitoring Your Crawl

Watch these metrics in your crawl output:
```
✅ Pages processed: 12      # Success rate should be >90%
❌ Validation errors: 1     # Should be low (<5%)
⚠️  Processing errors: 0    # Should be zero
```

If you see high error rates, immediately reduce your limits.