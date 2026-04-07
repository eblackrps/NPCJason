"""
generate_icon.py - Creates npcjason.ico from pixel art.
Produces a proper multi-resolution ICO file (16, 32, 48, 64, 256px).
Run this before building with PyInstaller.
"""

from PIL import Image, ImageDraw


def make_npcjason_image(size: int) -> Image.Image:
    """Draw the NPCJason pixel art face scaled to the given square size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # All coordinates are defined for a 64x64 canvas, then scaled.
    s = size / 64.0

    def r(x1, y1, x2, y2, fill, outline=None, width=1):
        coords = [x1 * s, y1 * s, x2 * s, y2 * s]
        if outline:
            draw.rectangle(coords, fill=fill, outline=outline, width=max(1, int(width * s)))
        else:
            draw.rectangle(coords, fill=fill)

    # Hair
    r(14, 4, 50, 16, "#4a3728", "#1a1a2e", 1)
    # Head / skin
    r(16, 8, 48, 40, "#e8c170", "#1a1a2e", 2)
    # Eyes
    r(22, 20, 28, 26, "#16213e")
    r(36, 20, 42, 26, "#16213e")
    # Eye whites (small highlight)
    r(23, 21, 25, 23, "#ffffff")
    r(37, 21, 39, 23, "#ffffff")
    # Mouth / smile
    r(26, 30, 38, 35, "#c84b31")
    # Body / shirt
    r(20, 40, 44, 56, "#3a86c8", "#1a1a2e", 1)
    # Legs / pants
    r(22, 56, 30, 64, "#2d4263")
    r(34, 56, 42, 64, "#2d4263")

    return img


def generate_ico(output_path: str = "npcjason.ico"):
    sizes = [16, 32, 48, 64, 256]
    images = [make_npcjason_image(s) for s in sizes]

    # Save as proper multi-resolution ICO.
    # Pillow uses the first image as the base; sizes kwarg embeds all resolutions.
    images[0].save(
        output_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )
    print(f"Icon saved: {output_path}  ({', '.join(str(s) for s in sizes)}px)")


if __name__ == "__main__":
    generate_ico()
