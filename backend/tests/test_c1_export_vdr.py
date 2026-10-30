"""
C1 — aeris-trip/1 export (backend/export_vdr.py) on S3b cropped to t <= 300 s.

Finds S3b through conftest (AERIS_DATA_DIR, else <repo>/IO-VNBD). Nothing here is skipped: a missing dataset FAILS every test.
All filter work happens once, at module level, while builtins.open and pandas.read_csv are patched so that any attempt to
open a V-* (VBOX) file raises and is recorded. Cached runs (all on the same <= 300 s phone input):
  TRIP        build_trip(<= 300 s)                     — the export itself (plus one truncated re-run per replay)
  TRIP_270    build_trip(<= 270 s)                     — causality: a shorter input must give the same earlier frames
  TRIP_CLEAN  build_trip(input with the in-outage fixes already removed)
  RAW_WINDOW  vehicle_dr.run_pipeline(<= 300 s raw input, outage_window=(200, 260))  — fixes present but masked
"""
import ast
import builtins
import json
import math
import os
import sys
import unittest
from unittest import mock

import numpy as np
import pandas

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import S3b_S_PATH       # noqa: E402
import export_vdr                     # noqa: E402
import vehicle_dr                     # noqa: E402
from data_loader import load_smartphone   # noqa: E402

OUTAGE = (200.0, 260.0)
FRAME_KEYS = {"t_s", "lat", "lon", "bearing_deg", "speed_mps", "sigma_major_m", "sigma_minor_m", "ellipse_angle_deg",
              "cov_en_m2", "fix_age_s", "status", "stationary"}
CAUSES = {"launch_cal", "gnss_rejoin", "replay", "other"}
V_ATTEMPTS = []
_real_open, _real_read_csv = builtins.open, pandas.read_csv


def _is_vbox(path):
    return os.path.basename(str(path)).upper().startswith("V-")


def _guarded_open(file, *a, **k):
    if _is_vbox(file):
        V_ATTEMPTS.append(str(file))
        raise PermissionError(f"VBOX file blocked in the export test: {file}")
    return _real_open(file, *a, **k)


def _guarded_read_csv(path, *a, **k):
    if _is_vbox(path):
        V_ATTEMPTS.append(str(path))
        raise PermissionError(f"VBOX file blocked in the export test: {path}")
    return _real_read_csv(path, *a, **k)


def _vbox_blocked():
    return mock.patch.multiple(builtins, open=_guarded_open), mock.patch.object(pandas, "read_csv", _guarded_read_csv)


LOAD_ERROR = None
try:
    S_CSV = S3b_S_PATH                # conftest: AERIS_DATA_DIR, else <repo>/IO-VNBD, else the old default
    if not os.path.isfile(S_CSV):
        raise FileNotFoundError(f"{S_CSV} (set AERIS_DATA_DIR to the IO-VNBD folder)")
    p_open, p_csv = _vbox_blocked()
    with p_open, p_csv:
        _s = load_smartphone(S_CSV)
        S300 = _s[_s["timestamp_s"] <= 300.0].reset_index(drop=True)
        S270 = _s[_s["timestamp_s"] <= 270.0].reset_index(drop=True)
        TRIP, CLEAN, RES = export_vdr.build_trip(S300, "S3b", (OUTAGE,))
        TRIP["meta"].update(export_vdr.provenance())
        TEXT = export_vdr.dumps(TRIP)
        TRIP_270, _, RES_270 = export_vdr.build_trip(S270, "S3b", (OUTAGE,))
        TRIP_CLEAN, _, _ = export_vdr.build_trip(CLEAN, "S3b", (OUTAGE,))
        RAW_WINDOW = vehicle_dr.run_pipeline(S300, None, outage_window=OUTAGE)
except Exception as ex:          # noqa: BLE001 — reported by every test as a FAILURE, never a skip
    LOAD_ERROR = f"{type(ex).__name__}: {ex}"


