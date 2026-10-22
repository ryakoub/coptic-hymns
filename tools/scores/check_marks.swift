import AppKit
import PDFKit
// Draws the marks of one page as red dots on it: swift check_marks.swift in.pdf marks.json out.png [page, from 1]
let a = CommandLine.arguments
let doc = PDFDocument(url: URL(fileURLWithPath: a[1]))!
let number = a.count > 4 ? Int(a[4])! : 1
let page = doc.page(at: number - 1)!
let box = page.bounds(for: .mediaBox)
struct M: Decodable { let marks: [[Double]] }
let marks = try! JSONDecoder().decode(M.self, from: Data(contentsOf: URL(fileURLWithPath: a[2]))).marks
let scale = 2.0
let img = NSImage(size: NSSize(width: box.width * scale, height: box.height * scale))
img.lockFocus()
let ctx = NSGraphicsContext.current!.cgContext
NSColor.white.setFill(); ctx.fill(CGRect(x: 0, y: 0, width: box.width * scale, height: box.height * scale))
ctx.scaleBy(x: scale, y: scale)
page.draw(with: .mediaBox, to: ctx)
NSColor.red.withAlphaComponent(0.6).setFill()
for m in marks where Int(m[1]) == number { let x = m[2] * box.width, y = (1 - m[3]) * box.height
    ctx.fillEllipse(in: CGRect(x: x - 3, y: y - 3, width: 6, height: 6)) }
img.unlockFocus()
let rep = NSBitmapImageRep(data: img.tiffRepresentation!)!
try! rep.representation(using: .png, properties: [:])!.write(to: URL(fileURLWithPath: a[3]))
