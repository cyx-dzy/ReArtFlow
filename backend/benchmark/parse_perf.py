"""Benchmark script for the multi‑language parser.

The script generates a synthetic repository containing a mixture of supported source files,
parses it using ``backend.parser.parse_project`` both sequentially (single‑thread) and in
parallel (default ``ThreadPoolExecutor``), and prints the elapsed times and speed‑up ratio.
If the parallel run does not achieve the requested speed‑up (default 30 %), the script
exits with a non‑zero status code so CI can fail.
"""

import argparse
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Import the parser implementation
from backend.parser import parse_project, SUPPORTED_EXTENSIONS

# Simple source snippets for a few languages (tiny files).
SNIPPETS = {
    ".py": "def hello():\n    return 'world'\n",
    ".js": "function hello() { return 'world'; }\n",
    ".java": "public class Hello { public static void main(String[] args) { System.out.println(\"world\"); } }\n",
    ".go": "package main\nfunc main() { println(\"world\") }\n",
    ".rs": "fn main() { println!(\"world\"); }\n",
    ".c": "#include <stdio.h>\nint main() { printf(\"world\n\"); return 0; }\n",
    ".cpp": "#include <iostream>\nint main(){ std::cout << \"world\" << std::endl; return 0; }\n",
    ".html": "<html><body>Hello</body></html>\n",
    ".css": "body { color: red; }\n",
    ".vue": "<template><div>Hello</div></template><script>export default {}</script><style scoped>div{color:red}</style>\n",
}

def generate_repo(root: Path, files_per_ext: int = 20) -> None:
    """Create a synthetic repository with *files_per_ext* files for each supported extension.
    """
    for ext, snippet in SNIPPETS.items():
        for i in range(files_per_ext):
            file_path = root / f"sample_{i}{ext}"
            file_path.write_text(snippet)

def time_parse(root: Path, workers: int | None = None) -> float:
    """Parse *root* and return elapsed time (seconds).
    If *workers* is provided, a temporary ``ThreadPoolExecutor`` with that many workers
    is used to dispatch the ``parse_file`` calls; otherwise the default executor inside
    ``parse_project`` is used (which creates its own pool).
    """
    start = time.perf_counter()
    if workers is not None:
        # Manually dispatch using a custom executor to enforce sequential or parallel mode.
        from backend.parser.tree_sitter_pool import parse_file
        files = [str(p) for p in root.rglob("*") if p.is_file() and p.suffix in SUPPORTED_EXTENSIONS]
        results = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            for fut in executor.map(parse_file, files):
                results.append(fut)
    else:
        # Let the library choose its own executor (parallel by default).
        _ = parse_project(str(root))
    return time.perf_counter() - start

def main() -> int:
    parser = argparse.ArgumentParser(description="Run parser performance benchmark")
    parser.add_argument("--assert-speedup", type=float, default=30.0,
                        help="Minimum required speed‑up percentage for parallel run")
    parser.add_argument("--files-per-ext", type=int, default=30,
                        help="Number of files to generate for each extension")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as td:
        repo_path = Path(td) / "synthetic_repo"
        repo_path.mkdir()
        generate_repo(repo_path, files_per_ext=args.files_per_ext)
        # Sequential (single‑thread) run
        seq_time = time_parse(repo_path, workers=1)
        # Parallel run (default pool size)
        par_time = time_parse(repo_path, workers=None)
        speedup = (seq_time - par_time) / seq_time * 100 if seq_time > 0 else 0
        print(f"Sequential time: {seq_time:.3f}s")
        print(f"Parallel   time: {par_time:.3f}s")
        print(f"Speed‑up: {speedup:.1f}%")
        if speedup < args.assert_speedup:
            print(f"⚠️  Parallel speed‑up {speedup:.1f}% is below required {args.assert_speedup}%")
            return 1
        return 0

if __name__ == "__main__":
    sys.exit(main())
