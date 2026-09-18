# Drop to MD

![Drop to MD](screenshot.png)

A small floating window for Mac and Windows. Drop one or more files on it and each one is converted to Markdown, saved next to the original (or in Downloads if that folder is read-only).

## Install on a Mac

1. Download `DropToMD.zip`, unzip it, and move **Drop to MD** into Applications.
2. The app isn't notarized by Apple, so macOS stops the first launch:
   - **macOS 14:** right-click the app, choose **Open**, then **Open** again.
   - **macOS 15 and later:** double-click the app and close the warning. Open **System Settings → Privacy & Security**, scroll down, click **Open Anyway** next to Drop to MD, and confirm.

After that it opens normally. Nothing else to install: Python and markitdown are bundled.

Requires macOS 14 or later on Apple Silicon.

## Install on Windows

Download `DropToMD.exe` and run it. It is a single file that installs nothing; put it wherever you like. Windows SmartScreen stops the first launch because the file is not signed: click **More info**, then **Run anyway**.

Requires Windows 10 or later on a 64-bit PC. RTF, DOC and ODT need Word installed; every other format works without it.

## Formats

PDF, Word, PowerPoint, Excel (xlsx, xls), HTML, EPUB, Jupyter, Outlook msg, ZIP, CSV, JSON, XML, RSS, text, YAML, audio (mp3, wav, m4a), RTF, DOC and ODT, and images (PNG, JPG, HEIC, TIFF, GIF, BMP, WebP) through on-device text recognition.

Mac only: Pages, Numbers and Keynote (needs the app installed and permission granted when prompted during conversion), RTFD and webarchive. Windows converts RTF, DOC and ODT through Word, so those need Word installed.

## Build

```sh
./build.sh
```

Needs Xcode command line tools and [uv](https://github.com/astral-sh/uv). Produces `~/Applications/Drop to MD.app` and `dist/DropToMD.zip`.

The Windows exe is built from `windows/droptomd.py` with Nuitka, on a Windows machine, from the repo root (`mdconvert.py` there is shared with the Mac app):

```pwsh
python -m pip install -r windows/requirements.txt nuitka[onefile]==4.2.1
$env:PYTHONPATH = $PWD.Path
python -m nuitka --onefile --enable-plugin=tk-inter --include-package=winrt `
  --include-package-data=magika --include-package-data=pdfminer --include-package-data=tkinterdnd2 `
  --include-package-data=speech_recognition `
  --include-data-dir=windows/assets=assets --output-dir=build --output-filename=DropToMD.exe windows/droptomd.py
```

`DropToMD.exe --check` prints what the machine can do; passing file paths converts them without opening the window.

## Release

Push a tag, `git tag vX.Y.Z && git push origin vX.Y.Z`. GitHub Actions builds and tests both apps and puts `DropToMD.zip` and `DropToMD.exe` in one draft release; write the notes and publish it. The Windows build takes about 45 minutes when its cache is cold.

## Built on

- [microsoft/markitdown](https://github.com/microsoft/markitdown): the conversion engine for most formats
- [pdfminer.six](https://github.com/pdfminer/pdfminer.six): PDF layout, from which font size gives the headings
- [python-build-standalone](https://github.com/astral-sh/python-build-standalone), installed through uv: the relocatable Python bundled in the app
- Apple Vision: on-device text recognition for images and scanned PDF pages on the Mac
- Apple `textutil`: RTF, DOC, ODT and webarchive to HTML before markitdown on the Mac
- Microsoft Word: the same formats on Windows, which has no built-in converter
- Windows.Media.Ocr and Windows.Data.Pdf: on-device text recognition for images and scanned PDF pages on Windows
- [Nuitka](https://nuitka.net): compiles the Windows version into a single exe
- [tkinterdnd2](https://github.com/pmgagne/tkinterdnd2): file drops on the Windows window
- Pages, Numbers and Keynote: iWork files are exported to Office formats through their own app
- [Lucide](https://lucide.dev): the `file-plus-corner`, `file-check` and `x` icons
- [shift-labs-ai/markit](https://github.com/shift-labs-ai/markit): evaluated as a faster Rust engine; not used, since it covers fewer formats

MIT licensed, see [LICENSE](LICENSE). License notices for bundled and embedded third-party work: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
