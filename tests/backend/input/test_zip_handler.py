import os
import tempfile
import zipfile
from pathlib import Path

from backend.input.zip_handler import ZipInputProcessor

def test_zip_handler_process_creates_extraction_dir():
    # Create a temporary zip file with a single text file
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = Path(tmp_dir) / "test.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("hello.txt", "hello world")
        # Prepare payload
        payload = {"file_path": str(zip_path)}
        processor = ZipInputProcessor()
        result = processor.process(payload)
        # Verify result dict
        assert result["source_type"] == "zip"
        extract_path = result["path"]
        assert os.path.isdir(extract_path)
        # Verify extracted file exists and content matches
        extracted_file = Path(extract_path) / "hello.txt"
        assert extracted_file.is_file()
        assert extracted_file.read_text() == "hello world"
