"""Cut the white background out of the product photos for the hero.

The catalogue photos are flat-lays on white. On the navy hero that reads as a
white box pasted onto the band. Making the background transparent lets the
garment sit directly on the navy, the way a cut-out lifestyle shot would.

The fill only spreads inward from the border through near-white pixels, so a
white graphic enclosed by fabric (a YALE wordmark, a crest) is never touched —
it is not connected to the edge. If the fill would consume most of the frame the
attempt is discarded and that product simply keeps its white photo.

Run from the backend folder:  python make_hero_cutouts.py
"""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
# Cut from the ORIGINAL photos, not the normalized copies. The normalizer
# already repainted some backdrops white, and cutting that result a second time
# leaves a ragged fringe of leftover anti-aliased pixels around the garment.
SOURCE_DIR = BASE_DIR / "data" / "products"
OUTPUT_DIR = BASE_DIR / "data" / "products_hero"

# The lightest garment (heather gray) sits around 210 and the darkest navy
# around 19, so these cut-offs clear background without biting into fabric.
WHITE_MIN = 236
DARK_MAX = 30
MAX_FILL_SHARE = 0.94
# Pixels this close to the boundary get partial alpha, which softens the edge
# instead of leaving a hard jagged outline against the navy.
FEATHER = 1


def _flood_clear(image: Image.Image, is_background) -> int:
    """Clear background pixels reachable from the border. Returns how many."""
    width, height = image.size
    pixels = image.load()

    seeds = [(x, y) for x in range(width) for y in (0, height - 1) if is_background(x, y)]
    seeds += [(x, y) for y in range(height) for x in (0, width - 1) if is_background(x, y)]
    if not seeds:
        return 0

    filled = set(seeds)
    queue = deque(seeds)
    limit = int(width * height * MAX_FILL_SHARE)

    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in filled:
                if is_background(nx, ny):
                    filled.add((nx, ny))
                    queue.append((nx, ny))
        if len(filled) > limit:
            return 0  # Ran away — treat as "not a background" and change nothing.

    for x, y in filled:
        pixels[x, y] = (255, 255, 255, 0)

    # Soften the boundary so the silhouette blends into the navy.
    if FEATHER:
        for x, y in filled:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in filled:
                    r, g, b, a = pixels[nx, ny]
                    if a == 255:
                        pixels[nx, ny] = (r, g, b, 128)

    return len(filled)


def cut_out(path: Path) -> Image.Image | None:
    """Remove the photo background, leaving just the garment.

    Two passes, because the catalogue mixes two kinds of photo and some have
    both: black letterbox padding on the outside and a white studio background
    inside it. Clearing only one leaves a visible box around the garment.
    """
    image = Image.open(path).convert("RGBA")
    pixels = image.load()

    def transparent(x: int, y: int) -> bool:
        return pixels[x, y][3] == 0

    def is_dark(x: int, y: int) -> bool:
        return transparent(x, y) or max(pixels[x, y][:3]) <= DARK_MAX

    def is_white(x: int, y: int) -> bool:
        return transparent(x, y) or min(pixels[x, y][:3]) >= WHITE_MIN

    cleared = _flood_clear(image, is_dark)      # letterbox bars
    cleared += _flood_clear(image, is_white)    # studio background

    if cleared == 0:
        return None

    bbox = image.getbbox()
    return image.crop(bbox) if bbox else image


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    made = skipped = 0

    for path in sorted(SOURCE_DIR.glob("*.jpg")):
        result = cut_out(path)
        if result is None:
            skipped += 1
            continue
        result.save(OUTPUT_DIR / f"{path.stem}.png", "PNG", optimize=True)
        made += 1

    print(f"Cut out {made} photos -> {OUTPUT_DIR.relative_to(BASE_DIR)} ({skipped} skipped)")


if __name__ == "__main__":
    main()
