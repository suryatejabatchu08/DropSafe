# DropSafe CI/CD Pipeline - Complete Setup Guide

## ✅ What's Been Created

### GitHub Actions Workflows
1. **`.github/workflows/ci.yml`** - Main CI pipeline (linting, testing, security)
2. **`.github/workflows/backend-ci.yml`** - Backend-specific tests
3. **`.github/workflows/frontend-ci.yml`** - Frontend-specific tests
4. **`.github/workflows/security.yml`** - Security scanning (daily + on-demand)
5. **`.github/workflows/deploy.yml`** - Production deployment

### Testing & Tools
- **pytest** - Backend unit tests
- **black** - Code formatting
- **flake8** - Linting
- **isort** - Import sorting
- **TypeScript** - Frontend type checking
- **ESLint** - Frontend linting
- **Bandit** - Security scanning (Python)
- **npm audit** - Dependency scanning (Node)
- **Trivy** - Vulnerability scanning
- **TruffleHog** - Secret detection

### Cache Service
- **`backend/utils/cache_service.py`** - Redis-based caching with fallback

---

## 🚀 Setup Instructions

### Step 1: Push Code to GitHub

```bash
cd /c/Users/Surya\ Teja/Desktop/DropSafe

# Initialize git if not already done
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial DropSafe setup with CI/CD pipelines"

# Add GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/DropSafe.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Step 2: Configure GitHub Secrets

1. Go to your GitHub repo
2. **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"** and add each:

**Backend Secrets:**
```
Name: SUPABASE_URL
Value: https://pypsfbnqhiqobvtatybg.supabase.co

Name: SUPABASE_KEY
Value: [Your anon key]

Name: SUPABASE_SERVICE_KEY
Value: [Your service role key]

Name: RAZORPAY_KEY_ID
Value: rzp_test_SXuLkQfcfRquMY

Name: RAZORPAY_KEY_SECRET
Value: yoOzDzkscT6GGiD1aL6qhRXq

Name: TWILIO_ACCOUNT_SID
Value: AC93f153d2eb520a2c55f56d8e8b3eeac4

Name: TWILIO_AUTH_TOKEN
Value: 32f09a9c811549ae0f023015bb4e57c8

Name: WEATHERAPI_KEY
Value: 067be5ff041e441ab93162806262903

Name: IQAIR_API_KEY
Value: 3f438a17-6b38-4f29-9ffc-15f5bdd65eb0
```

**Frontend/Deployment Secrets:**
```
Name: VITE_API_URL_PROD
Value: https://api.dropsafe.example.com

Name: VERCEL_TOKEN
Value: [Get from Vercel dashboard]

Name: VERCEL_ORG_ID
Value: [Your Vercel org ID]

Name: VERCEL_PROJECT_ID
Value: [Your Vercel project ID]

Name: RENDER_DEPLOY_HOOK
Value: [Get from Render deployment hooks]

Name: SLACK_WEBHOOK
Value: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### Step 3: Configure Branch Protection Rules

1. Go to **Settings** → **Branches**
2. Click **"Add rule"** under "Branch protection rules"
3. Branch pattern name: `main`
4. Check these options:
   - ✅ Require a pull request before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Require code reviews before merging (set to 1)
   - ✅ Require signed commits

### Step 4: Set Up Slack Notifications (Optional)

1. Go to your Slack workspace
2. **Settings** → **Manage apps** → **Build** → **Create app**
3. Choose "From scratch"
4. Name: `DropSafe CI/CD`
5. **Select features** → **Incoming Webhooks** → **Add New Webhook to Workspace**
6. Copy the webhook URL to GitHub Secrets as `SLACK_WEBHOOK`

### Step 5: Install & Configure Tools Locally

```bash
# Backend tools
cd backend
pip install -r requirements.txt
pip install black flake8 isort pytest pytest-asyncio

# Frontend tools
cd ../frontend
npm install

# Test locally before pushing
npm run build
cd ../backend
pytest -v
```

---

## 🔄 Workflow Triggers

### CI Pipeline (Automatic)
- **Trigger:** Push to `main` or `develop`, or PR to these branches
- **What runs:** Linting, tests, type checking, security scans
- **Time:** ~5-10 minutes
- **Result:** Shows on PR - must pass before merge

### Security Scan (Scheduled)
- **Trigger:** Daily at 2 AM UTC + on every push
- **What runs:** Bandit, Safety, npm audit, Trivy, TruffleHog
- **Time:** ~10-15 minutes
- **Result:** Check GitHub "Security" tab for vulnerabilities

