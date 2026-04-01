# GitHub Actions Workflows Reference

## Quick Overview

| Workflow | File | Trigger | Purpose | Duration |
|----------|------|---------|---------|----------|
| **CI Pipeline** | `ci.yml` | Push/PR to main/develop | Lint, test, security scan | 10-15 min |
| **Backend CI** | `backend-ci.yml` | backend/** changes | Python tests & coverage | 5-8 min |
| **Frontend CI** | `frontend-ci.yml` | frontend/** changes | Type check, build verification | 3-5 min |
| **Security Scan** | `security.yml` | On push + daily 2 AM | Bandit, Safety, Trivy | 10-15 min |
| **Deploy** | `deploy.yml` | Push to main | Deploy to Vercel + Render | 10-15 min |

---

## Workflow Details

### 🔄 CI Pipeline (`ci.yml`)
**When:** Every push/PR to `main` or `develop`

**Steps:**
1. ✅ Python linting (black, isort, flake8)
2. ✅ Backend unit tests (pytest)
3. ✅ TypeScript type checking
4. ✅ Frontend linting (ESLint)
5. ✅ Frontend prettier check
6. ✅ Production build verification
7. ✅ Security scanning (Trivy, Bandit, TruffleHog)
8. ✅ Final status check

**Pass/Fail:** Shows on PR as status check

**Time:** ~10-15 minutes

**Must pass before:** Merging to main

---

### 🧪 Backend CI (`backend-ci.yml`)
**When:** `backend/**` files change

**Tests:**
- Format check (black)
- Import sorting (isort)
- Style linting (flake8)
- Unit tests (pytest)
- Coverage reporting

**Requirements:**
- Python 3.11
- PostgreSQL service

**Time:** 5-8 minutes

---

### ⚛️ Frontend CI (`frontend-ci.yml`)
**When:** `frontend/**` files change

**Checks:**
- TypeScript compilation
- ESLint (style)
- Prettier (formatting)
- Production build
- Bundle size reporting

**Requirements:**
- Node 18
- npm dependencies

**Time:** 3-5 minutes

---

### 🔐 Security Scan (`security.yml`)
**When:**
- Every push/PR
- Daily at 2 AM UTC (scheduled)

**Scans:**
- Bandit (Python security)
- Safety (Python dependencies)
- npm audit (Node dependencies)
- Trivy (vulnerabilities)
- TruffleHog (secrets)

**Time:** 10-15 minutes

**Important:** Doesn't block merges (informational only)

---

### 🚀 Deployment (`deploy.yml`)
**When:** Merge to `main` (after CI passes)

**Steps:**
1. Deploy backend to Render/Railway
2. Build frontend (React prod build)
3. Deploy frontend to Vercel
4. Send Slack notification

**Requires:**
- All CI checks passed
- Secrets configured (VERCEL_TOKEN, RENDER_DEPLOY_HOOK)
- Vercel & Render accounts set up

**Time:** 10-15 minutes

**Result:** Live on production URL

---

## Status Check Meanings

### On Pull Request

```
✅ ci.yml - All checks passed, ready to merge
🟡 ci.yml - Running...
❌ ci.yml - One or more checks failed, see logs
```

### How to Debug

1. Click on the failed status check
2. Click "Details" to see full logs
3. Expand the failed step
4. Read error message and fix locally
5. Push fix: `git push`
6. CI automatically re-runs

---

## Secrets Required

### For CI to Run
```
SUPABASE_URL
SUPABASE_KEY
SUPABASE_SERVICE_KEY
RAZORPAY_KEY_ID
RAZORPAY_KEY_SECRET
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
WEATHERAPI_KEY
IQAIR_API_KEY
```

### For Deployment
```
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
RENDER_DEPLOY_HOOK
SLACK_WEBHOOK (optional)
```

---

## Common Commands

```bash
# Manually trigger a workflow
# Go to Actions tab → Select workflow → "Run workflow"

# Skip CI for non-code changes
git commit -m "Update README [skip ci]"

# View detailed logs
# GitHub → Actions → Click run → Click job → Expand steps

# Test locally before pushing
cd backend
black .
flake8 .
pytest -v

cd ../frontend
npm run build
npx tsc --noEmit
npm run lint
```

---

## Performance Tips

1. **Cache everything** - Configured in workflows
2. **Parallel jobs** - Backend & frontend run simultaneously
3. **Skip unnecessary runs** - Use `[skip ci]` for docs
4. **Use specific paths** - Workflows only trigger on relevant file changes

---

## Emergency: Disable Workflow

If a workflow is broken:

1. Go to `.github/workflows/filename.yml`
2. Comment out the `on:` section:
   ```yaml
   # on:
   #   push:
   #     branches: [main]
   ```
3. Push the change
4. Workflow stops running
5. Fix the issue
6. Uncomment to re-enable

---

## Monitoring Dashboard

**Real-time status:** GitHub repo → Actions tab

View:
- ✅ Successful runs (green)
- ❌ Failed runs (red)
- ⏱️ Duration of each step
- 📊 Trends over time

---

## Contact & Support

- **Docs:** https://docs.github.com/en/actions
- **Status:** https://www.githubstatus.com
- **Help:** Stack Overflow tag: `github-actions`

