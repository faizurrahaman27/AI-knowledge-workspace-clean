import axios from "axios";

// In Docker/production, set VITE_API_BASE_URL=/api (the Nginx container
// proxies /api/* to the backend, avoiding CORS entirely). In local dev,
// it defaults to the FastAPI dev server.
const baseURL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const api = axios.create({ baseURL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If an access token is rejected (expired, or invalidated by a password
// change / logout-everywhere elsewhere), try the refresh token exactly
// once before giving up and sending the user back to login. Without this,
// every one of the new session-invalidation features (change-password,
// logout-everywhere, account lockout recovery) would just silently break
// the user's current tab instead of recovering gracefully.
let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    const isAuthEndpoint = originalRequest?.url?.startsWith("/auth/login")
      || originalRequest?.url?.startsWith("/auth/token")
      || originalRequest?.url?.startsWith("/auth/refresh")
      || originalRequest?.url?.startsWith("/auth/register");

    if (error.response?.status !== 401 || isAuthEndpoint || originalRequest._retried) {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      return Promise.reject(error);
    }

    originalRequest._retried = true;

    try {
      if (!refreshPromise) {
        refreshPromise = axios
          .post(`${baseURL}/auth/refresh`, { refresh_token: refreshToken })
          .then((res) => res.data)
          .finally(() => {
            refreshPromise = null;
          });
      }

      const data = await refreshPromise;
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      return api(originalRequest);
    } catch {
      localStorage.removeItem("token");
      localStorage.removeItem("refresh_token");
      if (window.location.pathname !== "/") {
        window.location.href = "/";
      }
      return Promise.reject(error);
    }
  }
);

export default api;
export { baseURL as API_BASE_URL };

export function getWebsocketUrl(path) {
  // path e.g. "/ws/workspace/5?token=..."
  if (baseURL.startsWith("http")) {
    // Absolute base URL (local dev): just swap the scheme.
    return baseURL.replace(/^http/, "ws") + path;
  }
  // Relative base URL (production, proxied through nginx at /api): build
  // from the current page's origin instead.
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const prefix = baseURL.endsWith("/") ? baseURL.slice(0, -1) : baseURL;
  return `${protocol}//${window.location.host}${prefix}${path}`;
}
