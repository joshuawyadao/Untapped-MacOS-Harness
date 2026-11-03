"use strict";

// Installed only by the controlled-access bootstrap. The ordinary offline mode
// never loads this module.
const { URL, URLSearchParams } = require("node:url");

function gatewayAddress(value) {
  let url;
  try { url = new URL(value); }
  catch (_) { throw new Error("Invalid controlled gateway address"); }
  if (url.protocol !== "http:" || url.hostname !== "127.0.0.1" ||
      !/:[1-9][0-9]{0,4}\/fetch$/.test(value) ||
      url.port === "" || Number(url.port) > 65535 ||
      url.pathname !== "/fetch" || url.username || url.password ||
      url.search || url.hash) {
    throw new Error("Invalid controlled gateway address");
  }
  return url.href;
}

function oauthAddress(value) {
  if (typeof value !== "string") throw new Error("External URL blocked");
  if (!/^https:\/\/accounts\.untapped\.gg\/authorize\?/.test(value) || value.includes("#")) {
    throw new Error("External URL blocked");
  }
  let url;
  try { url = new URL(value); } catch (_) { throw new Error("External URL blocked"); }
  if (url.protocol !== "https:" || url.hostname !== "accounts.untapped.gg" ||
      url.port || url.username || url.password || url.hash || url.pathname !== "/authorize") {
    throw new Error("External URL blocked");
  }
  const required = new Map([
    ["response_type", "code"], ["scope", "companion:full-access"],
    ["code_challenge_method", "S256"],
    ["utm_source", "uc"], ["utm_medium", "app"],
    ["utm_campaign", "accounts"], ["utm_content", "add-account-button"],
  ]);
  const nonempty = new Set(["client_id", "state", "code_challenge", "redirect_uri"]);
  const optional = new Set(["franchise", "auth"]);
  const seen = new Set();
  for (const [name, field] of url.searchParams) {
    if (seen.has(name) || !(required.has(name) || nonempty.has(name) || optional.has(name))) {
      throw new Error("External URL blocked");
    }
    seen.add(name);
    if ((required.has(name) && field !== required.get(name)) ||
        (nonempty.has(name) && !field) || (optional.has(name) && !field) ||
        (name === "franchise" && field !== "STS2")) {
      throw new Error("External URL blocked");
    }
  }
  for (const name of [...required.keys(), ...nonempty]) {
    if (!seen.has(name)) throw new Error("External URL blocked");
  }
  let redirect;
  try { redirect = new URL(url.searchParams.get("redirect_uri")); }
  catch (_) { throw new Error("External URL blocked"); }
  if (redirect.protocol !== "http:" ||
      !["localhost", "127.0.0.1"].includes(redirect.hostname) ||
      !/^[0-9]+$/.test(redirect.port) || Number(redirect.port) < 17791 ||
      Number(redirect.port) > 17799 || redirect.pathname !== "/" ||
      redirect.username || redirect.password || redirect.search || redirect.hash ||
      url.searchParams.get("redirect_uri").includes("#")) {
    throw new Error("External URL blocked");
  }
  return value;
}

function headersObject(value) {
  if (value == null) return {};
  const headers = {};
  const append = (name, field) => {
    if (typeof name !== "string" || typeof field !== "string" ||
        !/^[!#$%&'*+.^_`|~0-9A-Za-z-]+$/.test(name) || /[\r\n]/.test(field)) {
      throw new TypeError("Unsupported fetch headers");
    }
    headers[name] = field;
  };
  if (typeof value.forEach === "function") {
    value.forEach((field, name) => append(name, field));
  } else if (Array.isArray(value)) {
    for (const pair of value) {
      if (!Array.isArray(pair) || pair.length !== 2) throw new TypeError("Unsupported fetch headers");
      append(pair[0], pair[1]);
    }
  } else if (typeof value === "object" && Object.getPrototypeOf(value) === Object.prototype) {
    for (const [name, field] of Object.entries(value)) append(name, field);
  } else {
    throw new TypeError("Unsupported fetch headers");
  }
  return headers;
}

function requestBody(value) {
  if (value == null) return null;
  if (typeof value === "string" || value instanceof URLSearchParams) return String(value);
  if (Buffer.isBuffer(value)) {
    const decoded = value.toString("utf8");
    if (!Buffer.from(decoded, "utf8").equals(value)) throw new TypeError("Unsupported fetch body");
    return decoded;
  }
  throw new TypeError("Unsupported fetch body");
}

function requestEnvelope(input, init = {}) {
  if (!init || typeof init !== "object" || Array.isArray(init)) throw new TypeError("Unsupported fetch options");
  let url;
  let request = {};
  if (typeof input === "string" || input instanceof URL) {
    url = String(input);
  } else if (input && typeof input === "object" && typeof input.url === "string") {
    url = input.url;
    request = input;
  } else {
    throw new TypeError("Unsupported fetch input");
  }
  let parsed;
  try { parsed = new URL(url); }
  catch (_) { throw new TypeError("Unsupported fetch URL"); }
  if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) {
    throw new TypeError("Unsupported fetch URL");
  }
  const method = init.method === undefined ? (request.method || "GET") : init.method;
  if (typeof method !== "string" || !/^[A-Za-z]+$/.test(method)) throw new TypeError("Unsupported fetch method");
  const headers = headersObject(init.headers === undefined ? request.headers : init.headers);
  const body = requestBody(init.body === undefined ? request.body : init.body);
  return { url, method: method.toUpperCase(), headers, body };
}

