"""
OCPP 1.6 message types, action names, and status enums.
Reference: https://www.openchargealliance.org/protocols/ocpp-16/
"""

from enum import Enum


# ── OCPP message type IDs ─────────────────────────────────────────────────────
class MsgType(int, Enum):
    CALL        = 2   # Central System → Charge Point (request)
    CALLRESULT  = 3   # Charge Point → Central System (response)
    CALLERROR   = 4   # Error response


# ── Actions (message names) ───────────────────────────────────────────────────
# Charge Point → Central System (incoming)
class CPAction(str, Enum):
    BOOT_NOTIFICATION    = "BootNotification"
    HEARTBEAT            = "Heartbeat"
    STATUS_NOTIFICATION  = "StatusNotification"
    START_TRANSACTION    = "StartTransaction"
    STOP_TRANSACTION     = "StopTransaction"
    METER_VALUES         = "MeterValues"
    AUTHORIZE            = "Authorize"
    DATA_TRANSFER        = "DataTransfer"
    FIRMWARE_STATUS      = "FirmwareStatusNotification"
    DIAGNOSTICS_STATUS   = "DiagnosticsStatusNotification"

# Central System → Charge Point (outgoing commands)
class CSAction(str, Enum):
    REMOTE_START         = "RemoteStartTransaction"
    REMOTE_STOP          = "RemoteStopTransaction"
    CHANGE_AVAILABILITY  = "ChangeAvailability"
    RESET                = "Reset"
    GET_CONFIGURATION    = "GetConfiguration"
    CHANGE_CONFIGURATION = "ChangeConfiguration"
    UNLOCK_CONNECTOR     = "UnlockConnector"
    CLEAR_CACHE          = "ClearCache"
    TRIGGER_MESSAGE      = "TriggerMessage"


# ── Status enums ──────────────────────────────────────────────────────────────
class ChargePointStatus(str, Enum):
    AVAILABLE     = "Available"
    PREPARING     = "Preparing"
    CHARGING      = "Charging"
    SUSPENDED_EV  = "SuspendedEV"
    SUSPENDED_EVSE = "SuspendedEVSE"
    FINISHING     = "Finishing"
    RESERVED      = "Reserved"
    UNAVAILABLE   = "Unavailable"
    FAULTED       = "Faulted"

class ChargePointErrorCode(str, Enum):
    CONNECTOR_LOCK_FAILURE = "ConnectorLockFailure"
    EV_COMMUNICATION_ERROR = "EVCommunicationError"
    GROUND_FAILURE         = "GroundFailure"
    HIGH_TEMPERATURE       = "HighTemperature"
    INTERNAL_ERROR         = "InternalError"
    LOCAL_LIST_CONFLICT    = "LocalListConflict"
    NO_ERROR               = "NoError"
    OTHER_ERROR            = "OtherError"
    OVER_CURRENT_FAILURE   = "OverCurrentFailure"
    OVER_VOLTAGE           = "OverVoltage"
    POWER_METER_FAILURE    = "PowerMeterFailure"
    POWER_SWITCH_FAILURE   = "PowerSwitchFailure"
    READER_FAILURE         = "ReaderFailure"
    RESET_FAILURE          = "ResetFailure"
    UNDER_VOLTAGE          = "UnderVoltage"
    WEAK_SIGNAL            = "WeakSignal"

class RegistrationStatus(str, Enum):
    ACCEPTED = "Accepted"
    PENDING  = "Pending"
    REJECTED = "Rejected"

class AuthorizationStatus(str, Enum):
    ACCEPTED    = "Accepted"
    BLOCKED     = "Blocked"
    EXPIRED     = "Expired"
    INVALID     = "Invalid"
    CONCURRENT  = "ConcurrentTx"

class AvailabilityType(str, Enum):
    INOPERATIVE = "Inoperative"
    OPERATIVE   = "Operative"

class AvailabilityStatus(str, Enum):
    ACCEPTED  = "Accepted"
    REJECTED  = "Rejected"
    SCHEDULED = "Scheduled"

class ResetType(str, Enum):
    HARD = "Hard"
    SOFT = "Soft"

class ResetStatus(str, Enum):
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"

class RemoteStartStopStatus(str, Enum):
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"

class Reason(str, Enum):
    DE_AUTHORIZED     = "DeAuthorized"
    EMERGENCY_STOP    = "EmergencyStop"
    EV_DISCONNECTED   = "EVDisconnected"
    HARD_RESET        = "HardReset"
    LOCAL             = "Local"
    OTHER             = "Other"
    POWER_LOSS        = "PowerLoss"
    REBOOT            = "Reboot"
    REMOTE            = "Remote"
    SOFT_RESET        = "SoftReset"
    UNLOCK_COMMAND    = "UnlockCommand"


# ── Map OCPP charger status → internal ChargerPoint status ───────────────────
OCPP_STATUS_MAP: dict[str, str] = {
    ChargePointStatus.AVAILABLE:      "available",
    ChargePointStatus.PREPARING:      "preparing",
    ChargePointStatus.CHARGING:       "occupied",
    ChargePointStatus.SUSPENDED_EV:   "occupied",
    ChargePointStatus.SUSPENDED_EVSE: "occupied",
    ChargePointStatus.FINISHING:      "finishing",
    ChargePointStatus.RESERVED:       "reserved",
    ChargePointStatus.UNAVAILABLE:    "offline",
    ChargePointStatus.FAULTED:        "faulted",
}

# Statuses that count as "available" for bay-count purposes
AVAILABLE_STATUSES = {"available"}
# Statuses that count as "occupied"
OCCUPIED_STATUSES  = {"occupied", "preparing", "finishing", "reserved"}
# Statuses that count as "faulted/offline"
PROBLEM_STATUSES   = {"faulted", "offline"}
