"""Synthetic profile coverage; no live Untapped profile is read."""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harness import main_preferences as prefs
from harness.asar import HarnessError


class PreferencesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name).resolve()
        self.profile = root / "profile"
        self.preferences = root / "preferences"
        self.profile.mkdir(mode=0o700)
        self.preferences.mkdir(mode=0o700)

    def test_default_lists_fill_all_characters_once_and_preserve_custom_choices(self):
        custom = "123e4567-e89b-12d3-a456-426614174000"
        baalo = prefs.DEFAULT_TIERS["baalorlord"]
        initial = {custom: {"uuid": custom, "color": "silent", "isEnabled": True},
                   baalo["ironclad"]: {"uuid": baalo["ironclad"], "color": "ironclad", "isEnabled": True}}
        (self.preferences / "preferences.json").write_text(json.dumps({"tier_lists": initial}))
        prefs.seed(self.profile, self.preferences, enable_default_tiers=True)
        index = self.profile / "sts2/tier-lists/index.json"
        tiers = json.loads(index.read_text())
        self.assertEqual({row["color"] for row in tiers.values() if row["isEnabled"]},
                         {"ironclad", "silent", "regent", "necrobinder", "defect"})
        self.assertEqual(tiers[custom], initial[custom])
        self.assertNotIn(baalo["silent"], tiers)
        self.assertFalse((self.profile / "config.json").exists())
        tiers[baalo["regent"]]["isEnabled"] = False
        index.write_text(json.dumps(tiers))
        prefs.harvest(self.profile, self.preferences)
        fresh = self.profile.parent / "next-profile"
        fresh.mkdir(mode=0o700)
        prefs.seed(fresh, self.preferences, enable_default_tiers=True)
        next_tiers = json.loads((fresh / "sts2/tier-lists/index.json").read_text())
        self.assertFalse(next_tiers[baalo["regent"]]["isEnabled"])
        self.assertEqual(json.loads((self.preferences / "preferences.json").read_text())["default_tiers_version"], 1)

    def test_default_lists_prefer_existing_jorbs_and_refuse_overflow(self):
        jorbs = prefs.DEFAULT_TIERS["jorbs"]
        initial = {jorbs["silent"]: {"uuid": jorbs["silent"], "color": "silent", "isEnabled": True}}
        self.assertEqual(set(prefs._fill_default_tiers(initial)), set(jorbs.values()))
        full = {f"123e4567-e89b-12d3-a456-{i:012d}": {
            "uuid": f"123e4567-e89b-12d3-a456-{i:012d}", "color": "colorless", "isEnabled": False}
            for i in range(128)}
        with self.assertRaises(HarnessError):
            prefs._fill_default_tiers(full)

    def test_first_run_does_not_accept_terms_or_create_config(self):
        result = prefs.seed(self.profile, self.preferences)
        self.assertFalse(result["terms_seeded"])
        self.assertFalse((self.profile / "config.json").exists())

    def test_only_allowlisted_settings_and_tier_ids_survive(self):
        identifier = "123e4567-e89b-12d3-a456-426614174000"
        disabled = "123e4567-e89b-12d3-a456-426614174001"
        (self.profile / "config.json").write_text(json.dumps({
            "acceptedTOS": True, "oauthToken": "secret-token", "account": {"email": "secret@example.test"},
            "sts2": {"badgeMode": "tiers", "enableOverlay": True, "enableCardRewardStats": False,
                     "privateKey": "secret-token"},
        }))
        tier = self.profile / "sts2/tier-lists"
        tier.mkdir(parents=True, mode=0o700)
        (self.profile / "sts2").chmod(0o700)
        (tier / "index.json").write_text(json.dumps({
            identifier: {"uuid": identifier, "isEnabled": True, "color": "silent",
                         "author": "secret@example.test", "items": ["secret-token"]},
            disabled: {"uuid": disabled, "isEnabled": False, "color": "regent"},
            "bad": {"uuid": "bad", "isEnabled": True, "color": "silent"},
        }))
        result = prefs.harvest(self.profile, self.preferences)
        self.assertEqual(result["tier_lists_saved"], 2)
        saved = (self.preferences / "preferences.json").read_text()
        self.assertNotIn("secret", saved)
        self.assertEqual(os.stat(self.preferences / "preferences.json").st_mode & 0o777, 0o600)
        fresh = Path(self.temp.name).resolve() / "fresh"
        fresh.mkdir(mode=0o700)
        seeded = prefs.seed(fresh, self.preferences)
        self.assertTrue(seeded["terms_seeded"])
        self.assertEqual(json.loads((fresh / "config.json").read_text()),
                         {"acceptedTOS": True, "sts2": {"badgeMode": "tiers", "enableOverlay": True,
                                                          "enableCardRewardStats": False}})
        tiers = json.loads((fresh / "sts2/tier-lists/index.json").read_text())
        self.assertTrue(tiers[identifier]["isEnabled"])
        self.assertFalse(tiers[disabled]["isEnabled"])
        self.assertEqual(set(tiers[identifier]), {"uuid", "isEnabled", "color"})

    def test_symlink_and_oversize_input_rejected(self):
        outside = Path(self.temp.name) / "outside"
        outside.write_text("{}")
        (self.profile / "config.json").symlink_to(outside)
        with self.assertRaises(HarnessError):
            prefs.harvest(self.profile, self.preferences)
        (self.profile / "config.json").unlink()
        (self.profile / "config.json").write_bytes(b" " * (prefs.MAX_JSON + 1))
        with self.assertRaises(HarnessError):
            prefs.harvest(self.profile, self.preferences)

    def test_invalid_values_drop_without_copying_secrets(self):
        (self.profile / "config.json").write_text(json.dumps({
            "acceptedTOS": "true", "sts2": {"badgeMode": "secret-token", "enableOverlay": 1}}))
        prefs.harvest(self.profile, self.preferences)
        self.assertEqual(json.loads((self.preferences / "preferences.json").read_text())["config"], {})

    def test_swapped_profile_root_still_reads_original_descriptor(self):
        (self.profile / "config.json").write_text(json.dumps({"sts2": {"enableOverlay": True}}))
        outside = Path(self.temp.name).resolve() / "outside"
        outside.mkdir(mode=0o700)
        (outside / "config.json").write_text(json.dumps({"sts2": {"enableOverlay": False}}))
        moved = Path(self.temp.name).resolve() / "moved-profile"
        original = prefs._read_at
        switched = False

        def swap_then_read(fd, names):
            nonlocal switched
            if not switched and names == ("config.json",):
                self.profile.rename(moved)
                self.profile.symlink_to(outside)
                switched = True
            return original(fd, names)

        with patch.object(prefs, "_read_at", side_effect=swap_then_read):
            prefs.harvest(self.profile, self.preferences)
        saved = json.loads((self.preferences / "preferences.json").read_text())
        self.assertTrue(saved["config"]["sts2"]["enableOverlay"])
        self.assertFalse(json.loads((outside / "config.json").read_text())["sts2"]["enableOverlay"])

    def test_swapped_preference_root_does_not_write_outside(self):
        (self.profile / "config.json").write_text(json.dumps({"sts2": {"badgeMode": "tiers"}}))
        outside = Path(self.temp.name).resolve() / "outside"
        outside.mkdir(mode=0o700)
        sentinel = outside / "preferences.json"
        sentinel.write_text("outside-unchanged")
        moved = Path(self.temp.name).resolve() / "moved-preferences"
        original = prefs._write_at

        def swap_then_write(fd, names, value):
            self.preferences.rename(moved)
            self.preferences.symlink_to(outside)
            return original(fd, names, value)

        with patch.object(prefs, "_write_at", side_effect=swap_then_write):
            prefs.harvest(self.profile, self.preferences)
        self.assertEqual(sentinel.read_text(), "outside-unchanged")
        self.assertEqual(json.loads((moved / "preferences.json").read_text())["config"]["sts2"]["badgeMode"],
                         "tiers")

    def test_symlink_tier_ancestor_rejected(self):
        outside = Path(self.temp.name).resolve() / "outside"
        outside.mkdir(mode=0o700)
        (self.profile / "sts2").symlink_to(outside)
        with self.assertRaises(HarnessError):
            prefs.harvest(self.profile, self.preferences)
        self.assertFalse((outside / "tier-lists").exists())
