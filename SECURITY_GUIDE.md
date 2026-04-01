# DropSafe Security Guide

## Current Security Setup (MVP/Demo)

### What's Exposed:
- ✅ **Read Access**: Anyone with anon key can read workers, policies, claims
- 🔒 **Write Access**: Only service_role can create/update/delete
- 🔒 **UPI IDs**: Encrypted in database
- 🔒 **Phone Numbers**: Hashed (SHA-256)
- 🔒 **CORS**: Only your frontend domain + localhost

### Why This Is Acceptable for MVP:
1. No real user data yet (test data only)
2. No sensitive financial data in plain text
3. Frontend is domain-restricted (CORS)
4. Still learning/building the platform
5. Write operations are protected

---

## Production Security Options

### Option 1: Service Role Key (Recommended) ⭐

**How it works:**
- Backend uses `SUPABASE_SERVICE_ROLE_KEY` (bypasses RLS)
- Frontend uses `SUPABASE_ANON_KEY` (respects RLS)
- RLS policies protect user-facing data

**Setup:**

1. Get your service role key from Supabase:
   - Settings → API → `service_role` key (keep this SECRET!)

2. Update `.env`:
   ```env
   SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

3. Update `backend/database.py`:
   ```python
   SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # Not anon key!
   ```

4. Update RLS policies to be strict:
   ```sql
   -- Workers can ONLY see their own data
   CREATE POLICY "Workers view own data" ON workers
     FOR SELECT USING (auth.uid()::text = id::text);
   ```

**Pros:**
- ✅ Backend has full access (needed for automation)
- ✅ Users can only see their own data
- ✅ Simple to implement

**Cons:**
- ⚠️ Service key must be kept SECRET (never commit to git!)
- ⚠️ If leaked, attacker has full database access

---

### Option 2: API Key Authentication

**How it works:**
- Add API key authentication to FastAPI
- Only authenticated API calls can access data
- Frontend gets API key after user login

**Setup:**

```python
# backend/auth.py
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    if api_key != os.getenv("API_SECRET_KEY"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key"
        )
    return api_key

# In your endpoints:
@app.get("/health")
async def health(api_key: str = Depends(verify_api_key)):
    # Only accessible with valid API key
    ...
```

**Pros:**
- ✅ Simple to implement
- ✅ Works with current RLS setup

**Cons:**
- ⚠️ All users share same API key
- ⚠️ Can't differentiate between users

---

### Option 3: JWT-Based Authentication (Most Secure) 🔐

**How it works:**
- Users authenticate via WhatsApp/Phone OTP
- Supabase issues JWT token
- RLS uses `auth.uid()` to enforce user-specific policies
- Each user can only see their own data

**Setup:**

1. Enable Supabase Auth:
   ```sql
   -- RLS policies check authenticated user
   CREATE POLICY "Users see own policies" ON policies
     FOR SELECT USING (auth.uid()::text = worker_id::text);
   ```

2. Frontend authenticates users:
   ```javascript
   // User logs in with phone OTP
   const { data, error } = await supabase.auth.signInWithOtp({
     phone: '+919876543210'
   })
   ```

3. Backend validates JWT automatically

**Pros:**
- ✅ Most secure (each user isolated)
- ✅ Built-in to Supabase
- ✅ Industry standard

**Cons:**
- ⚠️ Complex to implement
- ⚠️ Need OTP provider (Twilio, etc.)
- ⚠️ Users must authenticate

---

## Comparison Table

| Feature | Current (Anon Read) | Service Role | API Key | JWT Auth |
|---------|---------------------|--------------|---------|----------|
| **Setup Complexity** | ✅ Easy | ✅ Easy | 🟡 Medium | 🔴 Complex |
| **Security Level** | ⚠️ Low | 🟡 Medium | 🟡 Medium | ✅ High |
| **User Isolation** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Backend Access** | ✅ Full | ✅ Full | ✅ Full | 🟡 Limited* |
| **MVP Ready** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |

*Backend can use service role for automation

---

## Recommended Migration Path

### Phase 1: MVP/Demo (Current) ✅
```
Frontend (anon key) → Supabase (public read)
Backend (anon key)  → Supabase (public read)
```

### Phase 2: Beta Testing (Next 2-4 weeks)
```
Frontend (anon key) → Supabase (public read)
Backend (SERVICE key) → Supabase (bypass RLS)
```

**What to do:**
1. Add `SUPABASE_SERVICE_ROLE_KEY` to `.env`
2. Update `database.py` to use service key
3. Tighten RLS policies (users can only see own data)
4. Add API key to FastAPI (optional)

### Phase 3: Production (Before real users)
```
Frontend (user JWT) → Supabase (RLS enforced)
Backend (SERVICE key) → Supabase (bypass RLS for automation)
```

**What to do:**
1. Enable Supabase Auth
2. Add WhatsApp/Phone OTP login
3. Update frontend to authenticate users
4. RLS policies enforce user-specific access
5. Backend uses service key only for automation (claims, payouts)

---

## What You Should Do RIGHT NOW

### For MVP/Demo:
1. ✅ Run the RLS migration (allow public read)
2. ✅ Test that endpoints work
3. ✅ Continue building features
4. ⏰ Plan to migrate to service_role before beta

### Security Checklist:
- [x] CORS configured (only your domain)
- [x] Phone numbers hashed
- [x] UPI IDs encrypted
- [ ] Add rate limiting (Supabase Dashboard)
- [ ] Move to service_role key before beta
- [ ] Add authentication before production

---

## Quick Wins You Can Do Today

### 1. Add Rate Limiting
Supabase Dashboard → Settings → API → Set rate limits:
- 100 requests/minute per IP
- Prevents abuse

### 2. Enable Database Backups
Supabase Dashboard → Database → Backups:
- Enable daily backups
- Prevents data loss

### 3. Set Up Monitoring
Supabase Dashboard → Logs:
- Monitor API usage
- Detect suspicious activity

### 4. Secure Your .env
```bash
# Never commit .env to git!
git rm --cached .env  # Remove if accidentally committed
```

---

## TL;DR

**For MVP (Now):**
- Run the RLS migration I provided
- Public read is fine for test data
- Focus on building features

**For Beta (Soon):**
- Switch to `SUPABASE_SERVICE_ROLE_KEY`
- Tighten RLS policies
- Add basic API authentication

**For Production (Later):**
- Implement JWT-based user authentication
- Full RLS enforcement
- Security audit before launch

**Your data is reasonably safe for MVP, but definitely migrate to service_role before adding real users!**
