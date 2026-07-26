package net.infernodude777.buildermc.models;

import com.google.gson.annotations.SerializedName;

import java.util.ArrayList;
import java.util.List;

/**
 * Serialized snapshot of the world around the player.
 * <p>
 * Sent with every build request so the backend can adapt the design. The
 * backend's Pydantic model accepts unknown fields (extra = "allow"), so adding
 * a new field here will never break an older backend.
 */
public class WorldContext {

    @SerializedName("biome")
    public String biome = "";

    @SerializedName("terrain_height")
    public int terrainHeight;

    @SerializedName("surface_block")
    public String surfaceBlock = "";

    @SerializedName("nearby_trees")
    public int nearbyTrees;

    @SerializedName("nearby_water")
    public boolean nearbyWater;

    @SerializedName("nearby_buildings")
    public int nearbyBuildings;

    @SerializedName("nearby_entities")
    public List<String> nearbyEntities = new ArrayList<>();

    @SerializedName("player_position")
    public int[] playerPosition = new int[3];

    @SerializedName("player_facing")
    public String playerFacing = "";

    @SerializedName("build_radius")
    public int buildRadius;

    public WorldContext() {
    }

    @Override
    public String toString() {
        return String.format(
                "WorldContext{biome=%s, terrain=%d, surface=%s, trees=%d, water=%s, buildings=%d, "
                        + "entities=%d, pos=[%d,%d,%d], facing=%s, radius=%d}",
                biome, terrainHeight, surfaceBlock, nearbyTrees, nearbyWater,
                nearbyBuildings, nearbyEntities.size(),
                playerPosition[0], playerPosition[1], playerPosition[2],
                playerFacing, buildRadius);
    }
}
