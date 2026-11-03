"""Synthetic boundary tests for the controlled network adapter."""

import pathlib
import subprocess
import textwrap
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "harness" / "controlled_network.cjs"


class ControlledNetworkTests(unittest.TestCase):
    def run_node(self, script):
        result = subprocess.run(
            ["node", "-e", textwrap.dedent(script), str(ADAPTER)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_fetch_routes_only_to_gateway_and_preserves_module_exports(self):
        self.run_node("""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const os = require('node:os');
            const {install} = require(process.argv[1]);
            const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'controlled-fetch-'));
            fs.chmodSync(dir, 0o700);
            const calls = [];
            function realFetch(url, options) { calls.push([url, options]); return Promise.resolve('ok'); }
            realFetch.Headers = class Headers {};
            realFetch.Request = class Request {};
            realFetch.Response = class Response {};
            const events = [];
            const shell = { openExternal() { throw Error('browser called'); } };
            const adapter = install({ electron: { shell }, fs, path, profile: dir,
                gatewayUrl: 'http://127.0.0.1:18888/fetch', gatewayKey: 'x'.repeat(32),
                originalLoad(name) { assert.equal(name, 'node-fetch'); return realFetch; },
                event(name) { events.push(name); } });
            const wrapped = adapter.loadFetch({}, false);
            assert.equal(wrapped, adapter.loadFetch({}, false));
            assert.equal(wrapped.default, wrapped);
            assert.equal(wrapped.Headers, realFetch.Headers);
            assert.equal(wrapped.Request, realFetch.Request);
            assert.equal(wrapped.Response, realFetch.Response);
            wrapped('https://example.org/api', { method: 'post', headers: { Accept: 'application/json' },
                body: new URLSearchParams({ a: 'b' }), redirect: 'follow' });
            assert.equal(calls.length, 1);
            assert.equal(calls[0][0], 'http://127.0.0.1:18888/fetch');
            assert.deepEqual(JSON.parse(calls[0][1].body), {
                url: 'https://example.org/api', method: 'POST', headers: {Accept: 'application/json'}, body: 'a=b'
            });
            assert.equal(calls[0][1].redirect, 'manual');
            assert.equal(calls[0][1].timeout, 15000);
            assert.equal(calls[0][1].size, 8 * 1024 * 1024);
            assert.equal(calls[0][1].headers['X-Harness-Key'], 'x'.repeat(32));
            assert.deepEqual(events, []);
            assert.throws(() => wrapped('https://example.org', {body: {pipe() {}}}));
            assert.equal(calls.length, 1);
            fs.rmSync(dir, {recursive: true, force: true});
        """)

    def test_manual_oauth_url_is_strict_and_private(self):
        self.run_node("""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const os = require('node:os');
            const {install} = require(process.argv[1]);
            const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'controlled-oauth-'));
            fs.chmodSync(dir, 0o700);
            const events = [];
            const shell = { openExternal() { throw Error('browser called'); } };
            install({electron: {shell}, fs, path, profile: dir,
                gatewayUrl: 'http://127.0.0.1:18888/fetch', gatewayKey: 'y'.repeat(32),
                originalLoad() {throw Error('fetch not requested');}, event(name) {events.push(name);} });
            const url = new URL('https://accounts.untapped.gg/authorize');
            const fields = { response_type: 'code', client_id: 'client',
                redirect_uri: 'http://localhost:17791/', scope: 'companion:full-access',
                state: 'state', code_challenge_method: 'S256', code_challenge: 'challenge',
                utm_source: 'uc', utm_medium: 'app', utm_campaign: 'accounts',
                utm_content: 'add-account-button', franchise: 'STS2' };
            for (const [key, value] of Object.entries(fields)) url.searchParams.set(key, value);
            (async () => {
                await shell.openExternal(url.href);
                const file = path.join(dir, 'manual-sign-in-url.txt');
                assert.equal(fs.readFileSync(file, 'utf8'), url.href + '\\n');
                assert.equal(fs.statSync(file).mode & 0o777, 0o600);
                assert.deepEqual(events, ['manual-sign-in-ready']);
                const rejected = [
                    'https://evil.example/authorize',
                    url.href + '&scope=companion%3Afull-access',
                    url.href + '&extra=x',
                    url.href + '#fragment',
                    url.href.replace('17791', '17790'),
                    url.href.replace('accounts.untapped.gg', 'accounts.untapped.gg:444'),
                    url.href.replace('franchise=STS2', 'franchise=OTHER'),
                ];
                for (const candidate of rejected) await assert.rejects(shell.openExternal(candidate));
                assert.deepEqual(events, ['manual-sign-in-ready']);
                fs.unlinkSync(file);
                fs.symlinkSync('/tmp/controlled-oauth-decoy', file);
                await assert.rejects(shell.openExternal(url.href));
                assert.deepEqual(events, ['manual-sign-in-ready']);
                fs.rmSync(dir, {recursive: true, force: true});
            })().catch(error => { console.error(error); process.exitCode = 1; });
        """)

    def test_invalid_gateway_configuration_is_rejected(self):
        self.run_node("""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const {install} = require(process.argv[1]);
            const base = {electron: {shell: {openExternal() {}}}, fs, path, profile: '/tmp',
                gatewayKey: 'z'.repeat(32), originalLoad() {}, event() {}};
            for (const gatewayUrl of [
                'https://127.0.0.1:18888/fetch',
                'http://localhost:18888/fetch',
                'http://127.0.0.1:18888/fetch?x=1',
                'http://127.0.0.1:18888/other',
                'http://u@127.0.0.1:18888/fetch',
                'http://127.0.0.1:0/fetch',
            ]) assert.throws(() => install({...base, gatewayUrl}));
            assert.throws(() => install({...base, gatewayUrl: 'http://127.0.0.1:18888/fetch', gatewayKey: 'short'}));
        """)


if __name__ == "__main__":
    unittest.main()
