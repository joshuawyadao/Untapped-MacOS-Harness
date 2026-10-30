/* Original harness bootstrap. Runs before vendor imports in the disposable copy. */
(() => {
  const fs = require("node:fs");
  const path = require("node:path");
  const Module = require("node:module");
  const electron = require("electron");
  const profile = process.env.UC_TEST_SANDBOX_DIR;
  if (process.env.UNTAPPED_HARNESS_OFFLINE !== "1" || !profile || !path.isAbsolute(profile)) {
    throw new Error("Launch this disposable copy through the offline harness");
  }
  for (const key of ["home", "userData", "appData", "sessionData", "logs", "crashDumps", "temp"]) {
    const destination = key === "home" || key === "userData" ? profile : path.join(profile, key);
    fs.mkdirSync(destination, { recursive: true, mode: 0o700 });
    electron.app.setPath(key, destination);
  }
  // Do not access the macOS Keychain, including an existing Untapped service.
  const credentials = new Map();
  const credentialKey = (service, account) => JSON.stringify([service, account]);
  const memoryKeytar = {
    getPassword: async (service, account) => credentials.get(credentialKey(service, account)) ?? null,
    setPassword: async (service, account, password) => { credentials.set(credentialKey(service, account), password); },
    deletePassword: async (service, account) => credentials.delete(credentialKey(service, account)),
    findCredentials: async () => [],
    findPassword: async () => null,
  };
  const originalLoad = Module._load;
  Module._load = function (request, parent, isMain) {
    if (request === "keytar") return memoryKeytar;
    return originalLoad.call(this, request, parent, isMain);
  };
  // No browser handoff, protocol registration, or login-item changes even via UI.
  electron.shell.openExternal = async () => { throw new Error("Offline harness blocks external links"); };
  electron.app.setLoginItemSettings = () => {};
  electron.app.setAsDefaultProtocolClient = () => false;
  const events = path.join(profile, "events.jsonl");
  const seen = new Set();
  let rewards = 0;
  global.__untappedHarnessEvent = (event) => {
    if (!["bootstrap", "ready", "window-detected", "attach-attempt", "reader-connected"].includes(event) || seen.has(event)) return;
    seen.add(event);
    fs.appendFileSync(events, JSON.stringify({ event, time: new Date().toISOString() }) + "\n", { mode: 0o600 });
  };
  global.__untappedHarnessReward = (items) => {
    if (items?.source !== "cardReward" || !Array.isArray(items.cards) || rewards >= 100) return;
    const cards = items.cards.slice(0, 20).map(({ id, upgradeLevel, cx, cy, width, height }) => ({ id, upgradeLevel, cx, cy, width, height }));
    fs.appendFileSync(events, JSON.stringify({ event: "reward", time: new Date().toISOString(), cards }) + "\n", { mode: 0o600 });
    rewards++;
  };
  global.__untappedHarnessEvent("bootstrap");
  electron.app.whenReady().then(() => global.__untappedHarnessEvent("ready"));
})();
