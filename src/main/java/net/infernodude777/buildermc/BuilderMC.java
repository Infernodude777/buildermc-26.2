package net.infernodude777.buildermc;

import net.fabricmc.api.ModInitializer;

import net.infernodude777.buildermc.commands.ApiCommand;
import net.infernodude777.buildermc.commands.BuildCommand;
import net.infernodude777.buildermc.commands.PlaceCommand;
import net.infernodude777.buildermc.config.BuilderMCConfig;
import net.infernodude777.buildermc.config.ModConfigLoader;
import net.infernodude777.buildermc.network.BackendClient;
import net.infernodude777.buildermc.service.BuildService;
import net.infernodude777.buildermc.service.WorldContextCollector;

import net.minecraft.resources.Identifier;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * builderMC mod entrypoint.
 * <p>
 * Wires collaborators (config → backend client → context collector → build
 * service) and registers the {@code /aibuild} command. All collaborators are
 * constructed once here and injected where needed — no service-locator / global
 * state, which keeps the mod testable and the dependency graph explicit.
 */
public class BuilderMC implements ModInitializer {

    public static final String MOD_ID = "buildermc";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    @Override
    public void onInitialize() {
        LOGGER.info("[buildermc] Initializing AI builder mod.");

        BuilderMCConfig config = ModConfigLoader.load();
        config.log();

        BackendClient backendClient = new BackendClient(config);
        WorldContextCollector contextCollector = new WorldContextCollector(config);
        BuildService buildService = new BuildService(backendClient, contextCollector, config);

        BuildCommand.register(buildService);
        PlaceCommand.register(buildService);
        ApiCommand.register(config);

        LOGGER.info("[buildermc] Ready. Use /build <prompt> to generate a structure, /place to paste it, /api to configure the AI provider.");
    }

    /** Builds an {@link Identifier} in this mod's namespace. */
    public static Identifier id(String path) {
        return Identifier.fromNamespaceAndPath(MOD_ID, path);
    }
}
