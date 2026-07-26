"""NVIDIA NIM LLM provider — real AI generation via glm-5.2.

Uses the OpenAI-compatible ``/chat/completions`` endpoint on NVIDIA NIM
(``integrate.api.nvidia.com``).  Requires ``BUILDERMC_NVIDIA_API_KEY`` in the
environment or ``backend/.env``.

All three pipeline stages call the LLM with a JSON-schema-constrained system
prompt and validate the response against the Pydantic models in
``models.building_spec``.  Malformed LLM output is raised as
:class:`MalformedLLMOutputError` so the caller can decide how to handle it.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from models.building_spec import (
    BlockPlacementList,
    BuildingSpec,
    Interpretation,
)
from models.world_context import WorldContext

from .base import LanguageModelProvider, MalformedLLMOutputError

_T = TypeVar("_T", bound=BaseModel)

logger = logging.getLogger("buildermc.llm.nvidia")

# ─── Stage-specific system prompts ───────────────────────────────────────────
# Each prompt tells the LLM the EXACT JSON schema so the output validates
# against the Pydantic models (which use extra="forbid").

_INTERPRET_SYSTEM = """\
You are a Minecraft architecture interpreter.  Given a natural-language build \
prompt and the surrounding world context, classify the build request.

Output ONLY a JSON object with EXACTLY these fields and no others:
{
  "type": one of "house", "tower", "fort", "bridge", "garden", "sculpture", "other",
  "style": a short style descriptor (max 64 chars, e.g. "medieval", "modern", "cottage"),
  "description": a one-line restatement of intent (max 500 chars),
  "keywords": an array of up to 20 relevant keyword strings
}

The "type" value MUST be one of the exact lowercase strings listed above.
Do NOT include any text before or after the JSON object.
Do NOT wrap the JSON in markdown code fences.
Do NOT write Python code or any other code — output ONLY JSON.
"""

_SPEC_SYSTEM = """\
You are a Minecraft building designer.  Given a structure interpretation and \
the surrounding world context, produce a complete building specification.

Output ONLY a JSON object with EXACTLY these fields and no others:
{
  "interpretation": {
    "type": "house" | "tower" | "fort" | "bridge" | "garden" | "sculpture" | "other",
    "style": "...",
    "description": "...",
    "keywords": ["..."]
  },
  "dimensions": [width, height, depth],
  "palette": {
    "name": "palette name",
    "walls": ["minecraft:block_state", ...],
    "floor": ["minecraft:block_state", ...],
    "roof": ["minecraft:block_state", ...],
    "foundation": ["minecraft:block_state", ...],
    "detail": ["minecraft:block_state", ...]
  },
  "roof_style": one of "flat", "gable", "hip", "dome", "sloped",
  "orientation": one of "north", "south", "east", "west",
  "foundation_height": an integer from 0 to 8,
  "features": ["door", "windows", "floor", ...]
}

Rules:
- dimensions: exactly 3 positive integers, each at most 64.  Keep structures \
reasonable (e.g. a house is 7-12 wide, 5-8 tall, 7-12 deep).
- Every block-state string MUST start with "minecraft:".  Examples: \
"minecraft:oak_planks", "minecraft:stone_bricks", "minecraft:oak_stairs[facing=east]", \
"minecraft:glass_pane", "minecraft:oak_door[half=lower]".
- walls, floor, roof, and foundation arrays MUST each have at least 1 entry.
- detail may be empty.
- Adapt the palette and roof_style to the biome:
  desert -> sandstone + flat roof, snowy -> spruce + gable, water -> oak + hip, \
forest -> oak + gable, plains -> oak + cobblestone + gable.
- Set orientation to match the player's facing direction when provided.
- The "type" in interpretation MUST be a lowercase string from the list above.

Do NOT include any text before or after the JSON object.
Do NOT wrap the JSON in markdown code fences.
Do NOT write Python code or any other code — output ONLY JSON.
"""

_PLACEMENT_SYSTEM_TEMPLATE = """\
You are a Minecraft block-placement generator.  Given a building specification, \
generate the concrete block placements that form the complete structure.

