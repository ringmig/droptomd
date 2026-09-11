// Renders AppIcon.iconset: #0d0d0d rounded square with #f0f0f0 ".md". Run: swift icon.swift
import AppKit

try? FileManager.default.createDirectory(atPath: "AppIcon.iconset", withIntermediateDirectories: true)
for size in [16, 32, 128, 256, 512] {
    for scale in [1, 2] {
        let px = size * scale
        let rep = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: px, pixelsHigh: px, bitsPerSample: 8,
                                   samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
                                   bytesPerRow: 0, bitsPerPixel: 0)!
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
        let s = CGFloat(px) / 1024 // Apple grid: 824pt tile inset 100pt, corner radius ~185
        NSColor(red: 13/255, green: 13/255, blue: 13/255, alpha: 1).setFill()
        NSBezierPath(roundedRect: NSRect(x: 100*s, y: 100*s, width: 824*s, height: 824*s), xRadius: 185*s, yRadius: 185*s).fill()
        let text = NSAttributedString(string: ".md", attributes: [
            .font: NSFont.systemFont(ofSize: 300*s, weight: .semibold),
            .foregroundColor: NSColor(red: 240/255, green: 240/255, blue: 240/255, alpha: 1),
        ])
        let t = text.size()
        text.draw(at: NSPoint(x: (CGFloat(px) - t.width) / 2, y: (CGFloat(px) - t.height) / 2))
        NSGraphicsContext.current = nil
        let name = scale == 1 ? "icon_\(size)x\(size).png" : "icon_\(size)x\(size)@2x.png"
        try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: "AppIcon.iconset/\(name)"))
    }
}
