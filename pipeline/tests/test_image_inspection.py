import hashlib
import io
import unittest
from unittest.mock import patch

from PIL import Image
from pipeline.dump.images import inspection_view


class ImageInspectionTests(unittest.TestCase):
    def image_bytes(self, image, **options):
        stream = io.BytesIO()
        image.save(stream, **options)
        return stream.getvalue()

    def test_small_native_image_keeps_its_exact_source_bytes(self):
        raw = self.image_bytes(Image.new("RGB", (40, 20), "blue"), format="PNG")
        viewed, mime, metadata = inspection_view(raw, "image/png")
        self.assertEqual(viewed, raw)
        self.assertEqual(mime, "image/png")
        self.assertEqual(metadata["view_kind"], "original")
        self.assertEqual(metadata["original_sha256"], hashlib.sha256(raw).hexdigest())

    def test_oversized_image_has_a_labelled_preview_and_lossless_detail_access(self):
        image = Image.new("RGB", (80, 9000), "white")
        image.putpixel((5, 8500), (12, 34, 56))
        raw = self.image_bytes(image, format="PNG")
        preview, mime, metadata = inspection_view(raw, "image/png")
        self.assertLessEqual(max(metadata["rendered_dimensions"]), 8000)
        self.assertEqual(metadata["original_dimensions"], [80, 9000])
        self.assertEqual(metadata["view_kind"], "preview")
        self.assertTrue(metadata["source_bytes_unchanged"])
        detail, _, crop = inspection_view(raw, "image/png", [0, 8400, 20, 8600])
        with Image.open(io.BytesIO(detail)) as viewed:
            self.assertEqual(viewed.getpixel((5, 100)), (12, 34, 56))
        self.assertEqual(crop["rendered_dimensions"], [20, 200])
        self.assertEqual(crop["original_sha256"], metadata["original_sha256"])

    def test_invalid_crop_or_frame_cannot_relabel_unseen_evidence(self):
        raw = self.image_bytes(Image.new("RGB", (10, 10)), format="PNG")
        for region in ([0, 0, 11, 10], [0, 0, 0, 10], [False, 0, 5, 5], [0, 0, 5]):
            with self.assertRaisesRegex(ValueError, "original pixel bounds"):
                inspection_view(raw, "image/png", region)
        for frame in (True, -1, 1):
            with self.assertRaises(ValueError):
                inspection_view(raw, "image/png", frame=frame)

    def test_animation_frames_remain_individually_inspectable(self):
        raw = self.image_bytes(Image.new("RGB", (10, 10), "red"), format="GIF", save_all=True,
                               append_images=[Image.new("RGB", (10, 10), "blue")])
        frame, mime, metadata = inspection_view(raw, "image/gif", frame=1)
        self.assertEqual(metadata["frame_count"], 2)
        self.assertEqual(metadata["frame"], 1)
        with Image.open(io.BytesIO(frame)) as viewed:
            self.assertEqual(viewed.convert("RGB").getpixel((0, 0)), (0, 0, 255))

    def test_byte_budget_is_bounded_without_rewriting_original_evidence(self):
        image = Image.new("RGB", (40, 40))
        image.putdata([(index % 256, index * 7 % 256, index * 17 % 256) for index in range(1600)])
        raw = self.image_bytes(image, format="PNG")
        with patch("pipeline.dump.images.MAX_BYTES", 100):
            viewed, _, metadata = inspection_view(raw, "image/png")
        self.assertLessEqual(len(viewed), 100)
        self.assertEqual(metadata["original_sha256"], hashlib.sha256(raw).hexdigest())


if __name__ == "__main__":
    unittest.main()
