#!/usr/bin/env python3
"""Convert a multi-page (layer-separated) TIFF into a layered PSD.

Each page of the TIFF becomes one pixel layer in the output PSD, in order
from bottom (page 0) to top. This is handy for round-tripping artwork that
was exported as a multi-page TIFF back into an editable PSD.

Usage::

    uv run python examples/tiff_to_layered_psd.py INPUT.tiff -o output.psd \
        --names Background Logo Badge Headline Subtitle "CTA Button" Footer

If ``--names`` is omitted the layers are named ``Layer 1``, ``Layer 2``, ...
The page's TIFF ImageDescription tag (270), if present, is used as a fallback
layer name.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageSequence

from psd_tools import PSDImage


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("tiff", type=Path, help="Input multi-page TIFF file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PSD path (default: alongside the input, .psd extension)",
    )
    parser.add_argument(
        "--names",
        nargs="*",
        default=None,
        help="Layer names, one per page, bottom-to-top",
    )
    args = parser.parse_args()

    if not args.tiff.is_file():
        parser.error(f"No such file: {args.tiff}")
    output = args.output or args.tiff.with_suffix(".psd")

    im = Image.open(args.tiff)
    pages = []
    for i, frame in enumerate(ImageSequence.Iterator(im)):
        # Per-page name: explicit --names wins, else ImageDescription, else default.
        tag_name = ""
        if hasattr(frame, "tag_v2"):
            tag_name = (frame.tag_v2.get(270) or "").strip()
        if args.names and i < len(args.names):
            name = args.names[i]
        else:
            name = tag_name or f"Layer {i + 1}"
        pages.append((frame.convert("RGBA"), name))

    if not pages:
        parser.error("The TIFF has no pages.")

    width, height = pages[0][0].size
    psd = PSDImage.new("RGB", (width, height))
    for image, name in pages:
        if image.size != (width, height):
            # Pad/place smaller pages at the top-left corner.
            canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            canvas.paste(image, (0, 0))
            image = canvas
        psd.create_pixel_layer(image, name=name)
        print(f"[layer] {name!r}")

    psd.save(output)
    print(f"[psd] {output}  ({len(pages)} layers, {width}x{height})")


if __name__ == "__main__":
    main()
