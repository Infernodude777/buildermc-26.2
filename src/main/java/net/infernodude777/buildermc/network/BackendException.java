package net.infernodude777.buildermc.network;

/**
 * Root exception for anything that goes wrong talking to the Python backend.
 * Subclasses let the caller distinguish connection vs. HTTP vs. parse errors.
 */
public class BackendException extends RuntimeException {

    public BackendException(String message) {
        super(message);
    }

    public BackendException(String message, Throwable cause) {
        super(message, cause);
    }

    /** The backend could not be reached (connection refused, DNS, etc.). */
    public static class ConnectionFailed extends BackendException {
        public ConnectionFailed(String message, Throwable cause) {
            super(message, cause);
        }
    }

    /** The backend responded with a non-2xx HTTP status. */
    public static class HttpError extends BackendException {
        public final int statusCode;

        public HttpError(int statusCode, String message) {
            super(message);
            this.statusCode = statusCode;
        }
    }

    /** The response body could not be parsed as the expected JSON. */
    public static class ParseError extends BackendException {
        public ParseError(String message, Throwable cause) {
            super(message, cause);
        }
    }

    /** The response was valid JSON but semantically wrong (missing schematic, etc.). */
    public static class InvalidResponse extends BackendException {
        public InvalidResponse(String message) {
            super(message);
        }
    }
}
