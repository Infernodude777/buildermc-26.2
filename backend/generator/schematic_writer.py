"""Thin wrapper around the mcschematic library.

Converts a validated :class:`BlockPlacementList` into a Sponge ``.schem`` file
using the ``mcschematic`` API:
  schem = MCSchematic()
  schem.setBlock((x, y, z), "minecraft:stone[axis=y]")
  schem.save(folder, name, mcschematic.Version.JE_1_20_2)

The Version enum is resolved by name from settings so the target MC version can
be changed without editing code.
"""
from __future__ import annotations

import logging
from pathlib import Path

import mcschematic

from config.settings import settings
from models.building_spec import BlockPlacementList, BuildingSpec

logger = logging.getLogger("buildermc.generator.schematic_writer")


class SchematicWriter:
    """Writes a BuildingSpec + placements to disk as a .schem file."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or settings.output_dir

    def write(self, spec: BuildingSpec, placements: BlockPlacementList) -> Path:
        """Write the schematic and return its absolute path.

        Raises RuntimeError if mcschematic fails or the version enum is unknown.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

        version = self._resolve_version(settings.schematic_version)
        schem = mcschematic.MCSchematic()

        for p in placements.placements:
            schem.setBlock((p.x, p.y, p.z), p.block_state)

        # mcschematic appends the file extension itself; pass the stem only.
        stem = settings.latest_filename.removesuffix(".schem")
        schem.save(str(self.output_dir), stem, version)

        path = self.output_dir / settings.latest_filename
        logger.info(
            "wrote schematic: %s  dims=%dx%dx%d  blocks=%d",
            path, spec.width, spec.height, spec.depth, len(placements.placements),
        )
        return path

    @staticmethod
    def _resolve_version(name: str) -> "mcschematic.Version":
        try:
            return getattr(mcschematic.Version, name)
        except AttributeError as e:
            available = [v for v in dir(mcschematic.Version) if not v.startswith("_")]
            raise RuntimeError(
                f"Unknown mcschematic.Version {name!r}. Available: {available}"
            ) from e
