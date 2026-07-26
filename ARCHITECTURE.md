# builderMC — Architecture

> AI-powered Minecraft builder for **Fabric / Minecraft 26.2** (Prism Launcher, Fabric Loader 0.19.3).
> Two completely separate parts that talk over HTTP.

---

## 1. High-level design

```
 ┌─────────────────────── Minecraft Client/Server (Fabric mod, Java) ────────────────────────┐
 │  /aibuild <prompt>  →  BuildService  →  WorldContextCollector                              │
 │        →  BackendClient (async java.net.http)  →  POST /build  ───────────────┐            │
 │        ←  parse JSON response  ←  verify schematic  ←  notify player          │            │
 └────────────────────────────────────────────────────────────────────────────────┼───────────┘
                                                                                 │ HTTP (localhost)
 ┌────────────────────────────────────────────────────────────────────────────────▼───────────┐
 │  Python Backend (FastAPI + uvicorn)                                                        │
 │  POST /build → BuildService → AI Pipeline (interpret → spec → block placements)            │
 │     → SchematicWriter (mcschematic) → generated/latest.schem → JSON response               │
 │  IntelligentBuilder adapts the spec to the WorldContext (orientation, palette, roof, …)    │
 └────────────────────────────────────────────────────────────────────────────────────────────┘
```

The Fabric mod **never** generates structures itself. It is only responsible for:

- registering the `/aibuild` command,
- collecting Minecraft world information (WorldContext),
- sending async HTTP requests to the Python backend,
- receiving responses, validating them, and (future) placing schematics.

The Python backend is responsible for:

- receiving prompts + world context,
- calling an LLM through a swappable provider abstraction,
- converting the LLM response into block placements via Pydantic-validated JSON,
- generating `.schem` files with `mcschematic`,
- returning success/error responses.

### Design principles

- **Clean separation of responsibilities** — no giant classes; each package owns one concern.
- **Asynchronous by default** — the mod never blocks the server tick loop; the backend is async FastAPI.
- **Dependency injection** — the backend uses `Depends()` providers; the mod passes collaborators into constructors.
- **Swappable LLM providers** — a `LanguageModelProvider` interface lets us plug in Stub / OpenAI / local providers.
- **Forward-compatible API** — `WorldContext` is a permissive Pydantic model (`model_config = {"extra": "allow"}`) so new fields never break old mods.
- **Validation everywhere** — external input (command args, HTTP responses, LLM JSON) is validated before use.
- **Extensive logging** — both sides log every stage and every design decision.

---

## 2. Fabric mod file structure

```
src/main/java/net/infernodude777/buildermc/
├── BuilderMC.java                ModInitializer — wires collaborators, registers commands
├── BuilderMCDataGenerator.java   (template stub — datagen entrypoint)
├── config/
│   ├── BuilderMCConfig.java      Immutable config holder (backend URL, timeouts, build radius)
│   └── ModConfigLoader.java      Loads/saves config/buildermc.json (Gson, atomic write)
├── commands/
│   └── AIBuildCommand.java       Registers /aibuild <prompt>; delegates to BuildService
├── network/
│   ├── BackendClient.java        Async HTTP client (java.net.http) to the Python backend
│   ├── BackendResponse.java      Parsed /build response (status, schematic path, dimensions)
│   └── BackendException.java     Connection / timeout / HTTP-error exception hierarchy
├── models/
│   ├── WorldContext.java         Serialized world context (biome, terrain, water, trees, …)
│   ├── BuildTask.java            One build request (prompt + seed + world context)
│   └── SchematicResult.java      Result of a build (path, dimensions, status)
├── service/
│   ├── BuildService.java         Orchestrates: collect context → request → notify
│   └── WorldContextCollector.java  Scans the area around the player (biome, surface, water, …)
├── util/
│   ├── JsonUtil.java             Gson helpers (object → string, string → object)
│   └── MessageUtil.java          Thread-safe player feedback (runs on the server thread)
└── mixin/
    └── ExampleMixin.java         (template stub — kept for reference)
```

### Java mapping note (Minecraft 26.2)

The 26.2 Yarn mappings reorganize a few packages. The working scaffolding confirms
`net.minecraft.resources.Identifier` (older versions used `net.minecraft.util.Identifier`).
Version-sensitive imports are kept in small, isolated utility classes so a mapping drift is
a one-file fix. `./gradlew build` is the source of truth for mapping correctness.

---

## 3. Python backend file structure

```
backend/
├── server.py                       uvicorn entrypoint — creates the FastAPI app
├── requirements.txt                fastapi, uvicorn[standard], mcschematic, pydantic
├── README.md                       how to run
├── config/
│   ├── __init__.py
│   └── settings.py                 Settings (pydantic-settings) — host, port, output dir, LLM
├── routes/
│   ├── __init__.py
│   └── build.py                    POST /build router
├── models/
│   ├── __init__.py
│   ├── requests.py                 BuildRequest (prompt, seed, world_context)
│   ├── responses.py                BuildResponse (status, schematic, dimensions, decisions)
│   ├── world_context.py            WorldContext (permissive — extra fields allowed)
│   └── building_spec.py            Interpretation, BuildingSpec, BlockPlacement (LLM output)
├── services/
│   ├── __init__.py
│   └── build_service.py            Orchestrates the 3-stage pipeline + schematic write
├── generator/
│   ├── __init__.py
│   ├── schematic_writer.py         mcschematic wrapper — placements → .schem
│   └── demo_generator.py           No-LLM demo structure (tests the whole pipeline)
├── llm/
│   ├── __init__.py
│   ├── base.py                     LanguageModelProvider interface (swappable)
│   ├── stub_provider.py            Deterministic stub provider (no network)
│   └── pipeline.py                 3-stage pipeline: interpret → spec → placements
└── intelligent/
    ├── __init__.py
    └── builder.py                  IntelligentBuilder — adapts spec to WorldContext
```

### Request / response contract

`POST /build`

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
  "dimensions": [10, 8, 10],
  "decisions": ["orientation: faced north", "palette: oak + cobblestone", …]
}
```

---

## 4. Build & run

```bash
# Backend
cd C:\Users\Nikhil\Desktop\buildermc-26.2\backend
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Mod
cd C:\Users\Nikhil\Desktop\buildermc-26.2
.\gradlew build          # produce build/libs/buildermc-*.jar
.\gradlew runClient      # boot dev client
# in game:  /aibuild a small wooden house
```

The mod reads its backend URL from `config/buildermc.json` (default `http://localhost:8000`).

---

## 5. Prompt → file mapping

| Prompt | What it delivers | Files |
|---|---|---|
| 1. Project Architecture | this document | `ARCHITECTURE.md` |
| 2. Java Fabric Foundation | command + async HTTP + packages | `config/*`, `commands/*`, `network/*`, `service/BuildService`, `util/*`, `BuilderMC.java` |
| 3. Python Backend | FastAPI `/build` + demo generator | `backend/server.py`, `routes/*`, `services/*`, `generator/demo_generator`, `schematic_writer` |
| 4. Connect Java to Python | parse + verify + notify | `network/BackendClient`, `service/BuildService` |
| 5. AI Generation Pipeline | 3-stage LLM pipeline + schemas | `backend/llm/*`, `backend/models/building_spec.py`, `services/build_service.py` |
| 6. World Context System | collect + serialize + accept | `service/WorldContextCollector`, `models/WorldContext`, `backend/models/world_context.py` |
| 7. Intelligent Builder | context-aware design + decision logs | `backend/intelligent/builder.py` |
