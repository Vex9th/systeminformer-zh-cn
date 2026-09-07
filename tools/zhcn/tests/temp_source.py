import tempfile
from pathlib import Path


def scan_temporary_source(scanner, source: str):
    """Scan a closed temporary source file on every supported platform."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        source_path = Path(temporary_directory) / "fixture.c"
        source_path.write_text(source, encoding="utf-8")
        entries = []
        scanner(str(source_path), entries)
        return entries
