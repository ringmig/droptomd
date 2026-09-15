"""Drop to MD for Windows. `DropToMD.exe file...` converts without the window; `--check` smoke-tests the bundle."""
import sys
from pathlib import Path

# Kept in step with markitdownTypes in main.swift. markitdown passes unknown files through as text,
# so anything off this list is refused up front.
MARKITDOWN_TYPES = {"pdf", "docx", "pptx", "xlsx", "xls", "html", "htm", "epub", "ipynb", "msg", "zip",
                    "csv", "json", "xml", "rss", "atom", "txt", "md", "yaml", "yml", "mp3", "wav", "m4a"}


class Unsupported(Exception):
    pass


_markitdown = None


def markdown_for(src: Path) -> bytes:
    global _markitdown
    ext = src.suffix.lower().lstrip(".")
    if ext not in MARKITDOWN_TYPES:
        raise Unsupported("File not supported")
    if _markitdown is None:
        from markitdown import MarkItDown  # imports pandas and magika, seconds on first use

        _markitdown = MarkItDown()
    md = _markitdown.convert(str(src)).markdown
    # markitdown returns nothing on some broken files; an empty .md is a failure, not a success
    if not md.strip():
        raise ValueError("Empty result")
    return md.encode("utf-8")


def convert(src: Path) -> Path:
    """Writes `<name>.md` next to `src`, or in Downloads if that folder isn't writable."""
    md = markdown_for(src)
    out = src.with_suffix(".md")
    try:
        out.write_bytes(md)
    except OSError:
        out = Path.home() / "Downloads" / out.name
        out.write_bytes(md)
    return out


def headless(paths: list[str]) -> int:
    failed = False
    for p in paths:
        try:
            print("ok  ", convert(Path(p).resolve()))
        except Exception as e:
            failed = True
            print("FAIL", p, e)
    return 1 if failed else 0


def check() -> int:
    from tkinterdnd2 import TkinterDnD

    root = TkinterDnD.Tk()  # loads the bundled tkdnd DLL
    root.destroy()
    print("dnd ok")
    return 0


if __name__ == "__main__":
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")  # paths with å/ä/ö on a cp1252 console
    files = [a for a in sys.argv[1:] if Path(a).is_file()]
    if "--check" in sys.argv:
        sys.exit(check())
    sys.exit(headless(files) if files else 0)
