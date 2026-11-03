"""Exact guards for one user-supplied build; never spoof app.isPackaged globally."""
from pathlib import Path
from .asar import HarnessError
from .sts2_ui import SETTINGS_UI_ENTRY, patch_settings_ui

VERSION = "3.12.3-latest"
ASAR_SHA256 = "ca3a2e6a6f728b2d635abfc70a5434d4107438b8d801a650357989e8442d798c"
SCRY_SHA256 = "cf9c5d2925c255191c3fdeb898b7565f69aa5633bb090485226a4fb5731888d9"
EXECUTABLE_SHA256 = "457707bc67bd18287761e7987b2846bbb002b1807bd2a1a8d45688821805d49b"
FRAMEWORK_SHA256 = "f8a7fd42c970bf77e9ed0704809df3ae665a8bad9273419a018c7ef40a0ba02a"
CORE = "dist/main/chunks/Core-tWQs6NtS.js"
MAIN = "dist/main/index.js"
SERVICES = "dist/main/chunks/Services-DMO98y9F.js"
OVERLAY = "dist/renderer/assets/Sts2Overlay-DPeYNPLb.js"
RUNTIME = "dist/renderer/assets/ScryRuntime-Bw9hEAKx.js"
SETTINGS_UI = SETTINGS_UI_ENTRY
SCRY = "node_modules/untapped-scry/lib/binding/napi-v5/untapped-scry.node"
RUNTIME_STORE_GETTER_OLD = '  get LocalStore() {\n    return new GodotFileIo(this.object("LocalStore"));\n  }'
RUNTIME_STORE_GETTER_NEW = '  get LocalStore() {\n    return resolveHarnessSts2LocalFileIo(this);\n  }'
RUNTIME_STORE_CLASS = 'class CloudSaveStore extends ScryObject {'

# Small exact-match anchors, not a redistributed companion bundle.
CORE_PATCHES = [
    ('platforms: electron.app.isPackaged ? ["win32", "linux"] : ["win32", "darwin", "linux"]\n      // macOS is dev-only',
     'platforms: ["win32", "darwin", "linux"] // harness: STS2-only platform gate'),
    ('(process.platform === "win32" || process.platform === "linux" || process.platform === "darwin" && !electron.app.isPackaged)) {\n      this.games.sts2 = new Sts2();',
     '(process.platform === "win32" || process.platform === "linux" || process.platform === "darwin")) {\n      this.games.sts2 = new Sts2();'),
    ('    this.autostartManager.init();', '    // harness: no login-item registration'),
    ('    this.protocolManager.init();', '    // harness: no URL-handler registration'),
    ('    this.tryEnableMtga();', '    // harness: STS2 only'),
    ('    this.tryEnableYgom();', '    // harness: STS2 only'),
    ('    this.tryEnableSnap();', '    // harness: STS2 only'),
    ('    await scry.connect();\n    scry.startWatcher("sts2SettingsWatcher");',
     '    global.__untappedHarnessEvent("attach-attempt");\n    const harnessConnected = await scry.connect();\n    if (harnessConnected === true) global.__untappedHarnessEvent("reader-connected");\n    scry.startWatcher("sts2SettingsWatcher");'),
    ('      this.state.setVisibleItems(visibleItems);',
     '      global.__untappedHarnessReward(visibleItems);\n      this.state.setVisibleItems(visibleItems);'),
    ('      const wInfo = native.getWindowInfo(targetWindowOwnerName, partialBundlePath);\n      this.currentPid = wInfo.pid;',
     '      const wInfo = native.getWindowInfo(targetWindowOwnerName, partialBundlePath);\n      if (targetWindowOwnerName === "Slay the Spire 2" && wInfo.exists) global.__untappedHarnessEvent("window-detected");\n      this.currentPid = wInfo.pid;'),
    ('      this.disposeScry();\n      this._scry = new GameScryInstance({ pid, franchise });',
     '      if (franchise === "STS2") global.__untappedHarnessAssertTargetPid(pid);\n'
     '      this.disposeScry();\n      this._scry = new GameScryInstance({ pid, franchise });'),
]
MAIN_PATCHES = [('    Sentry.init({\n      dsn: pkg.sentry.dsn,',
                 '    Sentry.init({\n      enabled: false,\n      dsn: pkg.sentry.dsn,')]
SERVICES_PATCHES = [
    ('  async ensureLocalCredentials() {\n    const authDetails = await this.loadLocalCredentials();',
     '  async ensureLocalCredentials() {\n'
     '    if (process.env.UNTAPPED_HARNESS_OFFLINE === "1") {\n'
     '      if (process.env.UNTAPPED_HARNESS_CONTROLLED_ACCESS === "1") {\n'
     '        const { authenticatedCredentials } = await this.loadLocalCredentials();\n'
     '        return { authenticatedCredentials, anonymousCredentials: null };\n'
     '      }\n'
     '      return { authenticatedCredentials: {}, anonymousCredentials: null };\n'
     '    }\n'
     '    const authDetails = await this.loadLocalCredentials();'),
]

