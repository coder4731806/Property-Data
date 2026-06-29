"""
One-shot pipeline for your Mac: data prep -> train all four models -> charts.
(Skips GNAF centroid extraction; suburb_centroids.csv already ships in ../data.
 Re-run scripts/gnaf_centroids.py only if you refresh the address data.)

    python run_all.py
"""
import subprocess
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ["data_prep.py"],
    ["train.py"],            # all models; EBM uses good defaults (outer_bags=8)
    ["evaluate.py"],
]

for step in STEPS:
    print(f"\n=== running {' '.join(step)} ===", flush=True)
    r = subprocess.run([sys.executable, os.path.join(HERE, step[0])] + step[1:], cwd=HERE)
    if r.returncode != 0:
        sys.exit(f"step failed: {step}")
print("\nDone. Models in ../models, charts in ../charts, report in ../reports.")
