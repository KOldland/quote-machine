#!/usr/bin/env python3
"""
Script to generate template coordinate variants for image layouts.
Generates multiple layout permutations for given image counts and orientations.
"""

# A4 dimensions at 300dpi
PAGE_WIDTH = 2480
PAGE_HEIGHT = 3508
MARGIN = 100

def generate_grid_layout(num_images, cols, rows, landscape_ratio=0.5):
    """Generate a grid layout with given columns and rows."""
    cell_width = (PAGE_WIDTH - 2 * MARGIN) / cols
    cell_height = (PAGE_HEIGHT - 2 * MARGIN) / rows
    
    coords = []
    for row in range(rows):
        for col in range(cols):
            x = MARGIN + col * cell_width
            y = MARGIN + row * cell_height
            # Alternate landscape/portrait based on ratio
            if (row + col) % 2 == 0:
                w = cell_width * landscape_ratio
                h = cell_height
            else:
                w = cell_width
                h = cell_height * landscape_ratio
            coords.append((int(x), int(y), int(w), int(h)))
    
    return coords[:num_images]

def generate_vertical_stack(num_images, landscape_count):
    """Generate vertical stack layout."""
    coords = []
    y_offset = MARGIN
    
    for i in range(num_images):
        if i < landscape_count:
            # Landscape
            h = (PAGE_HEIGHT - 2 * MARGIN) / num_images * 0.6
        else:
            # Portrait
            h = (PAGE_HEIGHT - 2 * MARGIN) / num_images * 1.2
        
        coords.append((MARGIN, int(y_offset), PAGE_WIDTH - 2 * MARGIN, int(h)))
        y_offset += h + 20
    
    return coords

def generate_horizontal_row(num_images, landscape_count):
    """Generate horizontal row layout."""
    coords = []
    x_offset = MARGIN
    
    for i in range(num_images):
        if i < landscape_count:
            # Landscape
            w = (PAGE_WIDTH - 2 * MARGIN) / num_images * 1.2
        else:
            # Portrait
            w = (PAGE_WIDTH - 2 * MARGIN) / num_images * 0.6
        
        coords.append((int(x_offset), MARGIN, int(w), PAGE_HEIGHT - 2 * MARGIN))
        x_offset += w + 20
    
    return coords

def generate_mixed_layout(num_images, landscape_count):
    """Generate mixed layout with different sized blocks."""
    coords = []
    
    if num_images == 2:
        # One large, one small
        coords.append((MARGIN, MARGIN, PAGE_WIDTH - 2 * MARGIN, PAGE_HEIGHT * 0.6))
        coords.append((MARGIN, MARGIN + PAGE_HEIGHT * 0.65, PAGE_WIDTH - 2 * MARGIN, PAGE_HEIGHT * 0.3))
    elif num_images == 3:
        # One full-width top, two bottom
        coords.append((MARGIN, MARGIN, PAGE_WIDTH - 2 * MARGIN, PAGE_HEIGHT * 0.4))
        coords.append((MARGIN, MARGIN + PAGE_HEIGHT * 0.45, PAGE_WIDTH * 0.48, PAGE_HEIGHT * 0.5))
        coords.append((MARGIN + PAGE_WIDTH * 0.52, MARGIN + PAGE_HEIGHT * 0.45, PAGE_WIDTH * 0.48, PAGE_HEIGHT * 0.5))
    
    return coords

def generate_all_variants():
    """Generate all template variants systematically."""
    variants = {}
    
    # Generate for 2-10 images
    for total in range(2, 11):
        for landscape in range(total + 1):
            portrait = total - landscape
            base_key = f"template_{total}-{landscape}L{portrait}P"
            
            # Generate grid variants
            if total <= 10:
                rows = (total + 1) // 2
                cols = 2
                coords = generate_grid_layout(total, cols, rows)
                variants[f"{base_key}_grid"] = coords
            
            # Generate vertical stack
            coords = generate_vertical_stack(total, landscape)
            variants[f"{base_key}_stack"] = coords
            
            # Generate horizontal row
            coords = generate_horizontal_row(total, landscape)
            variants[f"{base_key}_row"] = coords
            
            # Generate mixed layout
            if total <= 6:
                coords = generate_mixed_layout(total, landscape)
                if coords:
                    variants[f"{base_key}_mixed"] = coords
    
    return variants

def main():
    print("Generating template variants...")
    
    all_variants = generate_all_variants()
    
    print(f"\nGenerated {len(all_variants)} template variants")
    print("\nSample variants:")
    for key in list(sorted(all_variants.keys()))[:10]:
        print(f"  {key}: {len(all_variants[key])} blocks")
    
    # Output as Python code
    print("\n\n# Add to TEMPLATE_COORDINATES:")
    for key, coords in sorted(all_variants.items()):
        coord_str = ", ".join([f"({x}, {y}, {w}, {h})" for x, y, w, h in coords])
        print(f'    "{key}": [{coord_str}],')

if __name__ == "__main__":
    main()