function privateUrlFile(fs, path, profile, url) {
  if (typeof profile !== "string" || !path.isAbsolute(profile)) throw new Error("Invalid controlled profile");
  const dir = fs.lstatSync(profile);
  if (!dir.isDirectory() || dir.isSymbolicLink() || dir.uid !== process.getuid() || (dir.mode & 0o077)) {
    throw new Error("Invalid controlled profile");
  }
  const file = path.join(profile, "manual-sign-in-url.txt");
  try {
    const prior = fs.lstatSync(file);
    if (!prior.isFile() || prior.isSymbolicLink() || prior.uid !== process.getuid() || prior.nlink !== 1) {
      throw new Error("Invalid manual sign-in file");
    }
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
  const flags = fs.constants.O_WRONLY | fs.constants.O_CREAT | fs.constants.O_NOFOLLOW;
  const fd = fs.openSync(file, flags, 0o600);
  try {
    const info = fs.fstatSync(fd);
    if (!info.isFile() || info.uid !== process.getuid() || info.nlink !== 1) {
      throw new Error("Invalid manual sign-in file");
    }
    fs.fchmodSync(fd, 0o600);
    fs.ftruncateSync(fd, 0);
    fs.writeFileSync(fd, url + "\n", { encoding: "utf8" });
  } finally {
    fs.closeSync(fd);
  }
}

function install({ electron, fs, path, profile, gatewayUrl, gatewayKey, originalLoad, event }) {
  const endpoint = gatewayAddress(gatewayUrl);
  if (typeof gatewayKey !== "string" || gatewayKey.length < 32 || /[\r\n]/.test(gatewayKey) ||
      typeof originalLoad !== "function" || typeof event !== "function" ||
      !electron || !electron.shell || typeof electron.shell.openExternal !== "function") {
    throw new Error("Invalid controlled network configuration");
  }
  const cached = new WeakMap();
  electron.shell.openExternal = async function manualSignIn(target) {
    const url = oauthAddress(target);
    privateUrlFile(fs, path, profile, url);
    event("manual-sign-in-ready");
  };
  return {
    loadFetch(parent, isMain) {
      const fetch = originalLoad.call(this, "node-fetch", parent, isMain);
      if (typeof fetch !== "function") throw new Error("Unsupported fetch module");
      if (cached.has(fetch)) return cached.get(fetch);
      const wrapped = function controlledFetch(input, init) {
        const envelope = requestEnvelope(input, init);
        const payload = JSON.stringify(envelope);
        if (Buffer.byteLength(payload, "utf8") > 8 * 1024 * 1024) {
          throw new TypeError("Fetch request too large");
        }
        return fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Harness-Key": gatewayKey },
          body: payload,
          redirect: "manual",
          timeout: 15000,
          size: 8 * 1024 * 1024,
        });
      };
      Object.assign(wrapped, fetch);
      wrapped.default = wrapped;
      for (const name of ["Headers", "Request", "Response"]) {
        if (fetch[name]) wrapped[name] = fetch[name];
      }
      cached.set(fetch, wrapped);
      return wrapped;
    },
  };
}

module.exports = { install };
