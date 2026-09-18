# Third-party notices

## Lucide

`main.swift` embeds the path data of the Lucide icons `file-plus-corner`, `file-check` and `x`.

```
ISC License

Copyright (c) 2026 Lucide Icons and Contributors

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

The `x` icon is derived from Feather:

```
The MIT License (MIT)

Copyright (c) 2013-present Cole Bemis

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Bundled in the Mac app (release zip only, not in this repo)

The app ships Python (PSF License) and markitdown (MIT, Microsoft) with its dependencies, all under permissive licenses (MIT, BSD, Apache 2.0, MPL 2.0 for certifi). Each package's license file is included inside the app under `Contents/Resources/python/lib/python3.12/site-packages/*.dist-info/`.

SpeechRecognition bundles the unmodified `flac` command-line encoder, licensed GPL 2.0, as a separate program used only for audio transcription. Its license is included alongside it; the source is available at https://github.com/xiph/flac.

## Bundled in the Windows exe (release only, not in this repo)

`DropToMD.exe` compiles in Python (PSF License) with Tcl/Tk (BSD-style), markitdown (MIT, Microsoft) with the same dependencies as the Mac app, pywinrt (MIT), tkinterdnd2 (MIT) with tkdnd (BSD-style) and Pillow (MIT-CMU). Each project's license is in its repository, and the exact versions are pinned in `windows/requirements.txt`.

The exe is compiled with [Nuitka](https://nuitka.net), which is AGPLv3 with a runtime exception (`LICENSE-RUNTIME.txt` in the Nuitka repository): the compiled program is not subject to the AGPL.
