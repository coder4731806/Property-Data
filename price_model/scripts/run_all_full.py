"""
Full v2 pipeline on a normal machine (your Mac): raw region dbs -> index ->
models -> Cloudflare artifacts. Takes minutes, no step limits.

    python run_all_full.py --data-dir ~/Downloads/REAscrape/data
"""
import argparse
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(cmd):
    print(f"\n=== {' '.join(cmd)} ===", flush=True)
    subprocess.run(cmd, cwd=HERE, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", required=True, help="REAscrape/data folder")
    ap.add_argument("--min-year", type=int, default=2013)
    args = ap.parse_args()
    py = sys.executable

    run([py, "data_prep_db.py", "--data-dir", os.path.expanduser(args.data_dir)])
    run([py, "price_index.py"])
    run([py, "train_full.py", "--min-year", str(args.min_year),
         "--ebm-bags", "8", "--ebm-interactions", "6", "--ebm-cap", "250000"])
    run([py, "export_cf.py", "models"])
    run([py, "export_cf.py", "lgbm"])
    run([py, "export_cf.py", "extras"])
    run([py, "make_parity_fixture.py"])
    run(["node", os.path.join("..", "cf_artifacts", "test_parity.mjs")])
    run([py, "export_d1.py"])
    print("\nAll done. Deployables in cf_artifacts/.")


if __name__ == "__main__":
    main()
