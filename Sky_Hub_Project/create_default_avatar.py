"""
create_default_avatar.py
Run once: python create_default_avatar.py
Creates static/uploads/profile_pics/default_profile.png
"""
import os
import sys

TARGET = os.path.join(
    os.path.dirname(__file__),
    "static", "uploads", "profile_pics", "default_profile.png"
)

def make_with_pillow():
    from PIL import Image, ImageDraw
    size = 200
    img = Image.new("RGB", (size, size), color="#e8edf5")
    draw = ImageDraw.Draw(img)

    # Head circle
    head_r = 42
    cx = size // 2
    draw.ellipse(
        [cx - head_r, 55, cx + head_r, 55 + head_r * 2],
        fill="#a0aec0"
    )
    # Body/shoulders arc
    body_r = 75
    draw.ellipse(
        [cx - body_r, size - 40, cx + body_r, size + body_r],
        fill="#a0aec0"
    )
    img.save(TARGET, "PNG")
    print(f"✅  Created: {TARGET}")

def make_with_svg_fallback():
    """Write a minimal SVG that browsers can display (rename to .svg if needed)."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">
  <rect width="200" height="200" rx="100" fill="#e8edf5"/>
  <circle cx="100" cy="80" r="40" fill="#a0aec0"/>
  <ellipse cx="100" cy="200" rx="70" ry="55" fill="#a0aec0"/>
</svg>"""
    svg_path = TARGET.replace(".png", ".svg")
    with open(svg_path, "w") as f:
        f.write(svg)
    print(f"⚠️  PIL not available — SVG fallback created: {svg_path}")
    print("    Rename or convert it to PNG, or install Pillow: pip install Pillow")

if __name__ == "__main__":
    os.makedirs(os.path.dirname(TARGET), exist_ok=True)
    try:
        make_with_pillow()
    except ImportError:
        make_with_svg_fallback()
