# DropSafe 🛵⚡
### *When the storm stops deliveries, we start paying.*

> **Guidewire DEVTrails 2026** | AI-Powered Parametric Income Insurance for India's Q-Commerce Delivery Partners
> Persona: Zepto / Blinkit | Platform: Web App (WhatsApp-First Worker UX)

---

## The Insight Nobody Talks About

Every InsurTech pitch says "we serve the gig worker." None of them have asked *how* a Blinkit delivery partner actually uses their phone at 2 PM in 44°C heat, parked outside a dark store, waiting for orders that aren't coming.

They don't open apps. They open WhatsApp.

**DropSafe is the only parametric insurance platform built around that reality.**

Workers interact entirely through a WhatsApp chatbot - no app download, no form filling, no claims process. The web platform exists for insurers and administrators. The worker's entire insurance lifecycle - onboarding, policy confirmation, payout notification - happens in a chat they already have open.

And when a disruption hits? DropSafe already knows. The payout arrives before the worker even thinks to ask.

---

## 📌 Table of Contents

1. [Why Q-Commerce, Why Now](#1-why-q-commerce-why-now)
2. [The DropSafe Difference - Three Core Innovations](#2-the-dropsafe-difference--three-core-innovations)
3. [Persona Scenarios & Application Workflow](#3-persona-scenarios--application-workflow)
4. [Weekly Premium Model & Parametric Triggers](#4-weekly-premium-model--parametric-triggers)
5. [AI/ML Architecture](#5-aiml-architecture)
6. [Tech Stack & System Design](#6-tech-stack--system-design)
7. [Development Roadmap](#7-development-roadmap)

---

## 1. Why Q-Commerce, Why Now

### The Q-Commerce Worker is Uniquely Vulnerable

Food delivery workers lose income when it rains. Q-Commerce workers lose income when it rains *and* when the specific 3 km corridor between their dark store and their delivery zone floods, *and* when the local market shuts, *and* when the Blinkit app shows zero orders because an AQI alert dropped demand in their pin-code.

Their disruption surface is **hyper-local, multi-layered, and faster-moving** than any other delivery segment.

| Factor | Food Delivery | Q-Commerce (Zepto/Blinkit) |
|---|---|---|
| Delivery radius | 5–8 km | 1.5–3 km (dark store radius) |
| Disruption granularity | City-level rain | Single-street flooding matters |
| Income trigger speed | Slows over hours | Drops to ₹0 within minutes |
| Platform dependency | Multiple restaurants | Single dark store = single point of failure |
| Weekly earnings | ₹4,000–₹7,000 | ₹3,500–₹6,000 |

This hyper-locality is exactly what makes parametric insurance *more powerful* here than anywhere else - because the triggers are **measurable, verifiable, and granular enough** to be fair.

---

## 2. The DropSafe Difference - Three Core Innovations

### 🟡 Innovation 1: WhatsApp-First Worker Experience

Every competitor in this space builds an app. DropSafe builds a conversation.

A Zepto partner earning ₹500/day is not going to download, register, and learn a new insurance app. But they will reply to a WhatsApp message that says:

> *"Hi Ravi 👋 Heavy rain alert in your zone (Koramangala, Bengaluru). Your DropSafe coverage is active. If deliveries stop, your payout triggers automatically. Stay safe. 🌧️"*

**Worker journey via WhatsApp:**
```
1. Onboarding:    Partner receives WhatsApp link from Zepto/Blinkit →
                  Replies with name, zone, UPI ID → Policy activated

2. Weekly Opt-in: Every Monday 7 AM → Bot sends: "Activate this week's
                  coverage? Reply YES (₹52) or SKIP"

3. Disruption:    Bot proactively notifies when a trigger fires →
                  No action needed from worker

4. Payout:        "✅ ₹240 sent to your UPI for 3 disrupted hours today."

5. Dashboard:     Worker replies "STATUS" → Bot sends weekly summary
```

No app. No login. No claim form. Zero friction.

---

### 🟠 Innovation 2: Dark Store Zone Intelligence (DSZI)

Traditional parametric insurance uses city-level or district-level weather data. That's useless for a Blinkit partner whose dark store serves a 2 km radius.

DropSafe maps **every active Zepto/Blinkit dark store in India's Tier 1 cities** and creates a **Zone Risk Profile** for each one - a living dataset that combines:

- Historical rainfall/flood incidents within 2 km of the store
- Historical AQI spikes for the store's pin-code
- Road connectivity score (how many routes exist out of the zone)
- Local civil incident frequency (curfews, bandhs, protests)
- Seasonal disruption calendar (e.g., Ganesh Chaturthi processions blocking specific corridors in Pune)

This means a Blinkit partner at HSR Layout, Bengaluru gets a *different* premium than a partner at Koramangala - even though they're 4 km apart - because HSR has better drainage infrastructure and fewer flood incidents.

**That's not generic insurance. That's precision coverage.**

---

### 🔴 Innovation 3: Order Volume Collapse as a Parametric Trigger

Every other solution only monitors weather APIs. DropSafe introduces a **novel trigger**: real-time platform order volume drop.

The logic: if Blinkit/Zepto shows a >75% drop in order assignments in a given dark store zone over 45 minutes, *something* has disrupted work - regardless of whether a weather API has caught it yet. A sudden local power cut, a building collapse nearby, a flash protest - these don't show up in OpenWeatherMap.

**Order Volume Collapse Trigger:**
```
IF (zone_orders_last_45min) < (zone_avg_orders_same_timeslot × 0.25)
AND (at least 3 workers in zone are online but unassigned)
THEN flag as "Anomalous Disruption Event" → cross-validate with weather/AQI APIs
  → If validated: trigger payout
  → If not validated: flag for fraud review (could be coordinated fraud)
```

This trigger is **both a coverage tool and a fraud detector** - coordinated fake claims would also spike this metric, making it self-correcting.

---

## 3. Persona Scenarios & Application Workflow

### Scenario A - The 11 AM Flood, Bengaluru

**Ravi**, Blinkit partner, HSR Layout. Tuesday, 11:15 AM.

Rainfall hits 58mm/hr. IMD issues a red alert. The road outside his dark store is waterlogged. Blinkit order assignments in his zone drop 82% in 40 minutes.

DropSafe's DSZI detects:
- Rainfall trigger threshold crossed ✅
- Order Volume Collapse trigger crossed ✅ (double confirmation)
- Ravi has an active policy this week ✅
- Ravi's GPS (from platform mock) is within his declared zone ✅

**Result:** Fraud score = 0.04 (very low). Auto-approved. ₹310 sent to UPI in under 8 minutes. Ravi gets a WhatsApp message. He didn't file anything.

---

### Scenario B - The Delhi AQI Emergency

**Fatima**, Zepto partner, Dwarka, Delhi NCR. November, 7 AM.

AQI crosses 450. GRAP Stage IV declared by CPCB. Government issues advisory against outdoor work. Zepto order volume in Fatima's zone drops 91%.

DropSafe detects AQI trigger + government advisory flag + order collapse. Triple confirmation.

**Result:** Full shift coverage activated for the advisory window (9 AM–6 PM). ₹720 disbursed in tranches (₹80/hr) as the advisory remains active. Fatima receives hourly WhatsApp updates: *"Advisory still active. ₹80 added to your payout. Total so far: ₹240 ✅"*

---

### Scenario C - The Suspicious Claim (Fraud Caught)

**Cluster of 14 workers** in Andheri West, Mumbai, all "offline" on the same Tuesday afternoon. No weather event. No AQI advisory. No curfew.

DropSafe's Order Volume Collapse trigger does NOT fire - because Andheri West has normal order volume. The 14 workers are simply not logging in.

**Result:** System flags the cluster. Fraud Detection Engine scores all 14 claims at 0.87+ (high fraud probability). Claims rejected. Insurer notified. Pattern logged for future detection.

---

### Full Application Workflow

```
╔══════════════════════════════════════════════════════════════════╗
║                    WORKER JOURNEY (WhatsApp)                     ║
╠══════════════════════════════════════════════════════════════════╣
║  [Monday 7AM]  Weekly opt-in message sent via WhatsApp Bot       ║
║       ↓                                                          ║
║  Worker replies YES → Premium deducted → Policy active           ║
║       ↓                                                          ║
║  [During Week] Trigger Monitor runs every 15 minutes per zone    ║
║       ↓                                                          ║
║  Disruption detected → Multi-source validation                   ║
║  (Weather API + AQI API + Order Volume API + GPS check)          ║
║       ↓                                                          ║
║  Fraud Engine scores the event cluster                           ║
║       ↓                              ↓                           ║
║  Score < 0.3 → Auto-approve    Score > 0.3 → Human review        ║
║       ↓                                                          ║
║  Payout via UPI (Razorpay mock) → WhatsApp confirmation          ║
╠══════════════════════════════════════════════════════════════════╣
║                   INSURER JOURNEY (Web Dashboard)                ║
╠══════════════════════════════════════════════════════════════════╣
║  Zone Risk Heatmap → Active Policies → Live Trigger Feed         ║
║  Loss Ratio by Zone → Fraud Alerts → 7-Day Exposure Forecast     ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 4. Weekly Premium Model & Parametric Triggers

### The Weekly Model - Built for Gig Reality

Q-Commerce workers earn and spend weekly. A daily premium feels like a tax. A monthly premium is unaffordable upfront. Weekly is the natural unit.

**DropSafe's weekly opt-in model:**
- Sent every Monday morning via WhatsApp
- Worker can SKIP any week - no penalties, no lock-in
- Premium auto-scales if the worker changes their declared hours
- Fully transparent: bot explains exactly why this week's premium is what it is

### Premium Formula

```
Weekly Premium (₹) = BasePremium
                     × ZoneRiskMultiplier     [0.75 – 1.60]
                     × HoursCoverageRatio     [declared_hrs / 40]
                     × MLDynamicAdjustment    [± 25%]
                     × SeasonalIndex          [1.0 – 1.35]

BasePremium = ₹38 (city-tier baseline, Tier 1 cities)

ZoneRiskMultiplier:
  Derived from DSZI - low-risk zone (good drainage, low incidents) → 0.75
  High-risk zone (flood-prone, AQI hotspot, curfew-heavy)          → 1.60

MLDynamicAdjustment:
  Based on 7-day weather forecast risk + next-week AQI prediction
  Applied as ±25% modifier - lower premium in calm weeks,
  higher in monsoon peak (transparent and explained to worker)

SeasonalIndex:
  June–September (monsoon)          → 1.25–1.35
  October–November (Delhi AQI)      → 1.20–1.30
  Rest of year                      → 1.00
```

### Sample Weekly Premiums

| Worker | City / Zone | Zone Risk | Hours | Season | Est. Premium | Max Payout |
|---|---|---|---|---|---|---|
| Ravi | Bengaluru - HSR Layout | 0.90 | 40 hrs | Monsoon | ₹48 | ₹1,400 |
| Fatima | Delhi - Dwarka | 1.55 | 40 hrs | AQI Season | ₹72 | ₹1,400 |
| Arjun | Mumbai - Andheri | 1.40 | 48 hrs | Monsoon | ₹80 | ₹1,680 |
| Priya | Hyderabad - Gachibowli | 1.05 | 30 hrs | Summer | ₹42 | ₹1,050 |
| Karan | Pune - Kothrud | 0.95 | 35 hrs | Off-Season | ₹36 | ₹1,225 |

### The 6 Parametric Triggers

| # | Trigger | Threshold | Data Source | Validation Required | Payout Rate |
|---|---|---|---|---|---|
| 1 | **Heavy Rainfall** | >50mm/hr in zone pin-code | OpenWeatherMap API | Cross-check order volume | ₹/disrupted hr |
| 2 | **Extreme Heat** | Temp >43°C sustained >90 min | OpenWeatherMap API | Time-of-day + shift check | ₹/disrupted hr |
| 3 | **Severe AQI** | AQI >400 + govt advisory | CPCB / IQAir API | Advisory document flag | ₹/advisory hr |
| 4 | **Zone Curfew / Civil Disruption** | Official order + order drop >80% | Govt alerts API + Platform mock | Dual-source required | Full hourly replacement |
| 5 | **Order Volume Collapse** *(novel)* | Zone orders <25% of avg for 45 min + 3+ workers unassigned | Platform mock API | Must co-occur with env. trigger | ₹/disrupted hr |
| 6 | **Dark Store Emergency Closure** | Store offline >2 hrs (platform-reported) | Platform mock API | GPS proximity of worker | ₹/closure hr |

> **Payout Cap:** 80% of worker's declared average hourly income - prevents over-insurance and moral hazard.
> **Minimum Disruption Duration:** 1 hour - prevents micro-claims for brief delays.

---

## 5. AI/ML Architecture

### Model 1 - DSZI Risk Scorer (Zone Risk Profiling)

**Purpose:** Generate the `ZoneRiskMultiplier` for every active dark store zone.

**Approach:** Unsupervised clustering + supervised regression
- **Input features:** 3-year historical rainfall events, AQI breach history, road network density (OSM data), civil incident reports, drainage quality index, population density
- **Output:** Zone Risk Score [0.75–1.60] per pin-code, updated monthly
- **Phase 1:** Pre-trained on synthetic + public data for 5 cities, 20 dark store zones

---

### Model 2 - Dynamic Premium Adjuster

**Purpose:** Apply `MLDynamicAdjustment` each Monday before opt-in messages go out.

**Approach:** Gradient Boosted Regressor (XGBoost)
- **Input features:** 7-day weather forecast, AQI forecast, seasonal index, zone claim history (last 8 weeks), city event calendar
- **Output:** Adjustment factor [-0.25 to +0.25] on base premium
- **Transparency commitment:** Bot tells workers exactly why their premium changed week-on-week

---

### Model 3 - Fraud Detection Engine (Multi-Signal Scoring)

**Purpose:** Assign a fraud probability score [0–1] to every triggered claim event.

**Two-layer architecture:**

**Layer 1 - Rule Engine (fast, deterministic):**
```
RULE 1: Worker GPS outside declared zone at trigger time        → +0.40
RULE 2: Claim window outside declared shift hours              → +0.35
RULE 3: Duplicate claim for same trigger_event_id             → +1.00 (hard reject)
RULE 4: Order Volume Collapse NOT firing in same zone/time     → +0.30
RULE 5: Worker has 0 platform GPS pings that day              → +0.25
```

**Layer 2 - Isolation Forest (Phase 3):**
- Detects coordinated fraud rings across multiple workers
- Flags unusual claim frequency at zone level

**Decision gate:** Score < 0.30 → auto-approve | 0.30–0.60 → review queue | >0.60 → auto-reject

---

### Model 4 - 7-Day Exposure Forecaster (Insurer Dashboard)

**Purpose:** Give insurers a forward view of likely claim exposure by zone.

```
Expected_Claim_Exposure(zone) = P(trigger)
                                × active_policies_in_zone
                                × avg_payout_per_event

P(trigger) = weighted combination of:
  7-day rainfall probability (OpenWeatherMap forecast)
  AQI trend projection (CPCB 5-day)
  Civil event calendar lookup
  Historical same-week-of-year disruption rate
```

Dashboard output: *"Zone: Koramangala, Bengaluru - 68% disruption probability - Est. exposure: ₹38,400"*

---

## 6. Tech Stack & System Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKER INTERFACE                             │
│         WhatsApp Business API (Twilio / Meta Cloud API)         │
│         Chatbot: Python FastAPI webhook + state in Redis        │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    WEB FRONTEND                                 │
│   React 18 + TypeScript + Vite                                 │
│   Tailwind CSS + shadcn/ui                                     │
│   Recharts (analytics) + Leaflet.js (zone heatmaps)            │
│   PWA-enabled (Workbox)                                        │
└──────────────────────────┬──────────────────────────────────────┘
                           │ REST + WebSocket
┌──────────────────────────▼──────────────────────────────────────┐
│                    BACKEND CORE                                 │
│   Python FastAPI (async)                                       │
│   APScheduler - trigger monitor runs every 15 min per zone     │
│   JWT Auth + OAuth2 (worker: phone OTP, insurer: login)        │
└──────────┬───────────────┬───────────────┬──────────────────────┘
           │               │               │
┌──────────▼───┐  ┌────────▼──────┐  ┌────▼──────────────────────┐
│   Supabase   │  │     Redis     │  │      ML Service           │
│  (PostgreSQL │  │  session +    │  │  FastAPI microservice     │
│   + Auth +   │  │  trigger      │  │  XGBoost + scikit-learn   │
│   Realtime)  │  │  state +      │  │  DSZI scorer              │
│  workers     │  │  WhatsApp     │  │  Premium adjuster         │
│  policies    │  │  conv state   │  │  Fraud detector           │
│  claims      │  └───────────────┘  │  Exposure forecaster      │
│  payouts     │                     └───────────────────────────┘
│  zones       │
└──────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                 EXTERNAL INTEGRATIONS                           │
│  OpenWeatherMap API    - weather triggers + 7-day forecast     │
│  CPCB / IQAir API      - AQI triggers + advisories            │
│  Platform Mock API     - order volume, GPS, store status       │
│  Govt Alerts Mock API  - curfew / civil disruption events      │
│  Razorpay Test Mode    - UPI payout simulation                 │
│  Twilio / Meta Cloud   - WhatsApp Business API                 │
└─────────────────────────────────────────────────────────────────┘
```

### Core Database Schema (Supabase / PostgreSQL)

> **Why Supabase?** Supabase gives us a hosted PostgreSQL database, built-in Auth (phone OTP for workers), Realtime subscriptions (live trigger feed on the insurer dashboard), and auto-generated REST APIs - cutting backend boilerplate significantly and accelerating development across all three phases.

```sql
-- Zone intelligence (the heart of DSZI)
zones (
  id, pincode, dark_store_name, platform,
  risk_multiplier       DECIMAL,   -- computed by DSZI Model
  flood_incident_count  INT,
  aqi_breach_count      INT,
  road_connectivity_score DECIMAL,
  last_updated          TIMESTAMP
)

-- Workers
workers (
  id, phone_hash         VARCHAR UNIQUE,  -- hashed for privacy
  name, zone_id          FK,
  platform               ENUM(zepto, blinkit),
  declared_weekly_hours  INT,
  avg_hourly_income      DECIMAL,
  ml_risk_score          DECIMAL,
  upi_id_encrypted       VARCHAR,
  whatsapp_state         JSONB            -- chatbot conversation state
)

-- Policies (weekly)
policies (
  id, worker_id FK, zone_id FK,
  week_start DATE, week_end DATE,
  premium_paid DECIMAL, coverage_cap DECIMAL,
  status ENUM(active, expired, cancelled)
)

-- Trigger events (zone-level, not per-worker)
trigger_events (
  id, zone_id FK,
  trigger_type  ENUM(rain, heat, aqi, curfew, order_collapse, store_closure),
  severity      DECIMAL,
  start_time    TIMESTAMP, end_time TIMESTAMP,
  data_sources  JSONB,     -- full audit trail of API sources used
  verified      BOOLEAN
)

-- Claims (auto-generated - never manually filed)
claims (
  id, policy_id FK, trigger_event_id FK,
  disrupted_hours  DECIMAL,
  payout_amount    DECIMAL,
  fraud_score      DECIMAL,
  fraud_flags      JSONB,
  status           ENUM(auto_approved, review, rejected, paid)
)

-- Payouts
payouts (
  id, claim_id FK, worker_id FK,
  amount DECIMAL, channel VARCHAR,
  razorpay_ref VARCHAR,
  status ENUM(initiated, success, failed),
  paid_at TIMESTAMP
)
```

---

## 7. Development Roadmap

### Phase 1 - Seed (Weeks 1–2, by March 20) ← *Current*
```
✅ Problem analysis + persona research
✅ DSZI concept + zone risk model architecture
✅ 6 parametric triggers defined (incl. novel Order Volume Collapse)
✅ WhatsApp-first UX flow designed
[ ] GitHub repo setup + project scaffold (FastAPI + React)
[ ] OpenWeatherMap + IQAir API connection (mock data layer)
[ ] DSZI baseline model - synthetic data for 5 cities, 20 zones
[ ] WhatsApp bot skeleton (Twilio sandbox) - onboarding flow only
[ ] Supabase project setup - schema creation + seed data
[ ] 2-minute strategy video
```

### Phase 2 - Scale (Weeks 3–4, by April 4)
```
[ ] Full worker onboarding via WhatsApp (OTP → zone → UPI → policy)
[ ] Weekly Monday 7 AM opt-in broadcast
[ ] Dynamic premium calculation (all 4 model components live)
[ ] All 6 triggers wired to real + mock APIs
[ ] Auto-claim generation engine (zero manual filing)
[ ] Layer 1 Fraud Detection (rule engine)
[ ] Razorpay test mode payout + WhatsApp confirmation
[ ] Insurer web dashboard v1 (active policies, live trigger feed)
```

### Phase 3 - Soar (Weeks 5–6, by April 17)
```
[ ] Layer 2 Fraud Detection (Isolation Forest)
[ ] 7-Day Exposure Forecaster on insurer dashboard
[ ] Zone heatmap (Leaflet.js) - risk by dark store, visualized
[ ] Worker WhatsApp "STATUS" command → weekly summary card
[ ] End-to-end disruption simulation (rainstorm → trigger → payout demo)
[ ] Final pitch deck (PDF)
[ ] 5-minute demo video
```

---

## Why DropSafe Wins

| What Everyone Builds | What DropSafe Builds |
|---|---|
| An app workers won't download | A WhatsApp conversation they already have open |
| City-level weather triggers | Pin-code level Dark Store Zone Intelligence |
| Weather API only | Weather + AQI + Order Volume + Store Status |
| Worker files a claim | Worker receives a payout |
| Generic fraud rules | Self-correcting Order Volume Collapse trigger |
| Static weekly premium | Dynamic premium that adjusts for next week's forecast |

> *DropSafe doesn't just insure gig workers. It disappears into the tools they already use - and shows up only when it matters most.*

---

## Team

| Name | Role |
|---|---|
| Karthik Cherukuru | Full Stack Lead |
| DNV Likhitha Chittineedi | ML / AI Engineer |
| Batchu Surya Teja | Backend / API Engineer |
| Ashika Jain | Frontend / UX |
| Collins K Wilson | Product & QA |

---

## 🔗 Links

| Resource | Link |
|---|---|
| GitHub Repository | *https://github.com/suryatejabatchu08/DropSafe* |
| Phase 1 Demo Video | *(Link)* |
| Live Demo | *[Phase 2]* |
| Insurer Dashboard | *[Phase 2]* |

---

<div align="center">

**DropSafe** - Built for Guidewire DEVTrails 2026

*Seed. Scale. Soar.*

*When the storm stops deliveries, we start paying.*

</div>
