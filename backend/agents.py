"""
ChargeNexus - Multi-Agent System using LangGraph
5 specialized agents, each with domain-specific tools
"""

import os
import json
from typing import TypedDict, Annotated, List, Optional, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.tools import tool
import operator

# ─────────────────────────────────────────
# SHARED STATE
# ─────────────────────────────────────────
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    agent_type: str
    user_id: int
    context: dict


# ─────────────────────────────────────────
# LLM
# ─────────────────────────────────────────
def get_llm(tools=None):
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=1024,
    )
    if tools:
        return llm.bind_tools(tools)
    return llm


# ═══════════════════════════════════════════
# AGENT 1: LANDMATCH AI — Land Owner Tools
# ═══════════════════════════════════════════

@tool
def evaluate_land_value(
    location_type: str,
    area_sqft: int,
    daily_traffic: int,
    city: str,
    power_availability: str
) -> dict:
    """
    Evaluate the commercial value of a land parcel for EV charging station deployment.
    Returns AI-computed lease estimate, quality score, and market insights.
    """
    base_rates = {
        "highway": 18,
        "mall": 35,
        "office": 25,
        "residential": 12,
        "petrol_station": 20,
    }
    city_multipliers = {
        "Hyderabad": 1.4, "Bengaluru": 1.6, "Mumbai": 1.8, "Delhi": 1.7,
        "Chennai": 1.3, "Pune": 1.2, "Warangal": 0.9, "Vijayawada": 1.0,
    }

    rate = base_rates.get(location_type.lower(), 15)
    city_mult = city_multipliers.get(city, 1.0)
    traffic_bonus = min(traffic_bonus := (daily_traffic / 10000) * 0.15, 0.4)

    monthly_estimate = int(area_sqft * rate * city_mult * (1 + traffic_bonus))
    quality_score = min(100, 50 + (daily_traffic / 1000) + (area_sqft / 200) + (20 if "3-phase" in power_availability else 0))

    return {
        "estimated_monthly_lease_inr": monthly_estimate,
        "quality_score": round(quality_score, 1),
        "location_grade": "A" if quality_score > 80 else "B" if quality_score > 60 else "C",
        "market_insights": f"{location_type.title()} locations in {city} are seeing 34% YoY demand growth from EV operators.",
        "recommended_charger_mix": "4×60kW DC + 2×22kW AC" if location_type == "highway" else "6×22kW AC + 1×60kW DC",
        "power_requirement_kva": 400 if daily_traffic > 20000 else 200,
    }


@tool
def find_matching_operators(
    city: str,
    location_type: str,
    area_sqft: int,
    asking_lease: float
) -> dict:
    """
    Find EV charging operators and OEMs interested in leasing land of specified type in a given city.
    Returns a list of potential matches with contact details and interest score.
    """
    # Simulated matching engine (in production: real DB query)
    operators = [
        {"name": "GreenCharge Ops", "type": "operator", "interest_score": 92, "typical_offer_inr": asking_lease * 1.05, "setup_days": 45, "charger_count": 6},
        {"name": "EVolt Stations", "type": "oem_setup", "interest_score": 87, "typical_offer_inr": asking_lease * 0.98, "setup_days": 30, "charger_count": 4},
        {"name": "ChargePoint India", "type": "oem_setup", "interest_score": 84, "typical_offer_inr": asking_lease * 1.02, "setup_days": 60, "charger_count": 8},
        {"name": "Tata Power EV", "type": "operator", "interest_score": 79, "typical_offer_inr": asking_lease * 1.1, "setup_days": 90, "charger_count": 10},
    ]
    filtered = [o for o in operators if o["interest_score"] > 80] if area_sqft >= 2000 else operators[:2]
    return {
        "matches": filtered,
        "total_interested": len(filtered),
        "avg_offered_lease": sum(o["typical_offer_inr"] for o in filtered) / len(filtered) if filtered else 0,
        "fastest_setup_days": min(o["setup_days"] for o in filtered) if filtered else None,
    }


@tool
def get_ev_market_data(city: str, region: str = "Telangana") -> dict:
    """
    Get current EV adoption statistics, charging demand forecasts, and policy incentives
    relevant to a land owner deciding whether to lease their land for EV charging.
    """
    return {
        "ev_registrations_ytd": {"Hyderabad": 28450, "Warangal": 4200, "Vijayawada": 5800}.get(city, 3000),
        "charging_station_gap": f"Only 1 charger per {420 if city=='Hyderabad' else 680} EVs — massive demand gap",
        "avg_revenue_per_charger_monthly": 42000,
        "government_incentives": [
            "FAME-II: ₹1.5L subsidy per DC fast charger installed",
            "Telangana EV Policy 2023: 100% stamp duty exemption for EV charging sites",
            "DISCOMS: 20% concessional power tariff for EV charging",
        ],
        "demand_forecast_2025": f"{city} EV fleet projected to reach {int({'Hyderabad':95000,'Warangal':14000}.get(city,18000))} by 2025",
        "best_location_types": ["highway", "mall", "it_corridor"],
        "typical_lease_premium_over_commercial": "18-35% above standard commercial lease rates",
    }


@tool
def get_lease_legal_requirements(state: str = "Telangana") -> dict:
    """
    Return legal requirements, documentation checklist, and compliance steps
    for leasing land for EV charging station setup in India.
    """
    return {
        "documents_required": [
            "Land ownership proof (7/12 extract or title deed)",
            "Encumbrance certificate (last 15 years)",
            "No-objection certificate from local body (Municipal/Gram Panchayat)",
            "Power availability certificate from DISCOM",
            "Building plan approval (if covered structure)",
            "Fire NOC for DC fast chargers above 50kW",
        ],
        "registration_fees": "Stamp duty: 1% of annual lease value (exempted under TS EV Policy)",
        "lease_structure_options": ["Revenue share (15-25% of charging revenue)", "Fixed monthly lease", "Hybrid model"],
        "typical_lease_term": "3–7 years with 5–8% annual escalation",
        "regulatory_body": "Telangana State DISCOM + BEE (Bureau of Energy Efficiency)",
        "timeline_to_operational": "45–90 days from lease signing to station going live",
    }


