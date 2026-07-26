package net.infernodude777.buildermc.commands;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;

import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;

import net.infernodude777.buildermc.BuilderMC;
import net.infernodude777.buildermc.config.BuilderMCConfig;
import net.infernodude777.buildermc.config.ModConfigLoader;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;

/**
 * Registers the {@code /api <base_url> <model_id> <api_key> [provider]} command.
 * <p>
 * Persists the supplied AI provider details to {@code config/buildermc.json}
 * so they survive restarts. The key is masked in logs and chat.
 */
public final class ApiCommand {

    private static final int KEY_MASK_LENGTH = 4;

    private ApiCommand() {
    }

    public static void register(BuilderMCConfig config) {
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            dispatcher.register(
                    Commands.literal("api")
                            .then(Commands.argument("base_url", StringArgumentType.string())
                                    .then(Commands.argument("model_id", StringArgumentType.string())
                                            .then(Commands.argument("api_key", StringArgumentType.string())
                                                    .executes(context -> execute(config, context, "openai"))
                                                    .then(Commands.argument("provider", StringArgumentType.string())
                                                            .executes(context -> execute(config, context,
                                                                    StringArgumentType.getString(context, "provider"))))))));
            BuilderMC.LOGGER.info("[buildermc] Registered /api command.");
        });
    }

    private static int execute(BuilderMCConfig config, CommandContext<CommandSourceStack> context, String provider) {
        String baseUrl = StringArgumentType.getString(context, "base_url");
        String modelId = StringArgumentType.getString(context, "model_id");
        String apiKey = StringArgumentType.getString(context, "api_key");

        if (baseUrl.isBlank() || modelId.isBlank() || apiKey.isBlank()) {
            context.getSource().sendSuccess(
                    () -> Component.literal("Usage: /api <base_url> <model_id> <api_key> [provider]"), false);
            return 0;
        }
        // Note: api_key is a regular (space-free) string so an trailing optional
        // provider argument can be supported. API keys supplied by major providers
        // do not contain spaces.

        config.apiBaseUrl = baseUrl.replaceAll("/+$", "");
        config.apiModelId = modelId;
        config.apiKey = apiKey;
        config.apiProvider = provider == null || provider.isBlank() ? "openai" : provider.strip().toLowerCase();
        ModConfigLoader.save(config);

        BuilderMC.LOGGER.info("[buildermc] /api updated: base_url={}  model={}  provider={}",
                config.apiBaseUrl, config.apiModelId, config.apiProvider);
        String masked = mask(apiKey);
        context.getSource().sendSuccess(
                () -> Component.literal("API config saved. Provider: " + config.apiProvider + "  Key: " + masked), false);
        return 1;
    }

    private static String mask(String key) {
        if (key.length() <= KEY_MASK_LENGTH) {
            return "****";
        }
        return "..." + key.substring(key.length() - KEY_MASK_LENGTH);
    }
}
