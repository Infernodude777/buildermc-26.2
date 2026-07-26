package net.infernodude777.buildermc.service;

import net.infernodude777.buildermc.BuilderMC;
import net.infernodude777.buildermc.config.BuilderMCConfig;
import net.infernodude777.buildermc.models.WorldContext;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;

import java.util.HashSet;
import java.util.Set;

/**
 * Collects a {@link WorldContext} snapshot around the player.
 * <p>
 * Must be called on the server thread (it reads world state). Broad scans are
 * subsampled every 2 blocks to keep the cost manageable for a one-shot command.
 *
 * <p>Ported to Minecraft 26.2 unobfuscated (Mojang) mappings. Biome id is
 * obtained via {@code Holder.unwrapKey().identifier()} (no Yarn
 * {@code Registries.BIOME.getId}).
 */
public class WorldContextCollector {

    private final BuilderMCConfig config;

    public WorldContextCollector(BuilderMCConfig config) {
        this.config = config;
    }

    public WorldContext collect(ServerPlayer player) {
        ServerLevel level = player.level();
        BlockPos origin = player.blockPosition();
        int r = config.buildRadius;

        WorldContext ctx = new WorldContext();
        ctx.buildRadius = r;
        ctx.playerPosition = new int[]{origin.getX(), origin.getY(), origin.getZ()};
        ctx.playerFacing = player.getDirection().getName();

        // Single-column facts.
        ctx.biome = biomeId(level, origin);
        int surfaceY = surfaceHeight(level, origin, r);
        ctx.terrainHeight = surfaceY;
        ctx.surfaceBlock = blockId(level.getBlockState(
                new BlockPos(origin.getX(), surfaceY, origin.getZ())).getBlock());

        // Broad scans — subsampled every 2 blocks for performance.
        int waterCells = 0;
        int logCells = 0;
        int plankCells = 0;
        int minY = origin.getY() - r;
        int maxY = origin.getY() + r;
        for (int x = origin.getX() - r; x <= origin.getX() + r; x += 2) {
            for (int z = origin.getZ() - r; z <= origin.getZ() + r; z += 2) {
                for (int y = minY; y <= maxY; y += 2) {
                    BlockState state = level.getBlockState(new BlockPos(x, y, z));
                    if (state.getBlock() == Blocks.WATER) {
                        waterCells++;
                    } else if (state.is(BlockTags.LOGS)) {
                        logCells++;
                    } else if (state.is(BlockTags.PLANKS)) {
                        plankCells++;
                    }
                }
            }
        }
        ctx.nearbyWater = waterCells > 0;
        ctx.nearbyTrees = logCells;
        ctx.nearbyBuildings = plankCells;

        // Nearby entities (distinct type ids within the radius box).
        AABB box = AABB.ofSize(player.position(), r * 2.0, r * 2.0, r * 2.0);
        Set<String> entityTypes = new HashSet<>();
        for (Entity e : level.getEntities(player, box, e -> true)) {
            String id = entityId(e);
            if (id != null) {
                entityTypes.add(id);
            }
        }
        ctx.nearbyEntities.addAll(entityTypes);

        BuilderMC.LOGGER.info("[buildermc] collected world context: {}", ctx);
        return ctx;
    }

    private static String biomeId(ServerLevel level, BlockPos pos) {
        try {
            Holder<Biome> holder = level.getBiome(pos);
            return holder.unwrapKey()
                    .map(key -> key.identifier().toString())
                    .orElse("unknown");
        } catch (Throwable t) {
            BuilderMC.LOGGER.warn("[buildermc] biome lookup failed: {}", t.toString());
            return "unknown";
        }
    }

    private static String blockId(Block block) {
        try {
            return BuiltInRegistries.BLOCK.getKey(block).toString();
        } catch (Throwable t) {
            return "unknown";
        }
    }

    private static String entityId(Entity entity) {
        try {
            return BuiltInRegistries.ENTITY_TYPE.getKey(entity.getType()).toString();
        } catch (Throwable t) {
            return null;
        }
    }

    /**
     * Y of the highest non-air, non-water block in the column at (x,z), bounded
     * to the scan radius.
     */
    private static int surfaceHeight(ServerLevel level, BlockPos pos, int r) {
        int x = pos.getX();
        int z = pos.getZ();
        for (int y = pos.getY() + r; y >= pos.getY() - r; y--) {
            BlockState state = level.getBlockState(new BlockPos(x, y, z));
            if (!state.isAir() && state.getBlock() != Blocks.WATER) {
                return y;
            }
        }
        return pos.getY();
    }
}
