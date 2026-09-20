"""Conversation Agent.

Owns the live thread with a prospect:

- opens a conversation and sends the Personalization Agent's draft
- records every inbound and outbound message
- classifies intent, sentiment and the next action after each reply
- drafts the reply, and escalates to a human when the campaign's
  approval rules say it should

Actual delivery goes through `core.channels`, which simulates sends
until real provider credentials are configured.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from agents.personalization_agent.agent import PersonalizationAgent
from core.channels import send_message
from core.config import model_for
from core.gemini import generate_json
from core.runs import record_event
from db.supabase_client import supabase
from rag.retrieval import format_knowledge_context, retrieve_knowledge


# `conversations.status` has a CHECK constraint in the database that
# allows exactly these four values. Finer-grained thread state lives in
# `next_action`, which is free text.
VALID_STATUSES = {
    "active",
    "paused",
    "escalated",
    "closed",
}

VALID_INTENTS = {
    "interested",
    "not_interested",
    "question",
    "objection",
    "meeting_request",
    "referral",
    "unsubscribe",
    "out_of_office",
    "unclear",
}

VALID_SENTIMENTS = {"positive", "neutral", "negative"}

VALID_NEXT_ACTIONS = {
    "send_reply",
    "wait",
    "follow_up",
    "escalate_to_human",
    "book_meeting",
    "stop",
}


class ConversationAgent:

    agent_type = "conversation"

    def __init__(self, system_prompt: str | None = None):
        self.model = model_for("conversation")
        self.system_prompt = system_prompt

    # ========================================================
    # OUTBOUND
    # ========================================================

    async def start_outreach(
        self,
        prospect_id: str,
        campaign_id: str,
        icp_id: str | None = None,
        channel: str | None = None,
    ) -> dict[str, Any]:
        """Draft and send the first message to a prospect."""

        prospect = await asyncio.to_thread(
            self._get_prospect,
            prospect_id,
        )

        strategy = await asyncio.to_thread(
            self._get_strategy,
            prospect_id,
            campaign_id,
        )

        if strategy and strategy.get("should_contact") is False:
            return {
                "success": False,
                "agent": self.agent_type,
                "prospect_id": prospect_id,
                "campaign_id": campaign_id,
                "skipped": True,
                "reason": (
                    strategy.get("strategy_reason")
                    or "The outreach strategy marked this prospect as "
                    "do-not-contact."
                ),
            }

        draft = await PersonalizationAgent().run(
            prospect_id=prospect_id,
            icp_id=icp_id,
            campaign_id=campaign_id,
        )

        personalization = draft["personalization"]

        resolved_channel = (
            channel
            or personalization.get("channel")
            or (strategy or {}).get("primary_channel")
            or "email"
        )

        conversation = await asyncio.to_thread(
            self._get_or_create_conversation,
            prospect_id,
            campaign_id,
            resolved_channel,
        )

        receipt = await asyncio.to_thread(
            send_message,
            resolved_channel,
            {
                "prospect_id": prospect_id,
                "full_name": prospect.get("full_name"),
                "linkedin_url": prospect.get("linkedin_url"),
            },
            personalization.get("subject", ""),
            personalization["message"],
        )

        message = await asyncio.to_thread(
            self._record_message,
            conversation["id"],
            "outbound",
            "agent",
            personalization["message"],
            receipt.get("channel_message_id"),
            {
                "subject": personalization.get("subject"),
                "personalization_angle": personalization.get(
                    "personalization_angle"
                ),
                "call_to_action": personalization.get("call_to_action"),
                "simulated": receipt.get("simulated", False),
                "agent": self.agent_type,
            },
        )

        await asyncio.to_thread(
            self._update_conversation,
            conversation["id"],
            {
                "status": "active",
                "next_action": "wait",
                "assigned_agent": self.agent_type,
            },
        )

        await asyncio.to_thread(
            record_event,
            campaign_id,
            "message_sent",
            "completed",
            {
                "conversation_id": conversation["id"],
                "message_id": message["id"],
                "subject": personalization.get("subject"),
                "simulated": receipt.get("simulated", False),
            },
            prospect_id,
            self.agent_type,
            resolved_channel,
        )

        return {
            "success": True,
            "agent": self.agent_type,
            "prospect_id": prospect_id,
            "campaign_id": campaign_id,
            "conversation_id": conversation["id"],
            "channel": resolved_channel,
            "simulated": receipt.get("simulated", False),
            "personalization": personalization,
            "message": message,
        }

    # ========================================================
    # INBOUND
    # ========================================================

    async def handle_reply(
        self,
        conversation_id: str,
        content: str,
        channel_message_id: str | None = None,
    ) -> dict[str, Any]:
        """Record a prospect reply, classify it and decide what is next."""

        conversation = await asyncio.to_thread(
            self._get_conversation,
            conversation_id,
        )

        await asyncio.to_thread(
            self._record_message,
            conversation_id,
            "inbound",
            "prospect",
            content,
            channel_message_id,
            {},
        )

        context = await asyncio.to_thread(
            self._load_context,
            conversation,
        )

        rag_chunks = await retrieve_knowledge(
            campaign_id=conversation["campaign_id"],
            query=(
                f"{context['campaign'].get('objective', '')}\n"
                f"Latest prospect reply: {content}"
            ),
        )

        analysis = self._normalize_analysis(
            await generate_json(
                model=self.model,
                prompt=self._build_prompt(
                    context=context,
                    rag_context=format_knowledge_context(rag_chunks),
                ),
                system_instruction=self.system_prompt,
            )
        )

        reply_message = None

        if (
            analysis["next_action"] == "send_reply"
            and analysis["reply"]
            and not analysis["requires_human_approval"]
        ):
            receipt = await asyncio.to_thread(
                send_message,
                conversation["channel"],
                {
                    "prospect_id": conversation["prospect_id"],
                    "full_name": context["prospect"].get("full_name"),
                    "linkedin_url": context["prospect"].get(
                        "linkedin_url"
                    ),
                },
                "",
                analysis["reply"],
            )

            reply_message = await asyncio.to_thread(
                self._record_message,
                conversation_id,
                "outbound",
                "agent",
                analysis["reply"],
                receipt.get("channel_message_id"),
                {
                    "simulated": receipt.get("simulated", False),
                    "agent": self.agent_type,
                    "in_response_to_intent": analysis["intent"],
                },
            )

            await asyncio.to_thread(
                record_event,
                conversation["campaign_id"],
                "message_sent",
                "completed",
                {
                    "conversation_id": conversation_id,
                    "message_id": reply_message["id"],
                    "simulated": receipt.get("simulated", False),
                },
                conversation["prospect_id"],
                self.agent_type,
                conversation["channel"],
            )

        status = analysis["status"]

        if analysis["requires_human_approval"]:
            status = "escalated"

        updated = await asyncio.to_thread(
            self._update_conversation,
            conversation_id,
            {
                "status": status,
                "intent": analysis["intent"],
                "sentiment": analysis["sentiment"],
                "next_action": analysis["next_action"],
                "assigned_agent": (
                    "human"
                    if analysis["requires_human_approval"]
                    else self.agent_type
                ),
            },
        )

        await asyncio.to_thread(
            record_event,
            conversation["campaign_id"],
            "reply_received",
            "completed",
            {
                "conversation_id": conversation_id,
                "intent": analysis["intent"],
                "sentiment": analysis["sentiment"],
                "next_action": analysis["next_action"],
            },
            conversation["prospect_id"],
            self.agent_type,
            conversation["channel"],
        )

        return {
            "success": True,
            "agent": self.agent_type,
            "conversation_id": conversation_id,
            "campaign_id": conversation["campaign_id"],
            "prospect_id": conversation["prospect_id"],
            "analysis": analysis,
            "conversation": updated,
            "reply_sent": reply_message is not None,
            "reply_message": reply_message,
            "rag_chunks_used": len(rag_chunks),
        }

    # ========================================================
    # DATA ACCESS
    # ========================================================

    def _get_prospect(self, prospect_id: str) -> dict[str, Any]:

        response = (
            supabase
            .table("prospects")
            .select("*")
            .eq("id", prospect_id)
            .maybe_single()
            .execute()
        )

        if not response or not response.data:
            raise ValueError("Prospect not found")

        return response.data

    def _get_strategy(
        self,
        prospect_id: str,
        campaign_id: str,
    ) -> dict[str, Any] | None:

        response = (
            supabase
            .table("outreach_strategies")
            .select("*")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .maybe_single()
            .execute()
        )

        return response.data if response else None

    def _get_conversation(self, conversation_id: str) -> dict[str, Any]:

        response = (
            supabase
            .table("conversations")
            .select("*")
            .eq("id", conversation_id)
            .maybe_single()
            .execute()
        )

        if not response or not response.data:
            raise ValueError("Conversation not found")

        return response.data

    def _get_or_create_conversation(
        self,
        prospect_id: str,
        campaign_id: str,
        channel: str,
    ) -> dict[str, Any]:

        existing = (
            supabase
            .table("conversations")
            .select("*")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .eq("channel", channel)
            .limit(1)
            .execute()
        )

        if existing.data:
            return existing.data[0]

        created = (
            supabase
            .table("conversations")
            .insert(
                {
                    "prospect_id": prospect_id,
                    "campaign_id": campaign_id,
                    "channel": channel,
                    "status": "active",
                    "assigned_agent": self.agent_type,
                }
            )
            .execute()
        )

        if not created.data:
            raise RuntimeError("Failed to create conversation")

        return created.data[0]

    def _record_message(
        self,
        conversation_id: str,
        direction: str,
        sender_type: str,
        content: str,
        channel_message_id: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:

        response = (
            supabase
            .table("conversation_messages")
            .insert(
                {
                    "conversation_id": conversation_id,
                    "direction": direction,
                    "sender_type": sender_type,
                    "content": content,
                    "channel_message_id": channel_message_id,
                    "metadata": metadata,
                }
            )
            .execute()
        )

        if not response.data:
            raise RuntimeError("Failed to record conversation message")

        return response.data[0]

    def _update_conversation(
        self,
        conversation_id: str,
        fields: dict[str, Any],
    ) -> dict[str, Any]:

        response = (
            supabase
            .table("conversations")
            .update(
                {
                    **fields,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            .eq("id", conversation_id)
            .execute()
        )

        return response.data[0] if response.data else {}

    def _load_context(
        self,
        conversation: dict[str, Any],
    ) -> dict[str, Any]:

        campaign_id = conversation["campaign_id"]
        prospect_id = conversation["prospect_id"]

        campaign = (
            supabase
            .table("campaigns")
            .select("*")
            .eq("id", campaign_id)
            .maybe_single()
            .execute()
        )

        if not campaign or not campaign.data:
            raise ValueError("Campaign not found")

        prospect = (
            supabase
            .table("prospects")
            .select("*")
            .eq("id", prospect_id)
            .maybe_single()
            .execute()
        )

        if not prospect or not prospect.data:
            raise ValueError("Prospect not found")

        research = (
            supabase
            .table("prospect_research")
            .select("*")
            .eq("prospect_id", prospect_id)
            .eq("campaign_id", campaign_id)
            .maybe_single()
            .execute()
        )

        messages = (
            supabase
            .table("conversation_messages")
            .select("*")
            .eq("conversation_id", conversation["id"])
            .order("created_at", desc=False)
            .execute()
        )

        return {
            "conversation": conversation,
            "campaign": campaign.data,
            "prospect": prospect.data,
            "research": research.data if research else None,
            "messages": messages.data or [],
        }

    # ========================================================
    # PROMPT
    # ========================================================

    def _build_prompt(
        self,
        context: dict[str, Any],
        rag_context: str,
    ) -> str:

        def dump(key: str) -> str:
            return json.dumps(context[key], indent=2, default=str)

        approval_rules = json.dumps(
            context["campaign"].get("human_approval_rules") or {},
            indent=2,
            default=str,
        )

        return f"""