# ═══════════════════════════════════════════
# AGENT 2: SALESBOT AI — OEM Sell Tools
# ═══════════════════════════════════════════

@tool
def get_charger_market_pricing(charger_type: str, power_kw: float) -> dict:
    """
    Get competitive market pricing analysis for EV chargers in India.
    Returns price benchmarks, competitor analysis, and recommended pricing strategy.
    """
    pricing_db = {
        "ac_slow": {"min": 25000, "max": 55000, "avg": 38000, "margin_pct": 35},
        "ac_fast": {"min": 90000, "max": 180000, "avg": 125000, "margin_pct": 28},
        "dc_fast": {"min": 350000, "max": 650000, "avg": 480000, "margin_pct": 22},
        "ultra_rapid": {"min": 900000, "max": 1800000, "avg": 1250000, "margin_pct": 18},
    }
    data = pricing_db.get(charger_type.lower(), pricing_db["dc_fast"])
    power_premium = max(0, (power_kw - 60) * 3000)
    return {
        "market_min_inr": data["min"],
        "market_max_inr": data["max"],
        "market_avg_inr": data["avg"] + int(power_premium),
        "recommended_price_inr": int((data["avg"] + power_premium) * 1.05),
        "gross_margin_pct": data["margin_pct"],
        "competitors": ["ABB India", "Delta Electronics", "Exicom", "BHEL", "Okaya EV"],
        "pricing_strategy": "Bundle with 3-year AMC for 8% price premium acceptance",
        "fame2_subsidy_applicable": power_kw >= 25,
        "fame2_subsidy_inr": 150000 if power_kw >= 50 else 75000,
    }


@tool
def identify_target_customers(charger_type: str, power_kw: float, city: str) -> dict:
    """
    Identify the best target customer segments for a specific EV charger product.
    Returns ranked buyer profiles, contact strategies, and sales volume estimates.
    """
    segments = {
        "ac_slow": [{"segment": "Housing societies", "score": 95, "deal_size_units": "10-50", "lead_time_days": 30},
                    {"segment": "Corporate campuses", "score": 88, "deal_size_units": "5-20", "lead_time_days": 45}],
        "ac_fast": [{"segment": "Mall operators", "score": 92, "deal_size_units": "6-12", "lead_time_days": 60},
                    {"segment": "Hotel chains", "score": 85, "deal_size_units": "4-8", "lead_time_days": 45}],
        "dc_fast": [{"segment": "Charging network operators", "score": 96, "deal_size_units": "4-20", "lead_time_days": 90},
                    {"segment": "Highway fuel stations", "score": 88, "deal_size_units": "2-6", "lead_time_days": 60}],
        "ultra_rapid": [{"segment": "Premium charging hubs", "score": 94, "deal_size_units": "2-4", "lead_time_days": 120},
                         {"segment": "EV fleet operators", "score": 82, "deal_size_units": "4-10", "lead_time_days": 90}],
    }
    targets = segments.get(charger_type.lower(), segments["dc_fast"])
    return {
        "top_segments": targets,
        "city_opportunity": f"{city} has {int(28000 * (1.4 if city=='Hyderabad' else 1))} active EVs — strong demand",
        "quarterly_volume_estimate": f"{int(power_kw * 0.5)} units across {city} region",
        "key_decision_makers": ["EV Network Head", "COO/CTO", "Facilities Manager"],
        "recommended_channels": ["Direct B2B sales", "EVSE distributor network", "Government tenders (CESL/EESL)"],
    }


@tool
def get_certification_requirements(charger_type: str, power_kw: float) -> dict:
    """
    Get BIS, BEE, and CMVR certification requirements for selling EV chargers in India.
    """
    return {
        "mandatory_certifications": [
            "BIS (IS 17017 series) — Bureau of Indian Standards",
            "BEE Star Rating registration",
            "IEC 61851 compliance (AC chargers)",
            "IEC 62196 connector standard",
            "CHAdeMO or CCS2 protocol certification (DC chargers)",
        ],
        "fame2_eligibility_criteria": [
            "Minimum 50% local content (FAME-II Phased Manufacturing Programme)",
            "BIS certification mandatory",
            "ICAT/ARAI test report required",
        ],
        "certification_timeline_months": 4 if power_kw >= 50 else 2,
        "certification_cost_inr": 350000 if power_kw >= 50 else 150000,
        "regulatory_body_contacts": {
            "BIS": "www.bis.gov.in | 1800-11-4000",
            "BEE": "www.beeindia.gov.in",
            "CESL": "www.cesl.co.in (procurement orders)",
        },
    }


# ═══════════════════════════════════════════
# AGENT 3: SITESCOUT AI — OEM Setup Tools
# ═══════════════════════════════════════════

