package net.infernodude777.buildermc.service;

import net.infernodude777.buildermc.BuilderMC;
import net.infernodude777.buildermc.network.BackendResponse;
import net.infernodude777.buildermc.util.MessageUtil;

import net.minecraft.commands.arguments.blocks.BlockStateParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.block.state.BlockState;

import java.util.List;

/**
 * Places a previously generated structure into the world block by block.
 * <p>
 * Placements are interpreted as schematic-local coordinates. They are pasted
 * with their origin at the player's feet, respecting the player's facing
 * direction if desired. The actual placement work runs on the server thread so
 * it is safe to mutate world state.
 */
public class PlacementService {

    /** Try to parse a block-state string. Returns null if parsing fails. */
    private static BlockState parseState(String state) {
        try {
            return BlockStateParser.parseForBlock(BuiltInRegistries.BLOCK, state, true).blockState();
        } catch (Exception e) {
            BuilderMC.LOGGER.warn("[buildermc] could not parse block state '{}': {}", state, e.getMessage());
            return null;
        }
    }

    /** Place the last generated response around the player. */
    public static void placeLast(ServerPlayer player, BackendResponse response) {
        if (response == null || response.placements == null || response.placements.isEmpty()) {
            MessageUtil.sendError(player, "No placement data available. Generate a structure with /build first.");
            return;
        }

        MinecraftServer server = player.level().getServer();
        if (server == null) {
            MessageUtil.sendError(player, "Cannot place: no server.");
            return;
        }

        BlockPos origin = player.blockPosition();
        List<BackendResponse.Placement> placements = response.placements;
        MessageUtil.sendInfo(player, "Placing " + placements.size() + " blocks...");
        BuilderMC.LOGGER.info("[buildermc] scheduling placement of {} blocks at {}", placements.size(), origin);

        server.execute(() -> placeAll(player, origin, placements));
    }

    private static void placeAll(ServerPlayer player, BlockPos origin, List<BackendResponse.Placement> placements) {
        ServerLevel level = player.level();
        int placed = 0;
        int failed = 0;

        for (BackendResponse.Placement p : placements) {
            BlockPos target = origin.offset(p.x, p.y, p.z);
            BlockState state = parseState(p.blockState);
            if (state == null) {
                failed++;
                continue;
            }

            level.setBlock(target, state, 3);
            placed++;
        }

        int finalPlaced = placed;
        int finalFailed = failed;
        BuilderMC.LOGGER.info("[buildermc] placement done: placed={} failed={}", finalPlaced, finalFailed);
        MessageUtil.sendSuccess(player, "Placed " + finalPlaced + " blocks" +
                (finalFailed > 0 ? " (" + finalFailed + " failed)" : ")"));
    }
}
