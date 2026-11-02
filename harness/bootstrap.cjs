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
  global.__untappedHarnessAssertTargetPid = (pid) => {
    const raw = process.env.UNTAPPED_HARNESS_TARGET_PID;
    const rawUid = process.env.UNTAPPED_HARNESS_TARGET_UID;
    const executable = process.env.UNTAPPED_HARNESS_TARGET_EXECUTABLE;
    const expectedProbeHash = process.env.UNTAPPED_HARNESS_IDENTITY_SHA256;
    if (typeof raw !== "string" || !/^[1-9][0-9]*$/.test(raw) ||
        typeof rawUid !== "string" || !/^[1-9][0-9]*$/.test(rawUid) ||
        typeof executable !== "string" || !path.isAbsolute(executable) ||
        typeof expectedProbeHash !== "string" || !/^[a-f0-9]{64}$/.test(expectedProbeHash)) {
      throw new Error("Complete harness target identity required before STS2 reader construction");
    }
    const expected = Number(raw);
    const expectedUid = Number(rawUid);
    if (!Number.isSafeInteger(expected) || !Number.isSafeInteger(pid) || pid <= 0 || pid !== expected ||
        !Number.isSafeInteger(expectedUid) || typeof process.getuid !== "function" ||
        expectedUid !== process.getuid()) {
      throw new Error("Harness STS2 target PID mismatch");
    }
    const probe = path.join(profile, "target-identity");
    const info = fs.lstatSync(probe);
    if (!info.isFile() || info.uid !== process.getuid() || info.nlink !== 1 ||
        (info.mode & 0o7777) !== 0o700) {
      throw new Error("Harness identity helper is not a private owned regular executable");
    }
    const { createHash } = require("node:crypto");
    if (createHash("sha256").update(fs.readFileSync(probe)).digest("hex") !== expectedProbeHash) {
      throw new Error("Harness identity helper changed before target verification");
    }
    const { execFileSync } = require("node:child_process");
    const row = execFileSync(probe, [String(pid)], {
      encoding: "utf8", timeout: 2000, maxBuffer: 1024,
    }).trim();
    const identity = /^([0-9]+)\s+(.+)$/.exec(row);
    if (!identity || Number(identity[1]) !== expectedUid || identity[2] !== executable) {
      throw new Error("Harness STS2 target process changed before reader construction");
    }
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
