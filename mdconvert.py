"""File to Markdown: markitdown, plus what it misses. `python3 mdconvert.py FILE` prints the Markdown.

PDFs skip markitdown, which reads them as flat text: here font size decides the headings. A page whose
text is only pixels or outlines comes out as `<!-- ocr-page N -->`, for the caller's OCR to fill in.
"""
import collections
import re
import statistics
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

OCR_MARK = "<!-- ocr-page {} -->"


def line_text(line):
    """A line's text and font size, spaced by the gaps between its glyphs."""
    from pdfminer.layout import LTChar

    chars = [c for c in line if isinstance(c, LTChar)]
    glyphs = [c for c in chars if c.get_text().strip()]
    if not glyphs:
        return "", 0
    gaps = [b.x0 - a.x1 for a, b in zip(glyphs, glyphs[1:])]
    size = statistics.median(c.size for c in glyphs)
    # Letter-spaced display type has wide gaps inside words, so words are measured against the line's own spacing
    track = max(0, statistics.median(gaps)) if len(gaps) >= 4 else 0
    text, prev, typed_space = "", None, False
    for c in chars:
        if not c.get_text().strip():
            typed_space = True
            continue
        if prev and (typed_space or c.x0 - prev.x1 > track + 0.15 * size):
            text += " "
        text, prev, typed_space = text + c.get_text(), c, False
    # "C R E A T I V E   P R I N C I P L E S": spaces typed between letters, words apart by two or more
    tokens = "".join(c.get_text() for c in chars).strip().split(" ")
    if len(tokens) >= 4 and all(len(t) <= 1 for t in tokens):
        text = re.sub(" +", " ", "".join(t or " " for t in tokens))
    return text, round(size * 2) / 2


def text_boxes(items):
    """Text boxes in pdfminer's reading order, including those inside figures."""
    from pdfminer.layout import LTFigure, LTTextBox

    for item in items:
        if isinstance(item, LTTextBox):
            yield item
        elif isinstance(item, LTFigure):
            yield from text_boxes(item)


def pdf_markdown(path):
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LAParams, LTTextBox

    pages = []
    for n, page in enumerate(extract_pages(path, laparams=LAParams(all_texts=True)), 1):
        boxes, seen = [], set()
        for box in text_boxes(page):
            lines = []
            for line in box:
                text, size = line_text(line)
                key = (text, round(line.x0), round(line.y0))
                if text and key not in seen:  # text drawn twice, as outline and fill, comes out once
                    seen.add(key)
                    lines.append((text, size))
            if lines:
                boxes.append(lines)
        if sum(len(t) for b in boxes for t, _ in b) < 20 and any(not isinstance(i, LTTextBox) for i in page):
            boxes = OCR_MARK.format(n)  # the text is in an image or outlined
        pages.append(boxes)

    sizes = collections.Counter()
    for boxes in pages:
        for text, size in (ln for b in boxes for ln in b) if isinstance(boxes, list) else ():
            sizes[size] += len(text)
    body = sizes.most_common(1)[0][0] if sizes else 0
    # Sizes clearly above body text are headings; within 10 % of each other they share a level, at most three
    levels, level, top = {}, 0, None
    for size in sorted((s for s in sizes if s >= body * 1.2 + 1), reverse=True):
        if top is None or size < top * 0.9:
            level, top = level + 1, size
        levels[size] = min(level, 3)

    blocks = []
    for boxes in pages:
        if isinstance(boxes, str):
            blocks.append(boxes)
            continue
        paras = []
        for box in boxes:
            out, prev = [], None
            for text, size in box:
                h = levels.get(size) if len(text) <= 150 else None
                text = re.sub(r"^[•●▪■◦‣∙·]\s*", "- ", text)
                if h and h == prev:
                    out[-1] += " " + text  # a heading wrapped onto the next line
                elif h:
                    out += ["", "#" * h + " " + text]
                else:
                    out += [""] * bool(prev) + [text]
                prev = h
            paras.append("\n".join(out).strip())
        if paras:
            blocks.append("\n\n".join(paras))
    return "\n\n---\n\n".join(blocks)


def text_shapes(shapes):
    for shape in shapes:
        if hasattr(shape, "shapes"):
            yield from text_shapes(shape.shapes)
        elif shape.has_text_frame and shape.text.strip():
            yield shape


def font_size(shape):
    return max((r.font.size or 0 for p in shape.text_frame.paragraphs for r in p.runs), default=0)


def pptx_headings(md, path):
    """Slides without a title placeholder, as Keynote exports them, get their largest text as the heading."""
    import pptx

    parts = re.split(r"(<!-- Slide number: \d+ -->\n)", md)
    for i, slide in enumerate(pptx.Presentation(path).slides):
        body = 2 + 2 * i
        if slide.shapes.title is not None or body >= len(parts):
            continue
        shapes = sorted(text_shapes(slide.shapes), key=font_size, reverse=True)
        if len(shapes) < 2 or font_size(shapes[0]) <= font_size(shapes[-1]) or len(shapes[0].text) > 150:
            continue
        text = shapes[0].text
        parts[body] = parts[body].replace(text + "\n", "# " + " ".join(text.split()) + "\n", 1)
    return "".join(parts)


def resolves(target, src):
    if target.startswith(("http://", "https://")):
        return True
    if target.startswith("data:"):
        return not target.endswith("...")  # markitdown cuts data URIs short unless told otherwise
    return (Path(src).parent / unquote(target)).exists()


def clean(md, src):
    """Strips what shows up as boxes and broken images: control characters, ligatures, unsaved image links."""
    md = md.replace("\r\n", "\n").replace("\x0b", "\n").replace("\x0c", "\n\n")
    md = re.sub("[ﬀ-ﬆ]", lambda m: unicodedata.normalize("NFKC", m[0]), md)
    md = re.sub(r"(?m)^[-]\s*", "- ", md)  # Symbol and Wingdings bullets
    md = re.sub("[\x00-\x08\x0b-\x1f\x7f​‎‏‪-‮⁦-⁩﻿-]", "", md)
    # markitdown names images it never saves; only links that lead somewhere stay
    md = re.sub(r"!\[[^\]]*\]\(([^)\s]*)\)\n?", lambda m: m[0] if resolves(m[1], src) else "", md)
    return re.sub(r"\n{3,}", "\n\n", md).strip() + "\n"


def convert(path):
    path = Path(path)
    ext = path.suffix.lower()
    md = None
    if ext == ".pdf":
        try:
            md = pdf_markdown(path)
        except Exception:  # a PDF pdfplumber can't lay out still gets markitdown's flat text
            pass
    if md is None:
        from markitdown import MarkItDown

        md = MarkItDown().convert(str(path)).markdown
        if ext == ".pptx":
            md = pptx_headings(md, path)
    return clean(md, path)


if __name__ == "__main__":
    sys.stdout.buffer.write(convert(sys.argv[1]).encode())
