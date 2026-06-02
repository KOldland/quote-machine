import matplotlib.pyplot as plt
from PIL import Image, ImageDraw
from templates import TEMPLATE_COORDINATES
    
# Constants
PAGE_WIDTH, PAGE_HEIGHT = 2480, 3508  # A4 @ 300 DPI
OUTPUT_DIR = './static/template_previews'
OFFSET = 3
DASH_WIDTH = 4

def draw_template(template_name):
    blocks = TEMPLATE_COORDINATES.get(template_name)
    if not blocks:
        print(f"No template found named: {template_name}")
        return

    img = Image.new('RGB', (PAGE_WIDTH, PAGE_HEIGHT), 'white')
    draw = ImageDraw.Draw(img)

    for i in range(0, PAGE_WIDTH, 20):
        draw.line([(i, OFFSET), (i + 10, OFFSET)], fill="red", width=DASH_WIDTH)
        draw.line([(i, PAGE_HEIGHT - OFFSET), (i + 10, PAGE_HEIGHT - OFFSET)], fill="red", width=DASH_WIDTH)
    for i in range(0, PAGE_HEIGHT, 20):
        draw.line([(OFFSET, i), (OFFSET, i + 10)], fill="red", width=DASH_WIDTH)
        draw.line([(PAGE_WIDTH - OFFSET, i), (PAGE_WIDTH - OFFSET, i + 10)], fill="red", width=DASH_WIDTH)

    for x, y, w, h in blocks:
        draw.rectangle([x, y, x + w, y + h], outline='black', width=5)

    plt.figure(figsize=(10, 14))
    plt.imshow(img)
    plt.axis('off')
    plt.title(template_name)
    plt.tight_layout()
    plt.show()

    output_path = f"{OUTPUT_DIR}/{template_name}.jpg"
    img.save(output_path)
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    while True:
        name = input("Template name (or 'exit' to quit): ").strip()
        if name.lower() == 'exit':
            break
        draw_template(name)
        