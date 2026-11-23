"""Reassemble the saved prediction archive and verify its SHA-256."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent / "results"
manifest = json.loads((root / "prediction_archive_verification.json").read_text())
parts = sorted((root / "prediction-parts").glob("held_out_predictions.csv.gz.part*"))
data = b"".join(part.read_bytes() for part in parts)
expected = manifest["compressed_file"]
if len(data) != expected["size_bytes"] or hashlib.sha256(data).hexdigest() != expected["sha256"]:
    raise SystemExit("Prediction parts are incomplete or corrupted.")
output = root / expected["name"]
output.write_bytes(data)
print(f"Verified and reassembled {output.name}")
