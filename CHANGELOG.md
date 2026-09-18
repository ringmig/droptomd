# Changelog

## 2026-09-18

### Headings, and no more boxes
PDFs used to come out as flat text. Now the size of the type decides what is a heading, so a deck or a report keeps its structure. Slides without a title field, as Keynote exports them, get their largest text as the heading. PDF pages whose text is only an image, as in many design decks, are read by the on-device text recognition instead of coming out empty. The crossed-out boxes are gone: they were page breaks, soft line breaks and other invisible characters, along with links to slide images that were never saved. Letter-spaced titles like `C R E A T I V E` read as words. Mac and Windows convert the same way.

### A dropped Markdown file stays as it is
Dropping a `.md` file used to overwrite it with its own conversion. It is now refused as not supported, and the file is left untouched.

### One release for both
Each release now carries both the Mac zip and the Windows exe, built and tested by GitHub Actions from the same tag.

## 2026-09-16

### Windows version
The same window on Windows, as a single exe that installs nothing. Drop files, get Markdown next to the originals. Text recognition for images runs on Windows' own engine, and RTF, DOC and ODT go through Word, which Windows needs for them since it has no built-in converter. The Mac app is unchanged.

## 2026-09-11

### First version
Floating drop window that converts files to Markdown next to the source, or in Downloads. Batch drop with a progress ticker, red error states, 2 s auto-reset. markitdown and Python are bundled, so the app runs without installing anything. Mac formats added on top of markitdown: Pages, Numbers, Keynote, RTF, DOC, ODT, webarchive, and image OCR.
