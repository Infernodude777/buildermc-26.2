package net.infernodude777.buildermc.network;

import net.infernodude777.buildermc.BuilderMC;
import net.infernodude777.buildermc.config.BuilderMCConfig;
import net.infernodude777.buildermc.models.BuildTask;
import net.infernodude777.buildermc.util.JsonUtil;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.concurrent.CompletableFuture;

/**
 * Asynchronous HTTP client for the Python backend.
 * <p>
 * Uses the built-in {@link java.net.http.HttpClient} (Java 11+) so the mod has
 * no extra networking dependencies and requests never block the server thread.
 * Errors are mapped into the {@link BackendException} hierarchy so callers can
 * branch on failure type.
 *
 * <p>The client exposes a generic {@link #postJson(String, Object, Class)} method
 * so new endpoints can be added without duplicating HTTP plumbing. The
 * higher-level {@link #requestBuild(BuildTask)} method is a thin wrapper around
 * that primitive.
 *
 * <p>Transient connection failures are retried up to the configured
 * {@code maxRetries}. Only the first connection attempt is logged at INFO; each
 * retry is logged at WARN so operators can spot flaky networks.
 */
public class BackendClient {

    private final BuilderMCConfig config;
    private final HttpClient http;

    public BackendClient(BuilderMCConfig config) {
        this.config = config;
        this.http = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(config.connectTimeoutSeconds))
                .build();
    }

    /**
     * POST a {@link BuildTask} to {@code /build} and return a future that
     * completes with a validated {@link BackendResponse}, or fails with a
     * {@link BackendException} subtype.
     */
    public CompletableFuture<BackendResponse> requestBuild(BuildTask task) {
        String path = "/build";
        return postJson(path, task, BackendResponse.class)
                .thenApply(this::validateBuildResponse);
    }

    /**
     * Generic async POST of a JSON payload to a backend endpoint.
     *
     * @param path          Relative path (e.g. {@code /build}).
     * @param body          Request body object (serialized to JSON).
     * @param responseClass Class to deserialize the JSON response into.
     * @param <T>           Response type.
     * @return A future completing with the deserialized response.
     */
    public <T> CompletableFuture<T> postJson(String path, Object body, Class<T> responseClass) {
        String url = config.backendUrl.replaceAll("/+$", "") + path;
        String json = JsonUtil.toJson(body);
        HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(url))
                .timeout(Duration.ofSeconds(config.requestTimeoutSeconds))
                .header("Content-Type", "application/json")
                .header("Accept", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(json))
                .build();

        BuilderMC.LOGGER.info("[buildermc] POST {} | body length={}", url, json.length());
        return sendWithRetries(url, request, 0, responseClass);
    }

    /** Loop-based retry helper that stays fully asynchronous. */
    private <T> CompletableFuture<T> sendWithRetries(String url, HttpRequest request, int attempt, Class<T> responseClass) {
        return http.sendAsync(request, HttpResponse.BodyHandlers.ofString())
                .thenApply(resp -> handleResponse(resp, responseClass))
                .exceptionallyCompose(error -> {
                    Throwable cause = (error.getCause() != null) ? error.getCause() : error;

                    // Never retry semantic failures (HTTP errors, parse errors, invalid responses).
                    if (cause instanceof BackendException) {
                        return CompletableFuture.failedFuture(cause);
                    }

                    if (attempt < config.maxRetries) {
                        BuilderMC.LOGGER.warn("[buildermc] backend request failed (attempt {}): {} — retrying...",
                                attempt + 1, cause.getMessage());
                        return sleep(500L).thenCompose(v -> sendWithRetries(url, request, attempt + 1, responseClass));
                    }

                    return CompletableFuture.failedFuture(
                            new BackendException.ConnectionFailed(
                                    "Could not reach backend at " + url + ": " + cause.getMessage(), cause));
                });
    }

    private <T> T handleResponse(HttpResponse<String> resp, Class<T> responseClass) {
        int code = resp.statusCode();
        String body = resp.body();

        if (code < 200 || code >= 300) {
            throw new BackendException.HttpError(code,
                    "Backend returned HTTP " + code + ": " + truncate(body));
        }

        try {
            T parsed = JsonUtil.fromJson(body, responseClass);
            if (parsed == null) {
                throw new BackendException.ParseError("Backend response was null: " + truncate(body), null);
            }
            BuilderMC.LOGGER.info("[buildermc] backend response: {}", parsed);
            return parsed;
        } catch (BackendException e) {
            throw e;
        } catch (Exception e) {
            throw new BackendException.ParseError(
                    "Unparseable backend response: " + truncate(body), e);
        }
    }

    private BackendResponse validateBuildResponse(BackendResponse response) {
        if (!response.isSuccess()) {
            throw new BackendException.InvalidResponse(
                    "Backend reported failure: " + response.status);
        }
        if (response.schematic == null || response.schematic.isBlank()) {
            throw new BackendException.InvalidResponse("Backend response missing schematic path.");
        }
        return response;
    }

    private static CompletableFuture<Void> sleep(long millis) {
        return CompletableFuture.runAsync(() -> {
            try {
                Thread.sleep(millis);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new RuntimeException(e);
            }
        });
    }

    private static String truncate(String s) {
        if (s == null) return "";
        return s.length() > 300 ? s.substring(0, 300) + "…" : s;
    }
}
