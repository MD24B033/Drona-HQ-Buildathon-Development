"""Outbound channel adapters.

Each adapter turns a drafted message into a real send and returns a
provider message id. Only the simulated adapter is wired up: the email,
LinkedIn and SMS providers need credentials this deployment does not
have yet, so they fail loudly rather than pretending to deliver.

To go live, implement `_send_email` / `_send_linkedin` / `_send_sms`
against your provider's SDK and set CHANNEL_<NAME>_ENABLED=true.
"""

import os
import uuid
from typing import Any


SUPPORTED_CHANNELS = {"email", "linkedin", "sms", "voice"}


class ChannelError(RuntimeError):
    """Raised when a channel cannot deliver a message."""


def simulation_enabled() -> bool:
    """Simulated delivery is the default until providers are configured."""

    return os.getenv("CHANNEL_SIMULATION", "true").lower() != "false"


def channel_enabled(channel: str) -> bool:
    return os.getenv(
        f"CHANNEL_{channel.upper()}_ENABLED",
        "false",
    ).lower() == "true"


def send_message(
    channel: str,
    recipient: dict[str, Any],
    subject: str,
    body: str,
) -> dict[str, Any]:
    """Deliver `body` to `recipient` over `channel`.

    Returns a delivery receipt: the provider's message id, whether the
    send was simulated, and the channel used.
    """

    if channel not in SUPPORTED_CHANNELS:
        raise ChannelError(f"Unsupported channel: {channel}")

    if channel_enabled(channel):
        sender = {
            "email": _send_email,
            "linkedin": _send_linkedin,
            "sms": _send_sms,
            "voice": _send_voice,
        }[channel]

        return sender(recipient, subject, body)

    if not simulation_enabled():
        raise ChannelError(
            f"The {channel} channel is not configured. Set "
            f"CHANNEL_{channel.upper()}_ENABLED=true and provide "
            "provider credentials, or enable CHANNEL_SIMULATION."
        )

    return {
        "channel": channel,
        "channel_message_id": f"sim-{uuid.uuid4()}",
        "simulated": True,
        "recipient": recipient,
    }


# ============================================================
# PROVIDER ADAPTERS
# ============================================================

def _not_configured(channel: str) -> ChannelError:
    return ChannelError(
        f"The {channel} adapter has not been implemented. Add your "
        f"provider integration in core/channels.py."
    )


def _send_email(
    recipient: dict[str, Any],
    subject: str,
    body: str,
) -> dict[str, Any]:
    raise _not_configured("email")


def _send_linkedin(
    recipient: dict[str, Any],
    subject: str,
    body: str,
) -> dict[str, Any]:
    raise _not_configured("linkedin")


def _send_sms(
    recipient: dict[str, Any],
    subject: str,
    body: str,
) -> dict[str, Any]:
    raise _not_configured("sms")


def _send_voice(
    recipient: dict[str, Any],
    subject: str,
    body: str,
) -> dict[str, Any]:
    raise _not_configured("voice")
