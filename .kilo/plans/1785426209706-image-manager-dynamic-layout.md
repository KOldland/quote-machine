# Image Manager Dynamic Layout Engine Implementation Plan

## Overview
Replace the predefined template-based image layout system with a dynamic constraint-based layout engine using Gridstack.js. This will eliminate the need for 320+ static configurations and allow users to freely arrange images with automatic reflow and resizing capabilities.

## Core Requirements
1. Implement a 6-unit grid system (canvas width = 6 units)
2. Define standardized image units:
   - Portrait (P): 2×3 units
   - Landscape (L): 3×2 units
3. Implement row/column bin-packing algorithm
4. Enable dynamic row filling and height normalization
5. Add manual resize handles for images
6. Implement auto-reflow when items are moved/swapped
7. Use Gridstack.js for the drag-and-drop grid layout

## Changes Required

### 1. Frontend Modifications (app/templates/image_upload.html)

#### Remove Existing Template System
- Remove template selection UI (accordion, carousel, template buttons)
- Remove template coordination logic from JavaScript
- Remove drag-overlay system for template-based dragging

#### Add Gridstack.js Implementation
- Include Gridstack.js and CSS via CDN:
  ```html
  <link href="https://unpkg.com/gridstack@latest/dist/gridstack.min.css" rel="stylesheet">
  <script src="https://unpkg.com/gridstack@latest/dist/gridstack.all.min.js"></script>
  ```
- Initialize Gridstack with 6-column grid:
  ```javascript
  const grid = GridStack.init({
    column: 6,
    float: true,
    disableDrag: false,
    disableResize: false,
    margin: 10,
    cellHeight: 80, // Will be calculated based on aspect ratio
    animate: true
  });
  ```

#### Image Upload Handling
- When site images are uploaded, analyze them to determine orientation
- Create Gridstack widgets for each image:
  - Portrait images: width=2, height=3 units
  - Landscape images: width=3, height=2 units
- Add images to grid in sequential order

#### Drag and Drop Functionality
- Use Gridstack's built-in drag-and-drop for reordering
- Implement auto-reflow on position change:
  ```javascript
  grid.on('change', function(event, items) {
    // Recalculate rows and normalize heights
    reflowLayout();
  });
  ```

#### Resize Handles
- Enable Gridstack's resize functionality
- Constrain resizing to maintain aspect ratios:
  - Portrait images can only scale in multiples of (2w, 3h)
  - Landscape images can only scale in multiples of (3w, 2h)
  - Implement snap-to-grid for clean resizing

#### Layout Persistence
- Add save button to capture current layout state
- Serialize grid layout to send to backend:
  ```javascript
  const layoutData = grid.save();
  // Format: [{x, y, width, height, id}, ...]
  ```

### 2. Backend Modifications (app/QMapp.py)

#### Image Analysis Endpoint
- Modify `/image_upload_page` to return image metadata instead of template coordinates:
  ```javascript
  // Return array of images with their properties
  [{
    id: 'img_site_1.jpg',
    url: '/static/uploads/project/img_site_1.jpg',
    width: 1200, // actual pixels
    height: 1800, // actual pixels
    aspectRatio: 0.667, // width/height
    orientation: 'portrait' // or 'landscape'
  }]
  ```

#### Layout Data Endpoint
- Add new endpoint to receive layout data:
  ```python
  @app.route('/save_layout', methods=['POST'])
  def save_layout():
      layout_data = request.get_json()
      # Store in session for later use
      session['image_layout'] = layout_data
      return jsonify({'success': True})
  ```

#### Image Composition Update
- Modify `compose_template()` function to accept layout data:
  ```python
  def compose_dynamic_layout(image_layout, upload_folder, output_basename='final_output'):
      # image_layout: [{'filename': 'img_site_1.jpg', 'x': 0, 'y': 0, 'width': 2, 'height': 3}, ...]
      # Convert grid units to pixels:
      # Canvas width = 2480px = 6 units
      # 1 unit = 2480/6 = 413.33px
      # Then position and size each image accordingly
  ```

#### Template Selection Removal
- Remove template-based logic from `image_upload_page()`:
  - Remove TEMPLATE_COORDINATES usage
  - Remove template selection handling
  - Remove compose_template calls with fixed templates
  - Add layout-based composition

### 3. Image Processing Updates

#### Unit Conversion
- Define canvas constants:
  ```python
  CANVAS_WIDTH_UNITS = 6
  CANVAS_WIDTH_PIXELS = 2480  # A4 @ 300dpi
  CANVAS_HEIGHT_PIXELS = 3508
  UNIT_PIXELS = CANVAS_WIDTH_PIXELS / CANVAS_WIDTH_UNITS  # ~413.33px
  ```
- Convert grid positions to pixels:
  ```python
  pixel_x = grid_x * UNIT_PIXELS
  pixel_y = grid_y * UNIT_PIXELS  # Y will need adjustment for aspect ratios
  pixel_width = grid_width * UNIT_PIXELS
  pixel_height = grid_height * UNIT_PIXELS
  ```

#### Aspect Ratio Preservation
- When placing indeterminate-sized images (those that don't fill a row completely):
  - Calculate required height based on aspect ratio
  - Adjust row height to accommodate tallest image
  - Scale all images in row to match row height while preserving aspect ratio

#### Row Layout Algorithm
1. Sort images by position (y, then x)
2. Group items into rows based on y position
3. For each row:
   - Calculate total width used
   - If < 6 units, distribute remaining space or scale items
   - Normalize heights of all items in row to match tallest
   - Ensure aspect ratios are maintained during scaling

## Implementation Phases

### Phase 1: Frontend Grid Implementation
1. Add Gridstack.js dependencies to image_upload.html
2. Remove template selection UI
3. Implement basic grid with image widgets
4. Add drag-and-drop functionality
5. Implement basic save/load layout

### Phase 2: Layout Intelligence
1. Add image orientation detection on upload
2. Implement proper sizing based on portrait/landscape units
3. Add constraint-based resizing (maintain aspect ratios)
4. Implement row calculation and height normalization
5. Add auto-reflow on item movement

### Phase 3: Backend Integration
1. Modify image upload to send metadata
2. Create layout save endpoint
3. Update image composition to use dynamic layout
4. Remove template-based code paths
5. Test end-to-end flow

### Phase 4: Refinement
1. Add visual feedback for grid snapping
2. Implement undo/redo functionality
3. Add layout presets (optional)
4. Optimize performance for large image sets
5. Add touch support for mobile devices

## Files to Modify
1. `app/templates/image_upload.html` - Frontend UI and logic
2. `app/QMapp.py` - Backend endpoints and image processing
3. `app/static/css/image_upload.css` (new) - Styling for grid layout
4. `app/static/js/image_upload.js` (new) - Gridstack implementation

## Dependencies to Add
- Gridstack.js (CSS and JS via CDN)
- No additional Python dependencies required

## Validation Criteria
1. Users can upload images of mixed orientations
2. Images automatically snap to 6-unit grid
3. Images maintain aspect ratios during manual resize
4. Rows automatically reflow when images are moved
5. Row heights normalize to match tallest image while preserving aspect ratios
6. Final composed image matches the on-screen layout exactly
7. Layout can be saved and restored
8. Performance remains acceptable with 10+ images

## Risks and Mitigations
- **Performance with many images**: Use virtualization or pagination if needed
- **Browser compatibility**: Gridstack.js supports modern browsers
- **Complex layout calculations**: Break down into smaller functions, test thoroughly
- **Maintaining aspect ratios during resize**: Use constraint callbacks in Gridstack