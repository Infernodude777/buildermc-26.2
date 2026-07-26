package net.infernodude777.buildermc.network;

import com.google.gson.annotations.SerializedName;

import java.util.ArrayList;
import java.util.List;

/**
 * Deserialized response from {@code POST /build}.
 * <p>
 * Fields are non-final so Gson can populate them directly. The
 * {@code decisions} list (Populated by the IntelligentBuilder) explains each
 * design choice for debugging. {@code placements} lets the mod paste the
 * structure immediately without parsing the {@code .schem} file itself.
 */
public class BackendResponse {

    @SerializedName("status")
    public String status = "";

    @SerializedName("schematic")
    public String schematic = "";

    @SerializedName("dimensions")
    public int[] dimensions = new int[0];

    @SerializedName("placements")
    public List<Placement> placements = new ArrayList<>();

    @SerializedName("decisions")
    public List<String> decisions = new ArrayList<>();

    public boolean isSuccess() {
        return "success".equalsIgnoreCase(status);
    }

    /**
     * A single block placement in schematic-local coordinates. Matches the
     * backend's ``BlockPlacementEntry`` schema.
     */
    public static class Placement {
        @SerializedName("x")
        public int x;

        @SerializedName("y")
        public int y;

        @SerializedName("z")
        public int z;

        @SerializedName("block_state")
        public String blockState = "";
    }

    @Override
    public String toString() {
        String dim = dimensions.length == 3
                ? dimensions[0] + "x" + dimensions[1] + "x" + dimensions[2]
                : "?";
        return String.format("BackendResponse{status=%s, schematic=%s, dim=%s, decisions=%d}",
                status, schematic, dim, decisions.size());
    }
}
