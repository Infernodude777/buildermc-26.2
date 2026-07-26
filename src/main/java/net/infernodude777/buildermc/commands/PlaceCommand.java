package net.infernodude777.buildermc.commands;

import com.mojang.brigadier.context.CommandContext;

import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;

import net.infernodude777.buildermc.BuilderMC;
import net.infernodude777.buildermc.network.BackendResponse;
import net.infernodude777.buildermc.service.BuildService;
import net.infernodude777.buildermc.service.PlacementService;
import net.infernodude777.buildermc.util.MessageUtil;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;

/**
 * Registers the {@code /place} command.
 * <p>
 * Places the most recently generated structure around the calling player.
 * The build response (including raw block placements) is kept in memory by
 * {@link BuildService}; it is lost on server restart.
 */
public final class PlaceCommand {

    private PlaceCommand() {
    }

    public static void register(BuildService buildService) {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            dispatcher.register(
                    Commands.literal("place")
                            .executes(context -> execute(buildService, context)));
            BuilderMC.LOGGER.info("[buildermc] Registered /place command.");
        });
    }

    private static int execute(BuildService buildService, CommandContext<CommandSourceStack> context) {
        CommandSourceStack source = context.getSource();
        ServerPlayer player = source.getPlayer();
        if (player == null) {
            source.sendSuccess(() -> Component.literal("Only players can run /place."), false);
            return 0;
        }

        BackendResponse last = buildService.getLastResponse(player.getUUID());
        if (last == null) {
            MessageUtil.sendError(player, "No structure to place. Use /build <prompt> first.");
            return 0;
        }

        PlacementService.placeLast(player, last);
        return 1;
    }
}
