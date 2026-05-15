"""
ChargeNexus — Chat Monetization Engine
=======================================

Two tiers:
  Tier 1 (NLP)  — free, rule-based, instant, zero LLM cost
  Tier 2 (LLM)  — paid credits, full Claude reasoning

Credit system:
  - 1 credit = smallest unit of LLM query value
  - Role-specific credit cost per LLM query
  - Subscription plans grant monthly credit bundles
  - Credits purchased à-la-carte via Razorpay
"""

from datetime import datetime, timedelta

# ── Plan definitions ──────────────────────────────────────────────────────────

PLANS = {
    "free": {
        "name": "Free",
        "price_inr": 0,
        "credits_per_month": 0,         # no subscription credits
        "llm_credits_on_signup": 10,    # one-time welcome credits
        "nlp_daily_limit": {            # free NLP queries per day per role
            "landowner": -1,            # -1 = unlimited
            "oem_sell":  -1,
            "oem_setup": -1,
            "operator":  -1,
            "driver":    20,            # drivers get 20 free NLP/day
        },
        "features": ["NLP chat (free)", "Basic data queries", "Station finder"],
    },
    "pro": {
        "name": "Pro",
        "price_inr_per_month": {
            "landowner": 299,
            "oem_sell":  499,
            "oem_setup": 499,
            "operator":  799,
            "driver":    149,
        },
        "credits_per_month": {
            "landowner": 500,
            "oem_sell":  800,
            "oem_setup": 800,
            "operator":  1200,
            "driver":    200,
        },
        "nlp_daily_limit": {k: -1 for k in ["landowner","oem_sell","oem_setup","operator","driver"]},
        "features": ["Everything in Free", "LLM AI assistant", "Monthly credit grant", "Priority support"],
    },
    "business": {
        "name": "Business",
        "price_inr_per_month": {
            "landowner": 999,
            "oem_sell":  1499,
            "oem_setup": 1499,
            "operator":  2499,
            "driver":    499,
        },
        "credits_per_month": {
            "landowner": 2000,
            "oem_sell":  3500,
            "oem_setup": 3500,
            "operator":  5000,
            "driver":    1000,
        },
        "nlp_daily_limit": {k: -1 for k in ["landowner","oem_sell","oem_setup","operator","driver"]},
        "features": ["Everything in Pro", "5× credit grants", "API access", "Dedicated account manager", "Custom agents"],
    },
}

# ── Credit packs (à-la-carte) ─────────────────────────────────────────────────

CREDIT_PACKS = [
    {"id": "pack_50",   "credits": 50,   "price_inr": 99,   "label": "Starter",  "bonus_pct": 0},
    {"id": "pack_150",  "credits": 150,  "price_inr": 249,  "label": "Basic",    "bonus_pct": 0},
    {"id": "pack_350",  "credits": 350,  "price_inr": 499,  "label": "Value",    "bonus_pct": 17},   # 50 bonus
    {"id": "pack_800",  "credits": 800,  "price_inr": 999,  "label": "Growth",   "bonus_pct": 23},   # 150 bonus
    {"id": "pack_2000", "credits": 2000, "price_inr": 1999, "label": "Scale",    "bonus_pct": 33},   # 500 bonus
]

# ── LLM credit cost per query by role ─────────────────────────────────────────
# Higher for roles with more valuable/complex queries

LLM_CREDIT_COST = {
    "landowner": 5,    # Land valuation, operator matching
    "oem_sell":  8,    # Market pricing, customer identification
    "oem_setup": 8,    # Site scoring, ROI projections
    "operator":  10,   # Portfolio analysis, dynamic pricing
    "driver":    3,    # Station finding, route planning (simpler)
}

# NLP queries are free — cost 0 credits
NLP_CREDIT_COST = 0

# ── Welcome credits on signup ─────────────────────────────────────────────────
SIGNUP_CREDITS = {
    "landowner": 10,
    "oem_sell":  10,
    "oem_setup": 10,
    "operator":  10,
    "driver":    5,
}

# ── Business logic helpers ────────────────────────────────────────────────────

def get_plan_price(plan: str, role: str) -> int:
    """Return monthly price in INR for a plan+role combination."""
    p = PLANS.get(plan, {})
    prices = p.get("price_inr_per_month", {})
    return prices.get(role, 0)


def get_monthly_credits(plan: str, role: str) -> int:
    """Return credits granted monthly by the plan."""
    p = PLANS.get(plan, {})
    credits = p.get("credits_per_month", {})
    return credits.get(role, 0)


def get_nlp_daily_limit(plan: str, role: str) -> int:
    """Return daily NLP query limit. -1 = unlimited."""
    p = PLANS.get(plan, {})
    limits = p.get("nlp_daily_limit", {})
    return limits.get(role, 20)


