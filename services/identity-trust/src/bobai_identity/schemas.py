"""Pydantic schemas: the auth/session event in, the risk decision out."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """The kind of action being risk-assessed. Sensitivity rises down the list."""

    LOGIN = "login"
    ACCOUNT_OPENING = "account_opening"  # new-customer signup
    TRANSACTION = "transaction"
    BENEFICIARY_ADD = "beneficiary_add"
    PROFILE_CHANGE = "profile_change"
    ACCOUNT_RECOVERY = "account_recovery"
    PRIVILEGE_CHANGE = "privilege_change"  # insider / admin action
    KYC_SUBMISSION = "kyc_submission"


class Channel(str, Enum):
    WEB = "web"
    MOBILE = "mobile"
    API = "api"
    BRANCH = "branch"
    IVR = "ivr"


class GeoPoint(BaseModel):
    """A consent-captured location (browser geolocation) or IP-derived estimate."""

    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    source: str = "client"  # "client" (browser, with consent) | "ip" (enrichment)


class BehavioralSignal(BaseModel):
    """Passively-collected behavioral biometrics for the current session.

    All values are derived client-side; raw keystroke/mouse streams never leave the
    device — only these aggregate features do (data minimisation / privacy-first).
    """

    typing_speed_cpm: float | None = Field(default=None, ge=0)  # chars per minute
    avg_dwell_ms: float | None = Field(default=None, ge=0)  # key hold time
    avg_flight_ms: float | None = Field(default=None, ge=0)  # inter-key time
    mouse_velocity: float | None = Field(default=None, ge=0)  # px/s
    paste_ratio: float | None = Field(default=None, ge=0, le=1)  # fraction pasted vs typed


class AuthEvent(BaseModel):
    """A single risk-assessable event from any channel."""

    user_id: str
    event_type: EventType = EventType.LOGIN
    channel: Channel = Channel.WEB
    # Epoch seconds. Provided by caller so the engine is deterministic and testable.
    timestamp: float
    ip: str | None = None
    device_fingerprint: str | None = None
    user_agent: str | None = None
    geo: GeoPoint | None = None
    behavioral: BehavioralSignal | None = None
    amount: float | None = Field(default=None, ge=0)  # for TRANSACTION events
    # Authentication factors already satisfied this session (e.g. ["password"]).
    satisfied_factors: list[str] = Field(default_factory=list)
    # IP/network hints the caller may pre-compute (optional).
    is_tor: bool = False
    is_datacenter: bool = False


class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAction(str, Enum):
    ALLOW = "allow"
    MONITOR = "monitor"  # allow but flag for review
    STEP_UP = "step_up"  # require passkey/WebAuthn challenge
    DENY = "deny"


class AAL(str, Enum):
    """NIST SP 800-63B Authentication Assurance Levels required to proceed."""

    AAL1 = "AAL1"
    AAL2 = "AAL2"
    AAL3 = "AAL3"


class SignalContribution(BaseModel):
    """One detector's contribution to the overall risk score (fully auditable)."""

    name: str
    weight: float  # detector weight in the blend
    raw: float = Field(ge=0, le=1)  # detector's own 0..1 risk output
    contribution: float  # weight * raw, normalised share of final score
    detail: str  # plain-English explanation (the reason-code source)
    data: dict = Field(default_factory=dict)  # supporting evidence


class RiskDecision(BaseModel):
    """The engine's verdict for an event — explainable and policy-mapped."""

    decision_id: str
    user_id: str
    event_type: EventType
    timestamp: float
    risk_score: float = Field(ge=0, le=1)
    band: RiskBand
    action: RiskAction
    required_aal: AAL
    reason_codes: list[str]
    signals: list[SignalContribution]
    # Why this policy action, in regulatory terms.
    policy_rationale: str
