import assert from "node:assert/strict";
import test from "node:test";
import { AUTH_SESSION_KEY, clearAuthSession, readStoredSession } from "../src/auth/session.js";
import { apiRequest } from "../src/services/api.js";

function fakeWindow(t, storedSession) {
  const storage = new Map([[AUTH_SESSION_KEY, JSON.stringify(storedSession)]]);
  const browser = Object.assign(new EventTarget(), {
    sessionStorage: {
      getItem: (key) => storage.get(key),
      setItem: (key, value) => storage.set(key, value),
      removeItem: (key) => storage.delete(key),
    },
  });
  t.mock.method(Date, "now", () => 1_000);
  const previousWindow = globalThis.window;
  globalThis.window = browser;
  t.after(() => {
    if (previousWindow === undefined) delete globalThis.window;
    else globalThis.window = previousWindow;
  });
  return browser;
}

test("expiry between session initialization and hydration clears storage and memory even if the event is missed", async (t) => {
  const session = { accessToken: "old", sessionId: "original", expiresAt: 1_001 };
  fakeWindow(t, session);
  let memory = readStoredSession();
  assert.ok(memory.expiresAt > Date.now());
  Date.now.mock.mockImplementation(() => 1_002);
  const fetch = t.mock.method(globalThis, "fetch", () => assert.fail("Sent an expired token"));

  // No listener installed. Reproduce the hydration catch after the API cleared storage.
  await assert.rejects(apiRequest("/auth/me"), (error) => {
    assert.equal(error.status, 401);
    assert.equal(readStoredSession(), null);
    clearAuthSession((update) => { memory = update(memory); }, session.accessToken, session.sessionId);
    return true;
  });
  assert.equal(memory, null);
  assert.equal(fetch.mock.callCount(), 0);
});

test("an old hydration request returning 401 cannot clear a newer sign-in with the same JWT", async (t) => {
  const previous = { accessToken: "same-jwt", sessionId: "original", expiresAt: 2_000 };
  const browser = fakeWindow(t, previous);
  let memory = previous;
  const setSession = (update) => { memory = update(memory); };
  browser.addEventListener("auth:unauthorized", ({ detail }) => {
    clearAuthSession(setSession, detail.accessToken, detail.sessionId);
  });
  let respond;
  t.mock.method(globalThis, "fetch", () => new Promise((resolve) => { respond = resolve; }));
  const hydration = apiRequest("/auth/me");
  const next = { ...previous, sessionId: "replacement" };
  browser.sessionStorage.setItem(AUTH_SESSION_KEY, JSON.stringify(next));
  memory = next;
  respond(new Response(null, { status: 401 }));

  await assert.rejects(hydration, { status: 401 });
  clearAuthSession(setSession, previous.accessToken, previous.sessionId);
  assert.deepEqual(readStoredSession(), next);
  assert.equal(memory, next);
});
