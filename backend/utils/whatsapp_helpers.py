"""
DropSafe WhatsApp Helper Functions
Utilities for WhatsApp bot operations, premium calculation, and messaging
"""

import os
import hashlib
from datetime import datetime
from typing import Optional
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Twilio configuration
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Initialize Twilio client
twilio_client: Optional[Client] = None


def get_twilio_client() -> Client:
    """Get or initialize Twilio client."""
    global twilio_client
    if twilio_client is None:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            raise ValueError("Missing Twilio credentials in environment variables")
        twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        print("[OK] Twilio client initialized")
    return twilio_client


def send_whatsapp_message(to: str, body: str) -> bool:
    """
    Send a WhatsApp message via Twilio.

    Args:
        to: Recipient phone number (e.g., "whatsapp:+919876543210")
        body: Message text to send

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        client = get_twilio_client()

        # Ensure 'to' has whatsapp: prefix
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"

        message = client.messages.create(from_=TWILIO_WHATSAPP_NUMBER, body=body, to=to)

        print(f"[OK] WhatsApp message sent to {to}: {message.sid}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send WhatsApp message to {to}: {e}")
        return False


def hash_phone(phone: str) -> str:
    """
    Create SHA-256 hash of phone number for privacy.

    Args:
        phone: Phone number (with or without whatsapp: prefix)

    Returns:
        SHA-256 hash as hexadecimal string
    """
    # Remove whatsapp: prefix if present
    clean_phone = phone.replace("whatsapp:", "").strip()

    # Create SHA-256 hash
    phone_hash = hashlib.sha256(clean_phone.encode()).hexdigest()
    return phone_hash


def calculate_premium(
    zone_risk: float, declared_hours: int, season: str = None
) -> float:
    """
    Calculate weekly insurance premium.

    Formula: base_rate(38) × zone_risk × (hours/40) × seasonal_index

    Args:
        zone_risk: Zone risk multiplier (e.g., 1.15)
        declared_hours: Weekly working hours (e.g., 42)
        season: Optional season override (monsoon, aqi_season, normal)

    Returns:
        Weekly premium amount in INR
    """
    base_rate = 38.0
    hours_ratio = declared_hours / 40.0

    # Get seasonal index
    if season:
        seasonal_index = get_seasonal_index(season)
    else:
        seasonal_index = get_seasonal_index()

    premium = base_rate * zone_risk * hours_ratio * seasonal_index
    return round(premium, 2)


def get_seasonal_index(season: str = None) -> float:
    """
    Get seasonal risk multiplier based on current month or provided season.

    Seasons in India:
    - Monsoon (June-Sep): 1.35 (highest risk - floods, waterlogging)
    - Post-monsoon (Oct-Nov): 1.30 (AQI issues in North India)
    - Winter/Summer (Dec-May): 1.0 (normal)

    Args:
        season: Optional season override ("monsoon", "aqi_season", "normal")

    Returns:
        Seasonal multiplier (1.0, 1.30, or 1.35)
    """
    if season:
        seasonal_map = {"monsoon": 1.35, "aqi_season": 1.30, "normal": 1.0}
        return seasonal_map.get(season, 1.0)

    # Auto-detect based on current month
    current_month = datetime.now().month

    if 6 <= current_month <= 9:  # June to September - Monsoon
        return 1.35
    elif 10 <= current_month <= 11:  # October to November - AQI season
        return 1.30
    else:  # December to May - Normal
        return 1.0


def get_current_season() -> str:
    """
    Get current season name based on month.

    Returns:
        Season name: "monsoon", "aqi_season", or "normal"
    """
    current_month = datetime.now().month

    if 6 <= current_month <= 9:
        return "monsoon"
    elif 10 <= current_month <= 11:
        return "aqi_season"
    else:
        return "normal"


def calculate_coverage_cap(
    zone_risk: float, declared_hours: int, avg_hourly_income: float
) -> float:
    """
    Calculate maximum coverage amount for a policy.

    Typically: weekly_expected_income × zone_risk × 1.2 (buffer)

    Args:
        zone_risk: Zone risk multiplier
        declared_hours: Weekly working hours
        avg_hourly_income: Average hourly income (INR)

    Returns:
        Coverage cap in INR
    """
    weekly_expected_income = declared_hours * avg_hourly_income
    coverage_cap = weekly_expected_income * zone_risk * 1.2
    return round(coverage_cap, 2)


def format_phone_for_whatsapp(phone: str) -> str:
    """
    Format phone number for WhatsApp (add whatsapp: prefix if missing).

    Args:
        phone: Phone number (e.g., "+919876543210" or "whatsapp:+919876543210")

    Returns:
        Formatted phone with whatsapp: prefix
    """
    if phone.startswith("whatsapp:"):
        return phone
    return f"whatsapp:{phone}"


def extract_phone_from_whatsapp(whatsapp_address: str) -> str:
    """
    Extract clean phone number from WhatsApp address.

    Args:
        whatsapp_address: Full WhatsApp address (e.g., "whatsapp:+919876543210")

    Returns:
        Clean phone number (e.g., "+919876543210")
    """
    return whatsapp_address.replace("whatsapp:", "").strip()


def validate_pincode(pincode: str) -> bool:
    """
    Validate Indian PIN code format (6 digits).

    Args:
        pincode: PIN code to validate

    Returns:
        True if valid, False otherwise
    """
    return pincode.isdigit() and len(pincode) == 6


def validate_upi_id(upi_id: str) -> bool:
    """
    Basic validation for UPI ID format.

    Valid formats:
    - phone@provider (9876543210@paytm)
    - username@provider (user.name@oksbi)

    Args:
        upi_id: UPI ID to validate

    Returns:
        True if valid format, False otherwise
    """
    if "@" not in upi_id:
        return False

    parts = upi_id.split("@")
    if len(parts) != 2:
        return False

    username, provider = parts
    if not username or not provider:
        return False

    # Basic validation: username exists, provider has reasonable length
    return len(username) >= 3 and len(provider) >= 3
