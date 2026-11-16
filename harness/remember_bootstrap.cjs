// Optional bridge; the companion itself still has no Keychain access.
  let harnessRememberKeytar = null;
  if (controlled && process.env.UNTAPPED_HARNESS_MAIN_ACCOUNT === "1" &&
      process.env.UNTAPPED_HARNESS_REMEMBER_LOGIN === "1") {
    const helper = path.join(profile, "remember-keytar.cjs");
    const info = fs.lstatSync(helper);
    const expected = process.env.UNTAPPED_HARNESS_LOGIN_HELPER_SHA256;
    const socketPath = path.join(path.dirname(profile), "remember.sock");
    if (!info.isFile() || info.uid !== process.getuid() || info.nlink !== 1 ||
        (info.mode & 0o7777) !== 0o600 || !/^[a-f0-9]{64}$/.test(expected || "") ||
        require("node:crypto").createHash("sha256").update(fs.readFileSync(helper)).digest("hex") !== expected ||
        process.env.UNTAPPED_HARNESS_LOGIN_SOCKET !== socketPath ||
        !/^[a-f0-9]{64}$/.test(process.env.UNTAPPED_HARNESS_LOGIN_CAPABILITY || "")) {
      throw new Error("Remember-login bridge failed validation");
    }
    harnessRememberKeytar = require(helper).create({ memoryKeytar, socketPath,
      capability: process.env.UNTAPPED_HARNESS_LOGIN_CAPABILITY });
  }