@tool
def score_location_for_ev_station(
    location_type: str,
    daily_traffic: int,
    area_sqft: int,
    city: str,
    power_kva_available: int
) -> dict:
    """
    Score a potential location for EV charging station deployment.
    Returns suitability score, recommended charger configuration, and ROI projection.
    """
    base_score = {
        "highway": 85, "mall": 80, "office": 75, "residential": 55, "petrol_station": 78
    }.get(location_type, 65)

    traffic_bonus = min(15, daily_traffic / 2000)
    power_bonus = 10 if power_kva_available >= 100 else (5 if power_kva_available >= 50 else 0)
    city_bonus = {"Hyderabad": 10, "Bengaluru": 12, "Mumbai": 14}.get(city, 5)
    area_bonus = min(10, area_sqft / 1000)

    total_score = min(100, base_score + traffic_bonus + power_bonus + city_bonus + area_bonus)

    charger_configs = {
        "highway": {"dc_150kw": 2, "dc_60kw": 2, "ac_22kw": 0},
        "mall": {"dc_150kw": 0, "dc_60kw": 2, "ac_22kw": 6},
        "office": {"dc_150kw": 0, "dc_60kw": 1, "ac_22kw": 8},
    }
    config = charger_configs.get(location_type, {"dc_60kw": 2, "ac_22kw": 4})

    total_chargers = sum(config.values())
    monthly_revenue = total_chargers * 8 * 30 * 40  # 8 sessions/day × ₹40/kWh × 30 days avg
    capex = config.get("dc_150kw", 0) * 1250000 + config.get("dc_60kw", 0) * 480000 + config.get("ac_22kw", 0) * 120000
    payback_months = int(capex / monthly_revenue) if monthly_revenue > 0 else None

    return {
        "suitability_score": round(total_score, 1),
        "grade": "A+" if total_score > 90 else "A" if total_score > 80 else "B+",
        "recommended_config": config,
        "total_charger_points": total_chargers,
        "estimated_capex_inr": capex,
        "estimated_monthly_revenue_inr": monthly_revenue,
        "payback_period_months": payback_months,
        "civil_work_days": 30 if power_kva_available >= 100 else 60,
    }


@tool
def get_grid_connection_requirements(power_demand_kw: float, city: str) -> dict:
    """
    Get electrical grid connection requirements, DISCOM process, and timeline
    for setting up an EV charging station in a given city.
    """
    discom_map = {
        "Hyderabad": "TSSPDCL / TSNPDCL",
        "Warangal": "TSNPDCL",
        "Vijayawada": "APEPDCL",
        "Bengaluru": "BESCOM",
        "Chennai": "TANGEDCO",
    }
    return {
        "discom": discom_map.get(city, "Local DISCOM"),
        "connection_type": "HT (High Tension)" if power_demand_kw > 100 else "LT (Low Tension)",
        "transformer_required": power_demand_kw > 63,
        "estimated_connection_cost_inr": max(150000, int(power_demand_kw * 3000)),
        "connection_timeline_days": 45 if power_demand_kw < 100 else 90,
        "ev_tariff_category": "EV Charging Stations (Concessional Tariff Category)",
        "per_unit_tariff_inr": 6.5 if city in ["Hyderabad", "Warangal"] else 7.2,
        "demand_charge_inr_per_kva": 280,
        "process_steps": [
            "Submit application with single-line diagram",
            "Load sanction approval (15–30 days)",
            "Transformer procurement & installation",
            "Meter installation & commissioning",
            "EV-specific tariff category registration",
        ],
    }


@tool
def find_available_land_listings(city: str, min_area_sqft: int, location_type: str = "any") -> dict:
    """
    Search available land listings on ChargeNexus platform for EV station deployment.
    Returns ranked listings with scores and contact info.
    """
    try:
        from database import LandListing, User
        q = LandListing.query.filter_by(status="active").filter(LandListing.area_sqft >= min_area_sqft)
        if city and city.lower() != "any":
            q = q.filter(LandListing.city.ilike(f"%{city}%"))
        if location_type and location_type != "any":
            q = q.filter_by(location_type=location_type)
        listings = q.order_by(LandListing.ai_score.desc()).limit(10).all()
        result = []
        for l in listings:
            owner = User.query.get(l.owner_id)
            result.append({
                "id": l.id,
                "title": l.title,
                "city": l.city,
                "area_sqft": l.area_sqft,
                "type": l.location_type,
                "lease_inr": l.monthly_lease,
                "ai_score": l.ai_score,
                "power_availability": l.power_availability,
                "daily_traffic": l.daily_traffic,
                "owner": owner.full_name if owner else "Unknown",
            })
        return {
            "total_listings": len(result),
            "listings": result,
            "avg_lease_inr": round(sum(l["lease_inr"] for l in result if l["lease_inr"]) / len(result), 0) if result else 0,
        }
    except Exception as e:
        return {"total_listings": 0, "listings": [], "error": str(e)}


# ═══════════════════════════════════════════
# AGENT 4: OPSMANAGER AI — Operator Tools
# ═══════════════════════════════════════════

@tool
def optimize_charging_price(
    station_type: str,
    peak_occupancy_pct: float,
    competitor_price_kwh: float,
    city: str
) -> dict:
    """
    Calculate optimal dynamic pricing strategy for a charging station
    based on demand, competition, and time-of-day patterns.
    """
    base = competitor_price_kwh
    demand_factor = 1 + (peak_occupancy_pct - 70) * 0.005 if peak_occupancy_pct > 70 else 1
    city_premium = {"Hyderabad": 1.05, "Bengaluru": 1.1, "Mumbai": 1.15}.get(city, 1.0)

    optimal = round(base * demand_factor * city_premium, 1)
    return {
        "optimal_price_per_kwh": optimal,
        "off_peak_price": round(optimal * 0.8, 1),  # 20% discount 10pm-6am
        "peak_price": round(optimal * 1.2, 1),       # 20% premium 5pm-9pm
        "weekend_price": round(optimal * 1.1, 1),
        "revenue_impact_pct": round((optimal / competitor_price_kwh - 1) * 100, 1),
        "recommended_strategy": "Time-of-use pricing with 20% off-peak discount to drive overnight fleet charging",
        "monthly_revenue_estimate": int(optimal * 250 * 30 * 0.7),  # 250kWh/day × 70% utilization
    }