You are the Conversation Agent for a B2B autonomous SDR.

A prospect has replied. Read the whole thread and decide what happens
next, then write the reply if one should be sent.

Use ONLY the supplied information. Never invent product capabilities,
pricing, customers, results, commitments or availability. If the
prospect asks something the supplied knowledge does not answer, do not
guess - escalate to a human instead.

Return JSON only:

{{
    "intent": "question",
    "sentiment": "neutral",
    "status": "active",
    "next_action": "send_reply",
    "requires_human_approval": false,
    "reply": "",
    "reasoning": "",
    "confidence": 0
}}

intent must be one of: interested, not_interested, question, objection,
meeting_request, referral, unsubscribe, out_of_office, unclear.

sentiment must be one of: positive, neutral, negative.

status must be one of: active (the thread is live), paused (waiting
before the next touch), escalated (a human must take over), closed (the
thread is finished).

next_action must be one of: send_reply, wait, follow_up,
escalate_to_human, book_meeting, stop.

Set requires_human_approval to true when the campaign's approval rules
require it, when the prospect asks about pricing, contracts, legal or
security terms, when they are unhappy, or when answering would require
information you do not have.

If the prospect asks to be removed or says they are not interested, set
intent accordingly, next_action to "stop", status to "closed" and leave
reply empty.

