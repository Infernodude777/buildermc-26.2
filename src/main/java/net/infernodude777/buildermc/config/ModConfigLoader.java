package net.infernodude777.buildermc.config;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;

import net.infernodude777.buildermc.BuilderMC;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * Loads {@link BuilderMCConfig} from {@code config/buildermc.json} (relative to
 * the game working directory) and writes a default file on first run.
 */
public final class ModConfigLoader {

    private static final Gson GSON = new GsonBuilder().setPrettyPrinting().create();
    private static final Path CONFIG_DIR = Paths.get("config");
    private static final Path CONFIG_FILE = CONFIG_DIR.resolve("buildermc.json");

    private ModConfigLoader() {
    }

    /** Returns the config, creating a default file on disk if none exists. */
    public static BuilderMCConfig load() {
        if (!Files.exists(CONFIG_FILE)) {
            BuilderMCConfig defaults = new BuilderMCConfig();
            save(defaults);
            BuilderMC.LOGGER.info("[buildermc] Created default config at {}", CONFIG_FILE);
            return defaults;
        }

        try {
            String json = Files.readString(CONFIG_FILE);
            BuilderMCConfig config = GSON.fromJson(json, BuilderMCConfig.class);
            if (config == null) {
                BuilderMC.LOGGER.warn("[buildermc] Config parsed to null — using defaults.");
                return new BuilderMCConfig();
            }
            // Backfill any null fields from a fresh default (forward-compatible).
            BuilderMCConfig defaults = new BuilderMCConfig();
            if (config.backendUrl == null) config.backendUrl = defaults.backendUrl;
            BuilderMC.LOGGER.info("[buildermc] Loaded config from {}", CONFIG_FILE);
            return config;
        } catch (IOException | com.google.gson.JsonSyntaxException e) {
            BuilderMC.LOGGER.error("[buildermc] Failed to load config — using defaults.", e);
            return new BuilderMCConfig();
        }
    }

    /** Persists the config to disk (best-effort). */
    public static void save(BuilderMCConfig config) {
        try {
            Files.createDirectories(CONFIG_DIR);
            Files.writeString(CONFIG_FILE, GSON.toJson(config));
        } catch (IOException e) {
            BuilderMC.LOGGER.error("[buildermc] Failed to save config.", e);
        }
    }
}