class _Base(unittest.TestCase):
    def setUp(self):
        if LOAD_ERROR:
            self.fail(f"C1 test data could not be built: {LOAD_ERROR}")


class TestSchema(_Base):
    def test_top_level_and_meta(self):
        self.assertEqual(set(TRIP), {"meta", "outages", "frames", "gnss", "corrections"})
        m = TRIP["meta"]
        self.assertEqual((m["schema"], m["schema_status"], m["drive"], m["filter"]), ("aeris-trip/1", "DRAFT", "S3b", "vehicle_dr"))
        self.assertIs(m["referenceUsed"], False)
        self.assertEqual(m["note"], "development drive, tuned on S3b/S2, not validation")
        self.assertEqual(m["sigma"], {"calibrated": False, "definition": "1-sigma ellipse, Mahalanobis<=1, expect 39% in 2D"})
        for k in ("git_commit", "sha256", "dirty", "params", "origin", "t_zero", "duration_s", "generated_at"):
            self.assertIn(k, m)
        self.assertEqual(set(m["sha256"]), {"export_vdr.py", "vehicle_dr.py"})
        self.assertEqual(m["params"], __import__("dataclasses").asdict(vehicle_dr.VDRParams()))
        self.assertAlmostEqual(m["origin"]["lat"], RES["lat0"], places=7)
        self.assertAlmostEqual(m["duration_s"], RES["timestamps"][-1], places=3)

    def test_outages(self):
        self.assertEqual(len(TRIP["outages"]), 1)
        o = TRIP["outages"][0]
        self.assertEqual(set(o), {"start_s", "end_s", "kind", "last_fix_s", "first_fix_after_s", "withheld_fix_count"})
        self.assertEqual((o["start_s"], o["end_s"], o["kind"]), (200.0, 260.0, "simulated"))
        self.assertLess(o["last_fix_s"], 200.0)
        self.assertGreater(o["first_fix_after_s"], 260.0)
        self.assertGreater(o["withheld_fix_count"], 0)

    def test_frames(self):
        fr = TRIP["frames"]
        self.assertEqual(len(fr), len(RES["timestamps"]))
        t = [f["t_s"] for f in fr]
        self.assertTrue(all(b > a for a, b in zip(t, t[1:])), "t_s must strictly increase")
        for f in fr:
            self.assertEqual(set(f), FRAME_KEYS)
            self.assertTrue(0.0 <= f["bearing_deg"] < 360.0)
            self.assertTrue(0.0 <= f["ellipse_angle_deg"] < 180.0)
            self.assertGreaterEqual(f["sigma_major_m"], f["sigma_minor_m"])
            self.assertGreaterEqual(f["sigma_minor_m"], 0.0)
            self.assertIn(f["status"], {"gnss", "dr", "warmup"})
            self.assertIsInstance(f["stationary"], bool)
            self.assertEqual(len(f["cov_en_m2"]), 3)
            if f["status"] == "gnss":
                self.assertLessEqual(f["fix_age_s"], 2.0)

    def test_gnss_and_corrections(self):
        for g in TRIP["gnss"]:
            self.assertEqual(set(g), {"t_s", "lat", "lon", "accuracy_m"})
        for c in TRIP["corrections"]:
            self.assertIn(c["cause"], CAUSES)
            self.assertGreater(c["jump_m"], export_vdr.JUMP_M)
        # every frame-to-frame step above 5 m is listed (and only those)
        lat0 = TRIP["meta"]["origin"]["lat"]
        fr = TRIP["frames"]
        jumps = {fr[k]["t_s"] for k in range(1, len(fr))
                 if math.hypot(math.radians(fr[k]["lon"] - fr[k - 1]["lon"]) * vehicle_dr.R_EARTH * math.cos(math.radians(lat0)),
                               math.radians(fr[k]["lat"] - fr[k - 1]["lat"]) * vehicle_dr.R_EARTH) > export_vdr.JUMP_M + 0.05}
        self.assertTrue(jumps <= {c["t_s"] for c in TRIP["corrections"]})