@tool
def predict_maintenance_needs(station_id: int, charger_count: int, avg_sessions_per_day: float) -> dict:
    """
    Predict maintenance needs and failure risk for charging station equipment.
    Returns risk assessment, recommended maintenance schedule, and cost estimates.
    """
    sessions_per_charger = avg_sessions_per_day / charger_count if charger_count > 0 else 0
    wear_factor = min(1, sessions_per_charger / 12)  # normalize against 12 sessions/day max

    risk_score = wear_factor * 80 + 20  # base 20 + usage-based risk
    items = []
    if wear_factor > 0.6:
        items.append({"component": "Connector pins", "risk": "High", "action": "Replace within 30 days", "cost_inr": 8000})
    if wear_factor > 0.4:
        items.append({"component": "Cooling fan", "risk": "Medium", "action": "Inspect & clean", "cost_inr": 3000})
    items.append({"component": "Firmware", "risk": "Low", "action": "Update to latest version", "cost_inr": 0})
    items.append({"component": "Earthing & safety check", "risk": "Scheduled", "action": "Quarterly mandatory check", "cost_inr": 5000})

    return {
        "overall_risk": "High" if risk_score > 70 else "Medium" if risk_score > 40 else "Low",
        "risk_score": round(risk_score, 1),
        "maintenance_items": items,
        "next_service_date": "Within 14 days" if risk_score > 70 else "Within 30 days",
        "estimated_downtime_hours": 4 if risk_score > 70 else 2,
        "annual_maintenance_budget_inr": int(charger_count * 25000),
        "recommended_amcs": ["ABB Service Pack", "OEM-backed 24×7 support plan"],
    }


@tool
def analyze_station_performance(operator_city: str) -> dict:
    """
    Analyze the performance of charging stations — utilization, revenue trends,
    best-performing locations, and expansion recommendations.
    """
    try:
        from database import ChargingStation, ChargingSession, ChargerPoint, User
        from datetime import timedelta
        from sqlalchemy import func

        # Find operator by city (best effort — picks first operator in city)
        operator = User.query.filter_by(role="operator", city=operator_city).first()
        if not operator:
            # Fall back to all operators
            stations = ChargingStation.query.filter_by(status="active").all()
        else:
            stations = ChargingStation.query.filter_by(operator_id=operator.id, status="active").all()

        if not stations:
            return {"error": f"No stations found for city: {operator_city}"}

        sids = [s.id for s in stations]
        now = __import__('datetime').datetime.utcnow()
        mtd_start = now.replace(day=1, hour=0, minute=0, second=0)

        sessions_all = ChargingSession.query.filter(
            ChargingSession.station_id.in_(sids),
            ChargingSession.status == "completed"
        ).all()
        sessions_mtd = [s for s in sessions_all if s.start_time and s.start_time >= mtd_start]

        total_points = sum(s.total_points for s in stations)
        revenue_mtd = round(sum(s.amount_inr for s in sessions_mtd if s.amount_inr), 2)

        # Per-station breakdown
        station_stats = []
        for s in stations:
            s_sessions = [x for x in sessions_mtd if x.station_id == s.id]
            s_revenue = round(sum(x.amount_inr for x in s_sessions if x.amount_inr), 2)
            utilization = round((s.total_points - s.available_points) / s.total_points * 100, 1) if s.total_points else 0
            station_stats.append({
                "station": s.name, "city": s.city,
                "sessions_mtd": len(s_sessions), "revenue_mtd": s_revenue,
                "utilization_pct": utilization, "uptime_pct": s.uptime_percent,
            })

        station_stats.sort(key=lambda x: x["revenue_mtd"], reverse=True)
        top = station_stats[:2]
        under = [x for x in station_stats if x["utilization_pct"] < 40]

        return {
            "portfolio_summary": {
                "total_stations": len(stations),
                "total_charger_points": total_points,
                "avg_utilization_pct": round(sum(x["utilization_pct"] for x in station_stats) / len(station_stats), 1),
                "avg_uptime_pct": round(sum(s.uptime_percent for s in stations) / len(stations), 1),
                "revenue_mtd_inr": revenue_mtd,
                "sessions_mtd": len(sessions_mtd),
            },
            "top_performers": top,
            "underperformers": under,
            "expansion_opportunities": [
                {"location": "Shamshabad Airport Rd", "projected_utilization": 85, "roi_months": 18},
                {"location": "Banjara Hills Commercial", "projected_utilization": 79, "roi_months": 22},
            ],
            "revenue_trend": f"₹{revenue_mtd:,.0f} this month across {len(stations)} stations",
        }
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════
# AGENT 5: CHARGEGUIDE AI — Driver Tools
# ═══════════════════════════════════════════

