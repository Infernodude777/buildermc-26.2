# BuilderMC — AI-Powered Minecraft Structure Generator

**BuilderMC** is a Fabric mod for Minecraft 26.2 that generates entire structures from natural-language prompts. Describe what you want to build — a medieval castle, a Japanese shrine on a hill, a dwarven forge embedded in a cliff face, or an underwater base with glass domes — and an AI backend generates a complete schematic file which the mod pastes directly into your world. The AI adapts every build to the surrounding terrain: it reads the biome, ground elevation, nearby trees and water, and even existing buildings, then chooses orientation, materials, foundation depth, and roof style to make the structure look like it belongs there.

## Architecture Overview

BuilderMC is split into two completely separate codebases that communicate over HTTP. The Fabric mod never generates structures itself. It is only responsible for registering commands, collecting Minecraft world information, sending HTTP requests to the Python backend, and placing completed schematics in the world.

The Python backend handles all the heavy lifting: receiving prompts and world context, calling an LLM through a three-stage generation pipeline, converting LLM output into validated block coordinates, generating schematic files using the mcschematic library, adapting structures to the world via the Intelligent Builder, and returning responses with detailed decision logs.

This separation keeps the Java mod focused purely on Minecraft integration while the Python backend handles AI generation and schematic creation. The two communicate exclusively through a well-defined JSON API with no Python-in-Minecraft embedding.

## Quick Start

**Prerequisites:** Minecraft 26.2, Fabric Loader 0.19.3, Fabric Loom 1.17, Fabric API 0.155.2, Java 25, Gradle 9.5.1, Python 3.12, and an OpenAI-compatible LLM API key.

**Step 1: Build the mod**

```
cd buildermc-26.2
gradlew.bat build
```

The compiled mod jar lands in `build/libs/`. Copy it into your Fabric instance `mods` folder along with Fabric API.

**Step 2: Start the Python backend**

```
cd backend
pip install -r requirements.txt
python server.py
```

The server starts on `http://localhost:8000` by default. Verify it is running with:

```
curl http://localhost:8000/health
```

Which should return `status: ok`.

**Step 3: Configure the AI provider**

In-game run:

```
/api set https://api.groq.com/openai/v1 groq/llama-3.3-70b-versatile gsk_your_key
```

Or set defaults in `backend/.env` with `LLM_BASE_URL`, `LLM_MODEL_ID`, and `LLM_API_KEY`.

**Step 4: Build something**

In-game, facing the area where you want the structure, run:

```
/build a small medieval house with a thatched roof
```

The mod displays progress in chat, sends the request to Python, and when the schematic is ready, pastes it into the world.

## Commands

### `/build <prompt>`

The main command. Sends your prompt plus the current world context to the AI backend.

Examples:
- `/build a castle with towers and a drawbridge`
- `/build a Japanese pagoda surrounded by cherry trees`
- `/build an underwater base with glass domes`
- `/build a dwarven forge built into a mountain`

The mod shows progress: *Generating structure* → *Interpreting prompt* → *Adapting to terrain* → *Generating block placements* → *Building complete*.

### `/place`

Pastes the last generated schematic at the player's current location.

```
/place
/place --offset 5 0 -3
```

### `/api`

Configures the AI provider at runtime. Settings are sent with every build request and override the backend defaults.

```
/api set <base_url> <model_id> <api_key>
/api show
/api reset
```

Switch between Groq, OpenAI, Ollama, or LM Studio without restarting the server.

## The AI Backend

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Returns status and docs link |
| GET | `/health` | Returns `status: ok` for liveness probes |
| POST | `/build` | Main generation endpoint |
| POST | `/build/stream` | SSE streaming updates during generation |

### POST /build

Accepts:
- `prompt` — the natural language build request
- `seed` — optional world seed for deterministic variants
- `world_context` — biome, terrain, nearby objects scanned by the mod
- `provider_config` — optional LLM provider override from the `/api` command

Add `?demo=true` to bypass the LLM and generate a small demo house for testing.

**Success response:**
```
{
  "status": "success",
  "schematic": "path/to/generated.schem",
  "dimensions": {"x": 15, "y": 8, "z": 12},
  "placements": [...],
  "decisions": [...]
}
```

**Error response:**
```
{
  "status": "error",
  "error": "description of what went wrong"
}
```

## World Context System

Before every build request, the Fabric mod scans the area around the player and packages the information into the `world_context` field sent to the backend.

