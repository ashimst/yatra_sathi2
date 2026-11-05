"""
YatraSathi E2E Test Suite Runner
Standalone executable runner that executes all test modules across Tiers 1–4,
data integrity, and database seeds, outputting clean pass/fail summaries.
"""
import sys
import time
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TESTS_E2E_DIR = PROJECT_ROOT / "tests" / "e2e"

TEST_FILES = [
    "test_tier1_feature_coverage.py",
    "test_tier2_boundary_corner.py",
    "test_tier3_cross_feature.py",
    "test_tier4_user_journeys.py",
    "test_data_integrity.py",
    "test_database_seeds.py"
]


def run_all_e2e_tests():
    """Run all E2E test files and return exit code."""
    print("=" * 80)
    print("YATRASATHI E2E TEST SUITE EXECUTION")
    print("4-Tier Opaque-Box Methodology & Database Verification")
    print("=" * 80)
    start_time = time.time()

    args = [
        "-v",
        "--tb=short",
        "-s"
    ]
    for tf in TEST_FILES:
        target = TESTS_E2E_DIR / tf
        if target.exists():
            args.append(str(target))

    exit_code = pytest.main(args)
    duration = time.time() - start_time
    print("=" * 80)
    print(f"E2E Suite Execution Completed in {duration:.2f}s with Exit Code: {exit_code}")
    print("=" * 80)
    return exit_code


if __name__ == "__main__":
    sys.exit(run_all_e2e_tests())