CONTROLLED = 'process.env.UNTAPPED_HARNESS_CONTROLLED_ACCESS === "1"'
CORE_PATCHES.extend([
    ('      this.state.settings.set(curr);\n      this.processWatcher.update();',
     '      this.state.settings.set(curr);\n'
     '      if (curr && typeof curr === "object") global.__untappedHarnessEvent("settings-read");\n'
     '      this.processWatcher.update();'),
    ('    index.ipcHandle(`${routerPath}.overlayReady`, async () => {\n      this.isWindowReady = true;',
     '    index.ipcHandle(`${routerPath}.overlayReady`, async () => {\n      this.isWindowReady = true;\n'
     '      if (routerPath === "sts2") global.__untappedHarnessEvent("overlay-ready");'),
    ('      index.decayGpuCrashCount();\n      this.emit("show");',
     '      index.decayGpuCrashCount();\n'
     '      if (this.routerPath === "sts2") global.__untappedHarnessEvent("overlay-show");\n'
     '      this.emit("show");'),
    ('    this.logWatcher.on("runComplete", this.onRunComplete.bind(this));',
     '    if (!(' + CONTROLLED + ')) this.logWatcher.on("runComplete", this.onRunComplete.bind(this));'),
    ('  maybeStartLogWatcher() {', '  maybeStartLogWatcher() {\n    if (' + CONTROLLED + ') return;'),
    ('  maybeUploadHistoricRuns() {', '  maybeUploadHistoricRuns() {\n    if (' + CONTROLLED + ') return;'),
    ('async function uploadRun(descriptor, uploadToken, ...entries) {',
     'async function uploadRun(descriptor, uploadToken, ...entries) {\n  if (' + CONTROLLED + ') throw new Error("Controlled harness blocks run uploads");'),
    ('async function uploadHistoricRun(descriptor, uploadToken, runJson) {',
     'async function uploadHistoricRun(descriptor, uploadToken, runJson) {\n  if (' + CONTROLLED + ') throw new Error("Controlled harness blocks historic uploads");'),
])
SERVICES_PATCHES.extend([
    ('      await this.ensureLocalCredentials().then(\n        (localCredentials) => this.ensureUploadToken("MTGA", email, localCredentials.authenticatedCredentials[email])\n      );',
     '      if (!(' + CONTROLLED + ')) await this.ensureLocalCredentials().then(\n        (localCredentials) => this.ensureUploadToken("MTGA", email, localCredentials.authenticatedCredentials[email])\n      );'),
    ('      this.emit("authorizationWorkflowComplete", error);',
     '      if (' + CONTROLLED + ' && error === null) global.__untappedHarnessEvent("authenticated");\n      this.emit("authorizationWorkflowComplete", error);'),
    ('  static async init(clientAnalyticsToken) {',
     '  static async init(clientAnalyticsToken) {\n    if (' + CONTROLLED + ') return;'),
    ('  static async sendInflux(measurement, data = {}, tags = {}) {',
     '  static async sendInflux(measurement, data = {}, tags = {}) {\n    if (' + CONTROLLED + ') return;'),
    ('  static sendMixpanel(event, params) {',
     '  static sendMixpanel(event, params) {\n    if (' + CONTROLLED + ') return;'),
])


def replace_once(text, old, new):
    count = text.count(old)
    if count != 1:
        raise HarnessError(f"Patch anchor must occur once (found {count})")
    return text.replace(old, new, 1)


def patched_entries(archive):
    core = archive.read(CORE).decode()
    for old, new in CORE_PATCHES:
        core = replace_once(core, old, new)
    main = archive.read(MAIN).decode()
    for old, new in MAIN_PATCHES:
        main = replace_once(main, old, new)
    services = archive.read(SERVICES).decode()
    for old, new in SERVICES_PATCHES:
        services = replace_once(services, old, new)
    runtime = archive.read(RUNTIME).decode()
    runtime = replace_once(runtime, RUNTIME_STORE_GETTER_OLD, RUNTIME_STORE_GETTER_NEW)
    store_helper = Path(__file__).with_name("sts2_store_compat.cjs").read_text()
    runtime = replace_once(runtime, RUNTIME_STORE_CLASS, store_helper + "\n" + RUNTIME_STORE_CLASS)
    settings_ui = patch_settings_ui(archive.read(SETTINGS_UI).decode())
    bootstrap = Path(__file__).with_name("bootstrap.cjs").read_text()
    if not main.startswith('"use strict";\n'):
        raise HarnessError("Main entry lost its strict-mode directive")
    main = '"use strict";\n' + bootstrap + "\n" + main[len('"use strict";\n'):]
    return {CORE: core.encode(), MAIN: main.encode(), SERVICES: services.encode(),
            RUNTIME: runtime.encode(), SETTINGS_UI: settings_ui.encode()}
