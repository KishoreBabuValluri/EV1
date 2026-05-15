"""
ChargeNexus - Database Models
SQLAlchemy ORM models for all stakeholders
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def init_db():
    """Create all tables and seed demo data."""
    db.create_all()
    _seed_demo_data()


# ─────────────────────────────────────────
# USER (shared auth across all roles)
# ─────────────────────────────────────────
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # landowner|oem_sell|oem_setup|operator|driver
    full_name = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(120))
    city = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    # Subscription / plan
    plan = db.Column(db.String(20), default="free")   # free|pro|business
    plan_expires_at = db.Column(db.DateTime, nullable=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "full_name": self.full_name,
            "phone": self.phone,
            "company": self.company,
            "city": self.city,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────
# LAND LISTINGS
# ─────────────────────────────────────────
class LandListing(db.Model):
    __tablename__ = "land_listings"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300))
    city = db.Column(db.String(80))
    state = db.Column(db.String(80))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    area_sqft = db.Column(db.Integer)
    location_type = db.Column(db.String(50))  # highway|mall|office|residential|petrol_station
    monthly_lease = db.Column(db.Float)
    power_availability = db.Column(db.String(100))
    daily_traffic = db.Column(db.Integer)
    description = db.Column(db.Text)
    status = db.Column(db.String(30), default="active")  # active|pending|leased
    ai_score = db.Column(db.Float)  # AI-computed location quality score
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "title": self.title,
            "address": self.address,
            "city": self.city,
            "area_sqft": self.area_sqft,
            "location_type": self.location_type,
            "monthly_lease": self.monthly_lease,
            "power_availability": self.power_availability,
            "daily_traffic": self.daily_traffic,
            "description": self.description,
            "status": self.status,
            "ai_score": self.ai_score,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────
# CHARGER PRODUCTS (OEM Sell)
# ─────────────────────────────────────────
class ChargerProduct(db.Model):
    __tablename__ = "charger_products"
    id = db.Column(db.Integer, primary_key=True)
    oem_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    model_name = db.Column(db.String(120), nullable=False)
    power_kw = db.Column(db.Float)
    charger_type = db.Column(db.String(50))  # dc_fast|ac_fast|ac_slow|ultra_rapid
    connector_standard = db.Column(db.String(100))  # CCS2|CHAdeMO|Type2|Bharat
    unit_price = db.Column(db.Float)
    stock_available = db.Column(db.Integer, default=0)
    warranty_years = db.Column(db.Integer)
    ip_rating = db.Column(db.String(20))
    efficiency_percent = db.Column(db.Float)
    description = db.Column(db.Text)
    status = db.Column(db.String(30), default="active")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "oem_id": self.oem_id,
            "model_name": self.model_name,
            "power_kw": self.power_kw,
            "charger_type": self.charger_type,
            "connector_standard": self.connector_standard,
            "unit_price": self.unit_price,
            "stock_available": self.stock_available,
            "warranty_years": self.warranty_years,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────
# CHARGING STATIONS (Operator)
# ─────────────────────────────────────────
class ChargingStation(db.Model):
    __tablename__ = "charging_stations"
    id = db.Column(db.Integer, primary_key=True)
    operator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    land_listing_id = db.Column(db.Integer, db.ForeignKey("land_listings.id"))
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300))
    city = db.Column(db.String(80))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    total_points = db.Column(db.Integer, default=0)
    available_points = db.Column(db.Integer, default=0)
    price_per_kwh = db.Column(db.Float)
    amenities = db.Column(db.String(300))  # comma-separated
    status = db.Column(db.String(30), default="active")  # active|maintenance|setup
    uptime_percent = db.Column(db.Float, default=99.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "operator_id": self.operator_id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "total_points": self.total_points,
            "available_points": self.available_points,
            "price_per_kwh": self.price_per_kwh,
            "amenities": self.amenities.split(",") if self.amenities else [],
            "status": self.status,
            "uptime_percent": self.uptime_percent,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────
# CHARGER POINTS (individual connectors)
# ─────────────────────────────────────────
class ChargerPoint(db.Model):
    __tablename__ = "charger_points"
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey("charging_stations.id"), nullable=False)
    point_number = db.Column(db.Integer, nullable=False)   # Bay 1, Bay 2 …
    connector_type = db.Column(db.String(50))              # CCS2|CHAdeMO|Type2|Bharat
    power_kw = db.Column(db.Float)
    status = db.Column(db.String(30), default="available") # available|occupied|faulted|offline
    current_session_id = db.Column(db.Integer, db.ForeignKey("charging_sessions.id", use_alter=True, name="fk_point_session"), nullable=True)
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
    fault_code = db.Column(db.String(50))
    total_sessions = db.Column(db.Integer, default=0)
    total_energy_kwh = db.Column(db.Float, default=0.0)
    installed_at = db.Column(db.DateTime, default=datetime.utcnow)

    station = db.relationship("ChargingStation", backref="charger_points")

    def to_dict(self):
        return {
            "id": self.id,
            "station_id": self.station_id,
            "point_number": self.point_number,
            "label": f"Bay {self.point_number}",
            "connector_type": self.connector_type,
            "power_kw": self.power_kw,
            "status": self.status,
            "fault_code": self.fault_code,
            "total_sessions": self.total_sessions,
            "total_energy_kwh": round(self.total_energy_kwh, 1),
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
        }


# ─────────────────────────────────────────
# CHARGING SESSIONS (Driver)
# ─────────────────────────────────────────
class ChargingSession(db.Model):
    __tablename__ = "charging_sessions"
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    station_id = db.Column(db.Integer, db.ForeignKey("charging_stations.id"), nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    energy_kwh = db.Column(db.Float)
    amount_inr = db.Column(db.Float)
    status = db.Column(db.String(30), default="completed")  # active|completed|cancelled
    payment_method = db.Column(db.String(50))

    station = db.relationship("ChargingStation", backref="sessions")

    def to_dict(self):
        return {
            "id": self.id,
            "station_name": self.station.name if self.station else None,
            "station_city": self.station.city if self.station else None,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "energy_kwh": self.energy_kwh,
            "amount_inr": self.amount_inr,
            "status": self.status,
            "duration_min": int((self.end_time - self.start_time).seconds / 60) if self.end_time and self.start_time else None,
        }


# ─────────────────────────────────────────
# LEASE REQUESTS
# ─────────────────────────────────────────
class LeaseRequest(db.Model):
    __tablename__ = "lease_requests"
    id = db.Column(db.Integer, primary_key=True)
    listing_id = db.Column(db.Integer, db.ForeignKey("land_listings.id"), nullable=False)
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    offered_monthly = db.Column(db.Float)
    lease_term_years = db.Column(db.Integer)
    message = db.Column(db.Text)
    status = db.Column(db.String(30), default="pending")  # pending|accepted|rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    listing = db.relationship("LandListing", backref="lease_requests")
    requester = db.relationship("User", backref="lease_requests_made")

    def to_dict(self):
        return {
            "id": self.id,
            "listing_title": self.listing.title if self.listing else None,
            "requester_name": self.requester.full_name if self.requester else None,
            "requester_company": self.requester.company if self.requester else None,
            "offered_monthly": self.offered_monthly,
            "lease_term_years": self.lease_term_years,
            "message": self.message,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────
# ORDERS (OEM Sell)
# ─────────────────────────────────────────
class ChargerOrder(db.Model):
    __tablename__ = "charger_orders"
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("charger_products.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Float)
    status = db.Column(db.String(30), default="confirmed")
    delivery_address = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("ChargerProduct", backref="orders")
    buyer = db.relationship("User", backref="orders")

    def to_dict(self):
        return {
            "id": self.id,
            "product_name": self.product.model_name if self.product else None,
            "buyer_name": self.buyer.full_name if self.buyer else None,
            "buyer_company": self.buyer.company if self.buyer else None,
            "quantity": self.quantity,
            "total_amount": self.total_amount,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────
# DRIVER WALLET
# ─────────────────────────────────────────
class DriverWallet(db.Model):
    __tablename__ = "driver_wallets"
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0.0)
    reward_points = db.Column(db.Integer, default=0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "balance": round(self.balance, 2),
            "reward_points": self.reward_points,
        }


# ─────────────────────────────────────────
# WALLET TRANSACTIONS
# ─────────────────────────────────────────
class WalletTransaction(db.Model):
    __tablename__ = "wallet_transactions"
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    txn_type = db.Column(db.String(20), nullable=False)   # topup|debit|refund
    status = db.Column(db.String(20), default="pending")  # pending|success|failed
    # Razorpay fields
    razorpay_order_id = db.Column(db.String(100), unique=True, nullable=True)
    razorpay_payment_id = db.Column(db.String(100), nullable=True)
    razorpay_signature = db.Column(db.String(200), nullable=True)
    notes = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "type": self.txn_type,
            "status": self.status,
            "razorpay_order_id": self.razorpay_order_id,
            "razorpay_payment_id": self.razorpay_payment_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────
# AI CHAT HISTORY
# ─────────────────────────────────────────
class AgentChatMessage(db.Model):
    __tablename__ = "agent_chat_messages"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.String(64))
    role = db.Column(db.String(20))       # user|assistant
    content = db.Column(db.Text)
    agent_type = db.Column(db.String(50))
    tool_calls = db.Column(db.Text)       # JSON list of tools used
    model_used = db.Column(db.String(50)) # haiku|sonnet — which model answered
    input_tokens = db.Column(db.Integer, default=0)
    output_tokens = db.Column(db.Integer, default=0)
    cache_hit = db.Column(db.Boolean, default=False)   # was this a tool-cache hit?
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
# AGENT USAGE BUDGET
# ─────────────────────────────────────────
class AgentUsage(db.Model):
    """Tracks monthly token usage per user for budget enforcement."""
    __tablename__ = "agent_usage"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    month = db.Column(db.String(7), nullable=False)    # "2024-12"
    input_tokens = db.Column(db.Integer, default=0)
    output_tokens = db.Column(db.Integer, default=0)
    total_calls = db.Column(db.Integer, default=0)
    haiku_calls = db.Column(db.Integer, default=0)
    sonnet_calls = db.Column(db.Integer, default=0)
    cache_hits = db.Column(db.Integer, default=0)
    estimated_cost_usd = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "month", name="uq_user_month"),)

    def to_dict(self):
        return {
            "month": self.month,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_calls": self.total_calls,
            "haiku_calls": self.haiku_calls,
            "sonnet_calls": self.sonnet_calls,
            "cache_hits": self.cache_hits,
            "estimated_cost_usd": round(self.estimated_cost_usd, 4),
        }


# ─────────────────────────────────────────
# CREDIT WALLET (AI credits per user)
# ─────────────────────────────────────────
class CreditWallet(db.Model):
    """
    Each user has one credit wallet.
    Credits are used for LLM (Tier 2) queries.
    NLP (Tier 1) queries are free and tracked separately.
    """
    __tablename__ = "credit_wallets"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    balance = db.Column(db.Integer, default=0)          # credits remaining
    lifetime_earned = db.Column(db.Integer, default=0)  # total ever credited
    lifetime_spent  = db.Column(db.Integer, default=0)  # total ever debited
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref=db.backref("credit_wallet", uselist=False))

    def to_dict(self):
        return {
            "balance": self.balance,
            "lifetime_earned": self.lifetime_earned,
            "lifetime_spent": self.lifetime_spent,
        }


class CreditTransaction(db.Model):
    """Audit trail for every credit debit/credit."""
    __tablename__ = "credit_transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount  = db.Column(db.Integer, nullable=False)         # positive=credit, negative=debit
    txn_type = db.Column(db.String(30), nullable=False)     # purchase|llm_query|refund|promo|subscription_grant
    description = db.Column(db.String(300))
    reference_id = db.Column(db.String(100))               # razorpay order id or session id
    balance_after = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "amount": self.amount,
            "type": self.txn_type,
            "description": self.description,
            "balance_after": self.balance_after,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────
# SUBSCRIPTION PLAN
# ─────────────────────────────────────────
class Subscription(db.Model):
    """Records active and past subscriptions."""
    __tablename__ = "subscriptions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    plan = db.Column(db.String(20), nullable=False)          # pro|business
    started_at  = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at  = db.Column(db.DateTime, nullable=False)
    credits_granted = db.Column(db.Integer, default=0)       # credits given on activation
    price_inr   = db.Column(db.Float)
    razorpay_order_id = db.Column(db.String(100))
    razorpay_payment_id = db.Column(db.String(100))
    status = db.Column(db.String(20), default="active")      # active|expired|cancelled

    def to_dict(self):
        return {
            "id": self.id,
            "plan": self.plan,
            "started_at": self.started_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "credits_granted": self.credits_granted,
            "status": self.status,
        }


# ─────────────────────────────────────────
# NLP USAGE TRACKING (Tier 1)
# ─────────────────────────────────────────
class NlpUsage(db.Model):
    """Tracks free NLP query count per user per day."""
    __tablename__ = "nlp_usage"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    date    = db.Column(db.String(10), nullable=False)   # "2024-12-25"
    count   = db.Column(db.Integer, default=0)

    __table_args__ = (db.UniqueConstraint("user_id", "date", name="uq_nlp_user_date"),)


# ─────────────────────────────────────────
# OCPP CHARGER (physical charger box)
# ─────────────────────────────────────────
class OcppCharger(db.Model):
    """
    Represents a physical charger box that connects via OCPP 1.6.
    One charger box can have multiple connectors (ChargerPoints).
    charger_id is the unique identifier the physical box presents
    at ws://<host>:9000/ocpp/<charger_id>
    """
    __tablename__ = "ocpp_chargers"
    id = db.Column(db.Integer, primary_key=True)
    charger_id = db.Column(db.String(50), unique=True, nullable=False)  # e.g. "CN-HYD-001"
    station_id = db.Column(db.Integer, db.ForeignKey("charging_stations.id"), nullable=False)
    # Populated from BootNotification
    vendor = db.Column(db.String(100))
    model  = db.Column(db.String(100))
    serial_number    = db.Column(db.String(100))
    firmware_version = db.Column(db.String(50))
    iccid = db.Column(db.String(30))
    imsi  = db.Column(db.String(20))
    # Connectivity
    ocpp_status    = db.Column(db.String(20), default="offline")  # online|offline|faulted
    last_heartbeat = db.Column(db.DateTime)
    last_boot      = db.Column(db.DateTime)
    registered_at  = db.Column(db.DateTime, default=datetime.utcnow)
    # Config
    heartbeat_interval = db.Column(db.Integer, default=60)
    notes = db.Column(db.Text)

    station = db.relationship("ChargingStation", backref="ocpp_chargers")

    def to_dict(self):
        return {
            "id": self.id,
            "charger_id": self.charger_id,
            "station_id": self.station_id,
            "station_name": self.station.name if self.station else None,
            "vendor": self.vendor,
            "model": self.model,
            "serial_number": self.serial_number,
            "firmware_version": self.firmware_version,
            "ocpp_status": self.ocpp_status,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "last_boot": self.last_boot.isoformat() if self.last_boot else None,
            "heartbeat_interval": self.heartbeat_interval,
            "notes": self.notes,
        }


# ─────────────────────────────────────────
# METER READINGS
# ─────────────────────────────────────────
class MeterReading(db.Model):
    """Stores sampled meter values from MeterValues OCPP messages."""
    __tablename__ = "meter_readings"
    id = db.Column(db.Integer, primary_key=True)
    charger_id     = db.Column(db.String(50), nullable=False)
    connector_id   = db.Column(db.Integer, nullable=False)
    transaction_id = db.Column(db.Integer, nullable=True)
    measurand      = db.Column(db.String(80))   # Energy.Active.Import.Register | Power.Active.Import | ...
    value          = db.Column(db.Float, nullable=False)
    unit           = db.Column(db.String(20))   # Wh | kWh | W | kW | V | A | Celsius
    context        = db.Column(db.String(40))   # Sample.Periodic | Transaction.Begin | Transaction.End
    recorded_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "charger_id": self.charger_id,
            "connector_id": self.connector_id,
            "transaction_id": self.transaction_id,
            "measurand": self.measurand,
            "value": self.value,
            "unit": self.unit,
            "context": self.context,
            "recorded_at": self.recorded_at.isoformat(),
        }


# ─────────────────────────────────────────
# NOTIFICATIONS (in-app bell)
# ─────────────────────────────────────────
class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text)
    notif_type = db.Column(db.String(40))  # lease_request|lease_accepted|lease_rejected|system
    entity_id = db.Column(db.Integer)      # related record id (lease id, station id …)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "type": self.notif_type,
            "entity_id": self.entity_id,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat(),
        }


def push_notification(user_id: int, title: str, body: str, notif_type: str = "system", entity_id: int = None):
    """Helper called from any route to push a notification to a user."""
    notif = Notification(user_id=user_id, title=title, body=body, notif_type=notif_type, entity_id=entity_id)
    db.session.add(notif)
    # Don't commit here — caller's transaction handles it


# ─────────────────────────────────────────
# SEED DATA
# ─────────────────────────────────────────
def _seed_demo_data():
    if User.query.count() > 0:
        return  # Already seeded

    # Demo users for each role
    users = [
        User(email="landowner@demo.com", role="landowner", full_name="Ramesh Kumar", phone="9876543210", city="Hyderabad"),
        User(email="oemsell@demo.com", role="oem_sell", full_name="Priya Sharma", company="ChargePoint India", phone="9876543211", city="Bengaluru"),
        User(email="oemsetup@demo.com", role="oem_setup", full_name="Anil Verma", company="EVolt Stations", phone="9876543212", city="Hyderabad"),
        User(email="operator@demo.com", role="operator", full_name="Suresh Reddy", company="GreenCharge Ops", phone="9876543213", city="Hyderabad"),
        User(email="driver@demo.com", role="driver", full_name="Kavitha Nair", phone="9876543214", city="Hyderabad"),
    ]
    for u in users:
        u.set_password("demo1234")
    db.session.add_all(users)
    db.session.flush()

    # Land listings
    listings = [
        LandListing(owner_id=users[0].id, title="NH-44 Warangal Highway Plot", address="NH-44, KM 203, Warangal", city="Warangal", state="Telangana", latitude=17.9784, longitude=79.5941, area_sqft=5000, location_type="highway", monthly_lease=95000, power_availability="3-phase 100kVA", daily_traffic=30000, status="active", ai_score=92.4),
        LandListing(owner_id=users[0].id, title="Phoenix Mall Parking Annex", address="Whitefield Road, Hitech City", city="Hyderabad", state="Telangana", latitude=17.4445, longitude=78.3772, area_sqft=2800, location_type="mall", monthly_lease=110000, power_availability="3-phase 60kVA", daily_traffic=8000, status="active", ai_score=88.7),
        LandListing(owner_id=users[0].id, title="HITEC City ORR Plot", address="Outer Ring Road, HITEC City", city="Hyderabad", state="Telangana", latitude=17.4399, longitude=78.3807, area_sqft=8000, location_type="office", monthly_lease=88000, power_availability="3-phase 200kVA", daily_traffic=15000, status="pending", ai_score=85.3),
    ]
    db.session.add_all(listings)
    db.session.flush()

    # Charger products
    products = [
        ChargerProduct(oem_id=users[1].id, model_name="AC Fast Charger Type-2", power_kw=22, charger_type="ac_fast", connector_standard="Type-2 AC", unit_price=120000, stock_available=50, warranty_years=3, status="active"),
        ChargerProduct(oem_id=users[1].id, model_name="DC Fast Charger CCS2", power_kw=60, charger_type="dc_fast", connector_standard="CCS2", unit_price=480000, stock_available=20, warranty_years=3, status="active"),
        ChargerProduct(oem_id=users[1].id, model_name="Ultra DC CCS2+CHAdeMO", power_kw=150, charger_type="ultra_rapid", connector_standard="CCS2,CHAdeMO", unit_price=1250000, stock_available=5, warranty_years=5, status="active"),
        ChargerProduct(oem_id=users[1].id, model_name="Home AC Smart Charger", power_kw=7.2, charger_type="ac_slow", connector_standard="Type-2 AC", unit_price=38000, stock_available=200, warranty_years=2, status="active"),
    ]
    db.session.add_all(products)
    db.session.flush()

    # Charging stations
    import random
    random.seed(42)
    stations = [
        ChargingStation(operator_id=users[3].id, land_listing_id=listings[0].id, name="GreenCharge @ NH-44 Warangal", address="NH-44, KM 203", city="Warangal", latitude=17.9784, longitude=79.5941, total_points=4, available_points=3, price_per_kwh=38, amenities="restroom,cafe,wifi", status="active", uptime_percent=97.2),
        ChargingStation(operator_id=users[3].id, land_listing_id=listings[1].id, name="GreenCharge @ Gachibowli", address="Gachibowli, Hyderabad", city="Hyderabad", latitude=17.4401, longitude=78.3489, total_points=6, available_points=5, price_per_kwh=42, amenities="restroom,cafe,shopping,wifi", status="active", uptime_percent=99.1),
        ChargingStation(operator_id=users[3].id, name="GreenCharge @ Hitech City", address="HITEC City, Hyderabad", city="Hyderabad", latitude=17.4444, longitude=78.3772, total_points=8, available_points=6, price_per_kwh=42, amenities="restroom,wifi,parking", status="active", uptime_percent=91.5),
    ]
    db.session.add_all(stations)
    db.session.flush()

    # ChargerPoints — one per bay, realistic connector mix
    station_configs = [
        # Station 0: 4-bay highway — 2×DC60, 2×DC150
        [(1,"CCS2",60,"available"),(2,"CHAdeMO",60,"occupied"),(3,"CCS2",150,"available"),(4,"CCS2",150,"available")],
        # Station 1: 6-bay mall — 4×AC22, 2×DC60
        [(1,"Type-2 AC",22,"available"),(2,"Type-2 AC",22,"occupied"),(3,"Type-2 AC",22,"available"),(4,"Type-2 AC",22,"available"),(5,"CCS2",60,"available"),(6,"CCS2",60,"occupied")],
        # Station 2: 8-bay IT corridor — 4×AC22, 3×DC60, 1×faulted
        [(1,"Type-2 AC",22,"available"),(2,"Type-2 AC",22,"available"),(3,"Type-2 AC",22,"occupied"),(4,"Type-2 AC",22,"available"),(5,"CCS2",60,"available"),(6,"CCS2",60,"occupied"),(7,"CCS2",60,"available"),(8,"CCS2",60,"faulted")],
    ]
    all_points = []
    for s_idx, config in enumerate(station_configs):
        for num, ctype, pkw, status in config:
            fault = "ConnectorLockFailure" if status == "faulted" else None
            total_s = random.randint(120, 800)
            total_e = round(total_s * random.uniform(28, 55), 1)
            p = ChargerPoint(
                station_id=stations[s_idx].id, point_number=num,
                connector_type=ctype, power_kw=pkw, status=status,
                fault_code=fault, total_sessions=total_s, total_energy_kwh=total_e,
            )
            all_points.append(p)
    db.session.add_all(all_points)

    # Register OCPP charger boxes (one per station for demo)
    ocpp_chargers = [
        OcppCharger(charger_id="CN-WGL-001", station_id=stations[0].id,
                    notes="NH-44 Warangal DC fast charger box 1"),
        OcppCharger(charger_id="CN-HYD-001", station_id=stations[1].id,
                    notes="Gachibowli station charger box 1"),
        OcppCharger(charger_id="CN-HYD-002", station_id=stations[1].id,
                    notes="Gachibowli station charger box 2"),
        OcppCharger(charger_id="CN-HYD-003", station_id=stations[2].id,
                    notes="Hitech City charger box 1"),
    ]
    db.session.add_all(ocpp_chargers)

    # Charging sessions — 30 days of history for revenue charts
    from datetime import timedelta
    now = datetime.utcnow()
    sessions = []
    payment_methods = ["UPI", "Wallet", "Card", "NetBanking"]
    # Realistic daily volume per station: grow slightly over 30 days
    for day in range(30, 0, -1):
        t = now - timedelta(days=day)
        growth = 1 + (30 - day) * 0.01   # 1% daily growth
        for s_idx, station in enumerate(stations):
            base_sessions = [5, 8, 11][s_idx]
            n = max(1, int(base_sessions * growth * random.uniform(0.7, 1.3)))
            for _ in range(n):
                hour_offset = random.randint(0, 22)
                start = t.replace(hour=hour_offset, minute=random.randint(0, 59))
                energy = round(random.uniform(15, 65), 1)
                duration_min = int(energy / station.price_per_kwh * 60 * random.uniform(0.8, 1.2))
                end = start + timedelta(minutes=max(20, duration_min))
                sessions.append(ChargingSession(
                    driver_id=users[4].id, station_id=station.id,
                    start_time=start, end_time=end,
                    energy_kwh=energy,
                    amount_inr=round(energy * station.price_per_kwh, 2),
                    status="completed",
                    payment_method=random.choice(payment_methods),
                ))
    db.session.add_all(sessions)

    # Driver wallet
    wallet = DriverWallet(driver_id=users[4].id, balance=4280, reward_points=1240)
    db.session.add(wallet)

    # Lease requests
    lease_reqs = [
        LeaseRequest(listing_id=listings[0].id, requester_id=users[2].id, offered_monthly=95000, lease_term_years=5, message="We plan to install 4×60kW DC fast chargers with immediate setup.", status="pending"),
        LeaseRequest(listing_id=listings[1].id, requester_id=users[3].id, offered_monthly=110000, lease_term_years=3, message="GreenCharge Ops would like to operate a premium charging hub here.", status="pending"),
    ]
    db.session.add_all(lease_reqs)
    db.session.commit()
