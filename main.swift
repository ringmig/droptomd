import SwiftUI
import AppKit
import Vision
import PDFKit

// markitdown runs on a standalone Python bundled inside the app, so nothing needs installing
let python = Bundle.main.resourcePath! + "/python/bin/python3"
let script = Bundle.main.resourcePath! + "/mdconvert.py"

func lucide(_ paths: String, stroke: String = "white") -> NSImage {
    let svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" \
    stroke="\(stroke)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">\(paths)</svg>
    """
    return NSImage(data: Data(svg.utf8))!
}

let filePlusCorner = lucide("""
<path d="M11.35 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v5.35"/>\
<path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="M14 19h6"/><path d="M17 16v6"/>
""")
let fileCheck = lucide("""
<path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/>\
<path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="m9 15 2 2 4-4"/>
""")
let xIcon = lucide(#"<path d="M18 6 6 18"/><path d="m6 6 12 12"/>"#, stroke: "#ef4444")

enum Status: Equatable { case idle, working(Int, Int), done, failed(String) }

func fail(_ msg: String, code: Int = 1) -> NSError { NSError(domain: "convert", code: code, userInfo: [NSLocalizedDescriptionKey: msg]) }
let unsupportedCode = 2

/// Runs a tool and returns its stdout; throws the last stderr line on a non-zero exit.
@discardableResult
func run(_ exe: String, _ args: [String]) throws -> Data {
    let p = Process()
    p.executableURL = URL(fileURLWithPath: exe)
    p.arguments = args
    let out = Pipe(), err = Pipe()
    p.standardOutput = out
    p.standardError = err
    try p.run()
    let data = out.fileHandleForReading.readDataToEndOfFile() // read before wait, or a full pipe deadlocks
    let errText = String(decoding: err.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
    p.waitUntilExit()
    guard p.terminationStatus == 0 else {
        throw fail(errText.split(separator: "\n").last.map(String.init) ?? "Conversion failed")
    }
    return data
}

// Mac formats markitdown can't read. Rich text goes through the system's textutil, iWork through its own app.
let textutilTypes: Set = ["rtf", "rtfd", "doc", "odt", "webarchive", "wordml"]
let iworkTypes = ["pages": ("Pages", "Microsoft Word", "docx"),
                  "numbers": ("Numbers", "Microsoft Excel", "xlsx"),
                  "key": ("Keynote", "Microsoft PowerPoint", "pptx")]
let imageTypes: Set = ["heic", "heif", "png", "jpg", "jpeg", "tiff", "tif", "gif", "bmp", "webp"]
// markitdown passes unknown files through as text, so anything off this list is refused up front.
// md is left off on purpose: its output path is the source itself, so converting would overwrite it.
let markitdownTypes: Set = ["pdf", "docx", "pptx", "xlsx", "xls", "html", "htm", "epub", "ipynb", "msg", "zip",
                            "csv", "json", "xml", "rss", "atom", "txt", "yaml", "yml", "mp3", "wav", "m4a"]

/// Text in an image via Vision, the same on-device OCR as Live Text.
// ponytail: no headings from OCR; line height mixes rotated margin text and photo text in with titles
func recognizeText(_ image: CGImage) throws -> String {
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.automaticallyDetectsLanguage = true
    try VNImageRequestHandler(cgImage: image).perform([request])
    return (request.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: "\n")
}

func ocr(_ src: URL) throws -> Data {
    guard let source = CGImageSourceCreateWithURL(src as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else { throw fail("Could not read image") }
    let text = try recognizeText(image)
    guard !text.isEmpty else { throw fail("No text found in image") }
    return Data(text.utf8)
}

/// Fills the `<!-- ocr-page N -->` marks mdconvert.py leaves where a PDF page's text is only pixels or outlines.
func ocrPages(_ md: String, pdf: URL) throws -> String {
    guard md.contains("<!-- ocr-page"), let doc = PDFDocument(url: pdf) else { return md }
    var out = md
    for match in md.matches(of: #/<!-- ocr-page (\d+) -->/#) {
        guard let page = doc.page(at: Int(match.1)! - 1) else { continue }
        let box = page.bounds(for: .mediaBox)
        let scale = 1600 / max(box.width, box.height)
        let image = page.thumbnail(of: CGSize(width: box.width * scale, height: box.height * scale), for: .mediaBox)
        guard let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
        out = out.replacingOccurrences(of: String(match.0), with: try recognizeText(cg))
    }
    return out.replacing(#/\n{3,}/#, with: "\n\n") // a page with no text found leaves blank lines behind
}

func markdown(for src: URL) throws -> Data {
    let ext = src.pathExtension.lowercased()
    if imageTypes.contains(ext) { return try ocr(src) }
    guard markitdownTypes.contains(ext) || textutilTypes.contains(ext) || iworkTypes[ext] != nil
    else { throw fail("File not supported", code: unsupportedCode) }
    let tmp = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    try FileManager.default.createDirectory(at: tmp, withIntermediateDirectories: true)
    defer { try? FileManager.default.removeItem(at: tmp) }
    var input = src
    if textutilTypes.contains(ext) {
        input = tmp.appendingPathComponent("doc.html")
        try run("/usr/bin/textutil", ["-convert", "html", src.path, "-output", input.path])
    } else if let (app, format, outExt) = iworkTypes[ext] {
        guard NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.iWork.\(app)") != nil
        else { throw fail("\(app) is needed to convert .\(ext) files") }
        input = tmp.appendingPathComponent("doc.\(outExt)")
        try run("/usr/bin/osascript", ["-e", """
            on run argv
                set wasRunning to application "\(app)" is running
                tell application "\(app)"
                    set d to open (POSIX file (item 1 of argv))
                    export d to (POSIX file (item 2 of argv)) as \(format)
                    close d saving no
                    if not wasRunning then quit
                end tell
            end run
            """, src.path, input.path])
    }
    var md = String(decoding: try run(python, [script, input.path]), as: UTF8.self)
    if ext == "pdf" { md = try ocrPages(md, pdf: input) }
    // markitdown exits 0 with nothing on a broken file; an empty .md is a failure, not a success
    guard !md.allSatisfy(\.isWhitespace) else { throw fail("Empty result") }
    return Data(md.utf8)
}

/// Converts `src` and writes `<name>.md` next to it, or in ~/Downloads if that folder isn't writable.
func convert(_ src: URL) throws -> URL {
    let md = try markdown(for: src)
    let name = src.deletingPathExtension().lastPathComponent + ".md"
    let beside = src.deletingLastPathComponent().appendingPathComponent(name)
    do {
        try md.write(to: beside)
        return beside
    } catch {
        let downloads = FileManager.default.urls(for: .downloadsDirectory, in: .userDomainMask)[0].appendingPathComponent(name)
        try md.write(to: downloads)
        return downloads
    }
}

struct DropView: View {
    @State private var status = Status.idle
    @State private var targeted = false

    var body: some View {
        VStack(spacing: 14) {
            switch status {
            case .idle:
                icon(filePlusCorner)
                Text("Drop files to convert to .md").foregroundStyle(.white.opacity(0.7))
            case .working(let n, let total):
                ProgressView().controlSize(.large).tint(.white)
                Text("Converting…").foregroundStyle(.white.opacity(0.7))
                if total > 1 { Text("\(n)/\(total)").monospacedDigit().foregroundStyle(.white.opacity(0.45)) }
            case .done:
                icon(fileCheck)
                Text("Conversion Successful").foregroundStyle(.white)
            case .failed(let title):
                icon(xIcon)
                Text(title).foregroundStyle(.white)
            }
        }
        .font(.system(size: 14, weight: .medium))
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color(red: 13/255, green: 13/255, blue: 13/255))
        .overlay(RoundedRectangle(cornerRadius: 12).strokeBorder(.white.opacity(targeted ? 0.35 : 0), style: StrokeStyle(lineWidth: 1.5, dash: [6])).padding(10))
        .dropDestination(for: URL.self) { urls, _ in
            if case .working = status { return false } // one batch at a time
            status = .working(1, urls.count)
            Task.detached {
                var lastError: NSError?
                for (i, url) in urls.enumerated() {
                    await MainActor.run { status = .working(i + 1, urls.count) }
                    do { _ = try convert(url) } catch { lastError = error as NSError }
                }
                // ponytail: no reason shown on purpose; the headless mode prints it
                let result: Status = switch lastError?.code {
                case nil: .done
                case unsupportedCode: .failed("File not supported")
                default: .failed("Conversion Failed")
                }
                await MainActor.run { status = result }
                try? await Task.sleep(for: .seconds(2))
                await MainActor.run { if status == result { status = .idle } }
            }
            return true
        } isTargeted: { targeted = $0 }
    }

    func icon(_ img: NSImage) -> some View {
        Image(nsImage: img).resizable().frame(width: 44, height: 44)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    func applicationDidFinishLaunching(_ n: Notification) {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 320, height: 220),
                          styleMask: [.titled, .closable, .fullSizeContentView], backing: .buffered, defer: false)
        window.titlebarAppearsTransparent = true
        window.titleVisibility = .hidden
        window.standardWindowButton(.miniaturizeButton)?.isHidden = true
        window.standardWindowButton(.zoomButton)?.isHidden = true
        window.isMovableByWindowBackground = true
        window.level = .floating
        window.backgroundColor = NSColor(red: 13/255, green: 13/255, blue: 13/255, alpha: 1)
        window.appearance = NSAppearance(named: .darkAqua)
        window.contentView = NSHostingView(rootView: DropView().ignoresSafeArea())
        window.center()
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { true }
}

// Headless check: `DropToMD file...` converts without the window.
let paths = CommandLine.arguments.dropFirst().filter { FileManager.default.fileExists(atPath: $0) }
if !paths.isEmpty {
    for p in paths {
        do { print("ok  ", try convert(URL(fileURLWithPath: p)).path) } catch { print("FAIL", p, error.localizedDescription) }
    }
    exit(0)
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
