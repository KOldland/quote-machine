import os
from PIL import Image, ImageDraw, ImageFont
from templates import TEMPLATE_COORDINATES  # ensure this is accessible

# Settings
canvas_width = 2480
canvas_height = 3508
output_dir = os.path.join("static", "layout_templates")

os.makedirs(output_dir, exist_ok=True)

def generate_preview(template_key, blocks):
    img = Image.new("RGB", (canvas_width, canvas_height), "white")
    draw = ImageDraw.Draw(img)

    # Draw each block
    for (x, y, w, h) in blocks:
        draw.rectangle([x, y, x + w, y + h], outline="black", width=5)

    # Add template label
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except IOError:
        font = ImageFont.load_default()

    draw.text((100, 50), template_key, fill="black", font=font)

    # Save image
    output_path = os.path.join(output_dir, f"{template_key}.jpg")
    img.save(output_path, "JPEG")
    print(f"[OK] Saved: {output_path}")

# Generate previews for all templates
for template_key, coords in TEMPLATE_COORDINATES.items():
    generate_preview(template_key, coords)

print(f"\n All previews generated in: {output_dir}")
