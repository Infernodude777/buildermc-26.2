package net.infernodude777.buildermc.models;

import com.google.gson.annotations.SerializedName;

import java.util.ArrayList;
import java.util.List;

/**
 * Represents a generated schematic returned by the Python backend.
 * <p>
 * This is a convenience model used by the mod when the backend returns a rich
 * result (e.g. from a download endpoint). The normal {@code /build} response is
 * deserialized directly into {@link net.infernodude777.buildermc.network.BackendResponse}.
 */
public class SchematicResult {

    @SerializedName("status")
    public String status = "";

    @SerializedName("schematic")
    public String schematic = "";

    @SerializedName("dimensions")
    public int[] dimensions = new int[0];

    @SerializedName("placements")
    public List<BlockPlacement> placements = new ArrayList<>();

    @SerializedName("decisions")
    public List<String> decisions = new ArrayList<>();

    @SerializedName("error")
    public String error = "";

    public boolean isSuccess() {
        return "success".equalsIgnoreCase(status);
    }

    @Override
    public String toString() {
        return String.format(
                "SchematicResult{status=%s, schematic=%s, dims=%s, blocks=%d, decisions=%d}",
                status, schematic, dimensions.length == 3 ? dimensions[0] + "x" + dimensions[1] + "x" + dimensions[2] : "?",
                placements.size(), decisions.size());
    }

    /** Single block placement inside a schematic. */
    public static class BlockPlacement {
        @SerializedName("x")
        public final int x;

        @SerializedName("y")
        public final int y;

        @SerializedName("z")
        public final int z;

        @SerializedName("block_state")
        public final String blockState;

        public BlockPlacement(int x, int y, int z, String blockState) {
            this.x = x;
            this.y = y;
            this.z = z;
            this.blockState = blockState;
        }
    }
}