### Deployment (Automatic on Main)
- **Trigger:** Merge to `main` branch
- **What runs:** Build backend + frontend, deploy to production
- **Time:** ~10-15 minutes
- **Result:** Slack notification with status

---

## 📊 Monitoring & Debugging

### View Status in GitHub

1. **Actions tab** - See all workflow runs
2. **Pull request** - Status checks appear above merge button
3. **Commits** - Green checkmark = passed, red X = failed

### Debug Failed Workflows

```bash
# 1. Check logs in GitHub Actions
# Click workflow run → Click job → Expand failed step

# 2. Reproduce locally
# Run same command that failed, e.g.:
black . --check
pytest -v
npm run build

# 3. Fix and push retry
git add .
git commit -m "Fix CI issues"
git push
```

### Common Issues & Fixes

| Issue | Cause | Fix |
|-------|-------|-----|
| Tests fail in CI but pass locally | Python/Node version mismatch | Check version in workflow, match locally |
| "Secret not found" | Missing GitHub secret | Add secret in repo settings |
| Frontend build fails | Missing dependencies | `npm ci` in frontend directory |
| TypeScript errors | Type checking too strict | Update tsconfig.json or fix types |
| Long build time | No caching | GitHub Actions caching is configured |

---

## 🎯 Best Practices

### Before Pushing Code

```bash
# 1. Format code
cd backend && black .
cd ../frontend && npx prettier --write src/

# 2. Type check
cd frontend && npx tsc --noEmit

# 3. Lint
cd backend && flake8 . --max-line-length=100
cd ../frontend && npm run lint

# 4. Test
cd ../backend && pytest -v

# 5. Build
cd ../frontend && npm run build
```

### Commit Messages

```bash
# Good commit messages (run CI once):
git commit -m "Add fraud detection layer 1"
git commit -m "Fix premium calculation formula"

# Skip CI for non-code changes:
git commit -m "Update README [skip ci]"
```

### PR Review Process

1. Create feature branch: `git checkout -b feature/xyz`
2. Make changes and commit
3. Push: `git push origin feature/xyz`
4. Open PR on GitHub
5. Wait for CI to pass (green checkmarks)
6. Request code review from team
7. Once approved, merge to `main`
8. CI automatically deploys to production

---

## 📈 Performance Monitoring

### Check CI Performance

1. **GitHub Actions** tab → Click workflow
2. **Timing** column shows duration
3. Target: Backend tests < 5 min, Frontend build < 3 min

### Optimize Slow Workflows

```yaml
# Add caching to speed up future runs
- uses: actions/setup-python@v4
  with:
    python-version: '3.11'
    cache: 'pip'  # Caches pip packages

- uses: actions/setup-node@v3
  with:
    node-version: '18'
    cache: 'npm'  # Caches node_modules
```

---

## 🚨 Security Considerations

### Secrets Management

✅ **Do:**
- Store API keys in GitHub Secrets
- Rotate keys regularly
- Use different keys for dev/prod
- Enable secret scanning

❌ **Don't:**
- Commit `.env` files
- Hardcode credentials in code
- Share webhook URLs publicly
- Commit private keys

### Branch Protection

Enforce before any merge to `main`:
- ✅ All status checks pass
- ✅ At least 1 code review approval
- ✅ Signed commits (if available)
- ✅ Up to date with main branch

---

## 📚 Next Steps

1. **Push code to GitHub** - Complete Step 1 above
2. **Configure secrets** - Complete Step 2 above
3. **Set branch protection** - Complete Step 3 above
4. **Make a test commit** - Trigger CI pipeline
   ```bash
   git commit --allow-empty -m "Test CI pipeline"
   git push
   ```
5. **Watch it run** - Go to Actions tab to see workflow execute
6. **Set up Slack** (optional) - Complete Step 4 above

---

## 🎉 Deployment Checklist

Before pushing to main (which deploys to production):

- [ ] All tests pass locally (`pytest -v`, `npm run build`)
- [ ] Code formatted (`black .`, `npx prettier --write src/`)
- [ ] No linting errors (`flake8 .`, `npm run lint`)
- [ ] Type checking passes (`npx tsc --noEmit`)
- [ ] No security warnings (run `bandit -r . -ll`)
- [ ] Dependencies updated (`npm audit fix`, `pip freeze > requirements.txt`)
- [ ] Environment variables set correctly
- [ ] Database migrations ready
- [ ] PR reviewed and approved
- [ ] Ready for production

---

## 📞 Support & Resources

- **GitHub Actions Docs:** https://docs.github.com/en/actions
- **Workflow Syntax:** https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions
- **Troubleshooting:** https://github.com/actions
- **Security:** https://docs.github.com/en/actions/security-guides

