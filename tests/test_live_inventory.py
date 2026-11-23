"""Persistent process inventory and native macOS candidate matching."""

import io
import os
import platform
from pathlib import Path
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from harness import live_inventory, reward_probe


class WorkerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.helper = self.root / "worker"

    def script(self, body):
        self.helper.write_text(f"#!{sys.executable}\n" + body)
        self.helper.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        return self.helper

    def test_reuses_worker_and_reads_a_fresh_response_each_time(self):
        helper = self.script(
            "import os, sys\n"
            "for number, request in enumerate(sys.stdin.buffer, start=1):\n"
            "    if request != b'\\n': break\n"
            "    sys.stdout.buffer.write(f'{number} {os.getuid()} /copy/Slay the Spire 2\\n'.encode() + b'\\x00')\n"
            "    sys.stdout.buffer.flush()\n"
        )
        inventory = live_inventory.LiveInventory(helper)
        self.addCleanup(inventory.close)
        self.assertEqual(inventory.candidates(), [(1, os.getuid(), "/copy/Slay the Spire 2", False)])
        worker_pid = inventory.process.pid
        self.assertEqual(inventory.candidates(), [(2, os.getuid(), "/copy/Slay the Spire 2", False)])
        self.assertEqual(inventory.process.pid, worker_pid)

    def test_stalled_worker_reap_does_not_block_fresh_alternate_scan(self):
        inventory = live_inventory.LiveInventory(self.helper)
        worker = inventory.process = Mock()
        worker.poll.return_value = None
        worker.wait.side_effect = AssertionError("The timed-out scan waited for child cleanup")
        inventory.channel = Mock()
        inventory.channel.recv.side_effect = socket.timeout
        fresh = f"7 {os.getuid()} /fresh/Slay the Spire 2\n"
        with patch.object(inventory, "_legacy_listing", return_value=fresh, create=True) as legacy:
            with self.assertRaises(subprocess.TimeoutExpired) as error:
                inventory.candidates()
            self.assertEqual(error.exception.phase, "NATIVE_RESPONSE")
            worker.kill.assert_called_once()
            worker.wait.assert_not_called()
            self.assertEqual(inventory.candidates(), [(7, os.getuid(), "/fresh/Slay the Spire 2", False)])
            legacy.assert_called_once()
            with self.assertRaises(live_inventory.InventoryTimeout) as blocked:
                inventory.candidates()
            self.assertEqual(blocked.exception.phase, "NATIVE_REAP")
            worker.wait.assert_not_called()

    def test_timed_out_legacy_scan_stops_without_waiting_and_retries_native(self):
        inventory = live_inventory.LiveInventory(self.helper)
        inventory._use_legacy = True
        worker = Mock(returncode=None, stdout=io.StringIO())
        worker.poll.return_value = None
        worker.communicate.side_effect = subprocess.TimeoutExpired("legacy fixture", 2)
        payload = f"7 {os.getuid()} /fresh/Slay the Spire 2\n".encode()
        with patch.object(live_inventory.subprocess, "Popen", return_value=worker), \
             patch.object(inventory, "_exchange", return_value=(payload, 0)) as native:
            with self.assertRaises(live_inventory.InventoryTimeout) as error:
                inventory.candidates()
            self.assertEqual(error.exception.phase, "LEGACY_RESPONSE")
            worker.kill.assert_called_once()
            worker.wait.assert_not_called()
            self.assertTrue(worker.stdout.closed)
            self.assertEqual(inventory.candidates(), [(7, os.getuid(), "/fresh/Slay the Spire 2", False)])
            native.assert_called_once()

    def test_dead_worker_and_malformed_output_fail_and_can_restart(self):
        for body, error in (
            ("import sys\nsys.exit(1)\n", subprocess.CalledProcessError),
            ("import sys\nsys.stdin.buffer.readline()\nsys.stdout.buffer.write(b'\\xff\\x00')\nsys.stdout.buffer.flush()\n", UnicodeError),
        ):
            with self.subTest(error=error):
                inventory = live_inventory.LiveInventory(self.script(body))
                self.addCleanup(inventory.close)
                with self.assertRaises(error):
                    inventory.candidates()
                self.assertIsNone(inventory.process)
                self.assertIsNone(inventory.channel)

    def test_incomplete_native_snapshot_uses_legacy_inventory(self):
        helper = self.script(
            "import os, sys\n"
            "for request in sys.stdin.buffer:\n"
            "    sys.stdout.buffer.write(f'1 {os.getuid()} /old/Slay the Spire 2\\n'.encode() + b'\\x01')\n"
            "    sys.stdout.buffer.flush()\n"
        )
        inventory = live_inventory.LiveInventory(helper)
        self.addCleanup(inventory.close)
        current = f"2 {os.getuid()} /current/Slay the Spire 2\n"
        command = (sys.executable, "-c", f"import sys; sys.stdout.write({current!r})")
        with patch.object(reward_probe, "PROCESS_INVENTORY_COMMAND", command):
            self.assertEqual(inventory.candidates(),
                             [(2, os.getuid(), "/current/Slay the Spire 2", False)])

    def test_resolves_only_unreadable_pids_and_keeps_native_candidates(self):
        uid = os.getuid()
        foreign_uid = uid + 1
        inventory = live_inventory.LiveInventory(self.helper)
        payload = f"1 {uid} /copy/Slay the Spire 2\n? 11 {foreign_uid}\n? 12 {uid}\n".encode()
        listing = f" 12 {uid} /usr/bin/true\n 11 {foreign_uid} /foreign/Steam.app/Contents/MacOS/steam_osx\n"
        worker = Mock(returncode=0, stdout=io.StringIO())
        worker.communicate.return_value = listing, None
        with patch.object(inventory, "_exchange", return_value=(payload, 1)), \
             patch.object(live_inventory.subprocess, "Popen", return_value=worker) as spawn:
            self.assertEqual(inventory.candidates(), [
                (1, uid, "/copy/Slay the Spire 2", False),
                (11, foreign_uid, "/foreign/Steam.app/Contents/MacOS/steam_osx", True),
            ])
        self.assertEqual(spawn.call_args.args[0], ("/bin/ps", "-p", "11,12", "-o", "pid=,uid=,comm="))

    def test_inconclusive_scoped_response_requires_fresh_full_listing(self):
        uid = os.getuid()
        inventory = live_inventory.LiveInventory(self.helper)
        payload = f"1 {uid} /stale/Slay the Spire 2\n? 11 {uid}\n? 12 {uid}\n".encode()
        full = f"2 {uid} /fresh/Slay the Spire 2\n"
        for scoped in (
            f"11 {uid} /usr/bin/true\n",
            f"11 {uid} /usr/bin/true\n12 {uid + 1} /usr/bin/true\n",
            f"11 {uid} /usr/bin/true\n11 {uid} /usr/bin/true\n",
            f"11 {uid} /usr/bin/true\n12 {uid}\n",
        ):
            with self.subTest(scoped=scoped), \
                 patch.object(inventory, "_exchange", return_value=(payload, 1)), \
                 patch.object(inventory, "_legacy_listing", side_effect=[scoped, full]) as legacy:
                self.assertEqual(inventory.candidates(), [(2, uid, "/fresh/Slay the Spire 2", False)])
                qualified, broad = legacy.call_args_list
                self.assertEqual(qualified.kwargs, {"pids": ("11", "12")})
                self.assertEqual(qualified.args, broad.args)
                self.assertEqual(broad.kwargs, {})

    def test_scoped_timeout_preserves_native_worker_and_never_returns_partial_rows(self):
        uid = os.getuid()
        inventory = live_inventory.LiveInventory(self.helper)
        native = inventory.process = Mock()
        worker = Mock(returncode=None, stdout=io.StringIO())
        worker.poll.return_value = None
        worker.communicate.side_effect = subprocess.TimeoutExpired("scoped fixture", 2)
        payload = f"1 {uid} /copy/Slay the Spire 2\n? 11 {uid}\n".encode()
        with patch.object(inventory, "_exchange", return_value=(payload, 1)), \
             patch.object(live_inventory.subprocess, "Popen", return_value=worker):
            with self.assertRaises(live_inventory.InventoryTimeout) as error:
                inventory.candidates()
            self.assertEqual(error.exception.phase, "SCOPED_RESPONSE")
            self.assertIn(error.exception.phase, live_inventory.TIMEOUT_PHASES)
            self.assertIs(inventory.process, native)
            native.kill.assert_not_called()
            worker.kill.assert_called_once()
            worker.wait.assert_not_called()

    def test_timed_out_worker_is_reaped_then_next_request_uses_a_new_worker(self):
        marker = self.root / "first-request"
        helper = self.script(
            "import os, pathlib, sys, time\n"
            f"marker = pathlib.Path({str(marker)!r})\n"
            "for request in sys.stdin.buffer:\n"
            "    if not marker.exists():\n"
            "        marker.touch()\n"
            "        time.sleep(5)\n"
            "    sys.stdout.buffer.write(f'7 {os.getuid()} /copy/Slay the Spire 2\\n'.encode() + b'\\x00')\n"
            "    sys.stdout.buffer.flush()\n"
        )
        inventory = live_inventory.LiveInventory(helper)
        self.addCleanup(inventory.close)
        inventory._start()
        original = inventory.process
        with patch.object(live_inventory, "TIMEOUT", 0.5):
            with self.assertRaises(subprocess.TimeoutExpired) as error:
                inventory.candidates()
            self.assertEqual(error.exception.timeout, 0.5)
            self.assertTrue(marker.exists())
            self.assertIsNone(inventory.process)
            self.assertIsNone(inventory.channel)
            original.wait(timeout=5)
            with patch.object(inventory, "_legacy_listing", return_value=""):
                self.assertEqual(inventory.candidates(), [])
            self.assertEqual(inventory.candidates(), [(7, os.getuid(), "/copy/Slay the Spire 2", False)])
            self.assertIsNot(inventory.process, original)


