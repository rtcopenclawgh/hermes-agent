"""Stale in-memory auth snapshots must not clobber a newer login on disk.

A process that loaded auth.json, then saved after another process added
openai-codex, used to rewrite the file without Codex. Logout must still
persist when the snapshot and the file share updated_at.
"""

from __future__ import annotations

import json

import hermes_cli.auth as auth


def _write(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_save_keeps_newer_disk_provider(tmp_path):
    auth_path = tmp_path / "auth.json"
    older = {
        "version": 1,
        "updated_at": "2026-09-02T22:00:00+00:00",
        "active_provider": "openai-codex",
        "providers": {"xai-oauth": {"last_refresh": "old"}},
        "credential_pool": {"xai-oauth": [{"id": "x1"}]},
    }
    newer = {
        "version": 1,
        "updated_at": "2026-09-02T22:26:00+00:00",
        "active_provider": "openai-codex",
        "providers": {
            "xai-oauth": {"last_refresh": "old"},
            "openai-codex": {"tokens": {"access_token": "a", "refresh_token": "r"}},
        },
        "credential_pool": {
            "xai-oauth": [{"id": "x1"}],
            "openai-codex": [{"id": "c1", "tokens": {"access_token": "a"}}],
        },
    }
    _write(auth_path, newer)

    auth._save_auth_store(older, target_path=auth_path)

    saved = json.loads(auth_path.read_text(encoding="utf-8"))
    assert "openai-codex" in saved["providers"]
    assert saved["providers"]["openai-codex"]["tokens"]["refresh_token"] == "r"
    assert "openai-codex" in saved["credential_pool"]
    assert saved["credential_pool"]["openai-codex"][0]["id"] == "c1"
    assert saved["providers"]["xai-oauth"]["last_refresh"] == "old"


def test_logout_still_drops_provider_when_disk_is_not_newer(tmp_path):
    auth_path = tmp_path / "auth.json"
    ts = "2026-09-02T22:00:00+00:00"
    _write(
        auth_path,
        {
            "version": 1,
            "updated_at": ts,
            "providers": {
                "xai-oauth": {"last_refresh": "old"},
                "openai-codex": {"tokens": {"access_token": "a"}},
            },
        },
    )
    incoming = {
        "version": 1,
        "updated_at": ts,
        "providers": {"xai-oauth": {"last_refresh": "old"}},
    }

    auth._save_auth_store(incoming, target_path=auth_path)

    saved = json.loads(auth_path.read_text(encoding="utf-8"))
    assert "openai-codex" not in saved["providers"]
    assert "xai-oauth" in saved["providers"]
