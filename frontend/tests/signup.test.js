import assert from "node:assert/strict";
import test from "node:test";
import { validateSignup } from "../src/pages/auth/signupValidation.js";

const valid = { username: "demo_user", password: "Sample-only-4567", confirmation: "Sample-only-4567" };

test("accepts valid signup fields", () => {
  assert.deepEqual(validateSignup(valid), {});
});

test("requires valid username and password data", () => {
  const errors = validateSignup({ username: "a b", password: "alllowercase", confirmation: "" });
  assert.ok(errors.username);
  assert.ok(errors.password);
  assert.ok(errors.confirmation);
});

test("rejects password confirmation mismatch", () => {
  assert.deepEqual(validateSignup({ ...valid, confirmation: "Different-123!" }), {
    confirmation: "The passwords do not match.",
  });
});