@unittest.skipUnless(platform.system() == "Darwin" and Path("/usr/bin/clang").is_file(),
                     "requires macOS and clang")
class NativeCandidateTests(unittest.TestCase):
    def test_native_inventory_matches_ps_for_own_aliased_game_and_steam(self):
        if os.getuid() == 0:
            self.skipTest("helper refuses privileged execution")
        if any(not steam for _, _, _, steam in reward_probe._candidates(reward_probe._process_inventory())):
            self.skipTest("game-name process fixtures require Slay the Spire 2 to be closed")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            aliases = (
                "/synthetic/Slay the Spire 2",
                "/synthetic/Steam.app/Contents/MacOS/steam_osx",
            )
            fixtures = []
            try:
                for alias in aliases:
                    fixture = subprocess.Popen([alias, "10"], executable="/bin/sleep")
                    fixtures.append(fixture)
                pids = {fixture.pid for fixture in fixtures}
                with live_inventory.prepare(root) as candidates:
                    native = [row for row in candidates() if row[0] in pids]
                    self.assertEqual(native, [row for row in candidates() if row[0] in pids])
                legacy = [row for row in reward_probe._candidates(reward_probe._process_inventory())
                          if row[0] in pids]
                self.assertEqual(sorted(native), sorted(legacy))
                self.assertEqual({row[2] for row in native}, set(aliases))
                self.assertEqual({row[3] for row in native}, {False, True})
            finally:
                for fixture in fixtures:
                    fixture.terminate()
                    fixture.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
