#!/usr/bin/env python3
"""Convert a multi-page (layer-separated) TIFF into a layered PSD.

Each page of the TIFF becomes one pixel layer in the output PSD, in order
from bottom (page 0) to top. This is handy for round-tripping artwork that
was exported as a multi-page TIFF back into an editable PSD.

Use it as a library::

    from tiff_to_layered_psd import tiff_to_layered_psd

    psd = tiff_to_layered_psd("ad_layered.tiff", "ad.psd")
    print(len(list(psd.descendants())), "layers")

...or from the command line::

    uv run python examples/tiff_to_layered_psd.py INPUT.tiff -o output.psd \
        --names Background Logo Badge Headline Subtitle "CTA Button" Footer

If ``--names`` is omitted the layer name comes from each page's TIFF
ImageDescription tag (270), falling back to ``Layer 1``, ``Layer 2``, ...

Note: ``PSDImage.frompil()`` always flattens to a single layer, and a flat
(single-page) TIFF can only yield a one-layer PSD. To get multiple layers the
input must be a genuine multi-page TIFF.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageSequence

from psd_tools import PSDImage


def _page_name(frame: Image.Image, index: int, names: Sequence[str] | None) -> str:
    """Resolve a layer name: explicit names win, then tag 270, then default."""
    if names is not None and index < len(names):
        return names[index]
    tag_name = ""
    if hasattr(frame, "tag_v2"):
        tag_name = (frame.tag_v2.get(270) or "").strip()
    return tag_name or f"Layer {index + 1}"


def tiff_to_layered_psd(
    tiff: str | Path | Image.Image,
    output: str | Path | None = None,
    names: Sequence[str] | None = None,
    mode: str = "RGB",
    verbose: bool = False,
) -> PSDImage:
    """Convert a multi-page TIFF into a layered :class:`PSDImage`.

    :param tiff: Path to a multi-page TIFF, or an already-open PIL image.
    :param output: If given, the resulting PSD is saved to this path.
    :param names: Optional layer names, one per page, bottom-to-top. When
        omitted, each page's ImageDescription tag (270) is used, then a
        ``Layer N`` default.
    :param mode: Color mode for the new PSD (``"RGB"`` by default).
    :param verbose: Print progress and warnings while converting.
    :return: The created :class:`~psd_tools.api.psd_image.PSDImage`.
    :raises ValueError: If the TIFF has no pages.
    """
    im = tiff if isinstance(tiff, Image.Image) else Image.open(tiff)

    n_frames = getattr(im, "n_frames", 1)
    if verbose:
        print(f"[input] {getattr(im, 'filename', tiff)}  ({n_frames} page(s))")
    if verbose and n_frames == 1:
        # The usual cause of an unexpected one-layer PSD.
        print(
            "[warn] this TIFF has only ONE page, so the PSD will have a single "
            "layer.\n"
            "       To get multiple layers, provide a MULTI-PAGE TIFF (one page "
            "per\n"
            "       element). Photoshop-style layers stored in a private TIFF "
            "tag are\n"
            "       not exposed as pages by Pillow and cannot be read here."
        )

    pages: list[tuple[Image.Image, str]] = []
    for i, frame in enumerate(ImageSequence.Iterator(im)):
        pages.append((frame.convert("RGBA"), _page_name(frame, i, names)))

    if not pages:
        raise ValueError("The TIFF has no pages.")

    width, height = pages[0][0].size
    psd = PSDImage.new(mode, (width, height))
    for image, name in pages:
        if image.size != (width, height):
            # Place a smaller/larger page at the top-left of a full canvas.
            canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            canvas.paste(image, (0, 0))
            image = canvas
        psd.create_pixel_layer(image, name=name)
        if verbose:
            print(f"[layer] {name!r}")

    if output is not None:
        psd.save(output)
        if verbose:
            # Verify by reopening: confirm every page became a real layer.
            saved = list(PSDImage.open(output).descendants())
            print(f"[psd] {output}  ({len(saved)} layers, {width}x{height})")
            if len(saved) != len(pages):
                print(
                    f"[warn] expected {len(pages)} layers but the saved PSD has "
                    f"{len(saved)}."
                )

    return psd


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
    parser.add_argument(
        "--mode",
        default="RGB",
        help="Color mode for the output PSD (default: RGB)",
    )
    args = parser.parse_args()

    if not args.tiff.is_file():
        parser.error(f"No such file: {args.tiff}")
    output = args.output or args.tiff.with_suffix(".psd")

    tiff_to_layered_psd(
        args.tiff,
        output=output,
        names=args.names,
        mode=args.mode,
        verbose=True,
    )


if __name__ == "__main__":
    main()