The structure dimensions are {width} (x) x {height} (y) x {depth} (z).
Every coordinate MUST satisfy: 0 <= x < {width}, 0 <= y < {height}, 0 <= z < {depth}.
Use ONLY block states from the palette below.

Palette:
  walls: {walls}
  floor: {floor}
  roof: {roof}
  foundation: {foundation}
  detail: {detail}

Build a complete structure:
  1. Foundation: a solid layer at y=0 using the foundation block.
  2. Floor: a solid layer at y=1 using the floor block.
  3. Walls: a hollow shell from y=2 to y={top_y} using the wall block, with a \
2-block-high door gap on the wall facing the player.
  4. Windows: place glass panes (from detail) on the long walls at y=3 and y=4.
  5. Roof: a solid cap at y={roof_y} using the roof block.

Output ONLY a JSON object with EXACTLY this field:
{{"placements": [{{"x": 0, "y": 0, "z": 0, "block_state": "minecraft:stone"}}, ...]}}

Every block_state MUST start with "minecraft:".
Do NOT include any text before or after the JSON object.
Do NOT wrap the JSON in markdown code fences.
Do NOT write Python code or any other code — output ONLY JSON.
"""


class NvidiaNimProvider(LanguageModelProvider):
    """Real LLM provider via NVIDIA NIM's OpenAI-compatible chat API."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError(
                "NvidiaNimProvider requires an API key.  "
                "Set BUILDERMC_NVIDIA_API_KEY in the environment or backend/.env."
            )
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )
        logger.info(
            "NvidiaNimProvider initialised: base_url=%s model=%s temp=%.1f max_tokens=%d",
            self.base_url, self.model, self.temperature, self.max_tokens,
        )

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    # ─── Stage implementations ───────────────────────────────────────────

    async def interpret(self, prompt: str, context: WorldContext) -> Interpretation:
        """Stage 1 — classify the prompt via the LLM."""
        user = (
            f"Build prompt: {prompt}\n\n"
            f"World context: {self._context_summary(context)}"
        )
        return await self._chat_model(_INTERPRET_SYSTEM, user, Interpretation, stage="interpret")

    async def generate_spec(
        self, interpretation: Interpretation, context: WorldContext
    ) -> BuildingSpec:
        """Stage 2 — generate a building spec via the LLM."""
        user = (
            f"Interpretation:\n{json.dumps(interpretation.model_dump(), indent=2)}\n\n"
            f"World context: {self._context_summary(context)}"
        )
        return await self._chat_model(_SPEC_SYSTEM, user, BuildingSpec, stage="spec")

    async def generate_placements(
        self, spec: BuildingSpec, context: WorldContext
    ) -> BlockPlacementList:
        """Stage 3 — generate block placements via the LLM.

        Raises:
            MalformedLLMOutputError: If the LLM does not emit valid JSON that
                matches the ``BlockPlacementList`` schema.
        """
        system = _PLACEMENT_SYSTEM_TEMPLATE.format(
            width=spec.width,
            height=spec.height,
            depth=spec.depth,
            top_y=spec.height - 2,
            roof_y=spec.height - 1,
            walls=spec.palette.walls,
            floor=spec.palette.floor,
            roof=spec.palette.roof,
            foundation=spec.palette.foundation,
            detail=spec.palette.detail,
        )
        user = (
            f"Build a {spec.interpretation.type.value} with style '{spec.interpretation.style}'.\n"
            f"Orientation: {spec.orientation}.  Roof style: {spec.roof_style.value}.\n"
            f"Features: {', '.join(spec.features) or 'none'}.\n"
            f"World context: {self._context_summary(context)}"
        )
        return await self._chat_model(
            system, user, BlockPlacementList, stage="placements", max_tokens=8192,
        )

    # ─── HTTP + JSON helpers ─────────────────────────────────────────────

    async def _chat(
        self, system: str, user: str, max_tokens: int | None = None,
    ) -> str:
        """Send a chat-completion request and return the content string."""
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": self.temperature,
            "max_tokens": max_tokens or self.max_tokens,
        }
        try:
            resp = await self._client.post("/chat/completions", json=body)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise MalformedLLMOutputError(
                f"NVIDIA NIM HTTP {e.response.status_code}: {e.response.text[:500]}"
            ) from e
        except httpx.RequestError as e:
            raise MalformedLLMOutputError(f"NVIDIA NIM request error: {e}") from e

        payload = resp.json()
        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise MalformedLLMOutputError(
                f"Unexpected NVIDIA NIM response structure: {json.dumps(payload)[:500]}"
            ) from e

    async def _chat_json(
        self, system: str, user: str, stage: str, max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Call the LLM, parse JSON, retry once on parse failure."""
        raw = await self._chat(system, user, max_tokens=max_tokens)
        try:
            return self._parse_json(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                "stage %s: first JSON parse failed (%s); retrying with correction.",
                stage, e,
            )
            correction = (
                f"\n\nYour previous response was not valid JSON: {e}\n"
                f"Please output ONLY the JSON object, no other text, no code fences."
            )
            raw2 = await self._chat(system, user + correction, max_tokens=max_tokens)
            try:
                return self._parse_json(raw2)
            except (json.JSONDecodeError, ValueError) as e2:
                raise MalformedLLMOutputError(
                    f"Stage {stage}: LLM produced invalid JSON after retry: {e2}"
                ) from e2

    async def _chat_model(
        self,
        system: str,
        user: str,
        model_cls: type[_T],
        stage: str,
        max_tokens: int | None = None,
    ) -> _T:
        """Call the LLM, parse JSON, validate against ``model_cls``.

        Retries once if JSON parsing OR Pydantic validation fails, appending
        the error to the prompt so the LLM can correct it.  This handles the
        common real-world case where the LLM emits valid JSON with wrong field
        values (e.g. uppercase enum values, extra fields that violate
        ``extra="forbid"``) — not just malformed JSON.
        """
        data = await self._chat_json(system, user, stage=stage, max_tokens=max_tokens)
        try:
            return model_cls.model_validate(data)
        except ValidationError as e:
            logger.warning(
                "stage %s: validation failed (%s); retrying with schema correction.",
                stage, e,
            )
            correction = (
                f"\n\nYour previous JSON did not match the required schema:\n{e}\n"
                f"Please fix the issues and output ONLY the valid JSON object."
            )
            data2 = await self._chat_json(
                system, user + correction, stage=stage, max_tokens=max_tokens,
            )
            try:
                return model_cls.model_validate(data2)
            except ValidationError as e2:
                raise MalformedLLMOutputError(
                    f"Stage {stage}: LLM JSON did not match schema after retry: {e2}"
                ) from e2

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        """Robustly extract a JSON object from an LLM response string."""
        text = raw.strip()
        # Strip markdown code fences if present.
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*\n?", "", text)
            text = re.sub(r"\n?```\s*$", "", text)
            text = text.strip()

        candidates = [text]
        # Fallback: extract the outermost JSON object.
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidates.append(text[start : end + 1])

        for candidate in candidates:
            try:
                result = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(result, dict):
                return result
            if isinstance(result, list) and result and isinstance(result[0], dict):
                return result[0]

        raise ValueError(f"No JSON object found in LLM response: {raw[:200]!r}")

    @staticmethod
    def _context_summary(context: WorldContext) -> str:
        """Compact one-line summary of world context for the LLM prompt."""
        parts = [
            f"biome={context.biome}",
            f"terrain_height={context.terrain_height}",
            f"surface={context.surface_block}",
            f"trees={context.nearby_trees}",
            f"water={context.nearby_water}",
            f"buildings={context.nearby_buildings}",
            f"facing={context.player_facing}",
            f"pos={context.player_position}",
        ]
        return ", ".join(parts)