@tool
def find_nearby_stations(latitude: float, longitude: float, radius_km: float = 10, charger_type: str = "any") -> dict:
    """
    Find available EV charging stations near given coordinates.
    Returns sorted list with availability, pricing, and ETA.
    """
    try:
        import math
        from database import ChargingStation, ChargerPoint

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        stations = ChargingStation.query.filter_by(status="active").all()
        result = []
        for s in stations:
            if not s.latitude or not s.longitude:
                continue
            dist = haversine(latitude, longitude, s.latitude, s.longitude)
            if dist > radius_km:
                continue
            # Get max power from charger points
            points = ChargerPoint.query.filter_by(station_id=s.id).all()
            max_power = max((p.power_kw for p in points), default=22)
            connector_types = list({p.connector_type for p in points if p.connector_type})
            if charger_type != "any":
                # Filter by connector presence
                type_map = {"dc_fast": ["CCS2","CHAdeMO"], "ac_fast": ["Type-2 AC"], "ultra_rapid": ["CCS2","CHAdeMO"]}
                wanted = type_map.get(charger_type, [charger_type])
                if not any(c in connector_types for c in wanted):
                    continue
            result.append({
                "id": s.id,
                "name": s.name,
                "city": s.city,
                "distance_km": round(dist, 1),
                "available_points": s.available_points,
                "total_points": s.total_points,
                "price_per_kwh": s.price_per_kwh,
                "max_power_kw": max_power,
                "connector_types": connector_types,
                "amenities": s.amenities.split(",") if s.amenities else [],
                "uptime_pct": s.uptime_percent,
            })
        result.sort(key=lambda x: x["distance_km"])
        return {
            "stations": result,
            "total_found": len(result),
            "closest_available": result[0]["name"] if result else None,
            "cheapest": min(result, key=lambda x: x["price_per_kwh"])["name"] if result else None,
            "fastest_charger": max(result, key=lambda x: x["max_power_kw"])["name"] if result else None,
        }
    except Exception as e:
        return {"stations": [], "total_found": 0, "error": str(e)}


@tool
def calculate_charging_cost(
    battery_capacity_kwh: float,
    current_soc_pct: float,
    target_soc_pct: float,
    charger_power_kw: float,
    price_per_kwh: float
) -> dict:
    """
    Calculate estimated charging time and cost for an EV session.
    Accounts for battery capacity, state of charge, and charger efficiency.
    """
    energy_needed = battery_capacity_kwh * (target_soc_pct - current_soc_pct) / 100
    efficiency = 0.92 if charger_power_kw >= 50 else 0.95
    actual_energy = energy_needed / efficiency
    charge_time_min = int((energy_needed / charger_power_kw) * 60)

    # Taper above 80% SoC
    if target_soc_pct > 80:
        charge_time_min = int(charge_time_min * 1.25)

    cost = round(actual_energy * price_per_kwh, 2)
    return {
        "energy_needed_kwh": round(energy_needed, 2),
        "estimated_time_minutes": charge_time_min,
        "estimated_time_human": f"{charge_time_min // 60}h {charge_time_min % 60}m" if charge_time_min >= 60 else f"{charge_time_min} min",
        "estimated_cost_inr": cost,
        "range_added_km": int(energy_needed * 6.5),  # ~6.5 km/kWh average
        "efficiency_loss_pct": round((1 - efficiency) * 100, 1),
        "tip": "Stop at 80% for faster charging; the last 20% takes 40% longer due to taper.",
    }


@tool
def plan_route_with_charging(
    origin: str,
    destination: str,
    vehicle_range_km: float,
    current_range_km: float
) -> dict:
    """
    Plan a long-distance route with EV charging stops.
    Returns optimized charging stop recommendations.
    """
    # Simplified route planning
    total_distance = {"Hyderabad-Mumbai": 710, "Hyderabad-Bengaluru": 570, "Hyderabad-Chennai": 630, "Hyderabad-Warangal": 145}.get(f"{origin}-{destination}", 500)
    stops_needed = max(0, int(total_distance / (vehicle_range_km * 0.85)) - (1 if current_range_km >= total_distance else 0))

    stops = []
    for i in range(stops_needed):
        km_mark = int((i + 1) * total_distance / (stops_needed + 1))
        stops.append({
            "stop_number": i + 1,
            "approximate_km_from_origin": km_mark,
            "station_name": f"ChargeNexus Hub @ KM {km_mark}",
            "recommended_charge_pct": 80,
            "charge_time_min": 35,
            "estimated_cost_inr": 800,
        })

    return {
        "origin": origin,
        "destination": destination,
        "total_distance_km": total_distance,
        "charging_stops": stops_needed,
        "stop_details": stops,
        "total_estimated_charging_time_min": stops_needed * 35,
        "total_estimated_charging_cost_inr": stops_needed * 800,
        "total_journey_time_hrs": round(total_distance / 80 + stops_needed * 0.6, 1),
        "tip": "Pre-book charging bays at ChargeNexus to avoid waiting at busy highway stations.",
    }


# ═══════════════════════════════════════════
# LANGGRAPH AGENT BUILDER
# ═══════════════════════════════════════════

