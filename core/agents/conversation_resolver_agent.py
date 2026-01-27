from typing import Dict, Any, Optional
import json
from groq import Groq
from core.agents.base_agent import BaseAgent
from config.settings import settings


class ConversationResolverAgent(BaseAgent):
    """
    Determines query continuity and resolves contextual references.

    HARD RULE:
    - This agent may ONLY reuse context explicitly provided.
    - It may NEVER invent entities, filters, metrics, limits, or intent.
    """

    META_PATTERNS = (
        "can i",
        "may i",
        "is it possible",
        "can we",
        "should i",
        "do i need",
    )

    def __init__(self):
        super().__init__("conversation_resolver")
        self.llm = Groq(api_key=settings.GROQ_API_KEY)

    def run(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            self.logger.info("resolving_conversation_context", query=query)

            context = context or {}
            last_turn = context.get("last_turn") or {}
            conversation_history = context.get("conversation_history", [])

            # ---------- HARD META SHORT-CIRCUIT ----------
            query_lower = query.lower().strip()
            if query_lower.startswith(self.META_PATTERNS):
                return self._create_response(
                    success=True,
                    result=self._meta_switch_result(),
                )

            prompt = self._build_prompt(query, last_turn, conversation_history)

            response = self.llm.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
            )

            raw_output = response.choices[0].message.content.strip()
            raw_output = raw_output.replace("```json", "").replace("```", "").strip()

            resolution = json.loads(raw_output)

            # ---------- POST-LLM SAFETY VALIDATION ----------
            validated = self._validate_resolution(resolution, last_turn)

            self.logger.info(
                "conversation_resolved",
                is_follow_up=validated["is_follow_up"],
                continuity_type=validated["continuity_type"],
            )

            return self._create_response(success=True, result=validated)

        except json.JSONDecodeError as e:
            self.logger.error("json_parse_failed", error=str(e), raw=raw_output[:200])
            return self._create_response(
                success=False,
                error="Failed to parse conversation resolution JSON",
            )

        except Exception as e:
            return self._handle_error(e, query)

    # ------------------------------------------------------------------
    # PROMPT
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        query: str,
        last_turn: Dict[str, Any],
        conversation_history: list,
    ) -> str:
        history_text = ""
        for turn in conversation_history[-4:]:
            role = turn.get("role", "")
            content = turn.get("content", "")
            history_text += f"{role.upper()}: {content}\n"

        last_turn_text = json.dumps(
            {
                "intent": last_turn.get("intent"),
                "entities": last_turn.get("entities", {}),
                "filters": last_turn.get("filters", {}),
                "had_results": last_turn.get("had_results", False),
            },
            indent=2,
        )

        return f"""
You are a conversation continuity resolver.

CRITICAL CONSTRAINTS:
- You may ONLY reuse entities and filters explicitly listed in PREVIOUS TURN METADATA.
- You MUST NOT invent metrics, limits, aggregations, or entities.
- If information is missing or ambiguous, require clarification.
- Meta-questions about the conversation itself are MODE_SWITCH.

CURRENT QUERY:
{query}

CONVERSATION HISTORY:
{history_text or "None"}

PREVIOUS TURN METADATA (AUTHORITATIVE):
{last_turn_text}

OUTPUT STRICT JSON ONLY:
{{
  "is_follow_up": true | false,
  "continuity_type": "REFINEMENT | EXTENSION | MODE_SWITCH | NEW_TOPIC | AMBIGUOUS",
  "resolved_references": {{
    "entities": {{}},
    "filters": {{}}
  }},
  "inherited_context": {{
    "intent": null,
    "entities": {{}},
    "filters": {{}}
  }},
  "override_context": {{
    "entities": {{}},
    "filters": {{}}
  }},
  "requires_clarification": true | false,
  "clarification_reason": "string or null"
}}

Return JSON only.
"""

    # ------------------------------------------------------------------
    # VALIDATION (FIXED)
    # ------------------------------------------------------------------

    def _validate_resolution(
        self, resolution: Dict[str, Any], last_turn: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enforces that the model did not invent context.

        FIXED: No longer modifies dictionary during iteration.
        """

        allowed_entities = set((last_turn.get("entities") or {}).keys())
        allowed_filters = set((last_turn.get("filters") or {}).keys())

        invented = False

        for section in ("resolved_references", "override_context", "inherited_context"):
            ctx = resolution.get(section, {})

            # Collect keys to remove FIRST (don't modify during iteration)
            entities_to_remove = [
                key
                for key in ctx.get("entities", {}).keys()
                if key not in allowed_entities
            ]
            for key in entities_to_remove:
                invented = True
                ctx["entities"].pop(key, None)

            # Same for filters
            filters_to_remove = [
                key
                for key in ctx.get("filters", {}).keys()
                if key not in allowed_filters
            ]
            for key in filters_to_remove:
                invented = True
                ctx["filters"].pop(key, None)

        if invented:
            resolution["requires_clarification"] = True
            resolution["clarification_reason"] = (
                "Query references entities or filters not present in prior context"
            )

        return resolution

    # ------------------------------------------------------------------
    # META SWITCH
    # ------------------------------------------------------------------

    def _meta_switch_result(self) -> Dict[str, Any]:
        return {
            "is_follow_up": False,
            "continuity_type": "MODE_SWITCH",
            "resolved_references": {"entities": {}, "filters": {}},
            "inherited_context": {},
            "override_context": {},
            "requires_clarification": False,
            "clarification_reason": None,
        }
