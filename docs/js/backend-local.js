/* Connects the chat page (chat.js) to the teaching engine running in this
   browser. Same functions as static/backend-server.js in the Flask version. */
"use strict";

window.Backend = (function () {
  const engine = PyTutor.createEngine(new PyTutor.FakeProvider(), PyTutor.storage);

  // Errors always come back as { message, retryable }, like the Flask version.
  const wrap = (fn) => async (...args) => {
    try { return await fn(...args); }
    catch (err) { throw { message: err && err.message ? err.message : "Something went wrong.", retryable: !!(err && err.retryable) }; }
  };

  return {
    basePath: location.pathname,
    storageNote: PyTutor.storage.isPersistent() ? null
      : "This browser isn't letting the page save data, so your progress will be lost when you close this tab.",
    siteNote: "FYP prototype. Your progress is saved in this browser only; nothing is sent to a server.",
    concepts: wrap(() => engine.concepts()),
    sessions: wrap(() => engine.sessions()),
    start: wrap((concept) => engine.start(concept)),
    state: wrap((id) => engine.state(id)),
    send: wrap((id, text) => engine.send(id, text)),   // the request id is only needed by the server
  };
})();
