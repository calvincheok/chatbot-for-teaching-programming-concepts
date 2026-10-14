/* Connects the chat page (chat.js) to the Flask server's JSON API.
   The GitHub Pages version uses docs/js/backend-local.js instead, which has
   the same functions but runs the teaching engine in the browser. */
"use strict";

window.Backend = (function () {
  const HEADERS = { "Content-Type": "application/json", "X-Requested-With": "fyp-chat" };
  const newId = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}${Math.random()}`).replace(/[^a-z0-9]/gi, "").slice(0, 32);

  // Errors always come back as { message, retryable }.
  async function call(method, url, body) {
    let res;
    try {
      res = await fetch(url, { method, headers: HEADERS, body: body ? JSON.stringify(body) : undefined, credentials: "same-origin" });
    } catch {
      throw { message: "Can't reach the server. Check that it's running, then send again.", retryable: true };
    }
    let data = null;
    try { data = await res.json(); } catch { /* handled below */ }
    if (!res.ok) throw { message: (data && data.error) || `Something went wrong (${res.status}).`, retryable: !data || data.retryable !== false };
    return data;
  }

  return {
    basePath: "/",
    storageNote: null,
    siteNote: null,
    concepts: () => call("GET", "/api/concepts"),
    sessions: () => call("GET", "/api/sessions"),
    start: (concept) => call("POST", "/api/sessions", { concept, request_id: newId() }),
    state: (id) => call("GET", `/api/sessions/${encodeURIComponent(id)}`),
    // requestId lets the server ignore a repeated send of the same message.
    send: (id, text, requestId) => call("POST", `/api/sessions/${encodeURIComponent(id)}/messages`, { text, request_id: requestId }),
  };
})();
