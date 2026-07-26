package net.infernodude777.buildermc.service;

import net.infernodude777.buildermc.BuilderMC;
import net.infernodude777.buildermc.models.BuildTask;
import net.infernodude777.buildermc.models.WorldContext;
import net.infernodude777.buildermc.network.BackendClient;
import net.infernodude777.buildermc.network.BackendException;
import net.infernodude777.buildermc.network.BackendResponse;
import net.infernodude777.buildermc.util.MessageUtil;

import net.minecraft.server.level.ServerPlayer;

import java.util.concurrent.CompletableFuture;

/**
 * Orchestrates a build request from the mod to the Python backend.
 * <p>
 * Responsibilities are limited to:
 * <ol>
 *   <li>Notify the player that generation has started,</li>
 *   <li>Collect world context on the server thread,</li>
 *   <li>Send an async HTTP POST to the backend,</li>
 *   <li>Parse and verify the JSON response,</li>
 *   <li>Report success or failure back to the player thread-safely.</li>
 * </ol>
 * The server thread is never blocked: HTTP work happens on the
 * {@link java.net.http.HttpClient} executor; player messages are dispatched
 * back onto the server thread by {@link MessageUtil}.
 *
 * <p>Schematic placement is intentionally <strong>not</strong> implemented here
 * yet. That will be wired in once the mod-side placement pipeline is ready.
 */
public class BuildService {

    private final BackendClient backendClient;
    private final WorldContextCollector contextCollector;

    public BuildService(BackendClient backendClient, WorldContextCollector contextCollector) {
        this.backendClient = backendClient;
        this.contextCollector = contextCollector;
    }

    /** Begins an asynchronous build. Returns immediately; feedback is sent later. */
    public void startBuild(ServerPlayer player, String prompt) {
        if (prompt == null || prompt.isBlank()) {
            MessageUtil.sendError(player, "Prompt cannot be empty.");
            return;
        }
        MessageUtil.sendInfo(player, "Generating structure...");
        BuilderMC.LOGGER.info("[buildermc] build started for player={} prompt={}",
                player.getName().getString(), prompt);

        // Collect world context synchronously (we're on the server thread).
        WorldContext context;
        try {
            context = contextCollector.collect(player);
            BuilderMC.LOGGER.info("[buildermc] world context collected: {}", context);
        } catch (Exception e) {
            BuilderMC.LOGGER.error("[buildermc] Failed to collect world context.", e);
            context = new WorldContext(); // empty context — backend still works
        }

        long seed = player.level().getSeed();
        BuildTask task = new BuildTask(prompt, seed, context);
        long startMs = System.currentTimeMillis();

        CompletableFuture<BackendResponse> future = backendClient.requestBuild(task);
        future.whenComplete((response, error) -> handleCompletion(player, response, error, startMs));
    }

    private void handleCompletion(ServerPlayer player, BackendResponse response,
                                  Throwable error, long startMs) {
        long elapsed = System.currentTimeMillis() - startMs;
        if (error != null) {
            BackendException be = unwrap(error);
            BuilderMC.LOGGER.error("[buildermc] Build failed after {} ms: {}", elapsed, be.getMessage());
            MessageUtil.sendError(player, "Build failed: " + be.getMessage());
            return;
        }

        // Response was already validated by BackendClient, but guard defensively.
        if (response == null || response.schematic == null || response.schematic.isBlank()) {
            BuilderMC.LOGGER.error("[buildermc] Build response missing schematic after validation.");
            MessageUtil.sendError(player, "Build failed: backend response missing schematic.");
            return;
        }

        String dim = (response.dimensions != null && response.dimensions.length == 3)
                ? response.dimensions[0] + "x" + response.dimensions[1] + "x" + response.dimensions[2]
                : "?";
        BuilderMC.LOGGER.info("[buildermc] Build succeeded in {} ms: {}", elapsed, response);
        MessageUtil.sendSuccess(player, "Structure generated: " + response.schematic
                + " (" + dim + ")");

        if (response.decisions != null && !response.decisions.isEmpty()) {
            MessageUtil.sendInfo(player, "Made " + response.decisions.size() + " design decisions (see logs).");
            for (String decision : response.decisions) {
                BuilderMC.LOGGER.info("[buildermc] decision: {}", decision);
            }
        }
    }

    /** Walks a completion-exception cause chain to find the underlying {@link BackendException}. */
    private static BackendException unwrap(Throwable t) {
        Throwable c = t;
        while (c.getCause() != null && !(c instanceof BackendException)) {
            c = c.getCause();
        }
        if (c instanceof BackendException be) {
            return be;
        }
        return new BackendException(t.getMessage() == null ? "unknown error" : t.getMessage(), t);
    }
}
