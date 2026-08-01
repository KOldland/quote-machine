#!/usr/bin/env python3
"""
Generate comprehensive template variants that respect image orientations.
Landscape images: width > height (aspect ratio ~1.4:1 to 2:1)
Portrait images: height > width (aspect ratio ~1:1.4 to 1:2)
"""

# A4 dimensions at 300dpi
PAGE_WIDTH = 2480
PAGE_HEIGHT = 3508
MARGIN = 100
GAP = 20

def create_proper_templates():
    """Create templates that respect landscape/portrait orientations."""
    templates = {}
    
    # Template patterns for different image counts
    # Each pattern is defined by the relative positions and sizes
    
    # 2 images
    # 2L0P - two landscape
    templates["template_2-2L0P_varA"] = [
        (MARGIN, MARGIN, PAGE_WIDTH - 2*MARGIN, 800),
        (MARGIN, MARGIN + 800 + GAP, PAGE_WIDTH - 2*MARGIN, 800)
    ]
    templates["template_2-2L0P_varB"] = [
        (MARGIN, MARGIN, PAGE_WIDTH - 2*MARGIN, 1200),
        (MARGIN, MARGIN + 1200 + GAP, PAGE_WIDTH - 2*MARGIN, 1200)
    ]
    
    # 1L1P - one landscape, one portrait
    templates["template_2-1L1P_varE"] = [
        (MARGIN, MARGIN, PAGE_WIDTH - 2*MARGIN, 1000),  # Full-width landscape top
        (MARGIN, MARGIN + 1000 + GAP, 900, PAGE_HEIGHT - MARGIN - 1000 - GAP)  # Portrait bottom
    ]
    templates["template_2-1L1P_varF"] = [
        (MARGIN, MARGIN, 900, PAGE_HEIGHT - 2*MARGIN),  # Portrait left
        (MARGIN + 900 + GAP, MARGIN, PAGE_WIDTH - MARGIN - 900 - GAP, 1000)  # Landscape right
    ]
    
    # 3 images - 2L1P
    templates["template_3-2L1P_varE"] = [
        (MARGIN, MARGIN, (PAGE_WIDTH - 2*MARGIN - GAP) / 2, 800),  # L top-left
        (MARGIN, MARGIN + 800 + GAP, (PAGE_WIDTH - 2*MARGIN - GAP) / 2, 800),  # L bottom-left
        (MARGIN + (PAGE_WIDTH - 2*MARGIN - GAP) / 2 + GAP, MARGIN, (PAGE_WIDTH - 2*MARGIN - GAP) / 2, PAGE_HEIGHT - 2*MARGIN)  # P right
    ]
    
    # 3 images - 1L2P
    templates["template_3-1L2P_varG"] = [
        (MARGIN, MARGIN, PAGE_WIDTH - 2*MARGIN, 800),  # L top
        (MARGIN, MARGIN + 800 + GAP, (PAGE_WIDTH - 2*MARGIN - GAP) / 2, PAGE_HEIGHT - MARGIN - 800 - GAP),  # P bottom-left
        (MARGIN + (PAGE_WIDTH - 2*MARGIN - GAP) / 2 + GAP, MARGIN + 800 + GAP, (PAGE_WIDTH - 2*MARGIN - GAP) / 2, PAGE_HEIGHT - MARGIN - 800 - GAP)  # P bottom-right
    ]
    
    return templates

if __name__ == "__main__":
    templates = create_proper_templates()
    print(f"Generated {len(templates)} proper templates")
    print("\nAdd these to TEMPLATE_COORDINATES:")
    for key, coords in sorted(templates.items()):
        coord_str = ", ".join([f"({x}, {y}, {w}, {h})" for x, y, w, h in coords])
        print(f'    "{key}": [{coord_str}],')
