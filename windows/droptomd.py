"""Drop to MD for Windows. `DropToMD.exe file...` converts without the window; `--check` smoke-tests the bundle."""
import os
import queue
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

ASSETS = Path(__file__).parent / "assets"

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
    Window().root.destroy()  # builds the real window: tkdnd DLL, assets, Pillow, DWM calls
    print("window ok")
    engine = ocr_engine()
    print("ocr", engine.recognizer_language.language_tag if engine else "none")
    print("word", "yes" if has_word() else "no")
    return 0


# Look settled on the Mac (main.swift DropView): white at 70/45/35 % opacity is flattened onto #0d0d0d.
BG, TEXT, TEXT_DIM, TEXT_FAINT, BORDER = "#0d0d0d", "#ffffff", "#b6b6b6", "#7a7a7a", "#626262"


def animations_enabled() -> bool:
    import ctypes

    flag = ctypes.c_bool(True)
    ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(flag), 0)  # SPI_GETCLIENTAREAANIMATION
    return flag.value


def antialiased(size: tuple[int, int], draw) -> "Image.Image":
    """Tk's canvas draws jagged arcs and can't dash lines wider than 1 px on Windows, so shapes are drawn 4x and scaled down."""
    from PIL import Image, ImageDraw

    big = Image.new("RGBA", (size[0] * 4, size[1] * 4))
    draw(ImageDraw.Draw(big), 4)
    return big.resize(size, Image.LANCZOS)


