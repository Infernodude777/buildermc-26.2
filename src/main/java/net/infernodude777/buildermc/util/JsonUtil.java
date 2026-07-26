package net.infernodude777.buildermc.util;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;

/**
 * Thin Gson wrapper — keeps a single compact and a single pretty-printing
 * instance so we don't rebuild Gson on every call.
 */
public final class JsonUtil {

    private static final Gson COMPACT = new Gson();
    private static final Gson PRETTY = new GsonBuilder().setPrettyPrinting().create();

    private JsonUtil() {
    }

    /** Compact JSON (for network payloads). */
    public static String toJson(Object obj) {
        return COMPACT.toJson(obj);
    }

    /** Pretty-printed JSON (for config files / logging). */
    public static String toPrettyJson(Object obj) {
        return PRETTY.toJson(obj);
    }

    /** Deserialize a JSON string into the given class. */
    public static <T> T fromJson(String json, Class<T> clazz) {
        return COMPACT.fromJson(json, clazz);
    }

    /** Parse a JSON string into a {@link JsonObject}. */
    public static JsonObject parseObject(String json) {
        return JsonParser.parseString(json).getAsJsonObject();
    }
}
