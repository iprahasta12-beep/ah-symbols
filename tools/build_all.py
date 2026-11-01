# One command: every symbols/<name>/rig.json -> PSD -> Spine json + atlas, then bake preview.
# usage: python tools/build_all.py            (all symbols)
#        python tools/build_all.py hammer     (one symbol)
import os, sys, subprocess
T = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(T, '..'); SD = os.path.join(ROOT, 'symbols')
only = sys.argv[1:]
for n in sorted(os.listdir(SD)):
    rig = os.path.join(SD, n, 'rig.json')
    if not os.path.exists(rig) or (only and n not in only):
        continue
    subprocess.run([sys.executable, os.path.join(T, 'psd_to_spine.py'), rig], check=True)
    subprocess.run([sys.executable, os.path.join(T, 'pack_atlas.py'), os.path.join(SD, n, 'images'), os.path.join(SD, n), n], check=True)
subprocess.run([sys.executable, os.path.join(T, 'bake.py'), ROOT], check=True)
