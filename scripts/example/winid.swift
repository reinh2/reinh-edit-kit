// prints "<id> <w>x<h> <title>" for on-screen windows of the app named in argv[1] (only that app)
import CoreGraphics
import Foundation
let app = CommandLine.arguments[1]
let list = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as! [[String: Any]]
for w in list where (w[kCGWindowOwnerName as String] as? String) == app && (w[kCGWindowLayer as String] as? Int) == 0 {
  let b = w[kCGWindowBounds as String] as! [String: Any]
  print(w[kCGWindowNumber as String]!, "\(b["Width"]!)x\(b["Height"]!)", w[kCGWindowName as String] ?? "")
}