reply must be empty unless next_action is "send_reply".
confidence must be a number from 0 to 100.

CAMPAIGN:
{dump("campaign")}

HUMAN APPROVAL RULES:
{approval_rules}

PROSPECT:
{dump("prospect")}

PROSPECT RESEARCH:
{dump("research")}

CONVERSATION:
{dump("conversation")}

FULL MESSAGE HISTORY (oldest first):
{dump("messages")}

RELEVANT CAMPAIGN KNOWLEDGE:
{rag_context}
"""

    # ========================================================
    # RESULT
    # ========================================================

    def _normalize_analysis(
        self,
        result: dict[str, Any],
    ) -> dict[str, Any]:

        def pick(key: str, allowed: set[str], fallback: str) -> str:
            value = result.get(key)

            return value if value in allowed else fallback

        intent = pick("intent", VALID_INTENTS, "unclear")

        next_action = pick(
            "next_action",
            VALID_NEXT_ACTIONS,
            "escalate_to_human",
        )

        status = pick("status", VALID_STATUSES, "active")

        requires_human_approval = bool(
            result.get("requires_human_approval", False)
        )

        # Anything we could not confidently classify goes to a human.
        if intent == "unclear" and next_action == "send_reply":
            next_action = "escalate_to_human"
            requires_human_approval = True

        if intent in {"unsubscribe", "not_interested"}:
            next_action = "stop"
            status = "closed"

        reply = str(result.get("reply") or "").strip()

        if next_action != "send_reply":
            reply = ""

        try:
            confidence = max(
                0.0,
                min(100.0, float(result.get("confidence") or 0)),
            )
        except (TypeError, ValueError):
            confidence = 0.0

        return {
            "intent": intent,
            "sentiment": pick("sentiment", VALID_SENTIMENTS, "neutral"),
            "status": status,
            "next_action": next_action,
            "requires_human_approval": requires_human_approval,
            "reply": reply,
            "reasoning": str(result.get("reasoning") or ""),
            "confidence": round(confidence, 2),
        }


async def start_outreach(
    prospect_id: str,
    campaign_id: str,
    icp_id: str | None = None,
    channel: str | None = None,
) -> dict[str, Any]:

    return await ConversationAgent().start_outreach(
        prospect_id=prospect_id,
        campaign_id=campaign_id,
        icp_id=icp_id,
        channel=channel,
    )


async def handle_reply(
    conversation_id: str,
    content: str,
    channel_message_id: str | None = None,
) -> dict[str, Any]:

    return await ConversationAgent().handle_reply(
        conversation_id=conversation_id,
        content=content,
        channel_message_id=channel_message_id,
    )
