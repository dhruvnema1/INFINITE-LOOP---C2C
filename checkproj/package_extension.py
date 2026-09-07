from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent
out = root / "dark-pattern-detector.zip"

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in (root / "extension").rglob("*"):
        if p.is_file():
            z.write(p, p.relative_to(root / "extension"))

print(out)
