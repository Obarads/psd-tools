#!/usr/bin/env python3
"""Edit the text of every TypeLayer in a PSD and render before/after images.

This demonstrates the writable ``TypeLayer.text`` property. It opens the PSD
given on the command line, renders the original composite, rewrites the text
of every text layer, optionally saves the edited PSD, and renders the result.

Usage::

    uv run python examples/edit_text_to_image.py INPUT.psd \
        --text "New text" --outdir ./out --save-psd

IMPORTANT: psd-tools has no font engine, so the rasterized pixels of a text
layer are NOT regenerated when the text changes. The ``*_after.png`` image
therefore looks identical to ``*_before.png`` for text layers -- the new text
becomes visible only when the edited PSD is reopened in Photoshop, which
re-renders the layer. The point of the rendered images here is to confirm the
rest of the document still composites cleanly after editing.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from psd_tools import PSDImage


def render(psd: PSDImage) -> Image.Image | None:
    """Render the document, falling back to the embedded preview."""
    try:
        return psd.composite()
    except ImportError as exc:
        # Composite extras (aggdraw/scipy/scikit-image) are not installed.
        print(f"[warn] composite unavailable ({exc}); using embedded preview")
        return psd.topil()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("psd", type=Path, help="Input PSD/PSB file")
    parser.add_argument(
        "-t",
        "--text",
        default="Edited by psd-tools\nテキスト編集テスト",
        help="New text to set on every type layer ('\\n' starts a new line)",
    )
    parser.add_argument(
        "-o",
        "--outdir",
        type=Path,
        default=Path("."),
        help="Directory for the output images (and edited PSD)",
    )
    parser.add_argument(
        "--save-psd",
        action="store_true",
        help="Also write the edited PSD next to the images",
    )
    args = parser.parse_args()

    if not args.psd.is_file():
        parser.error(f"No such file: {args.psd}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    stem = args.psd.stem

    psd = PSDImage.open(args.psd)

    # 1. Render the original composite.
    before = render(psd)
    if before is not None:
        before_path = args.outdir / f"{stem}_before.png"
        before.convert("RGBA").save(before_path)
        print(f"[before] {before_path}")

    # 2. Rewrite the text of every type layer.
    type_layers = [layer for layer in psd.descendants() if layer.kind == "type"]
    if not type_layers:
        print("[edit] no type layers found -- nothing to change")
    # Interpret literal '\n' / '\r' typed on the command line as line breaks
    # (without touching other characters, so non-ASCII text is preserved).
    new_text = args.text.replace("\\n", "\n").replace("\\r", "\r")
    for layer in type_layers:
        old = layer.text
        layer.text = new_text
        print(f"[edit] {layer.name!r}: {old!r} -> {layer.text!r}")

    # 3. Optionally persist the edited PSD (open this in Photoshop to verify).
    if args.save_psd:
        psd_path = args.outdir / f"{stem}_edited.psd"
        psd.save(psd_path)
        print(f"[psd] {psd_path}")

    # 4. Render again. Text pixels are unchanged (see the module docstring).
    after = render(psd)
    if after is not None:
        after_path = args.outdir / f"{stem}_after.png"
        after.convert("RGBA").save(after_path)
        print(f"[after] {after_path}")

    print(
        "\nNOTE: text layer pixels are not re-rendered by psd-tools. Open the "
        "edited\nPSD in Photoshop to see the new text rendered."
    )


if __name__ == "__main__":
    main()
