"""Bounded image inspection views; original evidence bytes never change."""
from __future__ import annotations

import hashlib
import io

MAX_BYTES = 5_000_000
MAX_DIMENSION = 8000
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_PIXELS = 64_000_000


def inspection_view(raw: bytes, mime: str, region=None, frame: int = 0) -> tuple[bytes, str, dict]:
    from PIL import Image
    if len(raw) > MAX_SOURCE_BYTES:
        raise ValueError("Image exceeds the bounded source inspection limit")
    if type(frame) is not int or frame < 0:
        raise ValueError("Image frame must be a nonnegative integer")
    with Image.open(io.BytesIO(raw)) as original:
        dimensions = original.size
        if dimensions[0] * dimensions[1] > MAX_PIXELS:
            raise ValueError("Image exceeds the bounded decoded-pixel inspection limit")
        frames = getattr(original, "n_frames", 1)
        if frame >= frames:
            raise ValueError("Requested image frame does not exist")
        original.seek(frame)
        metadata = {"original_dimensions": list(dimensions), "original_sha256": hashlib.sha256(raw).hexdigest(),
                    "frame": frame, "frame_count": frames, "source_bytes_unchanged": True}
        if region is not None:
            if (not isinstance(region, list) or len(region) != 4 or any(type(value) is not int for value in region)
                    or not 0 <= region[0] < region[2] <= dimensions[0]
                    or not 0 <= region[1] < region[3] <= dimensions[1]):
                raise ValueError("Image region must be [left, top, right, bottom] within original pixel bounds")
            rendered = original.crop(tuple(region))
            metadata.update(region=region, view_kind="crop")
        elif frame == 0 and max(dimensions) <= MAX_DIMENSION and len(raw) <= MAX_BYTES:
            return raw, mime, {**metadata, "rendered_dimensions": list(dimensions), "view_kind": "original"}
        else:
            rendered = original.copy()
            metadata["view_kind"] = "frame" if frame else "preview"
        rendered.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
        if rendered.mode not in {"RGB", "RGBA", "L", "LA", "P"}:
            rendered = rendered.convert("RGBA")
        while True:
            stream = io.BytesIO()
            rendered.save(stream, format="PNG")
            content = stream.getvalue()
            if len(content) <= MAX_BYTES:
                break
            if max(rendered.size) <= 1:
                raise ValueError("Image view cannot fit the provider inspection limit")
            rendered.thumbnail((max(1, int(rendered.width * .8)), max(1, int(rendered.height * .8))),
                               Image.Resampling.LANCZOS)
        metadata.update(rendered_dimensions=list(rendered.size), rendered_sha256=hashlib.sha256(content).hexdigest(),
                        detail_note="This is an inspection view, not recovered source bytes. Request an original-pixel region or frame to inspect details.")
        return content, "image/png", metadata
