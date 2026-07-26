# builderMC — Python backend

Turns natural-language prompts into Minecraft `.schem` files. Pairs with the
builderMC Fabric mod over HTTP.

## Stack

- **FastAPI** + **uvicorn** — async ASGI server
- **Pydantic v2** — request/response + LLM-output validation
- **mcschematic** — Sponge `.schem` writer
- **pydantic-settings** — env-driven config

## Install & run

```bash
cd C:\Users\Nikhil\Desktop\buildermc-26.2\backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

The backend listens on `127.0.0.1:8000` by default.

## Endpoints

| Method | Path        | Purpose |
|--------|-------------|---------|
| GET    | `/`         | Service info |
| GET    | `/health`   | Liveness probe |
| GET    | `/docs`     | Auto-generated OpenAPI UI |
| POST   | `/build`    | Generate a structure |

### `POST /build`

```json
// request
{
  "prompt": "a small wooden house",
  "seed": 12345,
  "world_context": {
    "biome": "minecraft:plains",
    "terrain_height": 64,
    "surface_block": "minecraft:grass_block",
    "nearby_trees": 2,
    "nearby_water": false,
    "nearby_buildings": 0,
    "nearby_entities": [],
    "player_position": [128, 64, -300],
    "player_facing": "north",
    "build_radius": 16
  }
}

// response
{
  "status": "success",
  "schematic": "generated/latest.schem",
  "dimensions": [9, 6, 9],
  "decisions": ["orientation: faced north", "palette: kept 'oak-cobble'", "..."]
}
```

Add `?demo=true` to use the no-LLM demo generator (smoke-tests the whole
pipeline without an AI provider):

```bash
curl -X POST http://localhost:8000/build?demo=true ^
  -H "Content-Type: application/json" ^
  -d "{\"prompt\":\"house\",\"seed\":1}"
```

## Configuration (env vars)

| Var | Default | Purpose |
|-----|---------|---------|
| `BUILDERMC_HOST` | `127.0.0.1` | Bind host |
| `BUILDERMC_PORT` | `8000` | Bind port |
| `BUILDERMC_OUTPUT_DIR` | `generated` | Where `.schem` files are written |
| `BUILDERMC_LATEST_FILENAME` | `latest.schem` | Filename the mod looks for |
| `BUILDERMC_LLM_PROVIDER` | `stub` | `stub` (offline) — `openai` is reserved |
| `BUILDERMC_MAX_DIMENSION` | `64` | Cap on structure size |

## Architecture

```
POST /build  →  BuildService
                  ├─ GenerationPipeline  (3 stages: interpret → spec → placements)
                  │     └─ LanguageModelProvider  (swappable: StubProvider, …)
                  ├─ IntelligentBuilder   (adapts spec to WorldContext)
                  └─ SchematicWriter      (mcschematic → .schem)
```

- **Prompts 3 & 5:** the pipeline + Pydantic schemas live in `llm/` and `models/`.
- **Prompt 6:** `WorldContext` is permissive (`extra="allow"`) so the mod can add
  fields without breaking older backends.
- **Prompt 7:** `IntelligentBuilder` adapts orientation, foundation, palette,
  roof, terrain, clearance, water, and trees — and logs every decision.

## Tests

```bash
python -m pytest tests/ -v
```

`tests/test_pipeline.py` exercises the full pipeline with the stub provider and
verifies the schematic file is produced.
