"""
Agent routes — dual-tier chat:
  Tier 1 (NLP)  /api/agent/nlp-chat  — free, rule-based, instant
  Tier 2 (LLM)  /api/agent/chat      — paid credits, full LangGraph
"""

import uuid
import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import db, User, AgentChatMessage, AgentUsage, CreditWallet
from agents import run_agent, AGENT_CONFIGS
from nlp_engine import handle_nlp
from credits import (
    can_use_nlp, can_use_llm, debit_credits,
    increment_nlp_usage, MONTHLY_CALL_LIMIT, MONTHLY_COST_LIMIT_USD,
    LLM_CREDIT_COST, SIGNUP_CREDITS, credit_credits,
)

agent_bp = Blueprint("agent", __name__)

ROLE_TO_AGENT = {
    "landowner": "landowner",
    "oem_sell":  "oem_sell",
    "oem_setup": "oem_setup",
    "operator":  "operator",
    "driver":    "driver",
}


def _get_user(user_id):
    return User.query.get(user_id)


def _ensure_welcome_credits(user_id: int, role: str):
    """Grant welcome credits on first use if wallet is empty."""
    wallet = CreditWallet.query.filter_by(user_id=user_id).first()
    if not wallet or (wallet.lifetime_earned == 0):
        welcome = SIGNUP_CREDITS.get(role, 10)
        credit_credits(user_id, welcome, "promo",
                       f"Welcome bonus — {welcome} free AI credits", "signup")


# ═══════════════════════════════════════════════════════════════════
# TIER 1 — FREE NLP CHAT
# ═══════════════════════════════════════════════════════════════════

@agent_bp.route("/nlp-chat", methods=["POST"])
@jwt_required()
def nlp_chat():
    """
    Free NLP tier. Rule-based intent matching, zero LLM cost.
    If no intent matched, returns matched=False so frontend can
    prompt user to use LLM tier.
    """
    user_id = int(get_jwt_identity())
    user    = _get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data       = request.get_json() or {}
    message    = (data.get("message") or "").strip()
    session_id = data.get("session_id", str(uuid.uuid4()))

    if not message:
        return jsonify({"error": "message required"}), 422

    agent_type = ROLE_TO_AGENT.get(user.role)
    plan       = user.plan or "free"

    # Check NLP daily limit
    allowed, reason = can_use_nlp(user_id, user.role, plan)
    if not allowed:
        return jsonify({
            "matched": False,
            "tier": "nlp",
            "response": f"⚠️ {reason}",
            "upgrade_required": True,
        })

    # Run NLP engine
    result = handle_nlp(user.role, message, user_id)

    if result["matched"]:
        increment_nlp_usage(user_id)

        # Persist
        db.session.add(AgentChatMessage(
            user_id=user_id, session_id=session_id,
            role="user", content=message, agent_type=agent_type, model_used="nlp"
        ))
        db.session.add(AgentChatMessage(
            user_id=user_id, session_id=session_id,
            role="assistant", content=result["response"],
            agent_type=agent_type, model_used="nlp",
            tool_calls="[]", input_tokens=0, output_tokens=0
        ))
        db.session.commit()

    return jsonify({
        "matched":   result["matched"],
        "intent":    result["intent"],
        "response":  result["response"],
        "data":      result.get("data"),
        "tier":      "nlp",
        "session_id": session_id,
        "agent_name": AGENT_CONFIGS.get(agent_type, {}).get("name", "AI"),
    })


# ═══════════════════════════════════════════════════════════════════
# TIER 2 — PAID LLM CHAT
# ═══════════════════════════════════════════════════════════════════

