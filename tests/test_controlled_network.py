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
            function realFetch(url, options) { calls.push([url, options]); return Promise.resolve(new realFetch.Response(Buffer.from('ok'), {status: 200, headers: {}, url})); }
            realFetch.Headers = class Headers {};
            realFetch.Request = class Request {};
            realFetch.Response = class Response {
                constructor(body, options) { this.body = body; Object.assign(this, options); }
                async buffer() { return this.body; }
            };
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
            (async () => {
            const reply = await wrapped('https://example.org/api', { method: 'post', headers: { Accept: 'application/json' },
                body: new URLSearchParams({ a: 'b' }), redirect: 'follow' });
            assert.equal(reply.body.toString(), 'ok');
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
            assert.throws(() => wrapped('https://example.org', {method: 'POST', body: 'x'.repeat(32768)}));
            assert.equal(calls.length, 1);
            fs.rmSync(dir, {recursive: true, force: true});
            })().catch(error => { console.error(error); process.exitCode = 1; });
        """)

    def test_startup_burst_waits_for_complete_bodies_and_never_exceeds_four(self):
        self.run_node("""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const {install} = require(process.argv[1]);
            const gates = [];
            let active = 0, maximum = 0, started = 0;
            class Response {
                constructor(body, options) { this.body = body; Object.assign(this, options); }
                async buffer() { return this.body; }
            }
            function realFetch(url, options) {
                assert.equal(url, 'http://127.0.0.1:18888/fetch');
                assert.equal(JSON.parse(options.body).method, 'GET');
                started += 1;
                active += 1;
                maximum = Math.max(maximum, active);
                let release;
                const gate = new Promise(resolve => { release = resolve; });
                gates.push(release);
                return Promise.resolve({status: 200, statusText: 'OK', headers: {}, url,
                    async buffer() { await gate; active -= 1; return Buffer.from('{}'); }});
            }
            realFetch.Response = Response;
            const secondFetch = Object.assign((...args) => realFetch(...args), {Response});
            const config = {electron: {shell: {openExternal() {}}}, fs, path, profile: '/tmp',
                gatewayUrl: 'http://127.0.0.1:18888/fetch', gatewayKey: 'x'.repeat(32),
                originalLoad(_name, _parent, isMain) {return isMain ? secondFetch : realFetch;}, event() {}};
            const adapter = install(config);
            const fetchA = adapter.loadFetch({}, false);
            const fetchB = adapter.loadFetch({}, true);
            const all = Array.from({length: 18}, (_, i) =>
                (i % 2 ? fetchA : fetchB)('https://sts2json.untapped.gg/data/public/latest/eng/cards.json'));
            (async () => {
                await new Promise(resolve => setImmediate(resolve));
                assert.equal(started, 4);
                for (let i = 0; i < 18; i++) {
                    gates[i]();
                    await new Promise(resolve => setImmediate(resolve));
                }
                const responses = await Promise.all(all);
                assert.equal(responses.length, 18);
                assert(responses.every(r => r.status === 200 && r.body.toString() === '{}'));
                assert.equal(started, 18);
                assert.equal(maximum, 4);
                assert.equal(active, 0);
            })().catch(error => { console.error(error); process.exitCode = 1; });
        """)

    def test_tier_read_retries_transient_failures_only(self):
        self.run_node("""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const {install} = require(process.argv[1]);
            const uuid = '12345678-1234-1234-1234-123456789abc';
            const tier = `https://api.sts2.untapped.gg/api/v1/tier-lists/${uuid}/resolve/?game_version=public`;
            class Response {
                constructor(body, options) { this.body = body; Object.assign(this, options); }
                async buffer() { return this.body; }
            }
            const steps = [];
            function realFetch(url, options) {
                const envelope = JSON.parse(options.body);
                const step = steps.shift();
                assert(step, 'unexpected extra request');
                assert.equal(envelope.url, step.url);
                if (step.error) return Promise.reject(Object.assign(new Error('transient'), step.error));
                return Promise.resolve({status: step.status, statusText: 'status', headers: {a: 'b'}, url,
                    async buffer() {
                        if (step.bodyError) throw Object.assign(new Error('body'), step.bodyError);
                        return Buffer.from('response');
                    }});
            }
            realFetch.Response = Response;
            const adapter = install({electron: {shell: {openExternal() {}}}, fs, path, profile: '/tmp',
                gatewayUrl: 'http://127.0.0.1:18888/fetch', gatewayKey: 'x'.repeat(32),
                originalLoad() {return realFetch;}, event() {}});
            const wrapped = adapter.loadFetch({}, false);
            (async () => {
                steps.push({url: tier, error: {code: 'ECONNRESET'}},
                    {url: tier, status: 502}, {url: tier, status: 200});
                assert.equal((await wrapped(tier)).status, 200);
                steps.push({url: tier, status: 200, bodyError: {type: 'body-timeout'}},
                    {url: tier, status: 200});
                assert.equal((await wrapped(tier)).status, 200);
                steps.push({url: tier, status: 503}, {url: tier, status: 503}, {url: tier, status: 503});
                assert.equal((await wrapped(tier)).status, 503);
                steps.push({url: tier, error: {code: 'ECONNRESET'}},
                    {url: tier, error: {code: 'ECONNRESET'}},
                    {url: tier, error: {code: 'ECONNRESET'}});
                await assert.rejects(wrapped(tier), error => error.code === 'ECONNRESET');
                for (const item of [
                    {url: tier, status: 401},
                    {url: tier, status: 403},
                    {url: tier, status: 404},
                    {url: tier + '&other=1', status: 502},
                    {url: 'https://api.accounts.untapped.gg/o/token', status: 502},
                ]) {
                    steps.push(item);
                    const result = await wrapped(item.url, {method: item.url.includes('/o/token') ? 'POST' : 'GET'});
                    assert.equal(result.status, item.status);
                }
                assert.equal(steps.length, 0);
            })().catch(error => { console.error(error); process.exitCode = 1; });
        """)

    def test_queue_has_finite_pending_capacity_and_drains_after_rejection(self):
        self.run_node("""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const {install} = require(process.argv[1]);
            const gates = [];
            class Response {
                constructor(body, options) { this.body = body; Object.assign(this, options); }
                async buffer() { return this.body; }
            }
            function realFetch(url) {
                let release;
                const gate = new Promise(resolve => { release = resolve; });
                gates.push(release);
                return Promise.resolve({status: 200, statusText: 'OK', headers: {}, url,
                    async buffer() { await gate; return Buffer.from('{}'); }});
            }
            realFetch.Response = Response;
            const wrapped = install({electron: {shell: {openExternal() {}}}, fs, path, profile: '/tmp',
                gatewayUrl: 'http://127.0.0.1:18888/fetch', gatewayKey: 'x'.repeat(32),
                originalLoad() {return realFetch;}, event() {}}).loadFetch({}, false);
            const target = 'https://sts2json.untapped.gg/data/public/latest/eng/cards.json';
            const admitted = Array.from({length: 132}, () => wrapped(target));
            const rejected = wrapped(target);
            (async () => {
                await assert.rejects(rejected, /queue full/);
                for (let i = 0; i < 132; i++) {
                    assert.equal(gates.length, Math.min(132, i + 4));
                    gates[i]();
                    await new Promise(resolve => setImmediate(resolve));
                }
                assert.equal((await Promise.all(admitted)).length, 132);
            })().catch(error => { console.error(error); process.exitCode = 1; });
        """)

    def test_waiting_request_expires_without_reaching_gateway(self):
        self.run_node("""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const {install} = require(process.argv[1]);
            const releases = [];
            let calls = 0;
            class Response {
                constructor(body, options) { this.body = body; Object.assign(this, options); }
                async buffer() { return this.body; }
            }
            function realFetch(url) {
                calls++;
                let release;
                const gate = new Promise(resolve => {release = resolve;});
                releases.push(release);
                return Promise.resolve({status: 200, statusText: 'OK', headers: {}, url,
                    async buffer() {await gate; return Buffer.from('{}');}});
            }
            realFetch.Response = Response;
            const wrapped = install({electron: {shell: {openExternal() {}}}, fs, path, profile: '/tmp',
                gatewayUrl: 'http://127.0.0.1:18888/fetch', gatewayKey: 'x'.repeat(32),
                originalLoad() {return realFetch;}, event() {}}).loadFetch({}, false);
            const target = 'https://sts2json.untapped.gg/data/public/latest/eng/cards.json';
            const realSetTimeout = global.setTimeout;
            const scheduled = [];
            global.setTimeout = (fn, delay) => {
                assert.equal(delay, 60000);
                scheduled.push(fn);
                return {mockTimer: true};
            };
            const active = Array.from({length: 4}, () => wrapped(target));
            const waiting = wrapped(target);
            global.setTimeout = realSetTimeout;
            (async () => {
                assert.equal(scheduled.length, 1);
                scheduled[0]();
                await assert.rejects(waiting, /queue timed out/);
                await new Promise(resolve => setImmediate(resolve));
                assert.equal(calls, 4);
                releases.forEach(release => release());
                assert.equal((await Promise.all(active)).length, 4);
                assert.equal(calls, 4);
            })().catch(error => { console.error(error); process.exitCode = 1; });
        """)

    def test_oversized_response_body_fails_closed(self):
        self.run_node("""
            const assert = require('node:assert/strict');
            const fs = require('node:fs');
            const path = require('node:path');
            const {install} = require(process.argv[1]);
            class Response {}
            function realFetch(url) {
                return Promise.resolve({status: 200, statusText: 'OK', headers: {}, url,
                    async buffer() {return Buffer.alloc(8 * 1024 * 1024 + 1);}});
            }
            realFetch.Response = Response;
            const wrapped = install({electron: {shell: {openExternal() {}}}, fs, path, profile: '/tmp',
                gatewayUrl: 'http://127.0.0.1:18888/fetch', gatewayKey: 'x'.repeat(32),
                originalLoad() {return realFetch;}, event() {}}).loadFetch({}, false);
            assert.rejects(wrapped('https://sts2json.untapped.gg/data/public/latest/eng/cards.json'),
                /response too large/).catch(error => { console.error(error); process.exitCode = 1; });
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
