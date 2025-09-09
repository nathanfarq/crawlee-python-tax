# 🔐 Security Setup Guide

## Critical Security Information

This repository is **PUBLIC** - never commit sensitive information like API keys, endpoints, or cluster IDs to version control.

## Required Environment Configuration

### 1. Create Your Environment File

```bash
# Copy the example file
cp .env.example .env

# Edit with your actual credentials (DO NOT COMMIT THIS FILE)
nano .env
```

### 2. Configure Your Qdrant Credentials

Add your actual values to the `.env` file:

```env
# Required: Your Qdrant Cloud Configuration
QDRANT_API_KEY=your_actual_api_key_here
QDRANT_ENDPOINT=https://your-cluster-id.region.aws.cloud.qdrant.io
QDRANT_CLUSTER_NAME=your_cluster_name
QDRANT_CLUSTER_ID=your_cluster_id

# Optional: Customize behavior
CRA_LIMITS__MAX_REQUESTS_PER_MINUTE=30
CRA_DATA_DIR=./cra_data
```

### 3. Verify Security

✅ **Protected Files** (in `.gitignore`):
- `.env` - Your actual environment file
- `.env.local` - Local overrides
- `*.key`, `*.pem` - Certificate files
- `cra_data/` - Scraped data directory

✅ **Safe to Commit**:
- `.env.example` - Template with placeholder values
- All source code files (no hardcoded secrets)

## Before You Commit

**Always verify** no sensitive data is being committed:

```bash
# Check what's being staged
git diff --staged

# Verify .env is ignored
git check-ignore .env

# Should show: .env
```

## GitHub Repository Actions

### If You Haven't Committed Yet (GOOD):
No action needed - the sensitive information has been removed from the code.

### If You Already Committed Sensitive Info (REQUIRES ACTION):

1. **Remove from Git History**:
   ```bash
   # Remove sensitive files from history
   git filter-branch --force --index-filter \
   'git rm --cached --ignore-unmatch .env*' \
   --prune-empty --tag-name-filter cat -- --all
   
   # Force push to update remote
   git push origin --force --all
   ```

2. **Rotate Your API Keys**:
   - Generate new API keys in Qdrant Cloud
   - Update your local `.env` file
   - Revoke the old keys that were exposed

3. **Consider Repository Settings**:
   - Review who has access to your repository
   - Check if you need to make it private instead

## Production Deployment

For production environments, use secure secret management:

- **Docker**: Use Docker secrets or environment files outside the image
- **Kubernetes**: Use Kubernetes secrets
- **Cloud Platforms**: Use platform secret managers (AWS Secrets Manager, etc.)
- **CI/CD**: Store secrets in your CI/CD platform's secure storage

## Verification Checklist

- [ ] `.env` file exists locally with your credentials
- [ ] `.env` is in `.gitignore` 
- [ ] No hardcoded credentials in source code
- [ ] Tests pass with environment-based configuration
- [ ] `git status` shows no sensitive files staged

## Need Help?

If you've accidentally committed sensitive information:
1. **Act quickly** - rotate exposed credentials immediately
2. **Clean the history** using the commands above
3. **Verify the cleanup** by checking your GitHub repository

Remember: Once something is pushed to a public repository, assume it has been seen by others.