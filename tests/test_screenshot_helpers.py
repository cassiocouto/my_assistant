import io
import unittest

from PIL import Image


class TestScreenshotHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from screenshot import _images_are_visually_unchanged, _trim_chunk_overlap

        cls.Image = Image
        cls.images_are_visually_unchanged = staticmethod(_images_are_visually_unchanged)
        cls.trim_chunk_overlap = staticmethod(_trim_chunk_overlap)

    def _png_bytes(self, width: int, height: int, color: tuple[int, int, int]) -> bytes:
        img = self.Image.new("RGB", (width, height), color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def test_images_are_visually_unchanged_for_identical_png(self):
        a = self._png_bytes(120, 120, (10, 20, 30))
        b = self._png_bytes(120, 120, (10, 20, 30))
        self.assertTrue(self.images_are_visually_unchanged(a, b))

    def test_images_are_visually_unchanged_false_when_clearly_different(self):
        a = self._png_bytes(120, 120, (0, 0, 0))
        b = self._png_bytes(120, 120, (255, 255, 255))
        self.assertFalse(self.images_are_visually_unchanged(a, b))

    def test_trim_chunk_overlap_crops_only_subsequent_chunks(self):
        first = self._png_bytes(100, 300, (255, 0, 0))
        second = self._png_bytes(100, 300, (0, 255, 0))

        trimmed = self.trim_chunk_overlap([first, second], overlap=60, sticky_header_crop=40)
        self.assertEqual(len(trimmed), 2)

        first_img = self.Image.open(io.BytesIO(trimmed[0]))
        second_img = self.Image.open(io.BytesIO(trimmed[1]))
        self.assertEqual(first_img.size, (100, 300))
        self.assertEqual(second_img.size, (100, 300))

    def test_trim_chunk_overlap_skips_overcropped_chunk(self):
        first = self._png_bytes(100, 200, (255, 0, 0))
        second = self._png_bytes(100, 80, (0, 255, 0))

        trimmed = self.trim_chunk_overlap([first, second], overlap=60, sticky_header_crop=40)
        self.assertEqual(len(trimmed), 2)


if __name__ == "__main__":
    unittest.main()
