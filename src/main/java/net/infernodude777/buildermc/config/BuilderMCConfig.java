package net.infernodude777.buildermc.config;

/**
 * Mod configuration loaded from {@code config/buildermc.json}.
 * <p>
 * Fields are public so Gson can (de)serialize them without reflection helpers.
 * Defaults are safe for local development against the bundled Python backend.
 */
public class BuilderMCConfig {

    /** Base URL of the Python backend (no trailing slash). */
    public String backendUrl = "http://localhost:8000";

    /** TCP connect timeout in seconds. */
    public int connectTimeoutSeconds = 10;

    /** Full HTTP request timeout in seconds — generation can be slow. */
    public int requestTimeoutSeconds = 120;

    /** Radius (in blocks) around the player scanned for world context. */
    public int buildRadius = 16;

    /** How many times to retry a failed backend request before giving up. */
    public int maxRetries = 2;

    /** Optional AI provider API base URL (e.g. https://api.openai.com/v1). */
    public String apiBaseUrl = "";

    /** Model identifier used on the optional AI provider. */
    public String apiModelId = "";

    /** API key for the optional AI provider (stored locally; never logged fully). */
    public String apiKey = "";

    /** Provider type (e.g. "openai", "nvidia"). Defaults to openai-compatible endpoints. */
    public String apiProvider = "openai";

    /** Logs the effective configuration at INFO level. */
    public void log() {
        net.infernodude777.buildermc.BuilderMC.LOGGER.info(
                "[buildermc] config  | backend={}  connectTimeout={}s  requestTimeout={}s  radius={}  retries={}",
                backendUrl, connectTimeoutSeconds, requestTimeoutSeconds,
                buildRadius, maxRetries);
        boolean hasApi = apiBaseUrl != null && !apiBaseUrl.isBlank();
        net.infernodude777.buildermc.BuilderMC.LOGGER.info(
                "[buildermc] config  | api configured={}  model={}",
                hasApi, apiModelId);
    }
}
