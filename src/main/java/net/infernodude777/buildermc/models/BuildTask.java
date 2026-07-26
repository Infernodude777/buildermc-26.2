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

    public BuildTask(String prompt, long seed, WorldContext worldContext) {
        this.prompt = prompt;
        this.seed = seed;
        this.worldContext = worldContext;
    }
}