class TestNoGnssInsideOutages(_Base):
    def test_gnss_list_has_nothing_inside(self):
        self.assertFalse([g["t_s"] for g in TRIP["gnss"] if OUTAGE[0] <= g["t_s"] <= OUTAGE[1]])

    def test_filter_input_has_no_new_fix_inside(self):
        ts = CLEAN["timestamp_s"].values
        fix = export_vdr.new_fix_mask(CLEAN["gps_lat"].values.astype(float), CLEAN["gps_lon"].values.astype(float))
        self.assertFalse(np.any(fix & (ts >= OUTAGE[0]) & (ts <= OUTAGE[1])))
        # the first new fix after the window is the first REAL fix after it, not a repeat of a withheld one
        after = ts[fix & (ts > OUTAGE[1])]
        self.assertAlmostEqual(float(after[0]), TRIP["outages"][0]["first_fix_after_s"], places=3)

    def test_no_gnss_status_inside(self):
        last = TRIP["outages"][0]["last_fix_s"]
        for f in TRIP["frames"]:
            if last + export_vdr.GNSS_FRESH_S < f["t_s"] <= OUTAGE[1]:
                self.assertNotEqual(f["status"], "gnss")


class TestWithheldFixes(_Base):
    def test_identical_frames_with_and_without_in_outage_fixes(self):
        self.assertEqual(TRIP_CLEAN["frames"], TRIP["frames"])
        self.assertEqual(TRIP_CLEAN["corrections"], TRIP["corrections"])

    def test_deletion_equals_the_filter_masking_the_window(self):
        # export path (fixes deleted, outage_window=None) == the check_outage path (fixes present, outage_window masks them)
        self.assertEqual(RES["positions"], RAW_WINDOW["positions"])
        self.assertEqual(RES["velocities"], RAW_WINDOW["velocities"])
        self.assertEqual(RES["cov_matrix"], RAW_WINDOW["cov_matrix"])


class TestCausality(_Base):
    def test_truncated_input_gives_identical_earlier_frames(self):
        n = sum(1 for f in TRIP["frames"] if f["t_s"] <= 270.0)
        self.assertEqual(TRIP_270["frames"], TRIP["frames"][:n])
        self.assertEqual(len(TRIP_270["frames"]), n)

    def test_replays_counted_and_never_rewrite_frames(self):
        reps = RES["replay_log"]
        print(f"\n    [C1] replay firings in S3b <= 300 s: {len(reps)} "
              f"({[(round(r['t_enter'], 1), round(r['t'], 1)) for r in reps]}); <= 270 s: {len(RES_270['replay_log'])}")
        self.assertEqual(TRIP["meta"]["replays"]["count"], len(reps))
        self.assertEqual(sum(c["cause"] == "replay" for c in TRIP["corrections"]),
                         sum(any(abs(c["t_s"] - r["t"]) < 1e-3 for r in reps) for c in TRIP["corrections"]))
        for r in reps:                    # the rewritten span stays as first emitted = as the 270 s run emitted it
            span = [f for f in TRIP["frames"] if r["t_enter"] <= f["t_s"] < r["t"]]
            if r["t"] > 270.0:
                ref = {f["t_s"]: f for f in TRIP_270["frames"]}
                for f in span:
                    if f["t_s"] in ref:
                        self.assertEqual(f, ref[f["t_s"]])


