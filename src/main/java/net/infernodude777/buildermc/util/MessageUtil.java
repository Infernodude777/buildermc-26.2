package net.infernodude777.buildermc.util;

import net.minecraft.ChatFormatting;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;

/**
 * Thread-safe chat feedback for players.
 * <p>
 * When called from an async thread (e.g. an HTTP completion handler), the
 * message is queued onto the server thread via {@link MinecraftServer#executeIfPossible}
 * so we never touch entity state off-thread.
 *
 * <p>Ported to Minecraft 26.2 unobfuscated (Mojang) mappings:
 * {@code Text} → {@link Component}, {@code Formatting} → {@link ChatFormatting},
 * {@code sendMessage(Text, boolean)} → {@code sendSystemMessage(Component)}.
 */
public final class MessageUtil {

    private MessageUtil() {
    }

    /** Plain white message. */
    public static void send(ServerPlayer player, String message) {
        dispatch(player, Component.literal(message));
    }

    /** Green success message. */
    public static void sendSuccess(ServerPlayer player, String message) {
        dispatch(player, Component.literal(message).withStyle(ChatFormatting.GREEN));
    }

    /** Red error message. */
    public static void sendError(ServerPlayer player, String message) {
        dispatch(player, Component.literal(message).withStyle(ChatFormatting.RED));
    }

    /** Gold/amber informational message. */
    public static void sendInfo(ServerPlayer player, String message) {
        dispatch(player, Component.literal(message).withStyle(ChatFormatting.GOLD));
    }

    private static void dispatch(ServerPlayer player, Component text) {
        if (player == null) {
            return;
        }
        // 26.2: ServerPlayer/Entity have no getServer(); Level (via level())
        // exposes the canonical getServer() returning the MinecraftServer.
        MinecraftServer server = player.level().getServer();
        if (server != null) {
            // Queue onto the server thread — 26.2 uses executeIfPossible
            // (MinecraftServer extends ReentrantBlockableEventLoop, not Executor).
            server.executeIfPossible(() -> player.sendSystemMessage(text));
        } else {
            // No server reference — best-effort direct send.
            player.sendSystemMessage(text);
        }
    }
}
