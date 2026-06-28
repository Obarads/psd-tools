#!/usr/bin/env python3
"""Edit text layers in a PSD: change the text, font, and size.

Demonstrates the writable :py:attr:`TypeLayer.text` property and the
:py:meth:`TypeLayer.set_text` convenience method (text + font + size).

Usage::

    uv run python examples/edit_text_layer.py [INPUT.psd] [-o OUTPUT.psd]

If INPUT is omitted it falls back to the bundled fixture
``tests/psd_files/text.psd``.

IMPORTANT: psd-tools has no font engine, so the rasterized preview pixels of
a text layer are NOT regenerated. The new text/font/size are stored in the
file; Photoshop re-renders the layer on reopen, provided the chosen font is
installed there.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from psd_tools import PSDImage
from psd_tools.api.layers import TypeLayer

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "tests" / "psd_files" / "text.psd"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "psd",
        type=Path,
        nargs="?",
        default=DEFAULT_INPUT,
        help=f"Input PSD with a text layer (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("text_edited.psd"),
        help="Output PSD path (default: text_edited.psd)",
    )
    parser.add_argument(
        "--font",
        default="Helvetica-Bold",
        help="PostScript font name to apply (default: Helvetica-Bold)",
    )
    parser.add_argument(
        "--size",
        type=float,
        default=48.0,
        help="Font size in points (default: 48)",
    )
    args = parser.parse_args()

    if not args.psd.is_file():
        parser.error(f"No such file: {args.psd}")

    psd = PSDImage.open(args.psd)
    type_layers = [layer for layer in psd.descendants() if isinstance(layer, TypeLayer)]
    if not type_layers:
        parser.error(f"No text layers found in {args.psd}")

    first = type_layers[0]
    print(f"[before] text={first.text!r} fonts={first.font_names}")

    # 1. Simplest edit: replace just the text (keeps the existing styling).
    #    '\n' is normalized to Photoshop's '\r' line separator.
    first.text = "Edited text\nsecond line"
    print(f"[text  ] {first.text!r}")

    # 2. Change text, font and size in one call (option B).
    first.set_text("Brand New!\nFont + size", font=args.font, size=args.size)
    print(f"[set_text] text={first.text!r} fonts={first.font_names} size={args.size}")

    psd.save(args.output)
    print(f"[saved ] {args.output}")

    # Confirm the changes persisted by reopening.
    reopened = PSDImage.open(args.output)
    layer = next(
        layer for layer in reopened.descendants() if isinstance(layer, TypeLayer)
    )
    print(f"[reopen] text={layer.text!r} fonts={layer.font_names}")

    print(
        "\nNOTE: text pixels are not re-rendered by psd-tools. Open the saved "
        "PSD in\nPhotoshop to see the new text/font rendered (the font must be "
        "installed there)."
    )


if __name__ == "__main__":
    main()
