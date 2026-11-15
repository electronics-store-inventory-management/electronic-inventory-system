import process from "node:process";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ command, mode }) => {
  if (command === "build") {
    const { VITE_API_BASE_URL } = loadEnv(mode, process.cwd(), "VITE_");
    let address;
    try {
      address = new URL(VITE_API_BASE_URL);
    } catch {
      throw new Error("Set VITE_API_BASE_URL to the backend URL before building.");
    }
    const local = ["localhost", "127.0.0.1", "[::1]"].includes(address.hostname);
    if (
      !(address.protocol === "https:" || (local && address.protocol === "http:")) ||
      address.username || address.password || address.search || address.hash
    ) {
      throw new Error("VITE_API_BASE_URL must be HTTPS (HTTP is allowed for local builds) without credentials, query, or fragment.");
    }
  }

  return { plugins: [react()] };
});