| Field | Description |
|-------|-------------|
| `biome` | Current biome identifier (e.g. `plains`, `desert`, `snowy_taiga`) |
| `terrain_height` | Y-level of the highest solid block at the player position |
| `surface_block` | Block ID at the terrain surface |
| `nearby_trees` | Count of log and wood blocks within the scan radius |
| `nearby_water` | Whether water blocks were detected nearby |
| `nearby_buildings` | Count of plank, door, and window blocks (heuristic) |
| `nearby_entities` | Number of non-player entities in the area |
| `player_x`, `player_z` | Player block position |
| `player_facing` | Direction the player is looking (north, south, east, west) |

The system is extensible by design. New fields can be added to `WorldContext` on both the Java and Python sides without breaking the API contract.

## Intelligent Builder

The Intelligent Builder is a post-processing layer that runs after the LLM generates a building spec but before the schematic is written to disk. It adjusts every aspect of the build to fit the surrounding environment.

- **Orientation** — Faces the structure toward the direction the player is looking. If a player faces south, the building entrance faces south.
- **Foundation depth** — Deeper on sand and water (soft terrain). Standard on grass and stone. Desert gets +2 blocks deep. Ocean gets +3 blocks deep.
- **Material palette** — Biome-appropriate material swaps. Desert uses sandstone. Snowy uses spruce and cobblestone. Nether uses nether bricks. Water biomes use watertight oak and stone bricks.
- **Roof style** — Climate-driven roof selection. Desert uses flat roofs. Forest and snowy regions use gabled roofs. Ocean areas use hipped roofs.
- **Terrain adaptation** — Detects elevation changes and adjusts the building pad. High terrain (y > 85) adds a leveling pad before foundations.
- **Clearance** — Shifts the build away from existing structures. 12+ nearby plank cells triggers a shift of +3 in both X and Z.
- **Water avoidance** — Chooses erosion-resistant blocks and raised foundations. Nearby water switches to stone brick foundations with a hipped roof.
- **Tree preservation** — Biases offset to avoid cutting down nearby trees. 6+ nearby trees triggers a shift of +2 in both X and Z.

Every decision is logged as a human-readable string and returned in the response `decisions` array so the mod can display it in chat.

## AI Generation Pipeline

The backend uses a three-stage generation pipeline to produce structures. Each stage has its own Pydantic model, its own prompt, and its own validation.

1. **Interpret** — The LLM receives the user prompt and world context and produces an `Interpretation` object with `type`, `style`, and `description` fields.

2. **Building Specification** — The Interpretation is fed into a second prompt that produces a `BuildingSpec` with dimensions, material palette, roof style, orientation, foundation height, and features list.

3. **Block Placements** — The BuildingSpec goes into a third prompt that produces the concrete block list with individual x, y, z coordinates and block state strings. All placements are validated against the spec bounds and any out-of-range coordinates are rejected.

**Design principles:** The LLM never generates Python code — it only outputs structured JSON. Every stage is validated by Pydantic before its output is used. Malformed output is caught safely and reported as a user-friendly error. Providers are swappable through any OpenAI-compatible API. There is a fallback to a stub provider when no provider is configured.

## Configuration

**Mod:** The mod ID is `buildermc` with entrypoint at `net.infernodude777.buildermc.BuilderMC`. The mod declares dependencies on `fabricloader` 0.19.3, `minecraft` 26.2, `java` 25, and `fabric-api`.

