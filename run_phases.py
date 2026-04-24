#!/usr/bin/env python3
"""One‑click script to run phases 1‑3.

Usage:
    Place a ZIP archive containing source files in the project root and run this script.
    The script will:
    1️⃣ Extract the ZIP safely using ``ZipInputProcessor`` (Phase 1).
    2️⃣ (Phase 2) Locate a Python source file and prepare it for analysis.
    3️⃣ Call ``LLMClient.generate_explanation`` to obtain a Chinese explanation
       and diagram (Phase 3) and print the JSON result.

Environment variables required for the LLM client (see ``backend/semantic/llm_client.py``):
    LLM_PROVIDER – "openai" or "qianwen"
    LLM_MODEL – model identifier (e.g. "gpt-4o")
    OPENAI_API_KEY / QIANWEN_API_KEY – corresponding API key
"""

import os
import sys
import json
from pathlib import Path

# Ensure the project root is on sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.input.zip_handler import ZipInputProcessor
from backend.semantic.llm_client import LLMClient

def find_zip_file() -> Path:
    """Return the first .zip file in the project root.
    Raises ``FileNotFoundError`` if none is found.
    """
    for entry in PROJECT_ROOT.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".zip":
            return entry
    raise FileNotFoundError("No .zip file found in project root")

def extract_zip(zip_path: Path) -> Path:
    """Extract the zip safely and return the extraction directory path."""
    processor = ZipInputProcessor()
    result = processor.process({"file_path": str(zip_path)})
    return Path(result["path"])

def locate_python_file(root: Path) -> Path:
    """Search for the first ``.py`` file under *root* and copy it into the project directory.
    Returns the copied file path (inside project) or raises ``FileNotFoundError``.
    """
    for py_file in root.rglob("*.py"):
        # Destination inside project to satisfy security checks
        dest_dir = PROJECT_ROOT / "extracted_src"
        dest_dir.mkdir(exist_ok=True)
        dest_path = dest_dir / py_file.name
        # Copy the file
        with open(py_file, "rb") as src_f, open(dest_path, "wb") as dst_f:
            dst_f.write(src_f.read())
        return dest_path
    raise FileNotFoundError(f"No Python source file found in extracted directory {root}")

def main() -> None:
    try:
        zip_file = find_zip_file()
        print(f"📦 Found ZIP: {zip_file.name}")
        extract_dir = extract_zip(zip_file)
        print(f"🗂️ Extracted to: {extract_dir}")
        try:
            source_file = locate_python_file(extract_dir)
            code = source_file.read_text(encoding="utf-8")
            language = source_file.suffix.lstrip(".")
            print(f"🔍 Using source file: {source_file.relative_to(PROJECT_ROOT)}")
        except FileNotFoundError as e:
            # Fallback: use a placeholder snippet
            print(str(e))
            code = "print('hello world')"
            language = "python"
        # Attempt to use LLMClient; if configuration is incomplete, fall back to placeholder
        try:
            client = LLMClient()
            result = client.generate_explanation(code, language)
        except Exception as exc:
            print(f"⚠️ LLM call failed ({exc}), using placeholder result.")
            result = {"explanation": "示例解释（未调用实际 LLM）", "diagram": {}}
        print("\n🧠 LLM Explanation Result (JSON):")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"❌ Error: {exc}")
        sys.exit(1)

if __name__ == "__main__":
    main()
