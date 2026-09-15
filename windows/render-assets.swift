// Renders windows/assets: the Lucide icons at 100/150/200 % and the app icon. Run from the repo root: swift windows/render-assets.swift
// The icon path data is copied from main.swift; keep the two in step.
import AppKit

func png(_ px: Int, to path: String, draw: (CGFloat) -> Void) {
    let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8, samplesPerPixel: 4,
                               hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB, bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    draw(CGFloat(px))
    NSGraphicsContext.current = nil
    try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: path))
}

func lucide(_ paths: String, stroke: String) -> NSImage {
    let svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" \
    stroke="\(stroke)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">\(paths)</svg>
    """
    return NSImage(data: Data(svg.utf8))!
}

let icons = [
    "file-plus-corner": lucide("""
    <path d="M11.35 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588A2.4 2.4 0 0 1 20 8v5.35"/>\
    <path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="M14 19h6"/><path d="M17 16v6"/>
    """, stroke: "white"),
    "file-check": lucide("""
    <path d="M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z"/>\
    <path d="M14 2v5a1 1 0 0 0 1 1h5"/><path d="m9 15 2 2 4-4"/>
    """, stroke: "white"),
    "x": lucide(#"<path d="M18 6 6 18"/><path d="m6 6 12 12"/>"#, stroke: "#ef4444"),
]

try? FileManager.default.createDirectory(atPath: "windows/assets", withIntermediateDirectories: true)
for (name, image) in icons {
    for px in [44, 66, 88] {
        png(px, to: "windows/assets/\(name)-\(px).png") { s in image.draw(in: NSRect(x: 0, y: 0, width: s, height: s)) }
    }
}

// Same tile as icon.swift, but filling the canvas the way Windows icons do instead of Apple's inset grid.
png(256, to: "windows/assets/app.png") { s in
    NSColor(red: 13/255, green: 13/255, blue: 13/255, alpha: 1).setFill()
    NSBezierPath(roundedRect: NSRect(x: 0, y: 0, width: s, height: s), xRadius: s * 0.22, yRadius: s * 0.22).fill()
    let text = NSAttributedString(string: ".md", attributes: [
        .font: NSFont.systemFont(ofSize: s * 0.36, weight: .semibold),
        .foregroundColor: NSColor(red: 240/255, green: 240/255, blue: 240/255, alpha: 1),
    ])
    let t = text.size()
    text.draw(at: NSPoint(x: (s - t.width) / 2, y: (s - t.height) / 2))
}
