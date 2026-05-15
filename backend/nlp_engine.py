"""
ChargeNexus NLP Chat Engine — Tier 1 (Free)
============================================
Rule-based intent detection + direct DB query + templated responses.
Zero LLM cost. Covers ~70% of real user queries.

Each intent handler returns a dict:
  { "response": str, "data": dict|None, "intent": str, "matched": bool }

If matched=False, the caller escalates to Tier 2 (LLM).
"""

import re
from datetime import datetime


# ── Intent keyword maps ────────────────────────────────────────────────────────

def _contains(text: str, *keywords) -> bool:
    t = text.lower()
    return any(kw in t for kw in keywords)

def _match_number(text: str) -> float | None:
    m = re.search(r'(\d+\.?\d*)', text)
    return float(m.group(1)) if m else None

def _match_city(text: str) -> str | None:
    cities = ["hyderabad", "warangal", "vijayawada", "bengaluru", "bangalore",
              "chennai", "pune", "mumbai", "delhi", "secunderabad"]
    t = text.lower()
    for c in cities:
        if c in t:
            return c.title().replace("Bangalore", "Bengaluru")
    return None


# ── Role-specific intent handlers ─────────────────────────────────────────────

class NlpEngine:
    """
    Stateless NLP engine. Instantiate once, call handle() per message.
    All DB access is lazy — only queries what's needed for the matched intent.
    """

    def handle(self, role: str, message: str, user_id: int) -> dict:
        """
        Route message to the correct role handler.
        Returns {"response", "data", "intent", "matched"}.
        """
        handlers = {
            "driver":    self._driver,
            "landowner": self._landowner,
            "operator":  self._operator,
            "oem_sell":  self._oem_sell,
            "oem_setup": self._oem_setup,
        }
        fn = handlers.get(role, self._generic)
        return fn(message, user_id)

    # ── DRIVER ────────────────────────────────────────────────────────────────

    def _driver(self, msg: str, user_id: int) -> dict:
        m = msg.lower()

        # Greet / help
        if _contains(m, "hello", "hi", "hey", "help", "what can"):
            return self._ok("driver_help", "👋 Hi! I'm your EV charging assistant. I can help you:\n\n• **Find nearby stations** — ask 'stations near me'\n• **Check wallet** — ask 'my balance'\n• **Charging cost** — ask 'cost to charge 40kWh at ₹42/kWh'\n• **Session history** — ask 'my recent sessions'\n• **Route planning** — for complex routes, upgrade to AI mode\n\nFor deeper analysis, switch to AI Chat (uses credits).")

        # Wallet balance
        if _contains(m, "wallet", "balance", "credits", "money", "points"):
            return self._driver_wallet(user_id)

        # Nearby stations
        if _contains(m, "station", "charger", "nearby", "near me", "find", "available"):
            city = _match_city(m)
            return self._driver_stations(city)

        # Cost calculation
        if _contains(m, "cost", "price", "how much", "calculate", "₹", "rupee"):
            kwh = _match_number(m)
            rate = 42.0  # default
            rate_match = re.search(r'₹\s*(\d+)', m) or re.search(r'(\d+)\s*(?:per\s*kwh|rupee)', m)
            if rate_match:
                rate = float(rate_match.group(1))
            if kwh:
                cost = kwh * rate
                time_min = int(kwh / 60 * 60)  # assume 60kW charger
                return self._ok("cost_calc", f"⚡ **Charging {kwh} kWh @ ₹{rate}/kWh**\n\n• Cost: **₹{cost:,.0f}**\n• Est. time (60kW charger): **{time_min} min**\n• Range added: ~{int(kwh*6.5)} km\n\nFor personalised route planning, use AI Chat.")
            else:
                return self._ok("cost_hint", "To calculate cost, tell me: 'cost to charge 40 kWh at ₹42/kWh'")

        # Session history
        if _contains(m, "session", "history", "recent", "last charge", "past"):
            return self._driver_sessions(user_id)

        # Connector types
        if _contains(m, "connector", "plug", "ccs", "chademo", "type 2", "compatible"):
            return self._ok("connector_info",
                "**Common EV connectors in India:**\n\n"
                "• **CCS2** — Tata Nexon, MG ZS, Kia EV6, Hyundai Ioniq 5\n"
                "• **CHAdeMO** — Nissan Leaf, Mitsubishi Outlander\n"
                "• **Type-2 AC** — AC slow/fast charging, nearly all EVs\n"
                "• **Bharat AC-001** — older Indian standard (less common)\n\n"
                "Check your car's spec sheet or the charging port shape. CCS2 is the dominant Indian standard for DC fast charging."
            )

        return self._no_match()

    def _driver_wallet(self, user_id: int) -> dict:
        from database import DriverWallet, CreditWallet
        dw = DriverWallet.query.filter_by(driver_id=user_id).first()
        cw = CreditWallet.query.filter_by(user_id=user_id).first()
        charging_bal = f"₹{dw.balance:,.0f}" if dw else "₹0"
        reward_pts   = dw.reward_points if dw else 0
        ai_credits   = cw.balance if cw else 0
        return self._ok("wallet_balance",
            f"**Your Wallet**\n\n"
            f"• Charging balance: **{charging_bal}**\n"
            f"• Reward points: **{reward_pts}** (≈ ₹{reward_pts})\n"
            f"• AI credits: **{ai_credits}** credits\n\n"
            f"Top up charging balance or buy AI credits in the Wallet tab.",
            {"charging_balance": charging_bal, "reward_points": reward_pts, "ai_credits": ai_credits}
        )

    def _driver_stations(self, city: str | None) -> dict:
        from database import ChargingStation
        q = ChargingStation.query.filter_by(status="active")
        if city:
            q = q.filter(ChargingStation.city.ilike(f"%{city}%"))
        stations = q.limit(5).all()
        if not stations:
            return self._ok("no_stations", f"No active stations found{f' in {city}' if city else ''}. Try searching in a different city.")

        lines = [f"**Charging stations{f' in {city}' if city else ''}:**\n"]
        for s in stations:
            avail_color = "🟢" if s.available_points > 0 else "🔴"
            lines.append(f"{avail_color} **{s.name}**")
            lines.append(f"   {s.available_points}/{s.total_points} bays · ₹{s.price_per_kwh}/kWh · {s.city}")
        lines.append("\nUse 'Find Stations' tab to see these on the map.")
        return self._ok("station_list", "\n".join(lines), {"stations": [s.to_dict() for s in stations]})

    def _driver_sessions(self, user_id: int) -> dict:
        from database import ChargingSession
        sessions = (ChargingSession.query
                    .filter_by(driver_id=user_id, status="completed")
                    .order_by(ChargingSession.start_time.desc())
                    .limit(5).all())
        if not sessions:
            return self._ok("no_sessions", "No charging sessions yet. Find a station and start charging!")
        total_kwh  = sum(s.energy_kwh or 0 for s in sessions)
        total_inr  = sum(s.amount_inr or 0 for s in sessions)
        lines = [f"**Your last {len(sessions)} sessions:**\n"]
        for s in sessions:
            date = s.start_time.strftime("%d %b") if s.start_time else "—"
            lines.append(f"• {date} · {s.station.name if s.station else '?'} · {s.energy_kwh or 0} kWh · ₹{s.amount_inr or 0:,.0f}")
        lines.append(f"\n**Total:** {total_kwh:.1f} kWh charged · ₹{total_inr:,.0f} spent")
        return self._ok("session_history", "\n".join(lines))

    # ── LAND OWNER ────────────────────────────────────────────────────────────

    def _landowner(self, msg: str, user_id: int) -> dict:
        m = msg.lower()

        if _contains(m, "hello", "hi", "hey", "help", "what can"):
            return self._ok("landowner_help",
                "👋 Hi! I'm your land management assistant. I can:\n\n"
                "• **Show my listings** — ask 'my listings'\n"
                "• **Pending requests** — ask 'lease requests'\n"
                "• **Market rates** — ask 'what's the rate for highway land in Hyderabad'\n"
                "• **Revenue** — ask 'my monthly revenue'\n\n"
                "For detailed valuation and operator matching, use AI Chat (uses credits)."
            )

        if _contains(m, "my listing", "my land", "my plot", "show listing"):
            return self._landowner_listings(user_id)

        if _contains(m, "lease request", "pending", "offer", "request"):
            return self._landowner_requests(user_id)

        if _contains(m, "revenue", "income", "earning", "how much"):
            return self._landowner_revenue(user_id)

        if _contains(m, "rate", "market rate", "how much lease", "what price"):
            city = _match_city(m)
            loc_type = "highway" if _contains(m, "highway", "nh", "road") else \
                       "mall" if _contains(m, "mall", "retail", "shop") else \
                       "office" if _contains(m, "office", "it", "tech") else None
            return self._landowner_market_rate(city, loc_type)

        return self._no_match()

    def _landowner_listings(self, user_id: int) -> dict:
        from database import LandListing
        listings = LandListing.query.filter_by(owner_id=user_id).limit(10).all()
        if not listings:
            return self._ok("no_listings", "No listings yet. Add your first location from the 'Add Location' tab.")
        lines = [f"**Your {len(listings)} listing(s):**\n"]
        for l in listings:
            status_icon = "🟢" if l.status == "active" else "🔵" if l.status == "leased" else "🟡"
            lines.append(f"{status_icon} **{l.title}** — {l.city}")
            lines.append(f"   {l.area_sqft:,} sqft · ₹{l.monthly_lease:,.0f}/mo · AI score: {l.ai_score or '—'}")
        return self._ok("listing_list", "\n".join(lines))

    def _landowner_requests(self, user_id: int) -> dict:
        from database import LandListing, LeaseRequest
        listing_ids = [l.id for l in LandListing.query.filter_by(owner_id=user_id).all()]
        requests = (LeaseRequest.query
                    .filter(LeaseRequest.listing_id.in_(listing_ids))
                    .order_by(LeaseRequest.created_at.desc()).limit(5).all())
        if not requests:
            return self._ok("no_requests", "No lease requests yet. Your listings are visible to operators.")
        pending = [r for r in requests if r.status == "pending"]
        lines = [f"**{len(requests)} lease request(s) · {len(pending)} pending:**\n"]
        for r in requests:
            icon = "⏳" if r.status == "pending" else "✅" if r.status == "accepted" else "❌"
            lines.append(f"{icon} **{r.listing_title}** — ₹{r.offered_monthly:,.0f}/mo · {r.status}")
        if pending:
            lines.append("\nGo to 'Lease Requests' tab to accept or reject pending offers.")
        return self._ok("request_list", "\n".join(lines))

    def _landowner_revenue(self, user_id: int) -> dict:
        from database import LandListing, LeaseRequest
        listings = LandListing.query.filter_by(owner_id=user_id, status="leased").all()
        total = sum(l.monthly_lease or 0 for l in listings)
        return self._ok("revenue",
            f"**Monthly Lease Revenue**\n\n"
            f"• Leased plots: **{len(listings)}**\n"
            f"• Total monthly: **₹{total:,.0f}**\n"
            f"• Annual projection: **₹{total*12:,.0f}**\n\n"
            f"For valuation and earnings optimization, use AI Chat."
        )

    def _landowner_market_rate(self, city: str | None, loc_type: str | None) -> dict:
        rates = {
            "highway":  {"min": 60000, "max": 150000, "avg": 95000},
            "mall":     {"min": 80000, "max": 200000, "avg": 120000},
            "office":   {"min": 50000, "max": 130000, "avg": 85000},
            "residential": {"min": 20000, "max": 60000, "avg": 38000},
        }
        city_multipliers = {"Hyderabad": 1.4, "Bengaluru": 1.6, "Mumbai": 1.8, "Delhi": 1.7}
        mult = city_multipliers.get(city, 1.0) if city else 1.0
        loc = loc_type or "highway"
        r = rates.get(loc, rates["highway"])
        return self._ok("market_rate",
            f"**Market Lease Rates — {loc.title()} · {city or 'India'}**\n\n"
            f"• Typical range: **₹{int(r['min']*mult):,} – ₹{int(r['max']*mult):,}/mo**\n"
            f"• Average: **₹{int(r['avg']*mult):,}/mo**\n"
            f"• City premium ({city}): **{mult:.1f}×** base rate\n\n"
            f"For a precise valuation of your specific plot, use AI Chat."
        )

    # ── OPERATOR ─────────────────────────────────────────────────────────────

    def _operator(self, msg: str, user_id: int) -> dict:
        m = msg.lower()

        if _contains(m, "hello", "hi", "hey", "help"):
            return self._ok("operator_help",
                "👋 Hi! I can give you quick stats on your network:\n\n"
                "• **Station summary** — ask 'my stations'\n"
                "• **Revenue** — ask 'my revenue'\n"
                "• **Availability** — ask 'how many bays available'\n\n"
                "For pricing optimization and predictive maintenance, use AI Chat."
            )

        if _contains(m, "station", "my station", "network"):
            return self._operator_stations(user_id)

        if _contains(m, "revenue", "earning", "income", "money"):
            return self._operator_revenue(user_id)

        if _contains(m, "available", "free", "bays", "slots"):
            return self._operator_availability(user_id)

        return self._no_match()

    def _operator_stations(self, user_id: int) -> dict:
        from database import ChargingStation, ChargerPoint
        stations = ChargingStation.query.filter_by(operator_id=user_id).all()
        if not stations:
            return self._ok("no_stations", "No stations yet. Add your first station from the 'My Stations' tab.")
        total_pts  = sum(s.total_points for s in stations)
        avail_pts  = sum(s.available_points for s in stations)
        avg_uptime = sum(s.uptime_percent or 0 for s in stations) / len(stations)
        lines = [f"**Your {len(stations)} station(s) · {total_pts} charger points:**\n"]
        for s in stations:
            pct = int(s.available_points / s.total_points * 100) if s.total_points else 0
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            lines.append(f"• **{s.name}** — {s.available_points}/{s.total_points} free [{bar}] {pct}%")
        lines.append(f"\n📈 Avg uptime: {avg_uptime:.1f}% · Available now: {avail_pts}/{total_pts} bays")
        return self._ok("station_summary", "\n".join(lines))

    def _operator_revenue(self, user_id: int) -> dict:
        from database import ChargingStation, ChargingSession
        from datetime import timedelta
        stations = ChargingStation.query.filter_by(operator_id=user_id).all()
        sids = [s.id for s in stations]
        mtd_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        sessions = ChargingSession.query.filter(
            ChargingSession.station_id.in_(sids),
            ChargingSession.status == "completed",
            ChargingSession.start_time >= mtd_start
        ).all()
        revenue  = sum(s.amount_inr or 0 for s in sessions)
        energy   = sum(s.energy_kwh or 0 for s in sessions)
        return self._ok("operator_revenue",
            f"**Revenue — Month to Date**\n\n"
            f"• Sessions: **{len(sessions)}**\n"
            f"• Energy delivered: **{energy:.0f} kWh**\n"
            f"• Revenue: **₹{revenue:,.0f}**\n"
            f"• Projected monthly: **₹{revenue / max(1, datetime.utcnow().day) * 30:,.0f}**\n\n"
            f"For pricing optimization analysis, use AI Chat."
        )

    def _operator_availability(self, user_id: int) -> dict:
        from database import ChargingStation
        stations = ChargingStation.query.filter_by(operator_id=user_id).all()
        total  = sum(s.total_points for s in stations)
        avail  = sum(s.available_points for s in stations)
        busy   = total - avail
        pct    = int(avail / total * 100) if total else 0
        return self._ok("availability",
            f"**Network Availability Right Now**\n\n"
            f"• Free bays: **{avail}/{total}** ({pct}% available)\n"
            f"• In use: **{busy}** bays\n"
            f"• Utilization: **{100-pct}%**\n\n"
            f"Check the 'My Stations' map for per-station detail."
        )

    # ── OEM SELL ──────────────────────────────────────────────────────────────

    def _oem_sell(self, msg: str, user_id: int) -> dict:
        m = msg.lower()

        if _contains(m, "hello", "hi", "hey", "help"):
            return self._ok("oemsell_help",
                "👋 Hi! Quick help available:\n\n"
                "• **My products** — ask 'my products'\n"
                "• **Orders** — ask 'recent orders'\n"
                "• **Connector types** — ask 'what connectors do we support'\n\n"
                "For pricing strategy and customer targeting, use AI Chat."
            )

        if _contains(m, "my product", "product list", "charger list"):
            return self._oemsell_products(user_id)

        if _contains(m, "order", "sales", "sold"):
            return self._oemsell_orders(user_id)

        if _contains(m, "connector", "ccs", "chademo", "type", "standard"):
            return self._ok("connectors",
                "**EV Charger Connector Standards — India**\n\n"
                "• **CCS2** — dominant DC fast charging standard · mandatory for FAME-II\n"
                "• **CHAdeMO** — Japanese standard · legacy, declining\n"
                "• **Type-2 AC** — universal AC charging connector\n"
                "• **Bharat AC-001** — Indian govt standard for slow charging\n\n"
                "CCS2 + Type-2 AC combo covers 95%+ of Indian EVs."
            )

        return self._no_match()

    def _oemsell_products(self, user_id: int) -> dict:
        from database import ChargerProduct
        products = ChargerProduct.query.filter_by(oem_id=user_id, status="active").all()
        if not products:
            return self._ok("no_products", "No products listed. Add your first charger from 'List Charger' tab.")
        lines = [f"**Your {len(products)} active product(s):**\n"]
        for p in products:
            lines.append(f"• **{p.model_name}** — {p.power_kw}kW {p.charger_type} · ₹{p.unit_price:,.0f} · Stock: {p.stock_available}")
        return self._ok("product_list", "\n".join(lines))

    def _oemsell_orders(self, user_id: int) -> dict:
        from database import ChargerProduct, ChargerOrder
        products = ChargerProduct.query.filter_by(oem_id=user_id).all()
        pids = [p.id for p in products]
        orders = (ChargerOrder.query
                  .filter(ChargerOrder.product_id.in_(pids))
                  .order_by(ChargerOrder.created_at.desc()).limit(5).all())
        if not orders:
            return self._ok("no_orders", "No orders yet.")
        total_revenue = sum(o.total_amount or 0 for o in orders)
        lines = [f"**Recent {len(orders)} order(s) · ₹{total_revenue:,.0f} total:**\n"]
        for o in orders:
            lines.append(f"• {o.product.model_name if o.product else '?'} × {o.quantity} → {o.buyer.company or o.buyer.full_name if o.buyer else '?'} · ₹{o.total_amount:,.0f}")
        return self._ok("order_list", "\n".join(lines))

    # ── OEM SETUP ─────────────────────────────────────────────────────────────

    def _oem_setup(self, msg: str, user_id: int) -> dict:
        m = msg.lower()

        if _contains(m, "hello", "hi", "hey", "help"):
            return self._ok("oemsetup_help",
                "👋 Hi! Quick help available:\n\n"
                "• **Available sites** — ask 'sites in Hyderabad'\n"
                "• **My requests** — ask 'my lease requests'\n"
                "• **Grid connection** — ask 'how to get grid connection'\n\n"
                "For site scoring and ROI analysis, use AI Chat."
            )

        if _contains(m, "site", "available land", "find land", "listing"):
            city = _match_city(m)
            return self._oemsetup_sites(city)

        if _contains(m, "my request", "sent request", "pending"):
            return self._oemsetup_requests(user_id)

        if _contains(m, "grid", "power", "kva", "discom", "electricity"):
            return self._ok("grid_info",
                "**Grid Connection for EV Stations — Quick Guide**\n\n"
                "• **<63kW** → LT (Low Tension) connection · 15–30 days\n"
                "• **>63kW** → HT (High Tension) · transformer required · 45–90 days\n"
                "• Apply to local DISCOM with single-line diagram\n"
                "• EV-specific concessional tariff: ~₹6.5/unit (Telangana)\n\n"
                "For a detailed grid requirement analysis for your site, use AI Chat."
            )

        return self._no_match()

    def _oemsetup_sites(self, city: str | None) -> dict:
        from database import LandListing
        q = LandListing.query.filter_by(status="active")
        if city:
            q = q.filter(LandListing.city.ilike(f"%{city}%"))
        sites = q.order_by(LandListing.ai_score.desc()).limit(5).all()
        if not sites:
            return self._ok("no_sites", f"No active listings found{f' in {city}' if city else ''}.")
        lines = [f"**Top sites{f' in {city}' if city else ''}:**\n"]
        for s in sites:
            score_str = f" · AI Score: {s.ai_score:.0f}" if s.ai_score else ""
            lines.append(f"• **{s.title}** — {s.area_sqft:,} sqft · ₹{s.monthly_lease:,.0f}/mo{score_str}")
        lines.append("\nOpen 'Site Matches' tab to view on map and send lease requests.")
        return self._ok("site_list", "\n".join(lines))

    def _oemsetup_requests(self, user_id: int) -> dict:
        from database import LeaseRequest
        requests = LeaseRequest.query.filter_by(requester_id=user_id).order_by(LeaseRequest.created_at.desc()).limit(5).all()
        if not requests:
            return self._ok("no_requests", "No lease requests sent yet. Browse sites to find your first location.")
        lines = [f"**Your {len(requests)} request(s):**\n"]
        for r in requests:
            icon = "⏳" if r.status == "pending" else "✅" if r.status == "accepted" else "❌"
            lines.append(f"{icon} **{r.listing_title}** — ₹{r.offered_monthly:,.0f}/mo · {r.status}")
        return self._ok("request_list", "\n".join(lines))

    # ── Generic ───────────────────────────────────────────────────────────────

    def _generic(self, msg: str, user_id: int) -> dict:
        return self._no_match()

    # ── Response builders ─────────────────────────────────────────────────────

    def _ok(self, intent: str, response: str, data: dict = None) -> dict:
        return {"intent": intent, "response": response, "data": data, "matched": True}

    def _no_match(self) -> dict:
        return {"intent": "unknown", "response": "", "data": None, "matched": False}


# Singleton
_engine = NlpEngine()

def handle_nlp(role: str, message: str, user_id: int) -> dict:
    return _engine.handle(role, message, user_id)