**Backend** settings in `config/settings.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `host` | `127.0.0.1` | Server bind address |
| `port` | `8000` | Server port |
| `llm_provider` | `openai` | Default LLM provider |
| `llm_base_url` | from `LLM_BASE_URL` env | API base URL |
| `llm_model_id` | from `LLM_MODEL_ID` env | Model identifier |
| `llm_api_key` | from `LLM_API_KEY` env | API key |
| `output_dir` | `generated` | Schematic output directory |
| `max_dimension` | `128` | Maximum structure size |
| `schematic_version` | `JE_1_20_2` | Schematic format version |

Set LLM credentials in `backend/.env` with the three environment variables above.

## Project Structure

```
buildermc-26.2/
├── src/main/java/net/infernodude777/buildermc/
│   ├── BuilderMC.java                    # Mod entrypoint
│   ├── BuilderMCDataGenerator.java       # Data generator entrypoint
│   ├── commands/
│   │   ├── ApiCommand.java               # /api command
│   │   ├── BuildCommand.java             # /build command
│   │   └── PlaceCommand.java             # /place command
│   ├── config/
│   │   ├── BuilderMCConfig.java          # Mod config
│   │   └── ModConfigLoader.java          # Config loader
│   ├── models/
│   │   ├── BuildTask.java                # Build request model
│   │   ├── SchematicResult.java          # Schematic response model
│   │   └── WorldContext.java             # World context model
│   ├── network/
│   │   ├── BackendClient.java            # HTTP client
│   │   ├── BackendException.java         # Custom exception
│   │   └── BackendResponse.java          # Response wrapper
│   ├── service/
│   │   ├── BuildService.java             # Build orchestration
│   │   ├── PlacementService.java         # Schematic placement
│   │   ├── SchematicPlacer.java          # Block-by-block placer
│   │   └── WorldContextCollector.java    # World scanning
│   └── util/
│       ├── JsonUtil.java                 # JSON helper
│       └── MessageUtil.java              # Chat message helper
├── src/main/resources/
│   ├── fabric.mod.json
│   ├── buildermc.mixins.json
│   └── assets/buildermc/icon.png
├── backend/
│   ├── server.py                         # FastAPI application
│   ├── requirements.txt
│   ├── config/settings.py
│   ├── routes/
│   │   ├── build.py                      # /build endpoint
│   │   ├── deps.py                       # Dependencies
│   │   └── stream.py                     # SSE streaming
│   ├── models/
│   │   ├── building_spec.py              # BuildingSpec model
│   │   ├── requests.py                   # Request models
│   │   ├── responses.py                  # Response models
│   │   └── world_context.py              # World context model
│   ├── services/
│   │   └── build_service.py              # Build orchestration
│   ├── generator/
│   │   ├── demo_generator.py             # Demo structure generator
│   │   └── schematic_writer.py           # .schem file writer
│   ├── intelligent/
│   │   └── builder.py                    # Post-processing adaptation
│   ├── llm/
│   │   ├── base.py                       # Provider interface
│   │   ├── chunked_generator.py          # Chunked generation
│   │   ├── nvidia_nim_provider.py        # NVIDIA NIM provider
│   │   ├── pipeline.py                   # 3-stage pipeline
│   │   ├── registry.py                   # Provider registry
│   │   └── stub_provider.py              # Fallback stub
│   └── tests/
│       ├── test_nvidia_provider.py
│       └── test_pipeline.py
├── build.gradle
├── settings.gradle
├── gradle.properties
├── gradlew / gradlew.bat
├── .github/workflows/build.yml
├── ARCHITECTURE.md
├── GENERATOR_WEAKNESSES.md
└── LICENSE
```

## Development Guide

Clone the repository, run `gradlew.bat build` to compile, `cd backend && pip install -r requirements.txt && python server.py` to start the backend, and `gradlew.bat runClient` to launch the Minecraft dev client with the mod loaded.

Run `cd backend && pytest -v` to execute the Python test suite.

Use `curl -X POST http://localhost:8000/build?demo=true` to test the full pipeline end-to-end without an LLM provider.

The CI pipeline in `.github/workflows/build.yml` checks out the repository, sets up JDK 25, validates the Gradle wrapper, runs `gradlew build`, and uploads build artifacts on every push and PR on ubuntu-24.04.

## Extending the Mod

- **New command** — Create a class in `commands/` and register it in `BuilderMC.onInitialize`.
- **New world context field** — Add it to `WorldContext.java` (Java) and `world_context.py` (Python). New fields with defaults won't break existing requests.
- **New LLM provider** — Implement the `LanguageModelProvider` interface from `base.py` and register it in `registry.py`. The mod sends the provider type in `provider_config`.
- **New material palette** — Edit `intelligent/builder.py` and add an entry to the `_BIOME_PALETTES` dictionary with the biome name and material list.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Build command does nothing | Verify the Python backend is running (`curl http://localhost:8000/health`). Check the mod log for connection errors. Run `/api show` to verify provider configuration. |
| Backend returns errors | Check the backend console log for details. Verify API key validity. Try the demo endpoint (`?demo=true`) to test without an LLM. |
| Structure looks wrong | The Intelligent Builder adapts structures to the world — try a different biome. Check the `decisions` array in the response to see what adaptations were applied. Start with a simpler prompt. |
| Mod fails to load | Ensure Fabric API is installed. Verify Java 25 is being used. Check `fabric.mod.json` dependency versions match your environment. |

## License

This project is available under the CC0-1.0 license.
