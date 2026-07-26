package net.infernodude777.buildermc.models;

import com.google.gson.annotations.SerializedName;

/**
 * A single build request — the JSON body POSTed to {@code /build}.
 */
public class BuildTask {

    @SerializedName("prompt")
    public final String prompt;

    @SerializedName("seed")
    public final long seed;

    @SerializedName("world_context")
    public final WorldContext worldContext;

    @SerializedName("provider_config")
    public final ProviderConfig providerConfig;

    public BuildTask(String prompt, long seed, WorldContext worldContext, ProviderConfig providerConfig) {
        this.prompt = prompt;
        this.seed = seed;
        this.worldContext = worldContext;
        this.providerConfig = providerConfig;
    }

    /**
     * Optional AI provider configuration forwarded from the mod's /api command.
     */
    public static class ProviderConfig {
        @SerializedName("provider")
        public final String provider;

        @SerializedName("base_url")
        public final String baseUrl;

        @SerializedName("model_id")
        public final String modelId;

        @SerializedName("api_key")
        public final String apiKey;

        /** Convenience constructor that defaults provider to "openai". */
        public ProviderConfig(String baseUrl, String modelId, String apiKey) {
            this("openai", baseUrl, modelId, apiKey);
        }

        public ProviderConfig(String provider, String baseUrl, String modelId, String apiKey) {
            this.provider = provider != null ? provider : "openai";
            this.baseUrl = baseUrl;
            this.modelId = modelId;
            this.apiKey = apiKey;
        }
    }
}
