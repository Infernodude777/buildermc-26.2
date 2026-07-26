package net.infernodude777.buildermc.service;

import net.infernodude777.buildermc.BuilderMC;
import net.infernodude777.buildermc.network.BackendResponse;
import net.infernodude777.buildermc.util.MessageUtil;

import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

import java.util.ArrayList;
import java.util.List;

/**
 * Places a backend-generated structure into the Minecraft world.
 * <p>
 * The mod never invents block positions — it receives a list of placements
 * from the backend and applies them to the world. Placement happens in small
 * batches scheduled on the server tick to keep the server responsive.
 *
 * <p>Block-state strings are parsed with best-effort syntax parsing: simple
 * names like {@code minecraft:stone} resolve directly to the block's default
 * state; names with bracket properties are stripped to the base block, then the
 * default state is used. This keeps the mod lightweight (no full NBT parser).
 */
public class SchematicPlacer {

    /** Number of blocks placed per server tick. Tweak to balance speed and TPS. */
    private static final int BLOCKS_PER_TICK = 200;

    public SchematicPlacer() {
    }

    /**
     * Schedules a placement task on the server thread.
     *
     * @param player    The player requesting the build; used for feedback.
     * @param origin    World position where the structure will be anchored.
     * @param response  The backend response containing placements.
     */
    public void place(ServerPlayer player, BlockPos origin, BackendResponse response) {
        if (response.placements == null || response.placements.isEmpty()) {
            MessageUtil.sendInfo(player, "No block placements received; structure was only saved to file.");
            return;
        }

        MinecraftServer server = player.level().getServer();
        if (server == null) {
            BuilderMC.LOGGER.error("[buildermc] cannot place blocks: no server attached to player level");
            return;
        }

        List<PendingBlock> queue = new ArrayList<>(response.placements.size());
        for (BackendResponse.Placement p : response.placements) {
            queue.add(new PendingBlock(p.x, p.y, p.z, p.blockState));
        }

        BuilderMC.LOGGER.info("[buildermc] scheduling placement of {} blocks at {}", queue.size(), origin);
        MessageUtil.sendInfo(player, "Placing " + queue.size() + " blocks...");

        server.execute(() -> new PlacementJob(server, player, origin, queue).run());
    }

    /** Internal job that places blocks in batches each tick. */
    private final class PlacementJob {
        private final MinecraftServer server;
        private final ServerPlayer player;
        private final BlockPos origin;
        private final List<PendingBlock> queue;
        private int index;

        PlacementJob(MinecraftServer server, ServerPlayer player, BlockPos origin, List<PendingBlock> queue) {
            this.server = server;
            this.player = player;
            this.origin = origin;
            this.queue = queue;
        }

        void run() {
            if (!player.isAlive()) {
                BuilderMC.LOGGER.warn("[buildermc] player logged out before placement completed");
                return;
            }
            ServerLevel level = player.level();
            int placedThisTick = 0;
            while (index < queue.size() && placedThisTick < BLOCKS_PER_TICK) {
                PendingBlock pending = queue.get(index);
                BlockState state = resolveState(pending.blockState);
                if (state != null) {
                    BlockPos target = origin.offset(pending.x, pending.y, pending.z);
                    level.setBlock(target, state, Block.UPDATE_ALL);
                }
                index++;
                placedThisTick++;
            }

            if (index < queue.size()) {
                server.execute(this::run);
            } else {
                BuilderMC.LOGGER.info("[buildermc] placement complete: {} blocks", queue.size());
                MessageUtil.sendSuccess(player, "Placement complete: " + queue.size() + " blocks.");
            }
        }

        /** Best-effort block-state resolution. */
        private BlockState resolveState(String blockState) {
            if (blockState == null || blockState.isBlank()) {
                return null;
            }
            String base = blockState.split("\\[", 2)[0].trim();
            Block block = BuiltInRegistries.BLOCK.getValue(Identifier.parse(base));
            if (block == null) {
                BuilderMC.LOGGER.warn("[buildermc] unknown block id: {}", base);
                return null;
            }
            return block.defaultBlockState();
        }
    }

    private record PendingBlock(int x, int y, int z, String blockState) {
    }
}
