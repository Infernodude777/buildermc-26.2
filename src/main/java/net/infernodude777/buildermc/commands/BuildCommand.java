package net.infernodude777.buildermc.commands;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;

import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;

import net.infernodude777.buildermc.BuilderMC;
import net.infernodude777.buildermc.service.BuildService;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;

/**
 * Registers the {@code /build <prompt>} command.
 * <p>
 * The command holds no business logic — it validates that the caller is a
 * player and delegates to {@link BuildService}. {@code <prompt>} is a greedy
 * string so the whole rest of the line is captured as the build prompt.
 */
public final class BuildCommand {

    private BuildCommand() {
    }

    public static void register(BuildService buildService) {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            dispatcher.register(
                    Commands.literal("build")
                            .then(Commands.argument("prompt", StringArgumentType.greedyString())
                                    .executes(context -> execute(buildService, context))));
            BuilderMC.LOGGER.info("[buildermc] Registered /build command.");
        });
    }

    private static int execute(BuildService buildService, CommandContext<CommandSourceStack> context) {
        CommandSourceStack source = context.getSource();
        ServerPlayer player = source.getPlayer();
        if (player == null) {
            source.sendSuccess(() -> Component.literal("Only players can run /build."), false);
            return 0;
        }
        String prompt = StringArgumentType.getString(context, "prompt");
        buildService.startBuild(player, prompt);
        return 1;
    }
}
