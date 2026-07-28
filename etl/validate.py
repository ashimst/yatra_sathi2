"""
validate.py — retained as a thin shim for any direct invocations.

Validation is fully integrated into normalize.py as a single merged pass.
Running this file just calls normalize.main().
"""

from etl.normalize import main

if __name__ == "__main__":
    print("[validate] Validation is merged into normalize.py — running normalize.")
    main()
