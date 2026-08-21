"""Smoke end-to-end Docker asset checks."""

from __future__ import annotations


def test_smoke_assets_exist_in_image(host):
    assert host.file(
        "/root/lunarvim-config/tests/smoke/fixtures/log/app.log"
    ).exists
