from pathlib import Path
import gzip, hashlib
folder = Path(__file__).resolve().parent
parts = sorted(folder.glob("MANTA-M5P.step.gz.part*"))
if len(parts) != 3:
    raise SystemExit("Put all three MANTA-M5P.step.gz.part01/02/03 files beside this script.")
data = gzip.decompress(b"".join(p.read_bytes() for p in parts))
expected = "dfd48215096c886ed22c76e4180ea3c11b6574870b684c8fca9e2d7d22fb4fe9"
if hashlib.sha256(data).hexdigest() != expected:
    raise SystemExit("Checksum mismatch. No STEP written.")
out = folder / "BIGTREETECH MANTA M5P.step"
out.write_bytes(data)
print("Verified original STEP written:", out)
