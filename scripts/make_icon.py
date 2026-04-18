#!/usr/bin/env python3
"""Renders the 👀 emoji to assets/icon.icns using AppKit."""
import subprocess
from pathlib import Path

from AppKit import (
    NSAttributedString,
    NSBitmapImageRep,
    NSColor,
    NSFont,
    NSFontAttributeName,
    NSImage,
    NSMakeRect,
    NSMakeSize,
    NSPNGFileType,
    NSRectFill,
)
from Foundation import NSMakePoint


def make_icns(emoji: str = "👀", output: str = "assets/icon.icns") -> None:
    size = 1024
    img = NSImage.alloc().initWithSize_(NSMakeSize(size, size))
    img.lockFocus()

    NSColor.clearColor().set()
    NSRectFill(NSMakeRect(0, 0, size, size))

    font = NSFont.systemFontOfSize_(size * 0.78)
    astr = NSAttributedString.alloc().initWithString_attributes_(
        emoji, {NSFontAttributeName: font}
    )
    bounds = astr.size()
    x = (size - bounds.width) / 2
    y = (size - bounds.height) / 2
    astr.drawAtPoint_(NSMakePoint(x, y))

    bitmap = NSBitmapImageRep.alloc().initWithFocusedViewRect_(
        NSMakeRect(0, 0, size, size)
    )
    img.unlockFocus()

    png_data = bitmap.representationUsingType_properties_(NSPNGFileType, None)
    tmp_png = Path("/tmp/eye_strain_icon_1024.png")
    png_data.writeToFile_atomically_(str(tmp_png), True)

    iconset = Path("/tmp/eye_strain_icon.iconset")
    iconset.mkdir(exist_ok=True)

    for s in [16, 32, 64, 128, 256, 512]:
        subprocess.run(
            ["sips", "-z", str(s), str(s), str(tmp_png),
             "--out", str(iconset / f"icon_{s}x{s}.png")],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["sips", "-z", str(s * 2), str(s * 2), str(tmp_png),
             "--out", str(iconset / f"icon_{s}x{s}@2x.png")],
            check=True, capture_output=True,
        )

    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)], check=True)
    print(f"Created {out}")


if __name__ == "__main__":
    make_icns()