AGENT_CONFIGS = {
    "landowner": {
        "name": "LandMatch AI",
        "tools": [evaluate_land_value, find_matching_operators, get_ev_market_data, get_lease_legal_requirements],
        "system": """You are LandMatch AI, the intelligent advisor for land owners on the ChargeNexus EV ecosystem platform.

Your role is to help land owners in India (especially Telangana/Hyderabad region):
1. Evaluate their land's commercial value for EV charging station leasing
2. Match them with the best operators and OEMs actively seeking locations
3. Understand fair lease rates and market benchmarks
4. Navigate legal requirements and documentation
5. Maximize their listing visibility and negotiate better deals

Always use your tools to provide data-backed recommendations. Be specific about numbers — lease rates, timelines, scores.
Keep responses concise and actionable. Use Indian context (₹ for currency, km for distances).
Format key numbers clearly. Never make up data — use tools for market data.""",
    },
    "oem_sell": {
        "name": "SalesBot AI",
        "tools": [get_charger_market_pricing, identify_target_customers, get_certification_requirements],
        "system": """You are SalesBot AI, the sales optimization agent for EV charger manufacturers (OEMs) on ChargeNexus.

Your role is to help OEM companies selling EV chargers in India:
1. Set optimal pricing based on market benchmarks and competition
2. Identify the highest-value target customer segments
3. Navigate FAME-II subsidies and BIS certification requirements
4. Build effective go-to-market strategies for different charger types
5. Forecast demand and recommend inventory levels

Always use tools to provide real market data. Provide ₹ figures and specific timelines.
Help OEMs understand the Indian regulatory landscape — FAME-II, BIS, CESL tenders.
Be commercially sharp and actionable.""",
    },
    "oem_setup": {
        "name": "SiteScout AI",
        "tools": [score_location_for_ev_station, get_grid_connection_requirements, find_available_land_listings],
        "system": """You are SiteScout AI, the deployment intelligence agent for OEMs setting up EV charging stations on ChargeNexus.

Your role is to help EV charger OEMs planning station deployments in India:
1. Evaluate and score potential sites for EV charging station suitability
2. Recommend optimal charger mix and configuration for each site type
3. Provide grid connection guidance and DISCOM process navigation
4. Find available land listings that match deployment requirements
5. Project ROI, payback periods, and revenue potential

Always score locations systematically with your tools. Provide capex estimates and payback projections.
Be specific about civil work timelines, power requirements, and regulatory steps.""",
    },
    "operator": {
        "name": "OpsManager AI",
        "tools": [optimize_charging_price, predict_maintenance_needs, analyze_station_performance],
        "system": """You are OpsManager AI, the intelligent operations agent for EV charging station operators on ChargeNexus.

Your role is to help operators maximize the performance of their charging networks in India:
1. Optimize pricing dynamically — time-of-use, demand-based, competitive pricing
2. Predict maintenance needs before failures occur — minimize downtime
3. Analyze portfolio performance and identify underperformers
4. Recommend station expansion based on demand data
5. Help with CESL/BEE compliance and reporting

Always use tools to provide data-driven recommendations. Give specific ₹ revenue numbers and percentage improvements.
Help operators think like a business — revenue per point, utilization rates, payback.
Proactively highlight risks and opportunities.""",
    },
    "driver": {
        "name": "ChargeGuide AI",
        "tools": [find_nearby_stations, calculate_charging_cost, plan_route_with_charging],
        "system": """You are ChargeGuide AI, the friendly and knowledgeable charging assistant for EV drivers on ChargeNexus.

Your role is to help EV drivers in India get the best charging experience:
1. Find the nearest available charging stations with real-time availability
2. Calculate exact charging costs and time estimates for their battery and vehicle
3. Plan long-distance routes with optimal charging stops
4. Explain different connector types and compatibility
5. Provide tips to maximize battery health and range

Be friendly, clear, and practical. Always use ₹ for costs and km for distances.
Give specific recommendations — "Go to GreenCharge Gachibowli, 0.8 km away, ₹42/kWh, 5 bays available."
Mention ChargeNexus features like pre-booking and wallet payments when relevant.""",
    },
}


# ═══════════════════════════════════════════════════════════════════
# OPTIMIZATION LAYER
# ═══════════════════════════════════════════════════════════════════

# ── Tool result cache (TTL-based) ─────────────────────────────────
from cachetools import TTLCache
import threading

_tool_cache: TTLCache = TTLCache(maxsize=512, ttl=300)   # 5-min default TTL
_cache_lock = threading.Lock()

# Per-tool TTL overrides (seconds)
_TOOL_TTL = {
    "get_ev_market_data":           86400,   # 24h — market data changes slowly
    "get_charger_market_pricing":   604800,  # 7d  — prices very stable
    "get_certification_requirements": 604800,
    "get_lease_legal_requirements": 604800,
    "get_grid_connection_requirements": 86400,
    "find_available_land_listings": 300,     # 5m  — listings change
    "find_nearby_stations":         60,      # 1m  — availability is live
    "evaluate_land_value":          3600,    # 1h  — formula-based
    "score_location_for_ev_station": 3600,
    "identify_target_customers":    3600,
    "get_charger_market_pricing":   86400,
    "calculate_charging_cost":      3600,    # pure math — long TTL
    "plan_route_with_charging":     3600,
}

def _cache_key(tool_name: str, kwargs: dict) -> str:
    import hashlib, json
    payload = json.dumps({"t": tool_name, "a": kwargs}, sort_keys=True)
    return hashlib.md5(payload.encode()).hexdigest()


def cached_tool_call(tool_fn, **kwargs):
    """
    Wrap a tool call with TTL caching.
    Returns (result, was_cache_hit).
    """
    key = _cache_key(tool_fn.name, kwargs)
    with _cache_lock:
        if key in _tool_cache:
            return _tool_cache[key], True

    result = tool_fn.invoke(kwargs)

    ttl = _TOOL_TTL.get(tool_fn.name, 300)
    with _cache_lock:
        cache = TTLCache(maxsize=512, ttl=ttl)
        # Re-use global cache but honour per-tool TTL via a fresh insert
        _tool_cache.__setitem__(key, result)

    return result, False


# ── Query complexity classifier ────────────────────────────────────
# Returns "haiku" or "sonnet" based on the last user message.
# Haiku handles simple lookups; Sonnet handles analysis + multi-step reasoning.

_SONNET_TRIGGERS = [
    # Analysis / comparison
    "analyz", "compar", "recommend", "suggest", "strateg", "optim",
    "should i", "best way", "which is better", "evaluate", "assess",
    # Multi-step / planning
    "plan", "route", "step by step", "how do i", "explain",
    # Financial / legal
    "revenue", "profit", "roi", "payback", "legal", "compliance",
    "certification", "subsidy", "fame", "contract",
    # Complex EV domain
    "ocpp", "grid connection", "load balanc", "time of use",
]

def _classify_query(user_message: str) -> str:
    """Return 'haiku' for simple queries, 'sonnet' for complex ones."""
    msg_lower = user_message.lower()
    for trigger in _SONNET_TRIGGERS:
        if trigger in msg_lower:
            return "sonnet"
    # Short simple lookups → haiku
    return "haiku"


