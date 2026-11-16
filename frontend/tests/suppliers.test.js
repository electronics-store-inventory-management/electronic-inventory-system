import assert from "node:assert/strict";
import { after, afterEach, test } from "node:test";
import React from "react";
import reactPlugin from "@vitejs/plugin-react";
import { JSDOM } from "jsdom";
import { createServer } from "vite";

const dom = new JSDOM("<!doctype html><html><body></body></html>", {
  url: "http://localhost/",
  pretendToBeVisual: true,
});
globalThis.window = dom.window;
globalThis.document = dom.window.document;
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.MutationObserver = dom.window.MutationObserver;
Object.defineProperty(globalThis, "navigator", { configurable: true, value: dom.window.navigator });
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const { cleanup, fireEvent, render, screen, waitFor } = await import("@testing-library/react");

const supplierServiceMock = {
  list: async () => [],
  create: async () => null,
  update: async () => null,
};
globalThis.__supplierServiceMock = supplierServiceMock;

const vite = await createServer({
  configFile: false,
  appType: "custom",
  plugins: [
    reactPlugin(),
    {
      name: "supplier-test-api-mock",
      enforce: "pre",
      resolveId(source) {
        return source.endsWith("services/supplierService") ? "\0supplier-service-mock" : null;
      },
      load(id) {
        return id === "\0supplier-service-mock"
          ? "export const supplierService = globalThis.__supplierServiceMock;"
          : null;
      },
    },
  ],
  server: { middlewareMode: true },
});
const [{ default: SuppliersPage }, { AuthContext }] = await Promise.all([
  vite.ssrLoadModule("/src/pages/suppliers/SuppliersPage.jsx"),
  vite.ssrLoadModule("/src/auth/AuthContextValue.js"),
]);
afterEach(cleanup);
after(async () => {
  delete globalThis.__supplierServiceMock;
  dom.window.close();
  await vite.close();
});

const supplier = {
  id: 42,
  name: "Northwind Parts",
  email: "supply@northwind.test",
  phone: "+91-555-0100",
  address: "17 Harbor Road",
};

function supplierPage(role = "admin") {
  return React.createElement(
    AuthContext.Provider,
    { value: { user: { id: role === "admin" ? 1 : 2, role } } },
    React.createElement(SuppliersPage),
  );
}

test("supplier page renders API records and their contact details", async (t) => {
  t.mock.method(supplierServiceMock, "list", async () => [supplier]);
  render(supplierPage());

  for (const value of ["Northwind Parts", "SUP-0042", supplier.email, supplier.phone, supplier.address]) {
    assert.ok(await screen.findByText(value));
  }
});

test("supplier page displays its loading state while the API request is pending", async (t) => {
  let resolveList;
  t.mock.method(supplierServiceMock, "list", () => new Promise((resolve) => { resolveList = resolve; }));
  render(supplierPage());
  assert.ok(screen.getByText("Loading suppliers"));

  resolveList([]);
  assert.ok(await screen.findByText("No suppliers yet"));
});

test("supplier page displays the empty state for an empty API response", async (t) => {
  t.mock.method(supplierServiceMock, "list", async () => []);
  render(supplierPage());
  assert.ok(await screen.findByText("No suppliers yet"));
});

test("supplier page displays API errors and a retry action", async (t) => {
  t.mock.method(supplierServiceMock, "list", async () => { throw new Error("Supplier API unavailable"); });
  render(supplierPage());
  assert.ok(await screen.findByText("Could not load suppliers"));
  assert.ok(screen.getByText("Supplier API unavailable"));
  assert.ok(screen.getByRole("button", { name: "Try again" }));
});

test("supplier search matches name, email, phone, address, and ID", async (t) => {
  t.mock.method(supplierServiceMock, "list", async () => [supplier]);
  render(supplierPage());
  const search = screen.getByRole("searchbox", { name: "Search suppliers" });
  await screen.findByText(supplier.name);

  for (const query of [supplier.name, supplier.email, supplier.phone, supplier.address, String(supplier.id)]) {
    fireEvent.change(search, { target: { value: query } });
    assert.ok(screen.getByText(supplier.name), `expected a match for ${query}`);
  }
  fireEvent.change(search, { target: { value: "not present" } });
  assert.ok(await screen.findByText("No matching suppliers"));
});

test("admin can add a supplier with the backend request format", async (t) => {
  let listCalls = 0;
  t.mock.method(supplierServiceMock, "list", async () => (listCalls++ === 0 ? [] : [{ ...supplier, id: 43, name: "Harbor Electronics" }]));
  const createSupplier = t.mock.method(supplierServiceMock, "create", async () => ({ ...supplier, id: 43, name: "Harbor Electronics" }));
  render(supplierPage());
  await screen.findByText("No suppliers yet");

  fireEvent.click(screen.getAllByRole("button", { name: "Add supplier" })[0]);
  fireEvent.change(screen.getByLabelText(/Supplier name/), { target: { value: "Harbor Electronics" } });
  fireEvent.change(screen.getByLabelText("Email address"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("Phone number"), { target: { value: "" } });
  fireEvent.change(screen.getByLabelText("Address"), { target: { value: "" } });
  fireEvent.click(screen.getAllByRole("button", { name: "Add supplier" }).at(-1));

  await waitFor(() => assert.equal(createSupplier.mock.callCount(), 1));
  assert.deepEqual(createSupplier.mock.calls[0].arguments[0], {
    name: "Harbor Electronics", email: null, phone: null, address: null,
  });
  assert.ok(await screen.findByText("Harbor Electronics"));
});

test("admin can edit a supplier and the page refreshes with the returned record", async (t) => {
  let listCalls = 0;
  const updated = { ...supplier, name: "Northwind Components" };
  t.mock.method(supplierServiceMock, "list", async () => (listCalls++ === 0 ? [supplier] : [updated]));
  const updateSupplier = t.mock.method(supplierServiceMock, "update", async () => updated);
  render(supplierPage());
  await screen.findByText(supplier.name);

  fireEvent.click(screen.getByRole("button", { name: `Edit ${supplier.name}` }));
  fireEvent.change(screen.getByLabelText(/Supplier name/), { target: { value: updated.name } });
  fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

  await waitFor(() => assert.equal(updateSupplier.mock.callCount(), 1));
  assert.equal(updateSupplier.mock.calls[0].arguments[0], supplier.id);
  assert.equal(updateSupplier.mock.calls[0].arguments[1].name, updated.name);
  assert.ok(await screen.findByText(updated.name));
});

test("admins can manage suppliers while employees can only view them", async (t) => {
  t.mock.method(supplierServiceMock, "list", async () => [supplier]);
  const admin = render(supplierPage("admin"));
  await screen.findByText(supplier.name);
  assert.ok(screen.getByRole("button", { name: `Edit ${supplier.name}` }));
  assert.ok(screen.getAllByRole("button", { name: "Add supplier" }).length > 0);
  admin.unmount();

  render(supplierPage("employee"));
  assert.ok(await screen.findByText(supplier.name));
  assert.equal(screen.queryByRole("button", { name: `Edit ${supplier.name}` }), null);
  assert.equal(screen.queryByRole("button", { name: "Add supplier" }), null);
});
