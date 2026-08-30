"""
run_tests.py — Single entry point for the IDRS backend test suite.

Usage:
    python run_tests.py                    # All tests; skips dataset tests if IO-VNBD absent
    python run_tests.py --unit-only        # Layer 1 only (no dataset, always fast ~2s)
    python run_tests.py --no-integration   # Skip slow integration tests
    python run_tests.py --verbose          # Full per-test output
    python run_tests.py --failfast         # Stop at first failure

Exit codes:
    0  — All tests passed (or all skipped gracefully)
    1  — One or more tests failed
"""

import sys
import os
import io
import unittest
import argparse
import time

# Force UTF-8 output on Windows (avoids cp1252 UnicodeEncodeError in docstrings)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure the backend/ directory is on the path for imports
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))

# ── test discovery helpers ─────────────────────────────────────────────────────

UNIT_MODULES = [
    "tests.test_math",
    "tests.test_ins",
    "tests.test_ekf",
    "tests.test_gnss_classifier",
    "tests.test_data_loader",   # has both unit + integration classes
]

INTEGRATION_MODULES = [
    "tests.test_pipeline",
    "tests.test_json_schema",
]

ALL_MODULES = UNIT_MODULES + INTEGRATION_MODULES

LAYER_DESCRIPTIONS = {
    "tests.test_math":             "Layer 1 — Math utilities (latlon_to_enu, quaternions, skew)",
    "tests.test_ins":              "Layer 1 — INS strapdown propagation",
    "tests.test_ekf":              "Layer 1 — 15-state ES-EKF mechanics",
    "tests.test_gnss_classifier":  "Layer 1 — Rule-based GNSS Quality Classifier",
    "tests.test_data_loader":      "Layer 1+2 — Data loader (unit + integration)",
    "tests.test_pipeline":         "Layer 2 — End-to-end pipeline (unit + full integration)",
    "tests.test_json_schema":      "Layer 3 — JSON export schema validation",
}


def print_banner():
    print()
    print("=" * 65)
    print("  IDRS Backend Test Suite")
    print("  Intelligent Dead Reckoning Navigation System — SIH 26168")
    print("=" * 65)


def print_environment():
    """Print key environment info before running tests."""
    from tests.conftest import DATASET_AVAILABLE, S1_AVAILABLE, EXPORTS_AVAILABLE

    print()
    print("  Environment:")
    print(f"    Python:  {sys.version.split()[0]}")
    try:
        import numpy as np
        print(f"    NumPy:   {np.__version__}")
    except ImportError:
        print("    NumPy:   NOT FOUND")
    try:
        import pandas as pd
        print(f"    Pandas:  {pd.__version__}")
    except ImportError:
        print("    Pandas:  NOT FOUND")

    print()
    print("  Dataset status:")
    print(f"    IO-VNBD S3b: {'OK Found' if DATASET_AVAILABLE else 'NOT FOUND -- integration tests will SKIP'}")
    print(f"    IO-VNBD S1:  {'OK Found' if S1_AVAILABLE else 'NOT FOUND'}")
    print(f"    exports/:    {'OK Found' if EXPORTS_AVAILABLE else 'NOT FOUND -- JSON schema tests will SKIP'}")
    print()


def run_suite(modules, verbosity=1, failfast=False):
    """Discover and run tests from the given module list."""
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    for mod_name in modules:
        try:
            mod_suite = loader.loadTestsFromName(mod_name)
            suite.addTests(mod_suite)
        except Exception as e:
            print(f"  [WARNING] Could not load {mod_name}: {e}")

    runner = unittest.TextTestRunner(
        verbosity=verbosity,
        failfast=failfast,
        stream=sys.stdout
    )
    return runner.run(suite)


def print_summary(result, elapsed):
    """Print a concise summary after the run."""
    total  = result.testsRun
    passed = total - len(result.failures) - len(result.errors)
    skipped = len(result.skipped)
    failed  = len(result.failures)
    errored = len(result.errors)

    print()
    print("=" * 65)
    print(f"  Results: {total} tests run in {elapsed:.1f}s")
    print(f"    PASS:    {passed}")
    if skipped:
        print(f"    SKIP:    {skipped}  (dataset not available)")
    if failed:
        print(f"    FAIL:    {failed}")
    if errored:
        print(f"    ERROR:   {errored}")
    print("=" * 65)

    if not result.wasSuccessful():
        print()
        print("  FAILURES/ERRORS:")
        for test, traceback in result.failures + result.errors:
            print(f"    FAIL: {test}")
        print()
    else:
        print()
        if skipped:
            print("  All executed tests PASSED  (some skipped -- see dataset status above)")
        else:
            print("  ALL TESTS PASSED")
        print()


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IDRS backend test runner")
    parser.add_argument("--unit-only",       action="store_true",
                        help="Run Layer 1 unit tests only (no dataset needed)")
    parser.add_argument("--no-integration",  action="store_true",
                        help="Skip integration tests")
    parser.add_argument("--verbose",   "-v", action="store_true",
                        help="Full per-test output")
    parser.add_argument("--failfast",  "-f", action="store_true",
                        help="Stop at the first failure")
    args = parser.parse_args()

    # Select modules
    if args.unit_only or args.no_integration:
        modules = UNIT_MODULES
    else:
        modules = ALL_MODULES

    verbosity = 2 if args.verbose else 1

    print_banner()
    print_environment()

    print("  Test files:")
    for mod in modules:
        print(f"    {LAYER_DESCRIPTIONS.get(mod, mod)}")
    print()

    t0 = time.time()
    result = run_suite(modules, verbosity=verbosity, failfast=args.failfast)
    elapsed = time.time() - t0

    print_summary(result, elapsed)

    sys.exit(0 if result.wasSuccessful() else 1)