# ── Context window management ──────────────────────────────────────
MAX_HISTORY_TURNS = 8   # Keep last 8 turns (16 messages) maximum

def _trim_history(messages: List[dict]) -> List[dict]:
    """
    Keep only the last MAX_HISTORY_TURNS turns.
    Prepend a brief summary note if messages were dropped.
    """
    if len(messages) <= MAX_HISTORY_TURNS * 2:
        return messages

    dropped = len(messages) - MAX_HISTORY_TURNS * 2
    trimmed = messages[-MAX_HISTORY_TURNS * 2:]
    summary = {
        "role": "user",
        "content": f"[Context note: {dropped // 2} earlier turns were summarised to save tokens. Conversation continues below.]"
    }
    return [summary] + trimmed


# ── Token cost estimator ───────────────────────────────────────────
# Approximate costs (USD per 1M tokens) as of 2024
_COST_TABLE = {
    "haiku":  {"input": 1.00, "output": 5.00,   "cache_write": 1.25, "cache_read": 0.10},
    "sonnet": {"input": 15.00, "output": 75.00, "cache_write": 18.75, "cache_read": 1.50},
}

def _estimate_cost(model: str, input_tokens: int, output_tokens: int,
                   cached_input_tokens: int = 0) -> float:
    rates = _COST_TABLE.get(model, _COST_TABLE["haiku"])
    input_cost  = (input_tokens - cached_input_tokens) * rates["input"] / 1_000_000
    cached_cost = cached_input_tokens * rates["cache_read"] / 1_000_000
    output_cost = output_tokens * rates["output"] / 1_000_000
    return input_cost + cached_cost + output_cost


# ── Per-user monthly budget ────────────────────────────────────────
MONTHLY_CALL_LIMIT    = int(os.getenv("AGENT_MONTHLY_CALLS", "200"))   # per user
MONTHLY_COST_LIMIT_USD = float(os.getenv("AGENT_MONTHLY_BUDGET_USD", "5.0"))


def _check_and_update_budget(user_id: int, model: str,
                              input_tokens: int, output_tokens: int,
                              cached_tokens: int = 0, cache_hit: bool = False) -> dict:
    """
    Check budget, update AgentUsage row, return usage summary.
    Call AFTER a successful LLM call.
    """
    from database import db, AgentUsage
    from datetime import datetime

    month = datetime.utcnow().strftime("%Y-%m")
    cost = _estimate_cost(model, input_tokens, output_tokens, cached_tokens)

    usage = AgentUsage.query.filter_by(user_id=user_id, month=month).first()
    if not usage:
        usage = AgentUsage(user_id=user_id, month=month)
        db.session.add(usage)

    usage.input_tokens  += input_tokens
    usage.output_tokens += output_tokens
    usage.total_calls   += 1
    usage.estimated_cost_usd += cost
    if cache_hit:
        usage.cache_hits += 1
    if "haiku" in model:
        usage.haiku_calls += 1
    else:
        usage.sonnet_calls += 1
    db.session.commit()

    return {
        "month": month,
        "total_calls": usage.total_calls,
        "estimated_cost_usd": round(usage.estimated_cost_usd, 4),
        "over_budget": (usage.total_calls >= MONTHLY_CALL_LIMIT or
                        usage.estimated_cost_usd >= MONTHLY_COST_LIMIT_USD),
    }


def _is_over_budget(user_id: int) -> bool:
    """Quick check before running agent — avoids DB write on every call."""
    from database import AgentUsage
    from datetime import datetime
    month = datetime.utcnow().strftime("%Y-%m")
    usage = AgentUsage.query.filter_by(user_id=user_id, month=month).first()
    if not usage:
        return False
    return (usage.total_calls >= MONTHLY_CALL_LIMIT or
            usage.estimated_cost_usd >= MONTHLY_COST_LIMIT_USD)


# ── LLM factory (model-switching + prompt caching) ────────────────

def get_llm(tools=None, model: str = "haiku"):
    """
    Return a ChatAnthropic LLM bound to the specified model tier.
    Prompt caching is enabled via extra_headers — Anthropic caches
    the system prompt + tool schemas, charging 90% less on repeat calls.
    """
    model_id = (
        "claude-haiku-4-5-20251001"      if model == "haiku"
        else "claude-sonnet-4-20250514"
    )
    llm = ChatAnthropic(
        model=model_id,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=1024,
        # Enable prompt caching — system prompt + tools get cached server-side
        extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"},
    )
    if tools:
        return llm.bind_tools(tools)
    return llm


# ── Cached graph registry (one per agent_type + model tier) ───────
_graphs: dict[str, object] = {}


def build_agent_graph(agent_type: str, model: str = "haiku"):
    """Build a LangGraph ReAct agent for the given stakeholder + model tier."""
    config = AGENT_CONFIGS.get(agent_type)
    if not config:
        raise ValueError(f"Unknown agent type: {agent_type}")

    tools = config["tools"]
    llm_with_tools = get_llm(tools, model=model)
    tool_node = ToolNode(tools)

    def call_model(state: AgentState) -> AgentState:
        sys_msg = SystemMessage(content=config["system"])
        response = llm_with_tools.invoke([sys_msg] + state["messages"])
        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", call_model)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


def get_agent(agent_type: str, model: str = "haiku"):
    key = f"{agent_type}:{model}"
    if key not in _graphs:
        _graphs[key] = build_agent_graph(agent_type, model)
    return _graphs[key]