@agent_bp.route("/chat", methods=["POST"])
@jwt_required()
def chat():
    """
    Paid LLM tier. Deducts credits on success.
    Checks credit balance before running agent.
    """
    user_id = int(get_jwt_identity())
    user    = _get_user(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    data       = request.get_json() or {}
    messages   = data.get("messages", [])
    session_id = data.get("session_id", str(uuid.uuid4()))

    agent_type = ROLE_TO_AGENT.get(user.role)
    if not agent_type:
        return jsonify({"error": "No agent configured for this role"}), 400

    # Grant welcome credits on first LLM use
    _ensure_welcome_credits(user_id, user.role)

    # Check credit balance
    allowed, reason, cost = can_use_llm(user_id, user.role)
    if not allowed:
        return jsonify({
            "error": reason,
            "insufficient_credits": True,
            "credits_required": cost,
            "credits_available": (CreditWallet.query
                                  .filter_by(user_id=user_id).first() or
                                  type("W", (), {"balance": 0})()).balance,
        }), 402   # 402 Payment Required

    # Run LangGraph agent
    result = run_agent(agent_type=agent_type, messages=messages, user_id=user_id)

    if result.get("success"):
        # Debit credits
        new_balance = debit_credits(user_id, user.role, session_id, "llm")

        # Persist
        model  = result.get("model", "unknown")
        tokens = result.get("tokens", {})
        if messages:
            db.session.add(AgentChatMessage(
                user_id=user_id, session_id=session_id, role="user",
                content=messages[-1].get("content", ""), agent_type=agent_type,
                model_used=model,
            ))
        db.session.add(AgentChatMessage(
            user_id=user_id, session_id=session_id, role="assistant",
            content=result["response"], agent_type=agent_type,
            tool_calls=json.dumps(result.get("tool_calls", [])),
            model_used=model,
            input_tokens=tokens.get("input", 0),
            output_tokens=tokens.get("output", 0),
            cache_hit=result.get("cache_hit", False),
        ))
        db.session.commit()

        return jsonify({
            "response":        result["response"],
            "tool_calls":      result.get("tool_calls", []),
            "session_id":      session_id,
            "agent_name":      AGENT_CONFIGS.get(agent_type, {}).get("name", "AI Agent"),
            "tier":            "llm",
            "model":           model,
            "tokens":          tokens,
            "credits_charged": cost,
            "credits_remaining": new_balance,
        })
    else:
        return jsonify({
            "error":      result.get("response", "Agent error"),
            "tool_calls": [],
            "tier":       "llm",
        }), 500


# ── Supporting endpoints ──────────────────────────────────────────────────────

@agent_bp.route("/usage", methods=["GET"])
@jwt_required()
def usage():
    user_id = int(get_jwt_identity())
    user    = User.query.get(user_id)
    month   = datetime.utcnow().strftime("%Y-%m")
    record  = AgentUsage.query.filter_by(user_id=user_id, month=month).first()
    wallet  = CreditWallet.query.filter_by(user_id=user_id).first()
    today   = datetime.utcnow().strftime("%Y-%m-%d")
    from database import NlpUsage
    nlp_today = NlpUsage.query.filter_by(user_id=user_id, date=today).first()
    from credits import get_nlp_daily_limit
    nlp_limit = get_nlp_daily_limit(user.plan if user else "free", user.role if user else "driver")

    return jsonify({
        "usage": record.to_dict() if record else {
            "month": month, "total_calls": 0, "estimated_cost_usd": 0,
            "haiku_calls": 0, "sonnet_calls": 0, "cache_hits": 0,
        },
        "credits": wallet.to_dict() if wallet else {"balance": 0, "lifetime_earned": 0, "lifetime_spent": 0},
        "plan":    user.plan if user else "free",
        "nlp_used_today": nlp_today.count if nlp_today else 0,
        "nlp_daily_limit": nlp_limit if nlp_limit != -1 else None,
        "llm_cost_per_query": LLM_CREDIT_COST.get(user.role, 5) if user else 5,
        "limits": {"monthly_calls": MONTHLY_CALL_LIMIT, "monthly_budget_usd": MONTHLY_COST_LIMIT_USD},
    })


@agent_bp.route("/history", methods=["GET"])
@jwt_required()
def history():
    user_id    = int(get_jwt_identity())
    session_id = request.args.get("session_id")
    q = AgentChatMessage.query.filter_by(user_id=user_id).order_by(AgentChatMessage.created_at)
    if session_id:
        q = q.filter_by(session_id=session_id)
    msgs = q.limit(100).all()
    return jsonify([{
        "role":         m.role,
        "content":      m.content,
        "tool_calls":   json.loads(m.tool_calls) if m.tool_calls else [],
        "model":        m.model_used,
        "tier":         "nlp" if m.model_used == "nlp" else "llm",
        "input_tokens": m.input_tokens,
        "output_tokens":m.output_tokens,
        "created_at":   m.created_at.isoformat(),
    } for m in msgs])


@agent_bp.route("/agents", methods=["GET"])
def list_agents():
    return jsonify({k: {"name": v["name"]} for k, v in AGENT_CONFIGS.items()})
