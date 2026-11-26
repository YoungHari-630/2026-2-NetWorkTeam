/* Centralized HTTP adapter for the APIs currently implemented by FastAPI. */
"use strict";
window.NetworkApi = Object.freeze({
  baseUrl: "http://127.0.0.1:8000",
  async request(path, options = {}, timeoutMessage = () => "Network request failed") {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch(this.baseUrl + path, {
        ...options,
        signal: controller.signal,
        headers: {
          ...(options.body ? { "Content-Type": "application/json" } : {}),
          ...options.headers,
        },
      });
      let body;
      try { body = await response.json(); } catch { body = {}; }
      if (!response.ok) {
        const error = new Error(body.detail || `HTTP ${response.status}`);
        error.status = response.status;
        throw error;
      }
      return body;
    } catch (error) {
      if (error.name === "AbortError") throw new Error(timeoutMessage());
      throw error;
    } finally {
      window.clearTimeout(timeoutId);
    }
  },
});
