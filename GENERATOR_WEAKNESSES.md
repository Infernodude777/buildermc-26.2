# Generator Weaknesses & Risks

This document lists the current weaknesses of the BuilderMC structure generator, why each is a problem, and the current or planned mitigation.

## 1. Stub / Deterministic Provider is Not AI

**What:** The default `StubProvider` uses simple keyword matching (`house`, `tower`, `castle`) and fixed geometry to produce structures. It does not call an LLM or learn from the prompt.

**Why it is bad:**
- Players asking for "a red-roofed Tudor inn with an attached stable" will get the same generic house as someone asking for "house".
- It cannot fulfill rich, creative, or architectural prompts.
- It is a placeholder, not a generative AI.

**Mitigation:** Wire a real LLM provider (OpenAI, NVIDIA NIM, etc.) behind the `LanguageModelProvider` interface. The `nvidia_nim_provider.py` exists for this purpose.

## 2. Roof Styles Are Only Partly Implemented

**What:** `generate_placements` now builds gable, hip, dome, and flat roofs, but the implementations are basic stepped approximations. Stairs and slabs are not yet rotated per wall face.

**Why it is bad:**
- Roofs can look blocky or wrong for larger structures.
- Stairs facing the wrong way produce ugly intersections.
- Dome roofs are a stepped pyramid, not a true dome.

**Mitigation:** Add a block-state rotation table and per-wall staircase logic. Consider a dedicated `RoofGeometry` module.

## 3. Foundation Logic Is Coarse

**What:** The intelligent builder raises `foundation_height`, but the generator simply fills the full foundation volume. It does not clear grass, trees, or irregular terrain first.

**Why it is bad:**
- Generated structures can be buried in hills or float above valleys.
- Existing trees and grass blocks may clip through walls.

**Mitigation:** On the mod side, clear the footprint before pasting. On the backend, add a pre-processing step that samples terrain and adjusts the anchor Y.

## 4. Orientation Rotation Is Post-Processing

**What:** Placements are generated as if the front wall faces south (`z=0`), then rotated mathematically.

**Why it is bad:**
- It works for symmetric blocks but is fragile for directional blocks.
- Directional block states (stairs, doors, torches) are not rotated with the geometry.

**Mitigation:** Build the structure in the correct orientation from the start, or implement a block-state rotation parser that adjusts `facing=`, `axis=`, etc., after rotation.

## 5. Doors and Multi-Block Objects Are Hardcoded

**What:** Doors are placed by explicitly emitting `half=lower` and `half=upper`. Windows are simple glass panes.

**Why it is bad:**
- Different door types require matching block states. Hardcoding oak is brittle.
- Trapdoors, fences, beds, and banners are all multi-state and not handled.

**Mitigation:** Build a small block-state library / template system and generate correct states programmatically.

## 6. Lighting Is Minimal

**What:** Only a handful of torches are placed.

**Why it is bad:**
- Interiors are dark and spawn mobs.
- There is no logic for exterior ambiance or redstone lighting.

**Mitigation:** Add a lighting pass that places torches/lanterns every N blocks and on pillars.

## 7. Interiors Are Empty

**What:** Generated houses are hollow boxes.

**Why it is bad:**
- Players expect furniture, crafting stations, chests, beds, etc.
- Empty rooms feel unfinished.

**Mitigation:** Add an interior-furnishing stage that interprets the structure type and places appropriate blocks.

## 8. Schematic Bounding Boxes Are Bloated by Offsets

**What:** To avoid trees/buildings, the intelligent builder expands `spec.dimensions` and shifts placements, which produces larger `.schem` files with empty padding.

**Why it is bad:**
- Larger schematics are slower to paste and more confusing to preview.
- The empty padding can overlap with terrain or other structures.

**Mitigation:** Keep the schematic tight and apply the offset on the Java side when pasting.

## 9. No Structural Validation

**What:** There is no check that a structure is physically stable (floating blocks, unsupported roofs).

**Why it is bad:**
- Roof blocks may fall if unsupported.
- Sand/gravel blocks can collapse.

**Mitigation:** Add a stability pass that ensures load-bearing walls connect to foundations and avoids gravity-affected blocks in unsupported positions.

## 10. Material Palettes Are Hardcoded

**What:** Biome-to-palette mapping is a fixed dictionary.

**Why it is bad:**
- New biomes or modded blocks require code changes.
- The LLM could choose more creative or context-aware palettes.

**Mitigation:** Move palette selection into the LLM prompt and validate the returned block states.