class Window:
    def __init__(self):
        import ctypes
        import tkinter.font

        from PIL import ImageTk
        from tkinterdnd2 import DND_FILES, TkinterDnD

        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI, or Windows blurs the whole window at 150 %
        self.root = root = TkinterDnD.Tk()
        self.scale = scale = root.winfo_fpixels("1i") / 96
        self.w, self.h = w, h = round(320 * scale), round(220 * scale)
        root.title("Drop to MD")
        root.configure(bg=BG)
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.geometry(f"{w}x{h}+{(root.winfo_screenwidth() - w) // 2}+{(root.winfo_screenheight() - h) // 2}")
        root.iconphoto(True, ImageTk.PhotoImage(file=ASSETS / "app.png"))
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        for attribute, value in ((20, 1), (35, 0x000D0D0D)):  # dark title bar; caption colour on Windows 11 only
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(ctypes.c_int(value)), 4)

        px = min((44, 66, 88), key=lambda size: abs(size - 44 * scale))
        self.icons = {name: ImageTk.PhotoImage(file=ASSETS / f"{name}-{px}.png") for name in ("file-plus-corner", "file-check", "x")}
        self.font = tkinter.font.Font(family="Segoe UI Semibold", size=-round(14 * scale))
        self.gap = round(14 * scale)

        inset, radius, stroke, dash = (round(v * scale) for v in (10, 12, 1.5, 6))
        self.border = ImageTk.PhotoImage(antialiased((w, h), lambda d, k: self.dashed_rounded_rect(
            d, inset * k, inset * k, (w - inset) * k, (h - inset) * k, radius * k, dash * k, max(1, stroke) * k)))
        spin = round(28 * scale)
        frames = 30 if animations_enabled() else 1
        self.spinner = [ImageTk.PhotoImage(antialiased((spin, spin), lambda d, k, i=i: d.arc(
            (2 * k, 2 * k, (spin - 2) * k, (spin - 2) * k), 360 * i / frames, 360 * i / frames + 100,
            fill=TEXT, width=round(2.5 * scale * k)))) for i in range(frames)]

        self.canvas = canvas = tkinter.Canvas(root, width=w, height=h, bg=BG, highlightthickness=0)
        canvas.pack()
        self.border_item = canvas.create_image(0, 0, image=self.border, anchor="nw", state="hidden")
        canvas.drop_target_register(DND_FILES)
        canvas.dnd_bind("<<DropEnter>>", lambda e: self.target(True) or e.action)
        canvas.dnd_bind("<<DropLeave>>", lambda e: self.target(False) or e.action)
        canvas.dnd_bind("<<Drop>>", self.drop)
        canvas.bind("<ButtonPress-1>", lambda e: setattr(self, "grab", (e.x_root - root.winfo_x(), e.y_root - root.winfo_y())))
        canvas.bind("<B1-Motion>", lambda e: root.geometry(f"+{e.x_root - self.grab[0]}+{e.y_root - self.grab[1]}"))

        self.updates = queue.Queue()
        self.frame = 0
        self.set_status(("idle",))

    @staticmethod
    def dashed_rounded_rect(d, x0, y0, x1, y1, r, dash, width):
        import math

        # walk the outline as a polyline and draw every other `dash`-long piece
        points = []
        for cx, cy, start in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
            points += [(cx + r * math.cos(math.radians(start + 90 * t / 12)), cy + r * math.sin(math.radians(start + 90 * t / 12)))
                       for t in range(13)]
        points.append(points[0])
        on, left = True, dash
        for (ax, ay), (bx, by) in zip(points, points[1:]):
            length = math.dist((ax, ay), (bx, by))
            pos = 0
            while pos < length:
                step = min(left, length - pos)
                if on:
                    f0, f1 = pos / length, (pos + step) / length
                    d.line((ax + (bx - ax) * f0, ay + (by - ay) * f0, ax + (bx - ax) * f1, ay + (by - ay) * f1),
                           fill=BORDER, width=round(width))
                pos += step
                left -= step
                if left <= 0:
                    on, left = not on, dash

    def target(self, on: bool):
        self.canvas.itemconfigure(self.border_item, state="normal" if on else "hidden")

    def drop(self, event):
        from tkinterdnd2 import REFUSE_DROP

        self.target(False)
        if self.status[0] == "working":  # one batch at a time
            return REFUSE_DROP
        paths = [Path(p) for p in self.root.tk.splitlist(event.data)]
        self.set_status(("working", 1, len(paths)))
        threading.Thread(target=self.work, args=(paths,), daemon=True).start()
        self.poll()
        return event.action

    def work(self, paths: list[Path]):
        last_error = None
        for i, path in enumerate(paths, 1):
            self.updates.put(("working", i, len(paths)))
            try:
                convert(path)
            except Exception as e:
                last_error = e
        # ponytail: no reason shown on purpose; the headless mode prints it
        if last_error is None:
            self.updates.put(("done",))
        else:
            self.updates.put(("failed", "File not supported" if isinstance(last_error, Unsupported) else "Conversion Failed"))

    def poll(self):
        # tkinter is not thread-safe: the worker only queues, the Tk thread draws
        while not self.updates.empty():
            self.set_status(self.updates.get())
        if self.status[0] == "working":
            self.frame = (self.frame + 1) % len(self.spinner)
            self.canvas.itemconfigure("spinner", image=self.spinner[self.frame])
            self.root.after(33, self.poll)

    def set_status(self, status: tuple):
        self.status = status
        kind = status[0]
        if kind == "idle":
            items = [("image", "file-plus-corner"), ("text", "Drop files to convert to .md", TEXT_DIM)]
        elif kind == "working":
            items = [("spinner",), ("text", "Converting\u2026", TEXT_DIM)]
            if status[2] > 1:
                items.append(("text", f"{status[1]}/{status[2]}", TEXT_FAINT))
        elif kind == "done":
            items = [("image", "file-check"), ("text", "Conversion Successful", TEXT)]
        else:
            items = [("image", "x"), ("text", status[1], TEXT)]
        if kind in ("done", "failed"):
            self.root.after(2000, lambda: self.status is status and self.set_status(("idle",)))

        heights = [self.font.metrics("linespace") if item[0] == "text" else self.spinner[0].height() if item[0] == "spinner"
                   else self.icons[item[1]].height() for item in items]
        y = (self.h - sum(heights) - self.gap * (len(items) - 1)) / 2
        c = self.canvas
        c.delete("content")
        for item, height in zip(items, heights):
            if item[0] == "text":
                c.create_text(self.w / 2, y, text=item[1], fill=item[2], font=self.font, anchor="n", tags="content")
            elif item[0] == "spinner":
                c.create_image(self.w / 2, y, image=self.spinner[self.frame], anchor="n", tags=("content", "spinner"))
            else:
                c.create_image(self.w / 2, y, image=self.icons[item[1]], anchor="n", tags="content")
            y += height + self.gap

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if sys.stdout:
        sys.stdout.reconfigure(encoding="utf-8")  # paths with å/ä/ö on a cp1252 console
    files = [a for a in sys.argv[1:] if Path(a).is_file()]
    if "--check" in sys.argv:
        sys.exit(check())
    if files:
        sys.exit(headless(files))
    Window().run()
