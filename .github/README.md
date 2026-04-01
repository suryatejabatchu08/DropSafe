# GitHub Actions CI/CD Pipeline

DropSafe uses GitHub Actions for automated testing, linting, and deployment.

## 📋 Workflows

### 1. **CI Pipeline** (`.github/workflows/ci.yml`)
Runs on every push and pull request to `main` and `develop` branches.

**What it does:**
- ✅ Python linting (black, isort, flake8)
- ✅ Backend tests (pytest)
- ✅ TypeScript type checking
- ✅ Frontend build verification
- ✅ Security scanning (Trivy, TruffleHog)
- ✅ Bundle size analysis

**When it triggers:**
- Push to `main` or `develop`
- Pull request to `main` or `develop`

---

### 2. **Backend CI** (`.github/workflows/backend-ci.yml`)
Focused backend testing with database services.

**Includes:**
- Python syntax validation
- Import sorting (isort)
- Code formatting (black)
- Linting (flake8)
- Unit tests (pytest)
- Coverage reporting to CodeCov

---

### 3. **Frontend CI** (`.github/workflows/frontend-ci.yml`)
Focused frontend testing and build checks.

**Includes:**
- TypeScript type checking
- ESLint linting
- Prettier formatting
- Production build verification
- Bundle size monitoring

---

### 4. **Security Scan** (`.github/workflows/security.yml`)
Comprehensive security scanning.

**Runs:**
- On every push/PR
- Daily at 2 AM UTC (scheduled)

**Checks:**
- Bandit (Python security)
- Safety (Python dependencies)
- npm audit (Node dependencies)
- Trivy (container/filesystem vulnerabilities)
- TruffleHog (secret detection)

---

### 5. **Production Deployment** (`.github/workflows/deploy.yml`)
Automated deployment on merge to `main`.

**What it does:**
- Builds and deploys backend to Render/Railway
- Builds and deploys frontend to Vercel
- Sends notifications to Slack

---

## 🔐 Secrets Configuration

Add these to GitHub repo settings (Settings → Secrets and variables → Actions):

### Backend Secrets
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
RAZORPAY_KEY_ID=rzp_test_xxxxx
RAZORPAY_KEY_SECRET=xxxxx
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
WEATHERAPI_KEY=xxxxx
IQAIR_API_KEY=xxxxx
```

### Frontend/Deployment Secrets
```
VITE_API_URL_PROD=https://api.dropsafe.example.com
VERCEL_TOKEN=your_vercel_token
VERCEL_ORG_ID=your_org_id
VERCEL_PROJECT_ID=your_project_id
RENDER_DEPLOY_HOOK=https://api.render.com/deploy/xxxxx
SLACK_WEBHOOK=https://hooks.slack.com/services/xxxxx
```

---

## 🚀 Deployment Process

### 1. Local Development
```bash
# Make changes
git add .
git commit -m "Your message"
git push origin your-branch
```

### 2. Create Pull Request
- Push opens CI pipeline automatically
- All tests must pass for merge
- GitHub shows status checks

### 3. Merge to Main
```bash
# After PR approval, merge to main
# This automatically triggers deploy.yml
```

### 4. Production Deployment
- Backend deploys to Render/Railway
- Frontend builds and deploys to Vercel
- Slack notification sent

---

## ✅ Pre-Commit Checks

Before pushing, run locally to catch issues early:

### Backend
```bash
cd backend

# Format code
black .

# Sort imports
isort .

# Lint
flake8 .

# Run tests
pytest -v

# Security scan
bandit -r . -ll
```

### Frontend
```bash
cd frontend

# Type check
npx tsc --noEmit

# Lint
npm run lint

# Format
npx prettier --write src/

# Build
npm run build
```

---

## 📊 Monitoring CI/CD

### View Build Status
1. Go to GitHub repository
2. Click "Actions" tab
3. See workflow runs and their status

### View Detailed Logs
1. Click on a workflow run
2. Click on specific job (backend, frontend, etc.)
3. Expand job steps to see logs

### Branch Protection Rules

Enable on `main` branch:
- ✅ Require status checks to pass
- ✅ Require branches to be up-to-date
- ✅ Require code reviews (1+ reviewer)
- ✅ Require signed commits

---

## 🔧 Troubleshooting

### Workflow fails but locally it works

**Common issues:**
1. Missing secrets - check GitHub Settings → Secrets
2. Environment differences - GitHub uses fresh Ubuntu, not your machine
3. Database config - CI uses test database

**Fix:**
```bash
# Check GitHub Actions logs
# Review error messages in "Actions" tab
# Update code and push retry
```

### Tests pass locally but fail in CI

**Possible causes:**
- Python/Node version mismatch
- Missing environment variables
- Timing issues (async code, network)

**Debug steps:**
```bash
# Use GitHub runner locally (expensive)
# Try Docker: docker run ubuntu:latest /bin/bash
# Or check specific Python/Node versions
python --version  # Match .github/workflows/ci.yml
node --version    # Match .github/workflows/ci.yml
```

### Deployment fails

**Check in this order:**
1. **Frontend builds locally?** - `npm run build` in `/frontend`
2. **Backend tests pass?** - `pytest` in `/backend`
3. **Secrets set correctly?** - Check GitHub Settings
4. **Vercel/Render setup?** - Verify webhook URLs

---

## 📈 Performance Tips

### Speed up CI

1. **Cache npm dependencies:**
   ```yaml
   cache: 'npm'
   cache-dependency-path: 'frontend/package-lock.json'
   ```

2. **Cache pip dependencies:**
   ```yaml
   cache: 'pip'
   ```

3. **Parallel jobs:** CI already runs backend and frontend in parallel

4. **Skip CI for docs:**
   ```bash
   git commit -m "Update README [skip ci]"
   ```

---

## 🎯 Best Practices

1. **Keep workflows simple** - Large YAML files are hard to debug
2. **Fail fast** - Early linting catches issues before tests
3. **Cache everything** - Speeds up repeated runs significantly
4. **Test locally first** - Use same tools as CI (black, pytest, etc.)
5. **Lock dependencies** - Use `package-lock.json` and `Pipfile.lock`
6. **Keep secrets secure** - Never commit .env files
7. **Automate everything** - Deploy automatically after merge

---

## 📚 Documentation

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Workflow Syntax Reference](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Security Hardening](https://docs.github.com/en/actions/security-guides)

