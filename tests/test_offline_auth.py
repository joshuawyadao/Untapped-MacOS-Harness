"""Synthetic execution checks for the pinned companion's offline auth seam."""
import shutil
import subprocess
import unittest

from harness.asar import Archive, HarnessError
from harness import patches
from test_harness import synthetic_archive


AUTH_ANCHOR = "  async ensureLocalCredentials() {\n    const authDetails = await this.loadLocalCredentials();"
SERVICES_SOURCE = """class AuthenticationManager {
  async ensureLocalCredentials() {
    const authDetails = await this.loadLocalCredentials();
    if (Object.keys(authDetails.authenticatedCredentials).length || authDetails.anonymousCredentials !== null) {
      return authDetails;
    }
    const token = await this.fetchAnonymousUploadToken();
    await this.localCredentialsManager.storeAnonymousCredentials(token);
    return { authenticatedCredentials: {}, anonymousCredentials: { token } };
  }
}
"""


def fixture_archive(services=SERVICES_SOURCE):
    core = "\n".join(old for old, _ in patches.CORE_PATCHES) + "\nTERMS_REMAIN_USER_CONTROLLED\n"
    main = '"use strict";\n' + "\n".join(old for old, _ in patches.MAIN_PATCHES)
    return Archive(synthetic_archive({
        patches.CORE: core.encode(),
        patches.MAIN: main.encode(),
        patches.SERVICES: services.encode(),
        "untouched.txt": b"unchanged",
    }))


class OfflineAuthTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node is required for synthetic JS execution")
    def test_offline_credentials_are_empty_without_credential_io_or_token_acquisition(self):
        archive = fixture_archive()
        source = patches.patched_entries(archive).get(patches.SERVICES, archive.read(patches.SERVICES)).decode()
        script = r"""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const vm = require('node:vm');
            const source = fs.readFileSync(0, 'utf8');
            function instance(environment, initialCredentials) {
              const context = vm.createContext({ process: { env: environment } });
              vm.runInContext(source + '\nglobalThis.Auth = AuthenticationManager;', context);
              const manager = new context.Auth();
              const calls = { load: 0, fetch: 0, store: 0 };
              manager.loadLocalCredentials = async () => {
                calls.load++;
                return initialCredentials;
              };
              manager.fetchAnonymousUploadToken = async () => {
                calls.fetch++;
                return 'synthetic-token';
              };
              manager.localCredentialsManager = { storeAnonymousCredentials: async () => { calls.store++; } };
              return { manager, calls };
            }
            (async () => {
              const empty = { authenticatedCredentials: {}, anonymousCredentials: null };
              const offline = instance({ UNTAPPED_HARNESS_OFFLINE: '1' }, empty);
              const first = await offline.manager.ensureLocalCredentials();
              const second = await offline.manager.ensureLocalCredentials();
              assert.deepEqual(JSON.parse(JSON.stringify(first)), empty);
              assert.deepEqual(JSON.parse(JSON.stringify(second)), empty);
              assert.notEqual(first, second);
              assert.deepEqual(offline.calls, { load: 0, fetch: 0, store: 0 });

              const existing = { authenticatedCredentials: { example: { token: 'existing' } }, anonymousCredentials: null };
              const normal = instance({}, existing);
              assert.equal(await normal.manager.ensureLocalCredentials(), existing);
              assert.deepEqual(normal.calls, { load: 1, fetch: 0, store: 0 });

              const emptyNormal = instance({ UNTAPPED_HARNESS_OFFLINE: 'true' }, empty);
              const acquired = await emptyNormal.manager.ensureLocalCredentials();
              assert.equal(acquired.anonymousCredentials.token, 'synthetic-token');
              assert.deepEqual(emptyNormal.calls, { load: 1, fetch: 1, store: 1 });
            })().catch((error) => { console.error(error); process.exitCode = 1; });
        """
        result = subprocess.run(
            [shutil.which("node"), "-e", script], input=source,
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_three_patched_entries_preserve_terms_and_unrelated_archive_content(self):
        archive = fixture_archive()
        replacements = patches.patched_entries(archive)
        self.assertEqual(set(replacements), {patches.CORE, patches.MAIN, patches.SERVICES})
        rewritten = Archive(archive.rewrite(replacements))
        self.assertEqual(rewritten.read("untouched.txt"), b"unchanged")
        self.assertIn(b"TERMS_REMAIN_USER_CONTROLLED", rewritten.read(patches.CORE))
        self.assertIn(b'UNTAPPED_HARNESS_OFFLINE === "1"', rewritten.read(patches.SERVICES))
        self.assertEqual(archive.read(patches.SERVICES), SERVICES_SOURCE.encode())

    def test_missing_or_duplicate_services_method_refuses_patch(self):
        for source in (SERVICES_SOURCE.replace(AUTH_ANCHOR, "async ensureOtherCredentials() {"),
                       SERVICES_SOURCE + SERVICES_SOURCE):
            with self.subTest(source_count=source.count(AUTH_ANCHOR)):
                with self.assertRaises(HarnessError):
                    patches.patched_entries(fixture_archive(source))


if __name__ == "__main__":
    unittest.main()
