"""Tests run without hardware via mock sysfs trees and live read-only checks."""
from __future__ import annotations

import os
import tempfile

from litage import capabilities as capmod
from litage.backends import legion, platform_profile, tlp


def _mock_yoga() -> str:
    d = tempfile.mkdtemp(prefix="litage-mock-")
    os.makedirs(os.path.join(d, "VPC2004:00"))
    open(os.path.join(d, "VPC2004:00/conservation_mode"), "w").write("1")
    os.makedirs(os.path.join(d, "platform-profile"))
    open(os.path.join(d, "platform-profile/profile"), "w").write("balanced")
    os.makedirs(os.path.join(d, "dmi"), exist_ok=True)
    open(os.path.join(d, "dmi/sys_vendor"), "w").write("LENOVO")
    open(os.path.join(d, "dmi/product_name"), "w").write("83JR")
    open(os.path.join(d, "dmi/bios_version"), "w").write("QXCN26WW")
    return d


def test_mock_detect_ideapad():
    d = _mock_yoga()
    cap = capmod.detect(sys_root=d)
    assert cap.has_ideapad is True
    assert cap.product_name == "83JR"
    assert cap.has_firmware_profile is True


def test_live_detect_does_not_crash():
    cap = capmod.detect()
    assert isinstance(cap.vendor, str)
    # on this Yoga: no legion, no nvidia -> pages hidden
    assert cap.show_dgpu_page is False
    assert cap.show_fan_curve_page is False


def test_set_profile_rejects_garbage():
    ok, _msg = platform_profile.set_profile("turbo-ultra")
    assert ok is False


def test_writable_map_filters():
    # capability gating logic used by `litage list`
    cap = capmod.detect()
    assert cap.has_ideapad is True  # live Yoga
    assert cap.has_battery is True
    assert len(cap.platform_profiles) >= 1
    assert cap.has_tlp is True  # tlp kurulu
    assert cap.has_thinkpad is False  # Yoga'da thinkpad_acpi yok


def test_legion_absent_on_yoga():
    # Yoga'da legion modülü yok -> backend present=False dönmeli
    assert legion.exists() is False
    assert legion.get_all() == {"present": False}
    ok, _msg = legion.set_bool("fan_fullspeed", "on")
    assert ok is False


def test_tlp_readonly_safe():
    # rootsuz okuma çökmemeli; yazma aralık kontrolü rootsuz da çalışır
    assert tlp.available() is True
    info = tlp.system_info()
    assert info.get("present") is True
    ok, _msg = tlp.setcharge(90, 20)  # ters aralık -> reddedilmeli (yazmadan)
    assert ok is False
    ok, _msg = tlp.force_profile("nonsense")
    assert ok is False


def test_apply_parses_pairs_without_writes():
    # donanıma yazmadan ayrıştırma testi (bilinmeyen özellik -> kod 1)
    from litage import cli
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = cli.cmd_apply(type("A", (), {"pairs": ["nope_xyz=1", "kötübiçim"]})())
    assert code == 1
    out = buf.getvalue()
    assert "nope_xyz" in out and "atlandi" in out
