"use strict";

const net = require("node:net");
const SERVICE = "Untapped.gg Companion";
const MAX_MESSAGE = 64 * 1024;

function create({ memoryKeytar, socketPath, capability }) {
  let hydrated = null;
  function exchange(message) {
    return new Promise((resolve) => {
      if (typeof socketPath !== "string" || typeof capability !== "string") return resolve(null);
      const socket = net.createConnection(socketPath);
      let data = "";
      let finished = false;
      function finish(value) {
        if (finished) return;
        finished = true;
        socket.destroy();
        resolve(value);
      }
      socket.setTimeout(20000, () => finish(null));
      socket.on("error", () => finish(null));
      socket.on("data", (chunk) => {
        data += chunk.toString("utf8");
        if (Buffer.byteLength(data) > MAX_MESSAGE) return finish(null);
        const end = data.indexOf("\n");
        if (end < 0) return;
        try { finish(JSON.parse(data.slice(0, end))); } catch { finish(null); }
      });
      socket.on("end", () => finish(null));
      const request = JSON.stringify({ ...message, capability }) + "\n";
      if (Buffer.byteLength(request) > MAX_MESSAGE) return finish(null);
      socket.write(request);
    });
  }
  async function ensureHydrated() {
    if (!hydrated) hydrated = (async () => {
      const response = await exchange({ op: "load" });
      if (response?.ok !== true || !Array.isArray(response.credentials)) return;
      for (const row of response.credentials) {
        if (typeof row?.account === "string" && typeof row.password === "string") {
          await memoryKeytar.setPassword(SERVICE, row.account, row.password);
        }
      }
    })();
    await hydrated;
  }
  return {
    async getPassword(service, account) {
      if (service === SERVICE) await ensureHydrated();
      return memoryKeytar.getPassword(service, account);
    },
    async setPassword(service, account, password) {
      if (service === SERVICE) await ensureHydrated();
      const result = await memoryKeytar.setPassword(service, account, password);
      if (service === SERVICE) await exchange({ op: "set", service, account, password });
      return result;
    },
    async deletePassword(service, account) {
      if (service === SERVICE) await ensureHydrated();
      const result = await memoryKeytar.deletePassword(service, account);
      if (service === SERVICE) await exchange({ op: "delete", service, account });
      return result;
    },
    async findCredentials(service) {
      if (service === SERVICE) await ensureHydrated();
      return memoryKeytar.findCredentials(service);
    },
    async findPassword(service) {
      if (service !== SERVICE) return memoryKeytar.findPassword(service);
      await ensureHydrated();
      const credentials = await memoryKeytar.findCredentials(service);
      return credentials[0]?.password ?? null;
    },
  };
}

module.exports = { create };
