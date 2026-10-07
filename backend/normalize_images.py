"""Normalize the product photos for consistent display.

The source images in `data/products/` are inconsistent in two ways: there are 60
distinct pixel sizes, and 73 of the 102 photos are letterboxed with black
padding while the rest sit on white. In a grid that reads as black boxes next to
white ones.

This script writes a cleaned copy of each photo to `data/products_web/`:

1. crop away the uniform near-black padding (it is padding, not the backdrop),
2. crop away any uniform near-white border as well, so every product is bounded
   the same way,
3. flood the black studio backdrop with white where one is present,
4. centre the result on a square white canvas with a fixed margin,
5. resize every canvas to the same dimensions.

The product itself is never stretched — aspect ratio is preserved throughout, so
nothing is distorted. The originals are left untouched, and `catalogue
.image_file_path` in the database stays the source of truth; the backend simply
prefers the normalized copy when one exists.

Run from the backend folder:  python normalize_images.py
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
SOURCE_DIR = BASE_DIR / "data" / "products"
OUTPUT_DIR = BASE_DIR / "data" / "products_web"

CANVAS = 900          # Every output is CANVAS x CANVAS.
MARGIN = 0.06         # Share of the canvas left as white space on each side.
DARK_MAX = 45         # A pixel this dark counts as letterbox padding.
LIGHT_MIN = 244       # A pixel this light counts as blank background.
WHITE = (255, 255, 255)

# Some photos are shot on a true black backdrop rather than merely padded. The
# backdrop is essentially pure black while the darkest navy fabric still reads
# around 19, so the cut-off sits just below that — and the fill only spreads
# inward from the edges, so it cannot punch a hole in the middle of a garment.
BACKDROP_MAX = 14
# If a fill would swallow most of the frame, the picture was not a dark backdrop
# after all; discard the attempt rather than wreck the photo.
MAX_FILL_SHARE = 0.80
# Black backdrops leave a soft anti-aliased halo where they meet the garment.
# These pixels are brighter than BACKDROP_MAX so the strict fill misses them,
# and they show up as a dark fringe once the backdrop turns white. Clearing a
# shallow band removes it on light garments. A navy garment photographed on
# black cannot be separated this way — its fabric is as dark as the halo — so a
# faint edge remains on that small group of photos.
HALO_MAX = 120
HALO_DEPTH = 3


def _row_is(image: Image.Image, y: int, predicate) -> bool:
    width = image.width
    step = max(1, width // 160)  # Sampling is plenty for a uniform border.
    return all(predicate(image.getpixel((x, y))) for x in range(0, width, step))


def _col_is(image: Image.Image, x: int, predicate) -> bool:
    height = image.height
    step = max(1, height // 160)
    return all(predicate(image.getpixel((x, y))) for y in range(0, height, step))


def _trim(image: Image.Image, predicate) -> Image.Image:
    """Remove edge rows and columns where every sampled pixel matches."""
    left, right = 0, image.width - 1
    top, bottom = 0, image.height - 1

    while top < bottom and _row_is(image, top, predicate):
        top += 1
    while bottom > top and _row_is(image, bottom, predicate):
        bottom -= 1
    while left < right and _col_is(image, left, predicate):
        left += 1
    while right > left and _col_is(image, right, predicate):
        right -= 1

    if right - left < 10 or bottom - top < 10:
        return image  # Refuse to trim away the whole picture.
    return image.crop((left, top, right + 1, bottom + 1))


def _whiten_backdrop(image: Image.Image) -> Image.Image:
    """Flood the black studio backdrop with white, starting from the edges.

    Conservative on purpose: it only spreads through pixels darker than
    BACKDROP_MAX and only from the border inward, so garment shadows that are
    enclosed by fabric are never touched. If the fill runs away, the original is
    returned unchanged.
    """
    width, height = image.size
    pixels = image.load()

    seeds = [(x, y) for x in range(width) for y in (0, height - 1)]
    seeds += [(x, y) for y in range(height) for x in (0, width - 1)]
    seeds = [(x, y) for x, y in seeds if max(pixels[x, y]) <= BACKDROP_MAX]
    if not seeds:
        return image

    filled = set(seeds)
    queue = deque(seeds)
    limit = int(width * height * MAX_FILL_SHARE)

    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in filled:
                if max(pixels[nx, ny]) <= BACKDROP_MAX:
                    filled.add((nx, ny))
                    queue.append((nx, ny))
        if len(filled) > limit:
            return image  # Not a backdrop — leave the photo alone.

    for x, y in filled:
        pixels[x, y] = WHITE

    # Walk a short distance inward from the cleared area, whitening the
    # leftover anti-aliased fringe.
    frontier = set(filled)
    for _ in range(HALO_DEPTH):
        nxt = set()
        for x, y in frontier:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in filled:
                    if max(pixels[nx, ny]) <= HALO_MAX:
                        filled.add((nx, ny))
                        nxt.add((nx, ny))
        if not nxt:
            break
        for x, y in nxt:
            pixels[x, y] = WHITE
        frontier = nxt

    return image


def normalize(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGB")
    image = _trim(image, lambda p: max(p) <= DARK_MAX)     # letterbox padding
    image = _whiten_backdrop(image)                        # black studio backdrop
    image = _trim(image, lambda p: min(p) >= LIGHT_MIN)    # blank white border

    # Scale the product to fit inside the canvas minus its margin, keeping the
    # original aspect ratio so nothing is stretched.
    inner = int(CANVAS * (1 - 2 * MARGIN))
    scale = min(inner / image.width, inner / image.height)
    new_size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    image = image.resize(new_size, Image.LANCZOS)

    canvas = Image.new("RGB", (CANVAS, CANVAS), WHITE)
    canvas.paste(image, ((CANVAS - new_size[0]) // 2, (CANVAS - new_size[1]) // 2))
    return canvas


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sources = sorted(SOURCE_DIR.glob("*.jpg"))

    for path in sources:
        normalize(path).save(OUTPUT_DIR / path.name, "JPEG", quality=88, optimize=True)

    print(f"Normalized {len(sources)} images -> {OUTPUT_DIR.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
