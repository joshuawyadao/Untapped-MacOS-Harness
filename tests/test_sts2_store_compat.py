"""Synthetic contract checks for the original, inlined STS2 store helper."""

import shutil
import subprocess
import textwrap
import unittest
from pathlib import Path


HELPER = Path(__file__).resolve().parents[1] / "harness" / "sts2_store_compat.cjs"

PRELUDE = r"""
    const assert = require('node:assert/strict');
    const vm = require('node:vm');
    const fs = require('node:fs');
    const godot = 'MegaCrit.Sts2.Core.Saves.GodotFileIo';
    const cloud = 'MegaCrit.Sts2.Core.Saves.CloudSaveStore';
    class ScryError extends Error {}
    class ScryObject {
      constructor(obj) { this.obj = obj; }
      get className() { return this.obj.getClassName(); }
      object(name) { return this.obj.getObject(name); }
      cast(ctor) { return new ctor(this.obj); }
      string(name) {
        const value = this.obj.getString(name);
        if (typeof value !== 'string') throw new TypeError('Invalid native string');
        return value;
      }
    }
    class GodotFileIo extends ScryObject {
      get SaveDir() { return this.string('SaveDir'); }
    }
    const context = vm.createContext({ ScryObject, GodotFileIo, ScryError });
    const source = fs.readFileSync(process.argv[1], 'utf8');
    const resolve = vm.runInContext(source + '\nresolveHarnessSts2LocalFileIo', context);
    function native(className, options = {}) {
      return {
        getClassName() { return className; },
        getObject(name) {
          if (options.getObject) return options.getObject(name);
          throw new Error('Unexpected property read: ' + name);
        },
        getString(name) {
          if (options.getString) return options.getString(name);
          throw new Error('Unexpected string read: ' + name);
        },
      };
    }
"""


@unittest.skipUnless(shutil.which("node"), "Node is required for synthetic JS execution")
class Sts2StoreCompatTests(unittest.TestCase):
    def run_node(self, body):
        script = textwrap.dedent(PRELUDE) + "\n" + textwrap.dedent(body)
        result = subprocess.run(
            [shutil.which("node"), "-e", script, str(HELPER)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_direct_godot_store_never_reads_local_store(self):
        self.run_node("""
            const handle = native(godot);
            const result = resolve(new ScryObject(handle));
            assert.ok(result instanceof GodotFileIo);
            assert.strictEqual(result.obj, handle);
        """)

    def test_cloud_store_unwraps_once_and_preserves_native_handle(self):
        self.run_node("""
            const local = native(godot);
            let reads = 0;
            let classReads = 0;
            const outer = native(cloud, { getObject(name) {
              reads++;
              assert.equal(name, 'LocalStore');
              return local;
            } });
            outer.getClassName = () => { classReads++; return cloud; };
            const result = resolve(new ScryObject(outer));
            assert.equal(reads, 1);
            assert.equal(classReads, 1);
            assert.ok(result instanceof GodotFileIo);
            assert.strictEqual(result.obj, local);
        """)

    def test_unknown_outer_and_inner_types_fail_with_fixed_message(self):
        self.run_node("""
            const unsupported = error => error instanceof ScryError &&
              error.message === 'Unsupported STS2 save store';
            assert.throws(() => resolve(new ScryObject(native('Secret.Outer'))), unsupported);
            const outer = native(cloud, { getObject(name) {
              assert.equal(name, 'LocalStore');
              return native('Secret.Inner');
            } });
            assert.throws(() => resolve(new ScryObject(outer)), unsupported);
        """)

    def test_native_class_and_property_errors_propagate(self):
        self.run_node("""
            const classError = new Error('native class failure');
            const classFailure = native(godot);
            classFailure.getClassName = () => { throw classError; };
            assert.throws(() => resolve(new ScryObject(classFailure)), error => error === classError);

            const propertyError = new Error('native property failure');
            const propertyFailure = native(cloud, { getObject() { throw propertyError; } });
            assert.throws(() => resolve(new ScryObject(propertyFailure)), error => error === propertyError);

            const innerError = new Error('native inner class failure');
            const inner = native(godot);
            inner.getClassName = () => { throw innerError; };
            const outer = native(cloud, { getObject() { return inner; } });
            assert.throws(() => resolve(new ScryObject(outer)), error => error === innerError);
        """)

    def test_save_dir_uses_native_string_and_rejects_invalid_values(self):
        self.run_node("""
            const path = '/private/tmp/sts2-saves';
            const valid = native(godot, { getString(name) {
              assert.equal(name, 'SaveDir');
              return path;
            } });
            assert.equal(resolve(new ScryObject(valid)).SaveDir, path);
            const cloudStore = native(cloud, { getObject() { return valid; } });
            assert.equal(resolve(new ScryObject(cloudStore)).SaveDir, path);
            for (const invalid of [null, 7, {}]) {
              const broken = native(godot, { getString() { return invalid; } });
              assert.throws(() => resolve(new ScryObject(broken)).SaveDir, TypeError);
            }
            const stringError = new Error('native string failure');
            const broken = native(godot, { getString() { throw stringError; } });
            assert.throws(() => resolve(new ScryObject(broken)).SaveDir,
              error => error === stringError);
        """)


if __name__ == "__main__":
    unittest.main()
