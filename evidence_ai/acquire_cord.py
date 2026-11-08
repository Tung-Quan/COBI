"""Download pinned public CORD v2 shards and the non-commercial LayoutLMv3 base."""
import argparse
import json
from shutil import copyfileobj
from urllib.request import urlopen

from ml.contracts import ROOT

RAW = ROOT / "data/raw/evidence-v3"
PROTOCOL = ROOT / "evidence_ai/cord_protocol.json"
SHARDS = (
    "train-00000-of-00004-b4aaeceff1d90ecb.parquet", "train-00001-of-00004-7dbbe248962764c5.parquet",
    "train-00002-of-00004-688fe1305a55e5cc.parquet", "train-00003-of-00004-2d0cd200555ed7fd.parquet",
    "validation-00000-of-00001-cc3c5779fe22e8ca.parquet", "test-00000-of-00001-9c204eb3f4e11791.parquet",
)
BASE_FILES = ("config.json", "model.safetensors", "preprocessor_config.json", "tokenizer_config.json", "vocab.json", "merges.txt")


def download(url, path):
    if path.exists():
        print(f"Already downloaded {path.name}", flush=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    with urlopen(url, timeout=120) as source, partial.open("wb") as dest:
        copyfileobj(source, dest, length=1024 * 1024)
    partial.replace(path)
    print(f"Downloaded {path.name} ({path.stat().st_size} bytes)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-only", action="store_true", help="Use the LayoutLMv3 base under its non-commercial research license")
    args = parser.parse_args()
    if not args.research_only:
        parser.error("Read the official CORD and LayoutLMv3 cards, then specify --research-only")
    config = json.loads(PROTOCOL.read_text())
    prefix = "https://huggingface.co"
    for name in SHARDS:
        download(f"{prefix}/datasets/naver-clova-ix/cord-v2/resolve/{config['receipt_revision']}/data/{name}", RAW / "cord" / name)
    for name in BASE_FILES:
        download(f"{prefix}/microsoft/layoutlmv3-base/resolve/{config['model_revision']}/{name}", RAW / "layoutlmv3" / name)


if __name__ == "__main__":
    main()
