"""Extract session files for chosen sessions from the 9/29 dump zip, under a size cap."""
import json, sys, zipfile
from pathlib import Path

zip_path, out_root, cap = sys.argv[1], Path(sys.argv[2]), int(sys.argv[3])
sids = set(Path(sys.argv[4]).read_text().split())
n = total = 0
with zipfile.ZipFile(zip_path) as z:
    for info in z.infolist():
        parts = info.filename.split("/")
        if len(parts) >= 5 and parts[1] == "sessions" and parts[3] == "files" and parts[2] in sids:
            if info.file_size > cap:
                continue
            dest = out_root / info.filename
            if dest.exists() and dest.stat().st_size == info.file_size:
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(dest, "wb") as dst:
                while chunk := src.read(1 << 20):
                    dst.write(chunk)
            n += 1; total += info.file_size
print(f"extracted {n} files, {total/1e9:.2f} GB")