class TestNoVbox(_Base):
    def test_no_vbox_file_was_opened(self):
        self.assertEqual(V_ATTEMPTS, [])

    def test_vbox_open_is_blocked(self):
        p_open, p_csv = _vbox_blocked()
        before = len(V_ATTEMPTS)
        with p_open, p_csv:
            with self.assertRaises(PermissionError):
                load_smartphone(os.path.join(os.path.dirname(S_CSV), "V-S3b.csv"))
        self.assertEqual(len(V_ATTEMPTS), before + 1)
        del V_ATTEMPTS[before:]

    def test_export_refuses_vbox_and_sealed_inputs(self):
        with self.assertRaises(SystemExit):
            export_vdr.check_input("S3b", "V-S3b.csv")
        for d in ("S3c", "S3a", "S4"):
            with self.assertRaises(SystemExit):
                export_vdr.check_input(d, f"S-{d}.csv")

    def test_imports_are_vehicle_dr_data_loader_numpy_stdlib(self):
        with _real_open(export_vdr.__file__, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        mods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                mods |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                mods.add((node.module or "").split(".")[0])
        allowed = {"vehicle_dr", "data_loader", "numpy"} | set(sys.stdlib_module_names)
        self.assertEqual(mods - allowed, set())
        self.assertNotIn("check_outage", mods)
        self.assertNotIn("ins_ekf", mods)


class TestConventions(unittest.TestCase):          # pure math: no dataset needed
    def test_bearing(self):
        for psi, brg in ((0.0, 90.0), (90.0, 0.0), (180.0, 270.0), (-90.0, 180.0), (45.0, 45.0), (-135.0, 225.0)):
            self.assertAlmostEqual(export_vdr.bearing_deg(psi), brg, places=9)

    def test_ellipse_on_synthetic_covariances(self):
        cases = (((1.0, 9.0, 0.0), (3.0, 1.0, 0.0)),        # major axis North
                 ((9.0, 1.0, 0.0), (3.0, 1.0, 90.0)),       # major axis East
                 ((5.0, 5.0, 4.0), (3.0, 1.0, 45.0)),       # major axis North-East
                 ((5.0, 5.0, -4.0), (3.0, 1.0, 135.0)))     # major axis South-East / North-West
        for (ee, nn, en), (a, b, ang) in cases:
            ma, mi, an = export_vdr.ellipse(ee, nn, en)
            self.assertAlmostEqual(ma, a, places=9)
            self.assertAlmostEqual(mi, b, places=9)
            self.assertAlmostEqual(an, ang, places=9)

    def test_ellipse_axis_is_an_eigenvector(self):
        rng = np.random.default_rng(1)
        for _ in range(50):
            A = rng.normal(size=(2, 2))
            P = A @ A.T + 0.01 * np.eye(2)
            ma, mi, an = export_vdr.ellipse(P[0, 0], P[1, 1], P[0, 1])
            u = np.array([math.sin(math.radians(an)), math.cos(math.radians(an))])   # bearing -> (east, north)
            self.assertTrue(np.allclose(P @ u, ma ** 2 * u, atol=1e-9))
            self.assertAlmostEqual(ma ** 2 + mi ** 2, P[0, 0] + P[1, 1], places=9)


class TestProvenanceHash(unittest.TestCase):       # no dataset needed
    def test_sha256_is_lf_normalised(self):
        import hashlib
        import tempfile
        lf = b"a = 1\nb = 2\n# \xc3\xa9\n"
        with tempfile.TemporaryDirectory() as d:
            p_lf, p_crlf = os.path.join(d, "lf.py"), os.path.join(d, "crlf.py")
            with _real_open(p_lf, "wb") as f:
                f.write(lf)
            with _real_open(p_crlf, "wb") as f:
                f.write(lf.replace(b"\n", b"\r\n"))
            self.assertEqual(export_vdr._sha256(p_crlf), export_vdr._sha256(p_lf))
            self.assertEqual(export_vdr._sha256(p_lf), hashlib.sha256(lf).hexdigest())


class TestStrictJson(_Base):
    def test_parses_strictly(self):
        def bad(x):
            raise ValueError(f"non-strict JSON constant {x}")
        d = json.loads(TEXT, parse_constant=bad)
        self.assertEqual(d["meta"]["schema"], "aeris-trip/1")
        self.assertNotIn('": ', TEXT)                                        # compact separators
        self.assertNotIn("\n", TEXT)

    def test_nan_is_refused(self):
        with self.assertRaises(ValueError):
            export_vdr.dumps({"x": float("nan")})


if __name__ == "__main__":
    unittest.main()
