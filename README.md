# BuilderMC

BuilderMC is an AI-powered Minecraft structure generator for the Fabric mod loader. It combines a lightweight Fabric mod written in Java with a Python FastAPI backend that can talk to any OpenAI-compatible LLM.

## Architecture

The project is split into two independent parts that communicate over HTTP:

1. **Fabric Mod (Java)** – lives in `src/main/java` and is only responsible for command registration, world context collection, sending build requests, and placing generated schematics.
2. **Python Backend** – lives in `backend/` and is responsible for prompt interpretation, building specification, block placement generation, and `.schem` output.

## Fabric Mod Responsibilities

- Registers `/build <prompt>`, `/place`, and `/api` commands.
- Collects world context around the player: biome, terrain height, surface blocks, trees, water, nearby buildings, entities, player position/facing, and build radius.
- Sends an async HTTP POST to the Python backend.
- Receives and validates the response, then pastes the generated structure with `/place`.
- Stores AI provider configuration locally in `config/buildermc.json` via `/api <base_url> <model_id> <api_key> [provider]`.

## Python Backend Responsibilities

- Exposes `POST /build` and `GET /health` endpoints via FastAPI.
- Runs a 3-stage AI pipeline:
  1. **Interpret** the prompt into a structured type, style, and keywords.
  2. **Generate** a `BuildingSpec` with dimensions, palette, roof style, orientation, and foundation height.
  3. **Generate** concrete `BlockPlacement` coordinates from the spec.
- Adapts the spec to the world context using `IntelligentBuilder`: orientation, foundation, palette, roof, terrain, clearance, water, and tree preservation.
- Supports runtime provider switching through the per-request `provider_config` sent by the mod.
- Writes the final structure to a `.schem` file using the `mcschematic` library.

## Provider System

The backend supports multiple LLM providers through a clean provider interface:

- **StubProvider** – deterministic, offline, keyword-driven generator used for testing and development.
- **OpenAiCompatibleProvider** – talks to any `/chat/completions` endpoint such as NVIDIA NIM, OpenAI, or Groq.

The mod's `/api` command stores provider details and forwards them with every build request, allowing players to switch providers without restarting the server.

## World Context

Every build request includes a `WorldContext` object containing:

- Biome and surface block
- Terrain height and nearby water
- Nearby trees, buildings, and entities
- Player position, facing direction, and build radius

This context drives intelligent decisions such as clearing trees, avoiding water, and orienting the structure toward the player.

## Commands

| Command | Description |
| --- | --- |
| `/build <prompt>` | Generates a structure matching the prompt. |
| `/place` | Pastes the last generated structure at the player's feet. |
| `/api <base_url> <model_id> <api_key> [provider]` | Saves AI provider config locally. |

## Typing Demo

The included `timer.py` script reads `overview_content.md` and slowly types it into a target Markdown file over a configurable duration. To run the 4-hour typing demo:

```bash
python timer.py --file overview_content.md --output README.md --duration 4
```

## Future Work

- True terrain-height adaptation so structures sit flush on uneven ground.
- Block-state rotation for doors, stairs, and torches when orientation changes.
- Furniture and interior detail generation.
- Streaming progress updates from backend to mod.
- Support for much larger structures through chunking and tick-scheduled placement.

## License

This project is provided as a demonstration of clean separation between a Minecraft mod and an AI backend, with dependency injection, Pydantic validation, async networking, and testable components.