def get_credit_cost(role: str, tier: str) -> int:
    """Return credit cost for a query. tier = 'nlp' | 'llm'"""
    if tier == "nlp":
        return NLP_CREDIT_COST
    return LLM_CREDIT_COST.get(role, 5)


def can_use_nlp(user_id: int, role: str, plan: str) -> tuple[bool, str]:
    """
    Check if user can make a free NLP query.
    Returns (allowed: bool, reason: str).
    """
    limit = get_nlp_daily_limit(plan, role)
    if limit == -1:
        return True, "unlimited"

    from database import NlpUsage
    today = datetime.utcnow().strftime("%Y-%m-%d")
    usage = NlpUsage.query.filter_by(user_id=user_id, date=today).first()
    count = usage.count if usage else 0

    if count >= limit:
        return False, f"Daily NLP limit ({limit}/day) reached. Upgrade to Pro for unlimited NLP."
    return True, "ok"


def can_use_llm(user_id: int, role: str) -> tuple[bool, str, int]:
    """
    Check if user has enough credits for an LLM query.
    Returns (allowed: bool, reason: str, cost: int).
    """
    from database import CreditWallet
    cost = LLM_CREDIT_COST.get(role, 5)
    wallet = CreditWallet.query.filter_by(user_id=user_id).first()
    balance = wallet.balance if wallet else 0

    if balance < cost:
        return False, f"Insufficient credits ({balance} available, {cost} required). Purchase credits to continue.", cost
    return True, "ok", cost


def debit_credits(user_id: int, role: str, session_id: str, tier: str) -> int:
    """
    Deduct credits for a query. Returns new balance.
    Call only after a successful agent response.
    """
    from database import db, CreditWallet, CreditTransaction

    cost = get_credit_cost(role, tier)
    if cost == 0:
        return -1   # NLP is free, no debit

    wallet = CreditWallet.query.filter_by(user_id=user_id).with_for_update().first()
    if not wallet or wallet.balance < cost:
        return 0

    wallet.balance -= cost
    wallet.lifetime_spent += cost

    db.session.add(CreditTransaction(
        user_id=user_id,
        amount=-cost,
        txn_type="llm_query",
        description=f"LLM query — {role} agent",
        reference_id=session_id,
        balance_after=wallet.balance,
    ))
    db.session.commit()
    return wallet.balance


def credit_credits(user_id: int, amount: int, txn_type: str,
                   description: str, reference_id: str = None) -> int:
    """
    Add credits to a user's wallet. Returns new balance.
    Used for: purchases, subscription grants, promos, refunds.
    """
    from database import db, CreditWallet, CreditTransaction

    wallet = CreditWallet.query.filter_by(user_id=user_id).with_for_update().first()
    if not wallet:
        wallet = CreditWallet(user_id=user_id, balance=0, lifetime_earned=0, lifetime_spent=0)
        db.session.add(wallet)
        db.session.flush()

    wallet.balance += amount
    wallet.lifetime_earned += amount

    db.session.add(CreditTransaction(
        user_id=user_id,
        amount=amount,
        txn_type=txn_type,
        description=description,
        reference_id=reference_id,
        balance_after=wallet.balance,
    ))
    db.session.commit()
    return wallet.balance


def increment_nlp_usage(user_id: int):
    """Record a free NLP query use."""
    from database import db, NlpUsage
    today = datetime.utcnow().strftime("%Y-%m-%d")
    usage = NlpUsage.query.filter_by(user_id=user_id, date=today).first()
    if usage:
        usage.count += 1
    else:
        db.session.add(NlpUsage(user_id=user_id, date=today, count=1))
    db.session.commit()


def activate_subscription(user_id: int, role: str, plan: str,
                           razorpay_order_id: str, razorpay_payment_id: str) -> dict:
    """
    Activate a Pro or Business subscription for a user.
    Credits monthly grant, updates User.plan, creates Subscription record.
    """
    from database import db, User, Subscription

    user = User.query.get(user_id)
    if not user:
        raise ValueError("User not found")

    price_inr     = get_plan_price(plan, role)
    credits_grant = get_monthly_credits(plan, role)
    expires_at    = datetime.utcnow() + timedelta(days=30)

    # Update user plan
    user.plan = plan
    user.plan_expires_at = expires_at

    # Create subscription record
    sub = Subscription(
        user_id=user_id,
        plan=plan,
        expires_at=expires_at,
        credits_granted=credits_grant,
        price_inr=price_inr,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        status="active",
    )
    db.session.add(sub)
    db.session.commit()

    # Grant credits
    new_balance = credit_credits(
        user_id=user_id,
        amount=credits_grant,
        txn_type="subscription_grant",
        description=f"{plan.title()} plan activated — {credits_grant} credits granted",
        reference_id=razorpay_order_id,
    )

    return {
        "plan": plan,
        "credits_granted": credits_grant,
        "new_balance": new_balance,
        "expires_at": expires_at.isoformat(),
    }
