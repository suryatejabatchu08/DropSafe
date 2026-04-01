"""
DropSafe WhatsApp Service
Wrapper for sending WhatsApp messages
"""

from utils.whatsapp_helpers import send_whatsapp_message


class WhatsAppService:
    """Service for sending WhatsApp messages to workers."""

    @staticmethod
    async def send_message(phone_number: str, message: str) -> bool:
        """
        Send WhatsApp message to worker.

        Args:
            phone_number: Worker phone number (without +91)
            message: Message text (supports markdown-like formatting with * and _)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not phone_number:
                print(f"[WARNING] Cannot send WhatsApp: phone_number is None")
                return False

            result = send_whatsapp_message(phone_number, message)
            return result
        except Exception as e:
            print(f"[WARNING] Failed to send WhatsApp message: {e}")
            return False
