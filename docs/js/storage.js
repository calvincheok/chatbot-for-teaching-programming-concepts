/* Saves sessions in this browser (localStorage), since GitHub Pages has no server.

   Each session keeps its messages, teaching decisions (events) and a log of
   every tutor call. Data stays on this device and this browser only. If the
   browser blocks storage (for example some private windows), sessions are kept
   in memory until the tab closes. */
"use strict";
var PyTutor = window.PyTutor || (window.PyTutor = {});

PyTutor.storage = (function () {
  const KEY = "pytutor.sessions.v1";
  let memory = {};
  let persistent = true;

  function readAll() {
    if (!persistent) return memory;
    try {
      const raw = window.localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : {};
    } catch {
      persistent = false;
      return memory;
    }
  }

  function writeAll(all) {
    memory = all;
    if (!persistent) return;
    try { window.localStorage.setItem(KEY, JSON.stringify(all)); }
    catch { persistent = false; }
  }

  return {
    get(id) { return readAll()[id] || null; },
    all() { return Object.values(readAll()); },
    save(session) {
      const all = readAll();
      all[session.id] = session;
      writeAll(all);
    },
    isPersistent() { readAll(); return persistent; },
  };
})();
