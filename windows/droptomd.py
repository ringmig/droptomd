"""Drop to MD for Windows. `DropToMD.exe file...` converts without the window; `--check` smoke-tests the bundle."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Kept in step with markitdownTypes in main.swift. markitdown passes unknown files through as text,
# so anything off this list is refused up front.
MARKITDOWN_TYPES = {"pdf", "docx", "pptx", "xlsx", "xls", "html", "htm", "epub", "ipynb", "msg", "zip",
                    "csv", "json", "xml", "rss", "atom", "txt", "md", "yaml", "yml", "mp3", "wav", "m4a"}
# Formats the Mac app sends through textutil. Word opens all of them; rtfd and webarchive have no Windows reader.
WORD_TYPES = {"rtf", "doc", "odt", "wordml"}
IMAGE_TYPES = {"heic", "heif", "png", "jpg", "jpeg", "tiff", "tif", "gif", "bmp", "webp"}

# Paths travel as environment variables, so quoting never reaches the PowerShell parser.
WORD_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
try {
    $word = New-Object -ComObject Word.Application
    try {
        $word.Visible = $false
        $word.DisplayAlerts = 0
        $doc = $word.Documents.Open($env:DROPTOMD_SRC, $false, $true, $false)
        $doc.SaveAs2($env:DROPTOMD_OUT, 16)
        $doc.Close(0)
    } finally { $word.Quit() }
} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }
"""


class Unsupported(Exception):
    pass


_markitdown = None


def has_word() -> bool:
    import winreg

    try:
        winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Word.Application").Close()
        return True
    except OSError:
        return False


def word_to_docx(src: Path, out: Path) -> None:
    if not has_word():
        raise RuntimeError(f"Word is needed to convert .{src.suffix.lower().lstrip('.')} files")
    env = {**os.environ, "DROPTOMD_SRC": str(src), "DROPTOMD_OUT": str(out)}
    # ponytail: a Word dialog that outlives the timeout leaves WINWORD.EXE running; kill it by hand
    p = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", WORD_SCRIPT], env=env,
                       capture_output=True, text=True, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    if p.returncode != 0:
        raise RuntimeError((p.stderr.strip().splitlines() or ["Conversion failed"])[-1])


def ocr_engine():
    from winrt.windows.media.ocr import OcrEngine

    return OcrEngine.try_create_from_user_profile_languages()


def ocr(src: Path) -> str:
    """Image text via Windows.Media.Ocr, the on-device OCR built into Windows 10 and 11."""
    import asyncio

    from winrt.windows.graphics.imaging import (BitmapAlphaMode, BitmapDecoder, BitmapPixelFormat, BitmapTransform,
                                                ColorManagementMode, ExifOrientationMode)
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage import FileAccessMode, StorageFile

    async def recognize() -> list[str]:
        engine = ocr_engine()
        if engine is None:
            raise RuntimeError("No text recognition language installed")
        try:
            file = await StorageFile.get_file_from_path_async(str(src))
            decoder = await BitmapDecoder.create_async(await file.open_async(FileAccessMode.READ))
        except OSError:
            raise RuntimeError("Could not read image") from None
        # OCR refuses images above max_image_dimension, so large photos are scaled down first
        scale = min(1, OcrEngine.max_image_dimension / max(decoder.pixel_width, decoder.pixel_height))
        transform = BitmapTransform()
        transform.scaled_width = int(decoder.pixel_width * scale)
        transform.scaled_height = int(decoder.pixel_height * scale)
        bitmap = await decoder.get_software_bitmap_transformed_async(
            BitmapPixelFormat.BGRA8, BitmapAlphaMode.PREMULTIPLIED, transform,
            ExifOrientationMode.RESPECT_EXIF_ORIENTATION, ColorManagementMode.DO_NOT_COLOR_MANAGE)
        return [line.text for line in (await engine.recognize_async(bitmap)).lines]

    lines = asyncio.run(recognize())
    if not lines:
        raise RuntimeError("No text found in image")
    return "\n".join(lines)


def markdown_for(src: Path) -> bytes:
    global _markitdown
    ext = src.suffix.lower().lstrip(".")
    if ext in IMAGE_TYPES:
        return ocr(src).encode("utf-8")
    if ext not in MARKITDOWN_TYPES | WORD_TYPES:
        raise Unsupported("File not supported")
    with tempfile.TemporaryDirectory() as tmp:
        source = src
        if ext in WORD_TYPES:
            source = Path(tmp) / "doc.docx"
            word_to_docx(src, source)
        if _markitdown is None:
            from markitdown import MarkItDown  # imports pandas and magika, seconds on first use

            _markitdown = MarkItDown()
        md = _markitdown.convert(str(source)).markdown
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
    engine = ocr_engine()
    print("ocr", engine.recognizer_language.language_tag if engine else "none")
    print("word", "yes" if has_word() else "no")
    return 0


if __name__ == "__main__":
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")  # paths with å/ä/ö on a cp1252 console
    files = [a for a in sys.argv[1:] if Path(a).is_file()]
    if "--check" in sys.argv:
        sys.exit(check())
    sys.exit(headless(files) if files else 0)
