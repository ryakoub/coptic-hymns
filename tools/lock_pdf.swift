// Locks a score shared only by permission, for the catalog: the PDF sealed with AES-GCM, which only the app opens.
//
//   swift tools/lock_pdf.swift SCORE.pdf content/notations/<id>/notation.pdf.locked
//
// The key is in ~/.config/coptic-chanter/notation.key (base64), outside both repos; the app has the same key.
// The PDF itself never goes in this repo, which is public: keep it with the cantor's permission (iCloud Hymns).
// In notation.json: "pdf": "notation.pdf.locked", "locked": true, and "permission": {"english": …, "arabic": …}.
import CryptoKit
import Foundation

let args = CommandLine.arguments
guard args.count == 3 else {
    FileHandle.standardError.write(Data("usage: swift tools/lock_pdf.swift SCORE.pdf OUT.pdf.locked\n".utf8))
    exit(2)
}
let keyFile = FileManager.default.homeDirectoryForCurrentUser.appending(path: ".config/coptic-chanter/notation.key")
guard let text = try? String(contentsOf: keyFile, encoding: .utf8),
      let keyData = Data(base64Encoded: text.trimmingCharacters(in: .whitespacesAndNewlines)), keyData.count == 32 else {
    FileHandle.standardError.write(Data("no key in \(keyFile.path)\n".utf8))
    exit(1)
}
let pdf = try Data(contentsOf: URL(fileURLWithPath: args[1]))
guard pdf.starts(with: Data("%PDF".utf8)) else {
    FileHandle.standardError.write(Data("\(args[1]) is not a PDF\n".utf8))
    exit(1)
}
let key = SymmetricKey(data: keyData)
let sealed = try AES.GCM.seal(pdf, using: key).combined!
let out = Data("CCLK1".utf8) + sealed
// Opened again before writing, so a bad file never reaches the catalog.
guard try AES.GCM.open(AES.GCM.SealedBox(combined: out.dropFirst(5)), using: key) == pdf else { exit(1) }
try out.write(to: URL(fileURLWithPath: args[2]), options: .atomic)
print("locked \(args[1]) → \(args[2]) (\(out.count) bytes)")