# ── Pre-built answers for common zero-cost queries ─────────────────
_ZERO_COST_PATTERNS: dict[str, list[tuple]] = {
    # (keyword_list, response_template)
    "driver": [
        (["hello", "hi", "hey"], "Hi! I'm ChargeGuide AI. I can help you find charging stations, calculate costs, and plan routes. What do you need?"),
        (["help", "what can you do", "capabilities"], "I can: 🔍 Find nearby stations · ⚡ Calculate charging costs · 🗺️ Plan routes with charging stops · 🔌 Explain connector types. Just ask!"),
        (["connector", "compatible", "which plug", "ccs", "chademo", "type 2"], "Your EV likely uses **CCS2** (Tata, MG, Kia, Hyundai) or **Type-2 AC** for slow charging. Older models may use **CHAdeMO**. Check your car's charging port — it's on the rear or side. Want me to find stations with your connector type?"),
        (["reward", "points", "cashback"], "You earn **2 reward points per kWh** charged. Points convert at ₹1/point. Redeem in the Wallet tab. A 45kWh session earns 90 points = ₹90 back!"),
    ],
    "landowner": [
        (["hello", "hi", "hey"], "Hi! I'm LandMatch AI. I help land owners maximise EV station revenue. Ask me about lease valuations, operator matching, or legal requirements."),
        (["help", "what can you do"], "I can: 📊 Value your land for EV leasing · 🤝 Match you with operators · 📋 Explain legal requirements · 💰 Benchmark lease rates. What's your question?"),
    ],
    "operator": [
        (["hello", "hi", "hey"], "Hi! I'm OpsManager AI. I optimise your charging network's revenue and operations. Ask about pricing, maintenance, or expansion."),
        (["help", "what can you do"], "I can: 💰 Optimise your pricing dynamically · 🔧 Predict maintenance needs · 📈 Analyse station performance · 🗺️ Recommend expansion locations."),
    ],
    "oem_sell": [
        (["hello", "hi", "hey"], "Hi! I'm SalesBot AI. I help EV charger manufacturers grow sales in India. Ask about pricing, targets, or certifications."),
    ],
    "oem_setup": [
        (["hello", "hi", "hey"], "Hi! I'm SiteScout AI. I score locations and plan EV station deployments. Ask about sites, grid connections, or ROI projections."),
    ],
}

def _try_zero_cost_response(agent_type: str, user_message: str) -> str | None:
    """
    Return a pre-built response for simple/common queries without any LLM call.
    Returns None if no match — caller should proceed to LLM.
    """
    patterns = _ZERO_COST_PATTERNS.get(agent_type, [])
    msg_lower = user_message.lower().strip()
    # Only match very short messages (greetings, help requests)
    if len(user_message) > 120:
        return None
    for keywords, response in patterns:
        if any(kw in msg_lower for kw in keywords):
            return response
    return None


# ── Main run_agent function (with all optimizations) ──────────────

def run_agent(agent_type: str, messages: List[dict], user_id: int = 0) -> dict:
    """
    Optimized agent runner. Applies in order:
    1. Budget check — block if over monthly limit
    2. Zero-cost pattern match — instant response for greetings/help
    3. Context windowing — trim to last 8 turns
    4. Model routing — classify query → haiku or sonnet
    5. LangGraph + prompt caching
    6. Token tracking + cost estimation
    """

    # ── 1. Budget check ────────────────────────────────────────────
    if user_id and _is_over_budget(user_id):
        return {
            "response": "⚠️ You've reached your monthly AI assistant limit. Your limit resets on the 1st of next month. For urgent help, contact support.",
            "tool_calls": [],
            "success": False,
            "model": "blocked",
        }

    # ── 2. Zero-cost response ──────────────────────────────────────
    last_user_msg = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
    )
    zero_cost = _try_zero_cost_response(agent_type, last_user_msg)
    if zero_cost:
        return {
            "response": zero_cost,
            "tool_calls": [],
            "success": True,
            "model": "zero_cost",
            "cache_hit": True,
        }

    # ── 3. Context windowing ───────────────────────────────────────
    trimmed_messages = _trim_history(messages)

    # ── 4. Model routing ───────────────────────────────────────────
    model = _classify_query(last_user_msg)

    # ── 5. LangGraph execution ─────────────────────────────────────
    graph = get_agent(agent_type, model)

    lc_messages = []
    for m in trimmed_messages:
        if m["role"] == "user":
            lc_messages.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            lc_messages.append(AIMessage(content=m["content"]))

    state = {
        "messages": lc_messages,
        "agent_type": agent_type,
        "user_id": user_id,
        "context": {},
    }

    try:
        result = graph.invoke(state)
        last_msg = result["messages"][-1]

        tool_calls_used = []
        for msg in result["messages"]:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_used.append({"tool": tc["name"], "args": tc["args"]})

        response_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        # ── 6. Token tracking ──────────────────────────────────────
        # LangChain's ChatAnthropic returns usage in response_metadata
        input_tokens  = getattr(last_msg, "usage_metadata", {}).get("input_tokens",  0) if hasattr(last_msg, "usage_metadata") else 0
        output_tokens = getattr(last_msg, "usage_metadata", {}).get("output_tokens", 0) if hasattr(last_msg, "usage_metadata") else 0
        cached_tokens = getattr(last_msg, "usage_metadata", {}).get("cache_read_input_tokens", 0) if hasattr(last_msg, "usage_metadata") else 0

        if user_id:
            try:
                _check_and_update_budget(
                    user_id, model, input_tokens, output_tokens, cached_tokens
                )
            except Exception:
                pass   # never block the response due to tracking failure

        return {
            "response": response_text,
            "tool_calls": tool_calls_used,
            "success": True,
            "model": model,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "cached": cached_tokens,
            },
        }

    except Exception as e:
        return {
            "response": f"I encountered an error. Please try again. ({str(e)})",
            "tool_calls": [],
            "success": False,
            "model": model,
        }

