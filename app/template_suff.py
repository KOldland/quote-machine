def get_layout_definition(template_key):
	layout_map = {
		'template_1p': [
			(0, 0, 2480, 3508) #Full size portrait
		],
		'template_1l': [
			(0, 0, 2480, 3508)
		],
		'template_2p': [
			(100, 100, 1140, 3308),     # Left portrait
			(1240, 100, 1140, 3308)     # Right portrait
		],
		'template_2l': [
			(100, 100, 2280, 1600),     # Top landscape
			(100, 1808, 2280, 1600)     # Bottom landscape (starts after 100px gap)
		],
		'template_3p': [
			(100, 100, 760, 3308),       # Left portrait
			(860, 100, 760, 3308),       # Middle portrait
			(1620, 100, 760, 3308)       # Right portrait
		],
		
		'template_3l': [
			(100, 100, 2280, 1000),      # Top full-width landscape
			(100, 1200, 1140, 1000),     # Bottom-left landscape
			(1240, 1200, 1140, 1000)     # Bottom-right landscape
		],
		
		'template_mix3a': [  # 2 portrait + 1 landscape
			(100, 100, 1140, 1500),      # Left portrait
			(1240, 100, 1140, 1500),     # Right portrait
			(100, 1700, 2280, 1300)      # Landscape beneath both
		],
		
		'template_mix3b':  [  # 1 portrait + 2 landscape
			(100, 100, 2280, 1200),      # Top full-width landscape
			(100, 1400, 1140, 1800),     # Bottom-left portrait
			(1240, 1400, 1140, 1800)     # Bottom-right portrait
		], 
		'template_mix4': [
			(100, 100, 2280, 800),        # Top landscape
			(100, 920, 1140, 1500),       # Left portrait
			(1240, 920, 1140, 1500),      # Right portrait
			(100, 2440, 2280, 800)        # Bottom landscape
		],
		
		'template_4p': [
			(100, 100, 1140, 1600),       # Top left
			(1240, 100, 1140, 1600),      # Top right
			(100, 1720, 1140, 1600),      # Bottom left
			(1240, 1720, 1140, 1600)      # Bottom right
		],
		
		'template_4l': [
			(100, 100, 1140, 800),        # Top left
			(1240, 100, 1140, 800),       # Top right
			(100, 920, 1140, 800),        # Bottom left
			(1240, 920, 1140, 800)        # Bottom right
		],
		
		'template_mix4a_l': [
			(100, 100, 760, 3308),        # Left full-height portrait
			(880, 100, 1500, 700),        # Top right landscape
			(880, 840, 1500, 700),        # Middle right landscape
			(880, 1580, 1500, 700)        # Bottom right landscape
		],
		
		'template_mix4a_r': [
			(100, 100, 1500, 700),        # Top left landscape
			(100, 840, 1500, 700),        # Middle left landscape
			(100, 1580, 1500, 700),       # Bottom left landscape
			(1660, 100, 760, 3308)        # Right full-height portrait
		],
		
		'template_mix4b_t': [
			(100, 100, 2280, 800),        # Top full-width landscape
			(100, 940, 760, 2400),        # Bottom-left portrait
			(880, 940, 760, 2400),        # Bottom-middle portrait
			(1660, 940, 760, 2400)        # Bottom-right portrait
		],
		
		'template_mix4b_b': [
			(100, 100, 760, 2400),        # Top-left portrait
			(880, 100, 760, 2400),        # Top-middle portrait
			(1660, 100, 760, 2400),       # Top-right portrait
			(100, 2620, 2280, 700)        # Bottom full-width landscape
		],
		
		'template_mix4c_top': [
			(100, 100, 1140, 1600),       # Top-left portrait
			(1240, 100, 1140, 1600),      # Top-right portrait
			(100, 1720, 1140, 800),       # Bottom-left landscape
			(1240, 1720, 1140, 800)       # Bottom-right landscape
		],
		
		'template_mix4c_bottom': [
			(100, 100, 1140, 800),        # Top-left landscape
			(1240, 100, 1140, 800),       # Top-right landscape
			(100, 940, 1140, 1600),       # Bottom-left portrait
			(1240, 940, 1140, 1600)       # Bottom-right portrait
		],
		
		'template_mix5a': [
			(100, 100, 1140, 1500),      # Top-left portrait
			(1240, 100, 1140, 1500),     # Top-right portrait
			(100, 1640, 2280, 700),      # Middle landscape
			(100, 2370, 1140, 1500),     # Bottom-left portrait
			(1240, 2370, 1140, 1500)     # Bottom-right portrait
		],
		
		'template_mix5b': [  # 4 Portraits + 1 Landscape — Landscape at top
			(100, 100, 2280, 700),      # Top landscape
			(100, 820, 1140, 1200),     # Middle-left portrait
			(1240, 820, 1140, 1200),    # Middle-right portrait
			(100, 2040, 1140, 1200),    # Bottom-left portrait
			(1240, 2040, 1140, 1200)    # Bottom-right portrait
		],
		
		'template_mix5c': [  # 4 Portraits + 1 Landscape — Landscape at bottom
			(100, 100, 1140, 1200),     # Top-left portrait
			(1240, 100, 1140, 1200),    # Top-right portrait
			(100, 1320, 1140, 1200),    # Middle-left portrait
			(1240, 1320, 1140, 1200),   # Middle-right portrait
			(100, 2540, 2280, 700)      # Bottom landscape
		],
		
		'template_mix5d': [  # 4 Portraits + 1 Landscape — Landscape side-left
			(100, 100, 1000, 3308),     # Left full-height landscape
			(1220, 100, 1140, 760),     # Top-right portrait
			(1220, 900, 1140, 760),     # Second portrait
			(1220, 1700, 1140, 760),    # Third portrait
			(1220, 2500, 1140, 760)     # Bottom-right portrait
		],
		
		'template_mix5e': [  # 4 Portraits + 1 Landscape — Landscape side-right
			(1340, 100, 1000, 3308),    # Right full-height landscape
			(100, 100, 1140, 760),      # Top-left portrait
			(100, 900, 1140, 760),      # Second portrait
			(100, 1700, 1140, 760),     # Third portrait
			(100, 2500, 1140, 760)      # Bottom-left portrait
		],
		
		'template_mix5f': [  # 3 Portraits + 2 Landscapes — Portraits left, Landscapes right
			(100, 100, 1140, 1000),     # Top-left portrait
			(100, 1220, 1140, 1000),    # Middle-left portrait
			(100, 2340, 1140, 1000),    # Bottom-left portrait
			(1240, 100, 1140, 1600),    # Top-right landscape
			(1240, 1720, 1140, 1600)    # Bottom-right landscape
		],
		
		'template_mix5g': [  # 3 Portraits + 2 Landscapes — Portraits right, Landscapes left
			(1240, 100, 1140, 1000),    # Top-right portrait
			(1240, 1220, 1140, 1000),   # Middle-right portrait
			(1240, 2340, 1140, 1000),   # Bottom-right portrait
			(100, 100, 1140, 1600),     # Top-left landscape
			(100, 1720, 1140, 1600)     # Bottom-left landscape
		],
		
		'template_mix5h': [  # 3 Portraits + 2 Landscapes — Portraits top, Landscapes below
			(100, 100, 760, 1000),      # Top-left portrait
			(880, 100, 760, 1000),      # Top-center portrait
			(1660, 100, 760, 1000),     # Top-right portrait
			(100, 1220, 2280, 1000),    # Middle full-width landscape
			(100, 2340, 2280, 1000)     # Bottom full-width landscape
		],
		
		'template_mix5i': [  # 3 Portraits + 2 Landscapes — Landscapes top, Portraits bottom
			(100, 100, 1140, 1000),     # Top-left landscape
			(1240, 100, 1140, 1000),    # Top-right landscape
			(100, 1220, 760, 2200),     # Bottom-left portrait
			(920, 1220, 760, 2200),     # Bottom-center portrait
			(1740, 1220, 760, 2200)     # Bottom-right portrait
		],
		
		'template_mix5j': [  # 2 Portraits + 3 Landscapes — Portraits left, Landscapes right
			(100, 100, 1140, 1600),     # Top-left portrait
			(100, 1720, 1140, 1600),    # Bottom-left portrait
			(1240, 100, 1140, 1000),    # Top-right landscape
			(1240, 1220, 1140, 1000),   # Middle-right landscape
			(1240, 2340, 1140, 1000)    # Bottom-right landscape
		],
		
		'template_mix5k': [  # 2 Portraits + 3 Landscapes — Portraits right, Landscapes left
			(1240, 100, 1140, 1600),    # Top-right portrait
			(1240, 1720, 1140, 1600),   # Bottom-right portrait
			(100, 100, 1140, 1000),     # Top-left landscape
			(100, 1220, 1140, 1000),    # Middle-left landscape
			(100, 2340, 1140, 1000)     # Bottom-left landscape
		],
		
		'template_mix5l': [  # 2 Portraits + 3 Landscapes — Portraits on top, Landscapes below
			(100, 100, 1140, 1200),     # Top-left portrait
			(1240, 100, 1140, 1200),    # Top-right portrait
			(100, 1320, 2280, 700),     # Mid landscape
			(100, 2050, 2280, 700),     # Next landscape
			(100, 2780, 2280, 700)      # Bottom landscape
		],
		
		'template_mix5m': [  # 2 Portraits + 3 Landscapes — Landscapes on top, Portraits bottom
			(100, 100, 2280, 700),      # Top landscape
			(100, 840, 2280, 700),      # Middle landscape
			(100, 1580, 2280, 700),     # Bottom landscape
			(100, 2320, 1140, 1100),    # Bottom-left portrait
			(1240, 2320, 1140, 1100)    # Bottom-right portrait
		],
		
		'template_mix5n': [  # 1 Portrait + 4 Landscapes — Portrait left, Landscapes right
			(100, 100, 760, 3308),       # Full-height portrait
			(880, 100, 1500, 600),       # Top-right landscape
			(880, 740, 1500, 600),       # Second landscape
			(880, 1380, 1500, 600),      # Third landscape
			(880, 2020, 1500, 600)       # Bottom landscape
		],
		
		'template_mix5o': [  # 1 Portrait + 4 Landscapes — Portrait right, Landscapes left
			(1660, 100, 760, 3308),      # Full-height portrait
			(100, 100, 1500, 600),       # Top-left landscape
			(100, 740, 1500, 600),       # Second landscape
			(100, 1380, 1500, 600),      # Third landscape
			(100, 2020, 1500, 600)       # Bottom landscape
		],
		
		'template_mix5p': [  # 1 Portrait + 4 Landscapes — Landscape grid + bottom portrait
			(100, 100, 1140, 800),       # Top-left landscape
			(1240, 100, 1140, 800),      # Top-right landscape
			(100, 940, 1140, 800),       # Bottom-left landscape
			(1240, 940, 1140, 800),      # Bottom-right landscape
			(100, 1780, 2280, 1600)      # Bottom portrait (tall orientation)
		],
		
		'template_mix5q': [  # 1 Portrait + 4 Landscapes — Top portrait + landscape grid
			(100, 100, 2280, 1600),      # Top portrait
			(100, 1720, 1140, 800),      # Bottom-left landscape
			(1240, 1720, 1140, 800),     # Bottom-right landscape
			(100, 2560, 1140, 800),      # Bottom-left second row
			(1240, 2560, 1140, 800)      # Bottom-right second row
		],
		
		'template_5l_a': [  # 5 Landscapes — 2 top, 3 bottom
			(100, 100, 1140, 800),       # Top-left
			(1240, 100, 1140, 800),      # Top-right
			(100, 940, 760, 800),        # Bottom-left
			(940, 940, 760, 800),        # Bottom-middle
			(1780, 940, 760, 800)        # Bottom-right
		],
		
		'template_5l_b': [  # 5 Landscapes — 3 top, 2 bottom
			(100, 100, 760, 800),        # Top-left
			(940, 100, 760, 800),        # Top-middle
			(1780, 100, 760, 800),       # Top-right
			(100, 940, 1140, 800),       # Bottom-left
			(1240, 940, 1140, 800)       # Bottom-right
		],
		
		'template_5l_c': [  # 5 Landscapes — Full-width top + 2x2 grid
			(100, 100, 2280, 600),       # Full-width landscape
			(100, 740, 1140, 800),       # Grid top-left
			(1240, 740, 1140, 800),      # Grid top-right
			(100, 1580, 1140, 800),      # Grid bottom-left
			(1240, 1580, 1140, 800)      # Grid bottom-right
		],
		
		'template_5l_d': [  # 5 Landscapes — 2x2 grid + centered bottom
			(100, 100, 1140, 800),       # Top-left
			(1240, 100, 1140, 800),      # Top-right
			(100, 940, 1140, 800),       # Bottom-left
			(1240, 940, 1140, 800),      # Bottom-right
			(490, 1780, 1500, 600)       # Centered bottom
		],
		
		'template_mix5_3l2p_a': [  # 3L left, 2P right
			(100, 100, 1140, 600),       # Top-left landscape
			(100, 740, 1140, 600),       # Middle-left landscape
			(100, 1380, 1140, 600),      # Bottom-left landscape
			(1240, 100, 1140, 1600),     # Top-right portrait
			(1240, 1720, 1140, 1600)     # Bottom-right portrait
		],
		
		'template_mix5_3l2p_b': [  # 2P left, 3L right
			(100, 100, 1140, 1600),      # Top-left portrait
			(100, 1720, 1140, 1600),     # Bottom-left portrait
			(1240, 100, 1140, 600),      # Top-right landscape
			(1240, 740, 1140, 600),      # Middle-right landscape
			(1240, 1380, 1140, 600)      # Bottom-right landscape
		],
		
		'template_mix5_3l2p_c': [  # 1P top, 3L middle, 1P bottom
			(100, 100, 2280, 1000),      # Top full-width portrait
			(100, 1220, 760, 600),       # Mid-left landscape
			(860, 1220, 760, 600),       # Mid-center landscape
			(1620, 1220, 760, 600),      # Mid-right landscape
			(100, 1900, 2280, 1000)      # Bottom full-width portrait
		],
		
		'template_mix5_2l3p_a': [  # 2L top, 3P bottom
			(100, 100, 2280, 600),       # Top landscape
			(100, 740, 2280, 600),       # Second landscape
			(100, 1380, 760, 1800),      # Bottom-left portrait
			(860, 1380, 760, 1800),      # Bottom-center portrait
			(1620, 1380, 760, 1800)      # Bottom-right portrait
		],
		
		'template_mix5_2l3p_b': [  # 3P top, 2L bottom
			(100, 100, 760, 1800),       # Top-left portrait
			(860, 100, 760, 1800),       # Top-center portrait
			(1620, 100, 760, 1800),      # Top-right portrait
			(100, 1940, 2280, 600),      # Bottom landscape
			(100, 2580, 2280, 600)       # Second bottom landscape
		],
		
		'template_mix5_2l3p_c': [  # L–P–L top, 2P bottom
			(100, 100, 760, 1000),       # Top-left landscape
			(860, 100, 760, 2000),       # Top-center portrait (tall)
			(1620, 100, 760, 1000),      # Top-right landscape
			(100, 1220, 1140, 1800),     # Bottom-left portrait
			(1240, 1220, 1140, 1800)     # Bottom-right portrait
		],
		
		'template_mix5_1l4p_a': [  # L top, 4P in 2x2 grid
			(100, 100, 2280, 700),        # Top full-width landscape
			(100, 840, 1140, 1500),       # Bottom-left portrait
			(1240, 840, 1140, 1500),      # Bottom-right portrait
			(100, 2380, 1140, 1000),      # Bottom-left 2nd row portrait
			(1240, 2380, 1140, 1000)      # Bottom-right 2nd row portrait
		],
		
		'template_mix5_1l4p_b': [  # 4P grid top, L bottom
			(100, 100, 1140, 1200),       # Top-left portrait
			(1240, 100, 1140, 1200),      # Top-right portrait
			(100, 1340, 1140, 1200),      # Bottom-left portrait
			(1240, 1340, 1140, 1200),     # Bottom-right portrait
			(100, 2660, 2280, 700)        # Bottom full-width landscape
		],
		
		'template_mix5_1l4p_c': [  # L left side, 4P stacked right
			(100, 100, 760, 3308),        # Left full-height landscape (rotated)
			(880, 100, 1500, 700),        # Top-right portrait
			(880, 840, 1500, 700),        # 2nd-right portrait
			(880, 1580, 1500, 700),       # 3rd-right portrait
			(880, 2320, 1500, 700)        # Bottom-right portrait
		],
		
		'template_mix5_1l4p_d': [  # L right side, 4P stacked left
			(1660, 100, 760, 3308),       # Right full-height landscape (rotated)
			(100, 100, 1500, 700),        # Top-left portrait
			(100, 840, 1500, 700),        # 2nd-left portrait
			(100, 1580, 1500, 700),       # 3rd-left portrait
			(100, 2320, 1500, 700)        # Bottom-left portrait
		],
		
		'template_mix6_4p_2l_a': [
			(100, 100, 2280, 600),        # Top full-width landscape
			(100, 740, 1140, 1300),       # Middle-left portrait
			(1240, 740, 1140, 1300),      # Middle-right portrait
			(100, 2070, 1140, 1300),      # Bottom-left portrait
			(1240, 2070, 1140, 1300),     # Bottom-right portrait
			(100, 3400, 2280, 600)        # Bottom full-width landscape (canvas overspill acceptable)
		],
		
		'template_mix5_5p_b': [  # 3 top, 2 bottom
			(100, 100, 760, 1500),     # Top-left
			(860, 100, 760, 1500),     # Top-middle
			(1620, 100, 760, 1500),    # Top-right
			(490, 1720, 760, 1500),    # Bottom-left (centered)
			(1250, 1720, 760, 1500)    # Bottom-right (centered)
		],
		
		'template_mix5_5p_c': [  # 2 top, 3 bottom
			(490, 100, 760, 1500),     # Top-left (centered)
			(1250, 100, 760, 1500),    # Top-right (centered)
			(100, 1720, 760, 1500),    # Bottom-left
			(880, 1720, 760, 1500),    # Bottom-middle
			(1660, 1720, 760, 1500)    # Bottom-right
		],
		
		'template_mix5_5p_d': [  # 5 stacked vertically
			(100, 100, 2280, 600),
			(100, 740, 2280, 600),
			(100, 1380, 2280, 600),
			(100, 2020, 2280, 600),
			(100, 2660, 2280, 600)
		], 		
		
		# Six image templates
		'template_mix6': [
			(100, 100, 2280, 700),     # Top landscape image
			(100, 820, 1140, 1300),    # Mid-left portrait
			(1240, 820, 1140, 1300),   # Mid-right portrait
			(100, 2140, 1140, 1300),   # Lower-left portrait
			(1240, 2140, 1140, 1300),  # Lower-right portrait
			(100, 3560, 2280, 700)     # Bottom landscape image
		],
		

		'template_mix6_4p2l_topbottom': [  # L at top and bottom, 2x2 P grid center
			(100, 100, 2280, 600),          # Top landscape
			(100, 740, 1140, 1200),         # Top-left portrait
			(1240, 740, 1140, 1200),        # Top-right portrait
			(100, 1980, 1140, 1200),        # Bottom-left portrait
			(1240, 1980, 1140, 1200),       # Bottom-right portrait
			(100, 3200, 2280, 300)          # Bottom landscape
		],
		
		'template_mix6_4p2l_center': [  # L top and bottom, 2x2 P in middle
			(100, 100, 2280, 700),          # Top landscape
			(100, 820, 1140, 1100),         # Top-left portrait
			(1240, 820, 1140, 1100),        # Top-right portrait
			(100, 1940, 1140, 1100),        # Bottom-left portrait
			(1240, 1940, 1140, 1100),       # Bottom-right portrait
			(100, 3160, 2280, 300)          # Bottom landscape
		],
		
		'template_mix6_4p2l_top': [  # 2x2 P at top, 2 stacked L below
			(100, 100, 1140, 1300),         # Top-left portrait
			(1240, 100, 1140, 1300),        # Top-right portrait
			(100, 1440, 1140, 1300),        # Bottom-left portrait
			(1240, 1440, 1140, 1300),       # Bottom-right portrait
			(100, 2780, 2280, 300),         # Landscape 1
			(100, 3100, 2280, 300)          # Landscape 2
		],
		
		'template_mix6_4p2l_bottom': [  # 2 L on top, 2x2 P grid below
			(100, 100, 2280, 300),          # Landscape 1
			(100, 440, 2280, 300),          # Landscape 2
			(100, 780, 1140, 1300),         # Top-left portrait
			(1240, 780, 1140, 1300),        # Top-right portrait
			(100, 2120, 1140, 1300),        # Bottom-left portrait
			(1240, 2120, 1140, 1300)        # Bottom-right portrait
		],
		
		'template_mix6_4p2l_side_l': [  # 4 stacked P on left, 2 L stacked on right
			(100, 100, 1140, 800),          # Portrait 1
			(100, 920, 1140, 800),          # Portrait 2
			(100, 1740, 1140, 800),         # Portrait 3
			(100, 2560, 1140, 800),         # Portrait 4
			(1240, 100, 1140, 1600),        # Landscape 1
			(1240, 1740, 1140, 1600)        # Landscape 2
		],
		
		'template_mix6_4p2l_side_r': [  # 4 stacked P on right, 2 L stacked on left
			(100, 100, 1140, 1600),         # Landscape 1
			(100, 1740, 1140, 1600),        # Landscape 2
			(1240, 100, 1140, 800),         # Portrait 1
			(1240, 920, 1140, 800),         # Portrait 2
			(1240, 1740, 1140, 800),        # Portrait 3
			(1240, 2560, 1140, 800)         # Portrait 4
		],
		
		'template_mix6_3p3l_top': [  # 3P on top row, 3L stacked below
			(100, 100, 760, 1200),         # Top-left portrait
			(860, 100, 760, 1200),         # Top-center portrait
			(1620, 100, 760, 1200),        # Top-right portrait
			(100, 1340, 2280, 600),        # Mid landscape 1
			(100, 1980, 2280, 600),        # Mid landscape 2
			(100, 2620, 2280, 600)         # Bottom landscape 3
		],
		
		'template_mix6_3p3l_bottom': [  # 3L on top row, 3P stacked below
			(100, 100, 760, 800),          # Top-left landscape
			(860, 100, 760, 800),          # Top-center landscape
			(1620, 100, 760, 800),         # Top-right landscape
			(100, 940, 760, 850),          # Bottom-left portrait
			(860, 940, 760, 850),          # Bottom-center portrait
			(1620, 940, 760, 850)          # Bottom-right portrait
		],
		
		'template_mix6_3p3l_column': [  # Portraits on left column, landscapes stacked right
			(100, 100, 1140, 800),         # Top-left portrait
			(100, 940, 1140, 800),         # Middle-left portrait
			(100, 1780, 1140, 800),        # Bottom-left portrait
			(1240, 100, 1140, 1000),       # Top-right landscape
			(1240, 1140, 1140, 1000),      # Middle-right landscape
			(1240, 2180, 1140, 1000)       # Bottom-right landscape
		],
		
		'template_mix6_3p3l_row': [  # 2 rows: portraits on top, landscapes below
			(100, 100, 760, 1000),         # Top-left portrait
			(860, 100, 760, 1000),         # Top-center portrait
			(1620, 100, 760, 1000),        # Top-right portrait
			(100, 1240, 760, 1000),        # Bottom-left landscape
			(860, 1240, 760, 1000),        # Bottom-center landscape
			(1620, 1240, 760, 1000)        # Bottom-right landscape
		],
		
		'template_mix6_1p5l_top': [  # 1P at top, 5L grid below
			(100, 100, 1140, 1200),         # Top portrait
			(100, 1340, 760, 800),          # Top-left landscape
			(880, 1340, 760, 800),          # Top-middle landscape
			(1660, 1340, 760, 800),         # Top-right landscape
			(100, 2180, 1140, 800),         # Bottom-left landscape
			(1240, 2180, 1140, 800)         # Bottom-right landscape
		],
		
		'template_mix6_1p5l_bottom': [  # 5L grid top, 1P at bottom
			(100, 100, 1140, 800),          # Top-left landscape
			(1240, 100, 1140, 800),         # Top-right landscape
			(100, 940, 760, 800),           # Middle-left landscape
			(880, 940, 760, 800),           # Middle-center landscape
			(1660, 940, 760, 800),          # Middle-right landscape
			(100, 1800, 2280, 1600)         # Bottom portrait
		],
		
		'template_mix6_1p5l_side_l': [  # 1P on left, 5L stacked right
			(100, 100, 760, 3308),          # Left full-height portrait
			(880, 100, 1500, 600),          # Top-right landscape
			(880, 740, 1500, 600),          # Second landscape
			(880, 1380, 1500, 600),         # Third landscape
			(880, 2020, 1500, 600),         # Fourth landscape
			(880, 2660, 1500, 600)          # Fifth landscape
		],
		
		'template_mix6_1p5l_side_r': [  # 1P on right, 5L stacked left
			(1660, 100, 760, 3308),         # Right full-height portrait
			(100, 100, 1500, 600),          # Top-left landscape
			(100, 740, 1500, 600),          # Second landscape
			(100, 1380, 1500, 600),         # Third landscape
			(100, 2020, 1500, 600),         # Fourth landscape
			(100, 2660, 1500, 600)          # Fifth landscape
		],
		
		'template_mix6_1p5l_split': [  # Portrait in center, 3L left, 2L right
			(100, 100, 1140, 600),          # Top-left landscape
			(100, 740, 1140, 600),          # Middle-left landscape
			(100, 1380, 1140, 600),         # Bottom-left landscape
			(1240, 100, 1140, 1000),        # Center portrait
			(1240, 1140, 1140, 800),        # Top-right landscape
			(1240, 1980, 1140, 800)         # Bottom-right landscape
		],
		
		'template_mix6_2p4l_top': [  # 2 stacked Portraits on left, 4L grid on right
			(100, 100, 1140, 1500),           # Top-left portrait
			(100, 1660, 1140, 1500),          # Bottom-left portrait
			(1240, 100, 1140, 700),           # Top-right landscape 1
			(1240, 840, 1140, 700),           # Top-right landscape 2
			(1240, 1580, 1140, 700),          # Bottom-right landscape 3
			(1240, 2320, 1140, 700)           # Bottom-right landscape 4
		],
		
		'template_mix6_2p4l_bottom': [  # 4L grid top, 2P stacked right
			(100, 100, 1140, 700),            # Top-left landscape
			(100, 840, 1140, 700),            # 2nd-left landscape
			(100, 1580, 1140, 700),           # 3rd-left landscape
			(100, 2320, 1140, 700),           # Bottom-left landscape
			(1240, 100, 1140, 1500),          # Top-right portrait
			(1240, 1660, 1140, 1500)          # Bottom-right portrait
		],
		
		'template_mix6_2p4l_center': [  # 2P center column, L on left and right
			(100, 100, 760, 1600),            # Left full-height landscape
			(880, 100, 760, 1500),            # Top-center portrait
			(880, 1660, 760, 1500),           # Bottom-center portrait
			(1660, 100, 760, 700),            # Top-right landscape
			(1660, 840, 760, 700),            # 2nd-right landscape
			(1660, 1580, 760, 700)            # Bottom-right landscape
		],
		
		'template_mix6_2p4l_leftstack': [  # 2P stacked left, 4L stacked right
			(100, 100, 1140, 1600),           # Top-left portrait
			(100, 1740, 1140, 1600),          # Bottom-left portrait
			(1240, 100, 1140, 700),           # Landscape 1
			(1240, 840, 1140, 700),           # Landscape 2
			(1240, 1580, 1140, 700),          # Landscape 3
			(1240, 2320, 1140, 700)           # Landscape 4
		],
		
		'template_mix6_2p4l_rightstack': [  # 2P stacked right, 4L stacked left
			(1240, 100, 1140, 1600),          # Top-right portrait
			(1240, 1740, 1140, 1600),         # Bottom-right portrait
			(100, 100, 1140, 700),            # Landscape 1
			(100, 840, 1140, 700),            # Landscape 2
			(100, 1580, 1140, 700),           # Landscape 3
			(100, 2320, 1140, 700)            # Landscape 4
		],
		
		'template_mix6_3p3l_top': [  # 3P on top row, 3L stacked below
			(100, 100, 760, 1200),         # Top-left portrait
			(860, 100, 760, 1200),         # Top-center portrait
			(1620, 100, 760, 1200),        # Top-right portrait
			(100, 1340, 2280, 600),        # Mid landscape 1
			(100, 1980, 2280, 600),        # Mid landscape 2
			(100, 2620, 2280, 600)         # Bottom landscape 3
		],
		
		'template_mix6_3p3l_bottom': [  # 3L on top row, 3P stacked below
			(100, 100, 760, 800),          # Top-left landscape
			(860, 100, 760, 800),          # Top-center landscape
			(1620, 100, 760, 800),         # Top-right landscape
			(100, 940, 760, 850),          # Bottom-left portrait
			(860, 940, 760, 850),          # Bottom-center portrait
			(1620, 940, 760, 850)          # Bottom-right portrait
		],
		
		'template_mix6_3p3l_column': [  # Portraits on left column, landscapes stacked right
			(100, 100, 1140, 800),         # Top-left portrait
			(100, 940, 1140, 800),         # Middle-left portrait
			(100, 1780, 1140, 800),        # Bottom-left portrait
			(1240, 100, 1140, 1000),       # Top-right landscape
			(1240, 1140, 1140, 1000),      # Middle-right landscape
			(1240, 2180, 1140, 1000)       # Bottom-right landscape
		],
		
		'template_mix6_3p3l_row': [  # 2 rows: portraits on top, landscapes below
			(100, 100, 760, 1000),         # Top-left portrait
			(860, 100, 760, 1000),         # Top-center portrait
			(1620, 100, 760, 1000),        # Top-right portrait
			(100, 1240, 760, 1000),        # Bottom-left landscape
			(860, 1240, 760, 1000),        # Bottom-center landscape
			(1620, 1240, 760, 1000)        # Bottom-right landscape
		],
		
		'template_mix6_5p1l_top': [  # L at top, 5P grid below (2x2 + 1 center)
			(100, 100, 2280, 600),           # Top full-width landscape
			(100, 740, 1140, 1100),          # Portrait TL
			(1240, 740, 1140, 1100),         # Portrait TR
			(100, 1880, 1140, 1100),         # Portrait BL
			(1240, 1880, 1140, 1100),        # Portrait BR
			(660, 3020, 1140, 380)           # Center bottom portrait
		],
		
		'template_mix6_5p1l_bottom': [  # 5P top grid, L at bottom
			(100, 100, 1140, 1000),          # Portrait TL
			(1240, 100, 1140, 1000),         # Portrait TR
			(100, 1140, 1140, 1000),         # Portrait ML
			(1240, 1140, 1140, 1000),        # Portrait MR
			(660, 2280, 1140, 500),          # Center bottom portrait
			(100, 2880, 2280, 500)           # Bottom landscape
		],
		
		'template_mix6_5p1l_side_l': [  # L left column, 5P stacked right
			(100, 100, 760, 3308),           # Landscape left (rotated)
			(880, 100, 1500, 620),           # Portrait 1
			(880, 760, 1500, 620),           # Portrait 2
			(880, 1420, 1500, 620),          # Portrait 3
			(880, 2080, 1500, 620),          # Portrait 4
			(880, 2740, 1500, 620)           # Portrait 5
		],
		
		'template_mix6_5p1l_side_r': [  # L right column, 5P stacked left
			(1660, 100, 760, 3308),          # Landscape right (rotated)
			(100, 100, 1500, 620),           # Portrait 1
			(100, 760, 1500, 620),           # Portrait 2
			(100, 1420, 1500, 620),          # Portrait 3
			(100, 2080, 1500, 620),          # Portrait 4
			(100, 2740, 1500, 620)           # Portrait 5
		],
		
		'template_mix6_5l1p_top': [  # P at top, 5L stacked below
			(100, 100, 2280, 700),            # Top portrait (wide center)
			(100, 860, 2280, 480),            # Landscape 1
			(100, 1360, 2280, 480),           # Landscape 2
			(100, 1860, 2280, 480),           # Landscape 3
			(100, 2360, 2280, 480),           # Landscape 4
			(100, 2860, 2280, 480)            # Landscape 5
		],
		
		'template_mix6_5l1p_bottom': [  # 5L top, P at bottom
			(100, 100, 2280, 480),            # Landscape 1
			(100, 600, 2280, 480),            # Landscape 2
			(100, 1100, 2280, 480),           # Landscape 3
			(100, 1600, 2280, 480),           # Landscape 4
			(100, 2100, 2280, 480),           # Landscape 5
			(100, 2700, 2280, 700)            # Bottom portrait (wide)
		],
		
		'template_mix6_5l1p_side_l': [  # P on left, 5L stacked right
			(100, 100, 760, 3308),            # Portrait full-height
			(880, 100, 1500, 520),            # Landscape 1
			(880, 680, 1500, 520),            # Landscape 2
			(880, 1260, 1500, 520),           # Landscape 3
			(880, 1840, 1500, 520),           # Landscape 4
			(880, 2420, 1500, 520)            # Landscape 5
		],
		
		'template_mix6_5l1p_side_r': [  # P on right, 5L stacked left
			(1660, 100, 760, 3308),           # Portrait full-height
			(100, 100, 1500, 520),            # Landscape 1
			(100, 680, 1500, 520),            # Landscape 2
			(100, 1260, 1500, 520),           # Landscape 3
			(100, 1840, 1500, 520),           # Landscape 4
			(100, 2420, 1500, 520)            # Landscape 5
		],
		
		#Seven image templates

		'template_mix7_1p6l_side_l': [  # 1P on left, 6L stacked right
				(100, 100, 720, 3308),       # Full-height portrait on left
				(860, 100, 1500, 480),       # Landscape 1
				(860, 620, 1500, 480),       # Landscape 2
				(860, 1140, 1500, 480),      # Landscape 3
				(860, 1660, 1500, 480),      # Landscape 4
				(860, 2180, 1500, 480),      # Landscape 5
				(860, 2700, 1500, 480)       # Landscape 6
			],
		
		'template_mix7_1p6l_side_r': [  # 1P on right, 6L stacked left
			(1660, 100, 720, 3308),      # Full-height portrait on right
			(100, 100, 1500, 480),       # Landscape 1
			(100, 620, 1500, 480),       # Landscape 2
			(100, 1140, 1500, 480),      # Landscape 3
			(100, 1660, 1500, 480),      # Landscape 4
			(100, 2180, 1500, 480),      # Landscape 5
			(100, 2700, 1500, 480)       # Landscape 6
		],
		
		'template_mix7_5p2l_stack': [  # 5P stacked left, 2L stacked right
			(100, 100, 1140, 600),        # Portrait 1
			(100, 740, 1140, 600),        # Portrait 2
			(100, 1380, 1140, 600),       # Portrait 3
			(100, 2020, 1140, 600),       # Portrait 4
			(100, 2660, 1140, 600),       # Portrait 5
			(1240, 100, 1140, 1200),      # Landscape 1
			(1240, 1340, 1140, 1200)      # Landscape 2
		],
		
		'template_mix7_5p2l_grid_top': [  # 2L top, 5P grid below
			(100, 100, 1140, 400),        # Landscape 1
			(1240, 100, 1140, 400),       # Landscape 2
			(100, 540, 760, 1000),        # Portrait 1
			(880, 540, 760, 1000),        # Portrait 2
			(1660, 540, 760, 1000),       # Portrait 3
			(100, 1580, 1140, 900),       # Portrait 4
			(1240, 1580, 1140, 900)       # Portrait 5
		],
		
		'template_mix7_5p2l_grid_bottom': [  # 5P grid top, 2L bottom
			(100, 100, 760, 1000),        # Portrait 1
			(880, 100, 760, 1000),        # Portrait 2
			(1660, 100, 760, 1000),       # Portrait 3
			(100, 1140, 1140, 900),       # Portrait 4
			(1240, 1140, 1140, 900),      # Portrait 5
			(100, 2080, 1140, 500),       # Landscape 1
			(1240, 2080, 1140, 500)       # Landscape 2
		],
		
		'template_mix7_5p2l_band_middle': [  # 2L middle band, P above and below
			(100, 100, 1140, 800),        # Portrait 1
			(1240, 100, 1140, 800),       # Portrait 2
			(100, 940, 2280, 500),        # Landscape 1
			(100, 1480, 2280, 500),       # Landscape 2
			(100, 2000, 760, 1000),       # Portrait 3
			(880, 2000, 760, 1000),       # Portrait 4
			(1660, 2000, 760, 1000)       # Portrait 5
		],
		
		'template_mix7_5p2l_block_right': [  # 5P stacked right, 2L left
			(100, 100, 1140, 1100),       # Landscape 1
			(100, 1240, 1140, 1100),      # Landscape 2
			(1240, 100, 1140, 600),       # Portrait 1
			(1240, 740, 1140, 600),       # Portrait 2
			(1240, 1380, 1140, 600),      # Portrait 3
			(1240, 2020, 1140, 600),      # Portrait 4
			(1240, 2660, 1140, 600)       # Portrait 5
		],
		
		'template_mix7_4p3l_topleftstack': [  # 4P stacked left, 3L stacked right
			(100, 100, 1140, 600),        # Portrait 1
			(100, 740, 1140, 600),        # Portrait 2
			(100, 1380, 1140, 600),       # Portrait 3
			(100, 2020, 1140, 600),       # Portrait 4
			(1240, 100, 1140, 800),       # Landscape 1
			(1240, 920, 1140, 800),       # Landscape 2
			(1240, 1740, 1140, 800)       # Landscape 3
		],
		
		'template_mix7_4p3l_topgrid': [  # 4P grid top, 3L below
			(100, 100, 1140, 1000),       # Portrait 1
			(1240, 100, 1140, 1000),      # Portrait 2
			(100, 1140, 1140, 1000),      # Portrait 3
			(1240, 1140, 1140, 1000),     # Portrait 4
			(100, 2280, 760, 400),        # Landscape 1
			(880, 2280, 760, 400),        # Landscape 2
			(1660, 2280, 760, 400)        # Landscape 3
		],
		
		'template_mix7_4p3l_bottomgrid': [  # 3L top, 4P grid bottom
			(100, 100, 760, 400),         # Landscape 1
			(880, 100, 760, 400),         # Landscape 2
			(1660, 100, 760, 400),        # Landscape 3
			(100, 540, 1140, 1000),       # Portrait 1
			(1240, 540, 1140, 1000),      # Portrait 2
			(100, 1580, 1140, 1000),      # Portrait 3
			(1240, 1580, 1140, 1000)      # Portrait 4
		],
		
		'template_mix7_4p3l_bandcenter': [  # L on top/bottom, 4P mid
			(100, 100, 2280, 400),        # Landscape 1
			(100, 540, 1140, 1000),       # Portrait 1
			(1240, 540, 1140, 1000),      # Portrait 2
			(100, 1580, 1140, 1000),      # Portrait 3
			(1240, 1580, 1140, 1000),     # Portrait 4
			(100, 2680, 1140, 400),       # Landscape 2
			(1240, 2680, 1140, 400)       # Landscape 3
		],
		
		'template_mix7_4p3l_zflow': [  # 4P zig-zag, 3L intercut
			(100, 100, 760, 1000),        # Portrait 1
			(860, 100, 760, 400),         # Landscape 1
			(1620, 100, 760, 1000),       # Portrait 2
			(100, 1140, 760, 400),        # Landscape 2
			(860, 1140, 760, 1000),       # Portrait 3
			(1620, 1140, 760, 400),       # Landscape 3
			(100, 1580, 760, 1000)        # Portrait 4
		],
		
		'template_mix7_5p2l_stack': [  # 5P stacked left, 2L stacked right
			(100, 100, 1140, 600),        # Portrait 1
			(100, 740, 1140, 600),        # Portrait 2
			(100, 1380, 1140, 600),       # Portrait 3
			(100, 2020, 1140, 600),       # Portrait 4
			(100, 2660, 1140, 600),       # Portrait 5
			(1240, 100, 1140, 1200),      # Landscape 1
			(1240, 1340, 1140, 1200)      # Landscape 2
		],
		
		'template_mix7_5p2l_grid_top': [  # 2L top, 5P grid below
			(100, 100, 1140, 400),        # Landscape 1
			(1240, 100, 1140, 400),       # Landscape 2
			(100, 540, 760, 1000),        # Portrait 1
			(880, 540, 760, 1000),        # Portrait 2
			(1660, 540, 760, 1000),       # Portrait 3
			(100, 1580, 1140, 900),       # Portrait 4
			(1240, 1580, 1140, 900)       # Portrait 5
		],
		
		'template_mix7_5p2l_grid_bottom': [  # 5P grid top, 2L bottom
			(100, 100, 760, 1000),        # Portrait 1
			(880, 100, 760, 1000),        # Portrait 2
			(1660, 100, 760, 1000),       # Portrait 3
			(100, 1140, 1140, 900),       # Portrait 4
			(1240, 1140, 1140, 900),      # Portrait 5
			(100, 2080, 1140, 500),       # Landscape 1
			(1240, 2080, 1140, 500)       # Landscape 2
		],
		
		'template_mix7_5p2l_band_middle': [  # 2L middle band, P above and below
			(100, 100, 1140, 800),        # Portrait 1
			(1240, 100, 1140, 800),       # Portrait 2
			(100, 940, 2280, 500),        # Landscape 1
			(100, 1480, 2280, 500),       # Landscape 2
			(100, 2000, 760, 1000),       # Portrait 3
			(880, 2000, 760, 1000),       # Portrait 4
			(1660, 2000, 760, 1000)       # Portrait 5
		],
		
		'template_mix7_5p2l_block_right': [  # 5P stacked right, 2L left
			(100, 100, 1140, 1100),       # Landscape 1
			(100, 1240, 1140, 1100),      # Landscape 2
			(1240, 100, 1140, 600),       # Portrait 1
			(1240, 740, 1140, 600),       # Portrait 2
			(1240, 1380, 1140, 600),      # Portrait 3
			(1240, 2020, 1140, 600),      # Portrait 4
			(1240, 2660, 1140, 600)       # Portrait 5
		], 
		
		'template_mix7_5p2l_stack': [  # 5P stacked left, 2L stacked right
			(100, 100, 1140, 600),        # Portrait 1
			(100, 740, 1140, 600),        # Portrait 2
			(100, 1380, 1140, 600),       # Portrait 3
			(100, 2020, 1140, 600),       # Portrait 4
			(100, 2660, 1140, 600),       # Portrait 5
			(1240, 100, 1140, 1200),      # Landscape 1
			(1240, 1340, 1140, 1200)      # Landscape 2
		],
		
		'template_mix7_5p2l_grid_top': [  # 2L top, 5P grid below
			(100, 100, 1140, 400),        # Landscape 1
			(1240, 100, 1140, 400),       # Landscape 2
			(100, 540, 760, 1000),        # Portrait 1
			(880, 540, 760, 1000),        # Portrait 2
			(1660, 540, 760, 1000),       # Portrait 3
			(100, 1580, 1140, 900),       # Portrait 4
			(1240, 1580, 1140, 900)       # Portrait 5
		],
		
		'template_mix7_5p2l_grid_bottom': [  # 5P grid top, 2L bottom
			(100, 100, 760, 1000),        # Portrait 1
			(880, 100, 760, 1000),        # Portrait 2
			(1660, 100, 760, 1000),       # Portrait 3
			(100, 1140, 1140, 900),       # Portrait 4
			(1240, 1140, 1140, 900),      # Portrait 5
			(100, 2080, 1140, 500),       # Landscape 1
			(1240, 2080, 1140, 500)       # Landscape 2
		],
		
		'template_mix7_5p2l_band_middle': [  # 2L middle band, P above and below
			(100, 100, 1140, 800),        # Portrait 1
			(1240, 100, 1140, 800),       # Portrait 2
			(100, 940, 2280, 500),        # Landscape 1
			(100, 1480, 2280, 500),       # Landscape 2
			(100, 2000, 760, 1000),       # Portrait 3
			(880, 2000, 760, 1000),       # Portrait 4
			(1660, 2000, 760, 1000)       # Portrait 5
		],
		
		'template_mix7_5p2l_block_right': [  # 5P stacked right, 2L left
			(100, 100, 1140, 1100),       # Landscape 1
			(100, 1240, 1140, 1100),      # Landscape 2
			(1240, 100, 1140, 600),       # Portrait 1
			(1240, 740, 1140, 600),       # Portrait 2
			(1240, 1380, 1140, 600),      # Portrait 3
			(1240, 2020, 1140, 600),      # Portrait 4
			(1240, 2660, 1140, 600)       # Portrait 5
		],
		
		'template_mix7_6p1l_stack_left': [  # 6P stacked left, 1L right
			(100, 100, 1140, 500),         # Portrait 1
			(100, 640, 1140, 500),         # Portrait 2
			(100, 1180, 1140, 500),        # Portrait 3
			(100, 1720, 1140, 500),        # Portrait 4
			(100, 2260, 1140, 500),        # Portrait 5
			(100, 2800, 1140, 500),        # Portrait 6
			(1240, 100, 1140, 3200)        # Landscape full-height right
		],
		
		'template_mix7_6p1l_stack_right': [  # 6P stacked right, 1L left
			(1240, 100, 1140, 500),        # Portrait 1
			(1240, 640, 1140, 500),        # Portrait 2
			(1240, 1180, 1140, 500),       # Portrait 3
			(1240, 1720, 1140, 500),       # Portrait 4
			(1240, 2260, 1140, 500),       # Portrait 5
			(1240, 2800, 1140, 500),       # Portrait 6
			(100, 100, 1140, 3200)         # Landscape full-height left
		],
		
		'template_mix7_6p1l_grid_top': [  # 6P grid, 1L at top
			(100, 100, 2280, 400),         # Landscape top
			(100, 540, 760, 900),          # Portrait 1
			(880, 540, 760, 900),          # Portrait 2
			(1660, 540, 760, 900),         # Portrait 3
			(100, 1480, 760, 900),         # Portrait 4
			(880, 1480, 760, 900),         # Portrait 5
			(1660, 1480, 760, 900)         # Portrait 6
		],
		
		'template_mix7_6p1l_grid_bottom': [  # 6P grid, 1L at bottom
			(100, 100, 760, 900),          # Portrait 1
			(880, 100, 760, 900),          # Portrait 2
			(1660, 100, 760, 900),         # Portrait 3
			(100, 1040, 760, 900),         # Portrait 4
			(880, 1040, 760, 900),         # Portrait 5
			(1660, 1040, 760, 900),        # Portrait 6
			(100, 1980, 2280, 500)         # Landscape bottom
		],
		
		'template_mix7_6p1l_centerband': [  # 1L in center, 3P above & below
			(100, 100, 760, 900),          # Portrait 1
			(880, 100, 760, 900),          # Portrait 2
			(1660, 100, 760, 900),         # Portrait 3
			(100, 1040, 2280, 500),        # Landscape center
			(100, 1580, 760, 900),         # Portrait 4
			(880, 1580, 760, 900),         # Portrait 5
			(1660, 1580, 760, 900)         # Portrait 6
		],
		
		'template_mix7_7p_vertical_stack': [  # 7P stacked column
			(100, 100, 2280, 420),      # Portrait 1
			(100, 540, 2280, 420),      # Portrait 2
			(100, 980, 2280, 420),      # Portrait 3
			(100, 1420, 2280, 420),     # Portrait 4
			(100, 1860, 2280, 420),     # Portrait 5
			(100, 2300, 2280, 420),     # Portrait 6
			(100, 2740, 2280, 420)      # Portrait 7
		],
		
		'template_mix7_7p_grid': [  # 3x2 grid + 1 centered portrait
			(100, 100, 760, 1000),      # Portrait 1
			(880, 100, 760, 1000),      # Portrait 2
			(1660, 100, 760, 1000),     # Portrait 3
			(100, 1140, 760, 1000),     # Portrait 4
			(880, 1140, 760, 1000),     # Portrait 5
			(1660, 1140, 760, 1000),    # Portrait 6
			(860, 2280, 760, 1000)      # Portrait 7 (centered bottom)
		],
		
		'template_mix7_7p_ladder_left': [  # Stair-step stack left
			(100, 100, 1140, 500),      # Portrait 1
			(200, 640, 1140, 500),      # Portrait 2
			(300, 1180, 1140, 500),     # Portrait 3
			(400, 1720, 1140, 500),     # Portrait 4
			(500, 2260, 1140, 500),     # Portrait 5
			(600, 2800, 1140, 500),     # Portrait 6
			(700, 3340, 1140, 500)      # Portrait 7
		],
		
		'template_mix7_7p_ladder_right': [  # Stair-step stack right
			(1240, 100, 1140, 500),     # Portrait 1
			(1140, 640, 1140, 500),     # Portrait 2
			(1040, 1180, 1140, 500),    # Portrait 3
			(940, 1720, 1140, 500),     # Portrait 4
			(840, 2260, 1140, 500),     # Portrait 5
			(740, 2800, 1140, 500),     # Portrait 6
			(640, 3340, 1140, 500)      # Portrait 7
		],
		
		'template_mix7_7p_center_column': [  # Tall center stack
			(860, 100, 760, 420),       # Portrait 1
			(860, 540, 760, 420),       # Portrait 2
			(860, 980, 760, 420),       # Portrait 3
			(860, 1420, 760, 420),      # Portrait 4
			(860, 1860, 760, 420),      # Portrait 5
			(860, 2300, 760, 420),      # Portrait 6
			(860, 2740, 760, 420)       # Portrait 7
		],
		
		'template_mix7_7l_vertical_stack': [  # 7L stacked vertically
			(100, 100, 2280, 420),      # Landscape 1
			(100, 540, 2280, 420),      # Landscape 2
			(100, 980, 2280, 420),      # Landscape 3
			(100, 1420, 2280, 420),     # Landscape 4
			(100, 1860, 2280, 420),     # Landscape 5
			(100, 2300, 2280, 420),     # Landscape 6
			(100, 2740, 2280, 420)      # Landscape 7
		],
		
		'template_mix7_7l_grid': [  # 3x2 grid + 1 centered
			(100, 100, 760, 600),       # Landscape 1
			(880, 100, 760, 600),       # Landscape 2
			(1660, 100, 760, 600),      # Landscape 3
			(100, 740, 760, 600),       # Landscape 4
			(880, 740, 760, 600),       # Landscape 5
			(1660, 740, 760, 600),      # Landscape 6
			(860, 1380, 760, 600)       # Landscape 7 (centered below)
		],
		
		'template_mix7_7l_column_left': [  # stacked L left column
			(100, 100, 1140, 400),      # Landscape 1
			(100, 520, 1140, 400),      # Landscape 2
			(100, 940, 1140, 400),      # Landscape 3
			(100, 1360, 1140, 400),     # Landscape 4
			(100, 1780, 1140, 400),     # Landscape 5
			(100, 2200, 1140, 400),     # Landscape 6
			(100, 2620, 1140, 400)      # Landscape 7
		],
		
		'template_mix7_7l_column_right': [  # stacked L right column
			(1240, 100, 1140, 400),     # Landscape 1
			(1240, 520, 1140, 400),     # Landscape 2
			(1240, 940, 1140, 400),     # Landscape 3
			(1240, 1360, 1140, 400),    # Landscape 4
			(1240, 1780, 1140, 400),    # Landscape 5
			(1240, 2200, 1140, 400),    # Landscape 6
			(1240, 2620, 1140, 400)     # Landscape 7
		],
		
		'template_mix7_7l_row_zigzag': [  # zigzag horizontal L placement
			(100, 100, 1140, 400),
			(1240, 540, 1140, 400),
			(100, 980, 1140, 400),
			(1240, 1420, 1140, 400),
			(100, 1860, 1140, 400),
			(1240, 2300, 1140, 400),
			(100, 2740, 1140, 400)
		],
		
		'template_mix8_8p_vertical_stack': [  # 8P stacked full height
			(100, 100, 2280, 400),       # Portrait 1
			(100, 520, 2280, 400),       # Portrait 2
			(100, 940, 2280, 400),       # Portrait 3
			(100, 1360, 2280, 400),      # Portrait 4
			(100, 1780, 2280, 400),      # Portrait 5
			(100, 2200, 2280, 400),      # Portrait 6
			(100, 2620, 2280, 400),      # Portrait 7
			(100, 3040, 2280, 400)       # Portrait 8
		],
		
		'template_mix8_8p_grid': [  # 4x2 grid
			(100, 100, 600, 800),        # Portrait 1
			(740, 100, 600, 800),        # Portrait 2
			(1380, 100, 600, 800),       # Portrait 3
			(2020, 100, 460, 800),       # Portrait 4
			(100, 940, 600, 800),        # Portrait 5
			(740, 940, 600, 800),        # Portrait 6
			(1380, 940, 600, 800),       # Portrait 7
			(2020, 940, 460, 800)        # Portrait 8
		],
		
		'template_mix8_8p_grid_topband': [  # 2 rows of 4P across top
			(100, 100, 560, 900),        # Portrait 1
			(700, 100, 560, 900),        # Portrait 2
			(1300, 100, 560, 900),       # Portrait 3
			(1900, 100, 560, 900),       # Portrait 4
			(100, 1040, 560, 900),       # Portrait 5
			(700, 1040, 560, 900),       # Portrait 6
			(1300, 1040, 560, 900),      # Portrait 7
			(1900, 1040, 560, 900)       # Portrait 8
		],
		
		'template_mix8_8p_ladder': [  # staggered descending P layout
			(100, 100, 760, 500),        # Portrait 1
			(880, 200, 760, 500),        # Portrait 2
			(1660, 300, 760, 500),       # Portrait 3
			(100, 800, 760, 500),        # Portrait 4
			(880, 900, 760, 500),        # Portrait 5
			(1660, 1000, 760, 500),      # Portrait 6
			(490, 1520, 760, 500),       # Portrait 7
			(1240, 1520, 760, 500)       # Portrait 8
		],
		
		'template_mix8_8p_center_column': [  # 8P narrow center stack
			(860, 100, 760, 400),        # Portrait 1
			(860, 540, 760, 400),        # Portrait 2
			(860, 980, 760, 400),        # Portrait 3
			(860, 1420, 760, 400),       # Portrait 4
			(860, 1860, 760, 400),       # Portrait 5
			(860, 2300, 760, 400),       # Portrait 6
			(860, 2740, 760, 400),       # Portrait 7
			(860, 3180, 760, 400)        # Portrait 8
		],
		
		'template_mix8_7p1l_vertical_right': [  # 7P stacked left, 1L full-height right
			(100, 100, 1140, 400),       # Portrait 1
			(100, 520, 1140, 400),       # Portrait 2
			(100, 940, 1140, 400),       # Portrait 3
			(100, 1360, 1140, 400),      # Portrait 4
			(100, 1780, 1140, 400),      # Portrait 5
			(100, 2200, 1140, 400),      # Portrait 6
			(100, 2620, 1140, 400),      # Portrait 7
			(1240, 100, 1140, 2920)      # Landscape full-height
		],
		
		'template_mix8_7p1l_vertical_left': [  # 7P stacked right, 1L full-height left
			(1240, 100, 1140, 400),      # Portrait 1
			(1240, 520, 1140, 400),      # Portrait 2
			(1240, 940, 1140, 400),      # Portrait 3
			(1240, 1360, 1140, 400),     # Portrait 4
			(1240, 1780, 1140, 400),     # Portrait 5
			(1240, 2200, 1140, 400),     # Portrait 6
			(1240, 2620, 1140, 400),     # Portrait 7
			(100, 100, 1140, 2920)       # Landscape full-height
		],
		
		'template_mix8_7p1l_top_band': [  # 1L across top, 7P below grid
			(100, 100, 2280, 400),       # Landscape (top)
			(100, 540, 760, 900),        # Portrait 1
			(880, 540, 760, 900),        # Portrait 2
			(1660, 540, 760, 900),       # Portrait 3
			(100, 1480, 760, 900),       # Portrait 4
			(880, 1480, 760, 900),       # Portrait 5
			(1660, 1480, 760, 900),      # Portrait 6
			(860, 2420, 760, 900)        # Portrait 7 (center bottom)
		],
		
		'template_mix8_7p1l_bottom_band': [  # 1L across bottom, 7P above
			(100, 100, 760, 900),        # Portrait 1
			(880, 100, 760, 900),        # Portrait 2
			(1660, 100, 760, 900),       # Portrait 3
			(100, 1040, 760, 900),       # Portrait 4
			(880, 1040, 760, 900),       # Portrait 5
			(1660, 1040, 760, 900),      # Portrait 6
			(860, 1980, 760, 900),       # Portrait 7 (center)
			(100, 2920, 2280, 400)       # Landscape (bottom)
		],
		
		'template_mix8_7p1l_centerband': [  # 1L in center, 3P above + 4P below
			(100, 100, 760, 900),        # Portrait 1
			(880, 100, 760, 900),        # Portrait 2
			(1660, 100, 760, 900),       # Portrait 3
			(100, 1040, 2280, 500),      # Landscape center band
			(100, 1580, 600, 900),       # Portrait 4
			(740, 1580, 600, 900),       # Portrait 5
			(1380, 1580, 600, 900),      # Portrait 6
			(2020, 1580, 360, 900)       # Portrait 7
		],
		
		'template_mix8_6p2l_stack_left': [  # 6P stacked left, 2L stacked right
			(100, 100, 1140, 500),         # Portrait 1
			(100, 640, 1140, 500),         # Portrait 2
			(100, 1180, 1140, 500),        # Portrait 3
			(100, 1720, 1140, 500),        # Portrait 4
			(100, 2260, 1140, 500),        # Portrait 5
			(100, 2800, 1140, 500),        # Portrait 6
			(1240, 100, 1140, 1300),       # Landscape 1
			(1240, 1440, 1140, 1300)       # Landscape 2
		],
		
		'template_mix8_6p2l_stack_right': [  # 6P stacked right, 2L stacked left
			(1240, 100, 1140, 500),        # Portrait 1
			(1240, 640, 1140, 500),        # Portrait 2
			(1240, 1180, 1140, 500),       # Portrait 3
			(1240, 1720, 1140, 500),       # Portrait 4
			(1240, 2260, 1140, 500),       # Portrait 5
			(1240, 2800, 1140, 500),       # Portrait 6
			(100, 100, 1140, 1300),        # Landscape 1
			(100, 1440, 1140, 1300)        # Landscape 2
		],
		
		'template_mix8_6p2l_topband': [  # 2L top, 6P grid below
			(100, 100, 1140, 400),         # Landscape 1
			(1240, 100, 1140, 400),        # Landscape 2
			(100, 540, 760, 1000),         # Portrait 1
			(880, 540, 760, 1000),         # Portrait 2
			(1660, 540, 760, 1000),        # Portrait 3
			(100, 1580, 760, 1000),        # Portrait 4
			(880, 1580, 760, 1000),        # Portrait 5
			(1660, 1580, 760, 1000)        # Portrait 6
		],
		
		'template_mix8_6p2l_bottomband': [  # 6P top grid, 2L bottom
			(100, 100, 760, 1000),         # Portrait 1
			(880, 100, 760, 1000),         # Portrait 2
			(1660, 100, 760, 1000),        # Portrait 3
			(100, 1140, 760, 1000),        # Portrait 4
			(880, 1140, 760, 1000),        # Portrait 5
			(1660, 1140, 760, 1000),       # Portrait 6
			(100, 2180, 1140, 500),        # Landscape 1
			(1240, 2180, 1140, 500)        # Landscape 2
		],
		
		'template_mix8_6p2l_bandcenter': [  # L center band, 3P above, 3P below
			(100, 100, 760, 900),          # Portrait 1
			(880, 100, 760, 900),          # Portrait 2
			(1660, 100, 760, 900),         # Portrait 3
			(100, 1040, 1140, 500),        # Landscape 1
			(1240, 1040, 1140, 500),       # Landscape 2
			(100, 1580, 760, 900),         # Portrait 4
			(880, 1580, 760, 900),         # Portrait 5
			(1660, 1580, 760, 900)         # Portrait 6
		],
		
		'template_mix8_5p3l_stack_left': [  # 5P stacked left, 3L stacked right
			(100, 100, 1140, 500),         # Portrait 1
			(100, 640, 1140, 500),         # Portrait 2
			(100, 1180, 1140, 500),        # Portrait 3
			(100, 1720, 1140, 500),        # Portrait 4
			(100, 2260, 1140, 500),        # Portrait 5
			(1240, 100, 1140, 800),        # Landscape 1
			(1240, 920, 1140, 800),        # Landscape 2
			(1240, 1740, 1140, 800)        # Landscape 3
		],
		
		'template_mix8_5p3l_stack_right': [  # 5P stacked right, 3L stacked left
			(1240, 100, 1140, 500),        # Portrait 1
			(1240, 640, 1140, 500),        # Portrait 2
			(1240, 1180, 1140, 500),       # Portrait 3
			(1240, 1720, 1140, 500),       # Portrait 4
			(1240, 2260, 1140, 500),       # Portrait 5
			(100, 100, 1140, 800),         # Landscape 1
			(100, 920, 1140, 800),         # Landscape 2
			(100, 1740, 1140, 800)         # Landscape 3
		],
		
		'template_mix8_5p3l_topband': [  # 3L top row, 5P grid below
			(100, 100, 760, 400),         # Landscape 1
			(880, 100, 760, 400),         # Landscape 2
			(1660, 100, 760, 400),        # Landscape 3
			(100, 540, 760, 1000),        # Portrait 1
			(880, 540, 760, 1000),        # Portrait 2
			(1660, 540, 760, 1000),       # Portrait 3
			(100, 1580, 1140, 900),       # Portrait 4
			(1240, 1580, 1140, 900)       # Portrait 5
		],
		
		'template_mix8_5p3l_bottomband': [  # 5P grid top, 3L bottom
			(100, 100, 760, 1000),        # Portrait 1
			(880, 100, 760, 1000),        # Portrait 2
			(1660, 100, 760, 1000),       # Portrait 3
			(100, 1140, 1140, 900),       # Portrait 4
			(1240, 1140, 1140, 900),      # Portrait 5
			(100, 2080, 760, 400),        # Landscape 1
			(880, 2080, 760, 400),        # Landscape 2
			(1660, 2080, 760, 400)        # Landscape 3
		],
		
		'template_mix8_5p3l_centerband': [  # 3L in middle, 2P above, 3P below
			(100, 100, 1140, 800),        # Portrait 1
			(1240, 100, 1140, 800),       # Portrait 2
			(100, 940, 2280, 400),        # Landscape 1
			(100, 1380, 2280, 400),       # Landscape 2
			(100, 1820, 2280, 400),       # Landscape 3
			(100, 2240, 760, 1000),       # Portrait 3
			(880, 2240, 760, 1000),       # Portrait 4
			(1660, 2240, 760, 1000)       # Portrait 5
		],
		
		'template_mix8_4p4l_stack_split': [  # 4 Portraits stacked left, 4 Landscapes stacked right
			(100, 100, 1140, 600),      # Portrait 1
			(100, 740, 1140, 600),      # Portrait 2
			(100, 1380, 1140, 600),     # Portrait 3
			(100, 2020, 1140, 600),     # Portrait 4
			(1240, 100, 1140, 600),     # Landscape 1
			(1240, 740, 1140, 600),     # Landscape 2
			(1240, 1380, 1140, 600),    # Landscape 3
			(1240, 2020, 1140, 600)     # Landscape 4
		],
		
		'template_mix8_4p4l_grid_split': [  # 2x2 Portrait grid top, 2x2 Landscape grid bottom
			(100, 100, 1140, 1000),     # Portrait 1
			(1240, 100, 1140, 1000),    # Portrait 2
			(100, 1140, 1140, 1000),    # Portrait 3
			(1240, 1140, 1140, 1000),   # Portrait 4
			(100, 2280, 1140, 600),     # Landscape 1
			(1240, 2280, 1140, 600),    # Landscape 2
			(100, 2900, 1140, 600),     # Landscape 3
			(1240, 2900, 1140, 600)     # Landscape 4
		],
		
		'template_mix8_4p4l_band_center': [  # L-P-L-P interleaved banding top to bottom
			(100, 100, 2280, 400),      # Landscape 1 (Top)
			(100, 520, 1140, 900),      # Portrait 1
			(1240, 520, 1140, 900),     # Portrait 2
			(100, 1440, 2280, 400),     # Landscape 2 (Center)
			(100, 1860, 1140, 900),     # Portrait 3
			(1240, 1860, 1140, 900),    # Portrait 4
			(100, 2780, 1140, 400),     # Landscape 3 (Bottom Left)
			(1240, 2780, 1140, 400)     # Landscape 4 (Bottom Right)
		],
		
		'template_mix8_4p4l_topband': [  # 4 Landscapes in top band, 2x2 Portrait grid below
			(100, 100, 560, 400),       # Landscape 1
			(700, 100, 560, 400),       # Landscape 2
			(1300, 100, 560, 400),      # Landscape 3
			(1900, 100, 560, 400),      # Landscape 4
			(100, 540, 1140, 1000),     # Portrait 1
			(1240, 540, 1140, 1000),    # Portrait 2
			(100, 1580, 1140, 1000),    # Portrait 3
			(1240, 1580, 1140, 1000)    # Portrait 4
		],
		
		'template_mix8_4p4l_bottomband': [  # 2x2 Portrait grid top, 4 Landscape strip below
			(100, 100, 1140, 1000),     # Portrait 1
			(1240, 100, 1140, 1000),    # Portrait 2
			(100, 1140, 1140, 1000),    # Portrait 3
			(1240, 1140, 1140, 1000),   # Portrait 4
			(100, 2280, 560, 400),      # Landscape 1
			(700, 2280, 560, 400),      # Landscape 2
			(1300, 2280, 560, 400),     # Landscape 3
			(1900, 2280, 560, 400)      # Landscape 4
		],
		
		'template_mix8_4p4l_alternate_columns': [  # Alternating P/L per column vertically
			(100, 100, 1140, 500),      # Portrait 1 (Left Top)
			(1240, 100, 1140, 500),     # Landscape 1 (Right Top)
			(100, 640, 1140, 500),      # Landscape 2 (Left)
			(1240, 640, 1140, 500),     # Portrait 2 (Right)
			(100, 1180, 1140, 500),     # Portrait 3 (Left)
			(1240, 1180, 1140, 500),    # Landscape 3 (Right)
			(100, 1720, 1140, 500),     # Landscape 4 (Left Bottom)
			(1240, 1720, 1140, 500)     # Portrait 4 (Right Bottom)
		],
		
		'template_mix8_4p4l_center_grid': [  # Centered 2x2 Portraits, Landscapes top/bottom
			(100, 100, 1140, 400),      # Landscape 1 (Top Left)
			(1240, 100, 1140, 400),     # Landscape 2 (Top Right)
			(100, 540, 1140, 1000),     # Portrait 1
			(1240, 540, 1140, 1000),    # Portrait 2
			(100, 1580, 1140, 1000),    # Portrait 3
			(1240, 1580, 1140, 1000),   # Portrait 4
			(100, 2700, 1140, 400),     # Landscape 3 (Bottom Left)
			(1240, 2700, 1140, 400)     # Landscape 4 (Bottom Right)
		],
		
		'template_mix8_3p5l_stack_split': [  # 3P stacked left, 5L stacked right
			(100, 100, 1140, 700),         # Portrait 1
			(100, 820, 1140, 700),         # Portrait 2
			(100, 1540, 1140, 700),        # Portrait 3
			(1240, 100, 1140, 500),        # Landscape 1
			(1240, 620, 1140, 500),        # Landscape 2
			(1240, 1140, 1140, 500),       # Landscape 3
			(1240, 1660, 1140, 500),       # Landscape 4
			(1240, 2180, 1140, 500)        # Landscape 5
		],
		
		'template_mix8_3p5l_stack_reverse': [  # 3P stacked right, 5L stacked left
			(1240, 100, 1140, 700),        # Portrait 1
			(1240, 820, 1140, 700),        # Portrait 2
			(1240, 1540, 1140, 700),       # Portrait 3
			(100, 100, 1140, 500),         # Landscape 1
			(100, 620, 1140, 500),         # Landscape 2
			(100, 1140, 1140, 500),        # Landscape 3
			(100, 1660, 1140, 500),        # Landscape 4
			(100, 2180, 1140, 500)         # Landscape 5
		],
		
		'template_mix8_3p5l_grid_bottom': [  # 3P row on top, 5L grid below
			(100, 100, 760, 1000),         # Portrait 1
			(880, 100, 760, 1000),         # Portrait 2
			(1660, 100, 760, 1000),        # Portrait 3
			(100, 1140, 1140, 500),        # Landscape 1
			(1240, 1140, 1140, 500),       # Landscape 2
			(100, 1680, 1140, 500),        # Landscape 3
			(1240, 1680, 1140, 500),       # Landscape 4
			(100, 2220, 2280, 400)         # Landscape 5
		],
		
		'template_mix8_3p5l_band_center': [  # 3L band in center, 3P above, 2L below
			(100, 100, 760, 1000),         # Portrait 1
			(880, 100, 760, 1000),         # Portrait 2
			(1660, 100, 760, 1000),        # Portrait 3
			(100, 1140, 2280, 400),        # Landscape 1
			(100, 1580, 2280, 400),        # Landscape 2
			(100, 2020, 2280, 400),        # Landscape 3
			(100, 2460, 1140, 500),        # Landscape 4
			(1240, 2460, 1140, 500)        # Landscape 5
		],
		
		'template_mix8_3p5l_wraparound': [  # 3P in center column, L surrounds top/bottom
			(860, 100, 760, 900),          # Portrait 1 (top center)
			(860, 1040, 760, 900),         # Portrait 2
			(860, 1980, 760, 900),         # Portrait 3
			(100, 100, 720, 500),          # Landscape 1 (top left)
			(1660, 100, 720, 500),         # Landscape 2 (top right)
			(100, 2020, 720, 500),         # Landscape 3 (bottom left)
			(1660, 2020, 720, 500),        # Landscape 4 (bottom right)
			(100, 2660, 2280, 400)         # Landscape 5 (footer)
		],
		
		'template_mix8_2p6l_stack_left': [  # 2P stacked left, 6L stacked right
			(100, 100, 1140, 1300),         # Portrait 1
			(100, 1440, 1140, 1300),        # Portrait 2
			(1240, 100, 1140, 450),         # Landscape 1
			(1240, 580, 1140, 450),         # Landscape 2
			(1240, 1060, 1140, 450),        # Landscape 3
			(1240, 1540, 1140, 450),        # Landscape 4
			(1240, 2020, 1140, 450),        # Landscape 5
			(1240, 2500, 1140, 450)         # Landscape 6
		],
		
		'template_mix8_2p6l_stack_right': [  # 2P stacked right, 6L stacked left
			(1240, 100, 1140, 1300),        # Portrait 1
			(1240, 1440, 1140, 1300),       # Portrait 2
			(100, 100, 1140, 450),          # Landscape 1
			(100, 580, 1140, 450),          # Landscape 2
			(100, 1060, 1140, 450),         # Landscape 3
			(100, 1540, 1140, 450),         # Landscape 4
			(100, 2020, 1140, 450),         # Landscape 5
			(100, 2500, 1140, 450)          # Landscape 6
		],
		
		'template_mix8_2p6l_topband': [  # 2L top, 2P mid-band, 4L below
			(100, 100, 1140, 400),          # Landscape 1
			(1240, 100, 1140, 400),         # Landscape 2
			(100, 540, 1140, 1100),         # Portrait 1
			(1240, 540, 1140, 1100),        # Portrait 2
			(100, 1680, 1140, 400),         # Landscape 3
			(1240, 1680, 1140, 400),        # Landscape 4
			(100, 2120, 1140, 400),         # Landscape 5
			(1240, 2120, 1140, 400)         # Landscape 6
		],
		
		'template_mix8_2p6l_centerband': [  # 3L top, 2P center band, 3L bottom
			(100, 100, 760, 400),           # Landscape 1
			(880, 100, 760, 400),           # Landscape 2
			(1660, 100, 760, 400),          # Landscape 3
			(100, 540, 1140, 1100),         # Portrait 1
			(1240, 540, 1140, 1100),        # Portrait 2
			(100, 1680, 760, 400),          # Landscape 4
			(880, 1680, 760, 400),          # Landscape 5
			(1660, 1680, 760, 400)          # Landscape 6
		],
		
		'template_mix8_2p6l_column_wrap': [  # 2P in center column, 3L left, 3L right
			(860, 100, 760, 1200),          # Portrait 1 (center top)
			(860, 1340, 760, 1200),         # Portrait 2 (center bottom)
			(100, 100, 720, 500),           # Landscape 1 (top left)
			(100, 640, 720, 500),           # Landscape 2
			(100, 1180, 720, 500),          # Landscape 3
			(1660, 100, 720, 500),          # Landscape 4 (top right)
			(1660, 640, 720, 500),          # Landscape 5
			(1660, 1180, 720, 500)          # Landscape 6
		],
		
		'template_mix8_2p6l_stack_left': [  # 2P stacked left, 6L stacked right
			(100, 100, 1140, 1300),         
			(100, 1440, 1140, 1300),        
			(1240, 100, 1140, 450),         
			(1240, 580, 1140, 450),         
			(1240, 1060, 1140, 450),        
			(1240, 1540, 1140, 450),        
			(1240, 2020, 1140, 450),        
			(1240, 2500, 1140, 450)         
		],
		
		'template_mix8_2p6l_stack_right': [  # 2P stacked right, 6L stacked left
			(1240, 100, 1140, 1300),        
			(1240, 1440, 1140, 1300),       
			(100, 100, 1140, 450),          
			(100, 580, 1140, 450),          
			(100, 1060, 1140, 450),         
			(100, 1540, 1140, 450),         
			(100, 2020, 1140, 450),         
			(100, 2500, 1140, 450)          
		],
		
		'template_mix8_2p6l_topband': [  # 2L top, 2P middle, 4L bottom
			(100, 100, 1140, 400),          
			(1240, 100, 1140, 400),         
			(100, 540, 1140, 1100),         
			(1240, 540, 1140, 1100),        
			(100, 1680, 1140, 400),         
			(1240, 1680, 1140, 400),        
			(100, 2120, 1140, 400),         
			(1240, 2120, 1140, 400)         
		],
		
		'template_mix8_2p6l_centerband': [  # 3L top, 2P center, 3L bottom
			(100, 100, 760, 400),           
			(880, 100, 760, 400),           
			(1660, 100, 760, 400),          
			(100, 540, 1140, 1100),         
			(1240, 540, 1140, 1100),        
			(100, 1680, 760, 400),          
			(880, 1680, 760, 400),          
			(1660, 1680, 760, 400)          
		],
		
		'template_mix8_2p6l_column_wrap': [  # 2P center, 3L left, 3L right
			(860, 100, 760, 1200),          
			(860, 1340, 760, 1200),         
			(100, 100, 720, 500),           
			(100, 640, 720, 500),           
			(100, 1180, 720, 500),          
			(1660, 100, 720, 500),          
			(1660, 640, 720, 500),          
			(1660, 1180, 720, 500)          
		],
		
		'template_mix8_1p7l_stack_left': [  # 1P on left, 7L stacked right
			(100, 100, 760, 3308),           # Portrait full height
			(880, 100, 1500, 440),           # Landscape 1
			(880, 560, 1500, 440),           # Landscape 2
			(880, 1020, 1500, 440),          # Landscape 3
			(880, 1480, 1500, 440),          # Landscape 4
			(880, 1940, 1500, 440),          # Landscape 5
			(880, 2400, 1500, 440),          # Landscape 6
			(880, 2860, 1500, 440)           # Landscape 7
		],
		
		'template_mix8_1p7l_stack_right': [  # 1P on right, 7L stacked left
			(1660, 100, 760, 3308),          # Portrait full height
			(100, 100, 1500, 440),           # Landscape 1
			(100, 560, 1500, 440),           # Landscape 2
			(100, 1020, 1500, 440),          # Landscape 3
			(100, 1480, 1500, 440),          # Landscape 4
			(100, 1940, 1500, 440),          # Landscape 5
			(100, 2400, 1500, 440),          # Landscape 6
			(100, 2860, 1500, 440)           # Landscape 7
		],
		
		'template_mix8_1p7l_band_split': [  # 1P center, 3L top, 4L bottom
			(100, 100, 760, 400),           # Landscape 1
			(880, 100, 760, 400),           # Landscape 2
			(1660, 100, 760, 400),          # Landscape 3
			(860, 540, 760, 1200),          # Portrait (center)
			(100, 1780, 1140, 400),         # Landscape 4
			(1240, 1780, 1140, 400),        # Landscape 5
			(100, 2220, 1140, 400),         # Landscape 6
			(1240, 2220, 1140, 400)         # Landscape 7
		],
		
		'template_mix8_1p7l_column_wrap': [  # 1P in middle column, 3L left, 4L right
			(880, 100, 760, 1300),          # Portrait center
			(100, 100, 720, 400),           # Landscape 1 (top-left)
			(100, 540, 720, 400),           # Landscape 2
			(100, 980, 720, 400),           # Landscape 3
			(1660, 100, 720, 400),          # Landscape 4 (top-right)
			(1660, 540, 720, 400),          # Landscape 5
			(1660, 980, 720, 400),          # Landscape 6
			(1660, 1420, 720, 400)          # Landscape 7
		],
		
		'template_mix8_1p7l_bottomband': [  # 7L above, 1P at bottom
			(100, 100, 1140, 400),          # Landscape 1
			(1240, 100, 1140, 400),         # Landscape 2
			(100, 540, 1140, 400),          # Landscape 3
			(1240, 540, 1140, 400),         # Landscape 4
			(100, 980, 1140, 400),          # Landscape 5
			(1240, 980, 1140, 400),         # Landscape 6
			(100, 1420, 2280, 400),         # Landscape 7
			(100, 1860, 2280, 1600)         # Portrait (bottom full-width)
		],
		
		'template_mix8_0p8l_grid_4x2': [  # 4x2 Landscape grid
			(100, 100, 560, 600),          # Row 1
			(700, 100, 560, 600),
			(1300, 100, 560, 600),
			(1900, 100, 560, 600),
			(100, 740, 560, 600),          # Row 2
			(700, 740, 560, 600),
			(1300, 740, 560, 600),
			(1900, 740, 560, 600)
		],
		
		'template_mix8_0p8l_grid_2x4': [  # 2 columns, 4 rows (tall layout)
			(100, 100, 1140, 400),         # Column 1
			(100, 540, 1140, 400),
			(100, 980, 1140, 400),
			(100, 1420, 1140, 400),
			(1240, 100, 1140, 400),        # Column 2
			(1240, 540, 1140, 400),
			(1240, 980, 1140, 400),
			(1240, 1420, 1140, 400)
		],
		
		'template_mix8_0p8l_stack_vertical': [  # Full stacked vertical column
			(100, 100, 2280, 400),
			(100, 540, 2280, 400),
			(100, 980, 2280, 400),
			(100, 1420, 2280, 400),
			(100, 1860, 2280, 400),
			(100, 2300, 2280, 400),
			(100, 2740, 2280, 400),
			(100, 3180, 2280, 400)
		],
		
		'template_mix8_0p8l_grid_3top_5bottom': [  # 3L on top row, 5L below
			(100, 100, 760, 500),
			(880, 100, 760, 500),
			(1660, 100, 760, 500),
			(100, 640, 440, 500),
			(560, 640, 440, 500),
			(1020, 640, 440, 500),
			(1480, 640, 440, 500),
			(1940, 640, 440, 500)
		],
		
		'template_mix8_0p8l_grid_5top_3bottom': [  # 5L top, 3L below
			(100, 100, 440, 500),
			(560, 100, 440, 500),
			(1020, 100, 440, 500),
			(1480, 100, 440, 500),
			(1940, 100, 440, 500),
			(100, 640, 760, 500),
			(880, 640, 760, 500),
			(1660, 640, 760, 500)
		],
		
		# 9 image layouts
		
		'template_mix9_0p9l_grid_3x3': [  # 3x3 Landscape grid (even balance)
			(100, 100, 760, 500),       # Row 1: L1–L3
			(880, 100, 760, 500),
			(1660, 100, 760, 500),
			(100, 640, 760, 500),       # Row 2: L4–L6
			(880, 640, 760, 500),
			(1660, 640, 760, 500),
			(100, 1180, 760, 500),      # Row 3: L7–L9
			(880, 1180, 760, 500),
			(1660, 1180, 760, 500)
		],
		
		'template_mix9_0p9l_stack_vertical': [  # 9L stacked vertically (scroll format)
			(100, 100, 2280, 400),      # L1
			(100, 540, 2280, 400),      # L2
			(100, 980, 2280, 400),      # L3
			(100, 1420, 2280, 400),     # L4
			(100, 1860, 2280, 400),     # L5
			(100, 2300, 2280, 400),     # L6
			(100, 2740, 2280, 400),     # L7
			(100, 3180, 2280, 400),     # L8
			(100, 3620, 2280, 400)      # L9
		],
		
		'template_mix9_0p9l_grid_2x5_toprow': [  # 5L top row, 2x2 grid below + center
			(100, 100, 440, 500),       # Top L1–L5
			(560, 100, 440, 500),
			(1020, 100, 440, 500),
			(1480, 100, 440, 500),
			(1940, 100, 440, 500),
			(100, 640, 1140, 600),      # Lower grid left: L6
			(1240, 640, 1140, 600),     # Lower grid right: L7
			(100, 1280, 1140, 600),     # Bottom grid left: L8
			(1240, 1280, 1140, 600)     # Bottom grid right: L9
		],
		
		'template_mix9_0p9l_band_topgrid': [  # 3x3 banded layout, consistent widths
			(100, 100, 760, 400),       # Top band L1–L3
			(880, 100, 760, 400),
			(1660, 100, 760, 400),
			(100, 540, 760, 400),       # Middle band L4–L6
			(880, 540, 760, 400),
			(1660, 540, 760, 400),
			(100, 980, 760, 400),       # Bottom band L7–L9
			(880, 980, 760, 400),
			(1660, 980, 760, 400)
		],
		
		'template_mix9_0p9l_mosaic_leftbias': [  # 5 stacked on left, 4 grid blocks on right
			(100, 100, 1140, 500),       # Left stack L1–L5
			(100, 620, 1140, 500),
			(100, 1140, 1140, 500),
			(100, 1660, 1140, 500),
			(100, 2180, 1140, 500),
			(1240, 100, 1140, 600),      # Right grid L6–L9
			(1240, 720, 1140, 600),
			(1240, 1340, 1140, 600),
			(1240, 1960, 1140, 600)
		],
		
		'template_mix9_1p8l_stack_left': [  # 1P full-height left, 8L stacked right
			(100, 100, 760, 3308),           # Portrait (left full-height)
			(880, 100, 1500, 400),           # Landscape 1
			(880, 540, 1500, 400),           # Landscape 2
			(880, 980, 1500, 400),           # Landscape 3
			(880, 1420, 1500, 400),          # Landscape 4
			(880, 1860, 1500, 400),          # Landscape 5
			(880, 2300, 1500, 400),          # Landscape 6
			(880, 2740, 1500, 400),          # Landscape 7
			(880, 3180, 1500, 400)           # Landscape 8
		],
		
		'template_mix9_1p8l_stack_right': [  # 1P full-height right, 8L stacked left
			(1660, 100, 760, 3308),          # Portrait (right full-height)
			(100, 100, 1500, 400),           # Landscape 1
			(100, 540, 1500, 400),           # Landscape 2
			(100, 980, 1500, 400),           # Landscape 3
			(100, 1420, 1500, 400),          # Landscape 4
			(100, 1860, 1500, 400),          # Landscape 5
			(100, 2300, 1500, 400),          # Landscape 6
			(100, 2740, 1500, 400),          # Landscape 7
			(100, 3180, 1500, 400)           # Landscape 8
		],
		
		'template_mix9_1p8l_band_center': [  # 1P center column, 4L left, 4L right
			(860, 100, 760, 1300),           # Portrait (center)
			(100, 100, 720, 400),            # Landscape 1 (left top)
			(100, 540, 720, 400),            # Landscape 2
			(100, 980, 720, 400),            # Landscape 3
			(100, 1420, 720, 400),           # Landscape 4
			(1660, 100, 720, 400),           # Landscape 5 (right top)
			(1660, 540, 720, 400),           # Landscape 6
			(1660, 980, 720, 400),           # Landscape 7
			(1660, 1420, 720, 400)           # Landscape 8
		],
		
		'template_mix9_1p8l_footer_portrait': [  # 8L grid above, P full-width footer
			(100, 100, 560, 500),            # Landscape 1
			(700, 100, 560, 500),            # Landscape 2
			(1300, 100, 560, 500),           # Landscape 3
			(1900, 100, 560, 500),           # Landscape 4
			(100, 640, 560, 500),            # Landscape 5
			(700, 640, 560, 500),            # Landscape 6
			(1300, 640, 560, 500),           # Landscape 7
			(1900, 640, 560, 500),           # Landscape 8
			(100, 1200, 2280, 1600)          # Portrait (footer full-width)
		],
		
		'template_mix9_1p8l_header_portrait': [  # P at top, 8L below in bands
			(100, 100, 2280, 1000),          # Portrait (header)
			(100, 1220, 760, 400),           # Landscape 1
			(880, 1220, 760, 400),           # Landscape 2
			(1660, 1220, 760, 400),          # Landscape 3
			(100, 1660, 760, 400),           # Landscape 4
			(880, 1660, 760, 400),           # Landscape 5
			(1660, 1660, 760, 400),          # Landscape 6
			(100, 2100, 1140, 500),          # Landscape 7
			(1240, 2100, 1140, 500)          # Landscape 8
		], 
		
		'template_mix9_2p7l_stack_left': [  # 2P stacked left, 7L stacked right
			(100, 100, 1140, 1600),         # Portrait 1
			(100, 1740, 1140, 1600),        # Portrait 2
			(1240, 100, 1140, 400),         # Landscape 1
			(1240, 540, 1140, 400),         # Landscape 2
			(1240, 980, 1140, 400),         # Landscape 3
			(1240, 1420, 1140, 400),        # Landscape 4
			(1240, 1860, 1140, 400),        # Landscape 5
			(1240, 2300, 1140, 400),        # Landscape 6
			(1240, 2740, 1140, 400)         # Landscape 7
		],
		
		'template_mix9_2p7l_stack_right': [  # 2P stacked right, 7L stacked left
			(1240, 100, 1140, 1600),        # Portrait 1
			(1240, 1740, 1140, 1600),       # Portrait 2
			(100, 100, 1140, 400),          # Landscape 1
			(100, 540, 1140, 400),          # Landscape 2
			(100, 980, 1140, 400),          # Landscape 3
			(100, 1420, 1140, 400),         # Landscape 4
			(100, 1860, 1140, 400),         # Landscape 5
			(100, 2300, 1140, 400),         # Landscape 6
			(100, 2740, 1140, 400)          # Landscape 7
		],
		
		'template_mix9_2p7l_topband': [  # 3L top, 2P center, 4L bottom
			(100, 100, 760, 400),           # Landscape 1
			(880, 100, 760, 400),           # Landscape 2
			(1660, 100, 760, 400),          # Landscape 3
			(100, 540, 1140, 1100),         # Portrait 1
			(1240, 540, 1140, 1100),        # Portrait 2
			(100, 1680, 1140, 400),         # Landscape 4
			(1240, 1680, 1140, 400),        # Landscape 5
			(100, 2120, 1140, 400),         # Landscape 6
			(1240, 2120, 1140, 400)         # Landscape 7
		],
		
		'template_mix9_2p7l_centerwrap': [  # 2P center column, 3L left, 4L right
			(860, 100, 760, 1300),          # Portrait 1
			(860, 1440, 760, 1300),         # Portrait 2
			(100, 100, 720, 400),           # Landscape 1
			(100, 540, 720, 400),           # Landscape 2
			(100, 980, 720, 400),           # Landscape 3
			(1660, 100, 720, 400),          # Landscape 4
			(1660, 540, 720, 400),          # Landscape 5
			(1660, 980, 720, 400),          # Landscape 6
			(1660, 1420, 720, 400)          # Landscape 7
		],
		
		'template_mix9_2p7l_footer_portrait': [  # 7L grid above, 2P stacked at bottom
			(100, 100, 760, 500),           # Landscape 1
			(880, 100, 760, 500),           # Landscape 2
			(1660, 100, 760, 500),          # Landscape 3
			(100, 640, 760, 500),           # Landscape 4
			(880, 640, 760, 500),           # Landscape 5
			(1660, 640, 760, 500),          # Landscape 6
			(100, 1180, 2280, 500),         # Landscape 7
			(100, 1720, 1140, 1400),        # Portrait 1
			(1240, 1720, 1140, 1400)        # Portrait 2
		],
		
		'template_mix9_3p6l_stack_left': [  # 3P stacked left, 6L stacked right
			(100, 100, 1140, 1000),         # Portrait 1
			(100, 1140, 1140, 1000),        # Portrait 2
			(100, 2280, 1140, 1000),        # Portrait 3
			(1240, 100, 1140, 500),         # Landscape 1
			(1240, 640, 1140, 500),         # Landscape 2
			(1240, 1180, 1140, 500),        # Landscape 3
			(1240, 1720, 1140, 500),        # Landscape 4
			(1240, 2260, 1140, 500),        # Landscape 5
			(1240, 2800, 1140, 500)         # Landscape 6
		],
		
		'template_mix9_3p6l_stack_right': [  # 3P stacked right, 6L stacked left
			(1240, 100, 1140, 1000),        # Portrait 1
			(1240, 1140, 1140, 1000),       # Portrait 2
			(1240, 2280, 1140, 1000),       # Portrait 3
			(100, 100, 1140, 500),          # Landscape 1
			(100, 640, 1140, 500),          # Landscape 2
			(100, 1180, 1140, 500),         # Landscape 3
			(100, 1720, 1140, 500),         # Landscape 4
			(100, 2260, 1140, 500),         # Landscape 5
			(100, 2800, 1140, 500)          # Landscape 6
		],
		
		'template_mix9_3p6l_centerwrap': [  # 3P center column, 3L left, 3L right
			(860, 100, 760, 800),           # Portrait 1
			(860, 920, 760, 800),           # Portrait 2
			(860, 1740, 760, 800),          # Portrait 3
			(100, 100, 720, 500),           # Landscape 1 (left)
			(100, 640, 720, 500),           # Landscape 2
			(100, 1180, 720, 500),          # Landscape 3
			(1660, 100, 720, 500),          # Landscape 4 (right)
			(1660, 640, 720, 500),          # Landscape 5
			(1660, 1180, 720, 500)          # Landscape 6
		],
		
		'template_mix9_3p6l_grid_top': [  # 3P row top, 2x3 L grid below
			(100, 100, 760, 1000),          # Portrait 1
			(880, 100, 760, 1000),          # Portrait 2
			(1660, 100, 760, 1000),         # Portrait 3
			(100, 1140, 760, 500),          # Landscape 1
			(880, 1140, 760, 500),          # Landscape 2
			(1660, 1140, 760, 500),         # Landscape 3
			(100, 1680, 760, 500),          # Landscape 4
			(880, 1680, 760, 500),          # Landscape 5
			(1660, 1680, 760, 500)          # Landscape 6
		],
		
		'template_mix9_3p6l_band_footer': [  # 6L top banded, 3P bottom stacked
			(100, 100, 760, 500),           # Landscape 1
			(880, 100, 760, 500),           # Landscape 2
			(1660, 100, 760, 500),          # Landscape 3
			(100, 640, 760, 500),           # Landscape 4
			(880, 640, 760, 500),           # Landscape 5
			(1660, 640, 760, 500),          # Landscape 6
			(100, 1180, 1140, 1100),        # Portrait 1
			(1240, 1180, 1140, 1100),       # Portrait 2
			(100, 2400, 2280, 900)          # Portrait 3 (centered footer)
		], 
		
		'template_mix9_4p5l_stack_left': [  # 4P stacked left, 5L stacked right
			(100, 100, 1140, 750),          # Portrait 1
			(100, 870, 1140, 750),          # Portrait 2
			(100, 1740, 1140, 750),         # Portrait 3
			(100, 2610, 1140, 750),         # Portrait 4
			(1240, 100, 1140, 500),         # Landscape 1
			(1240, 640, 1140, 500),         # Landscape 2
			(1240, 1180, 1140, 500),        # Landscape 3
			(1240, 1720, 1140, 500),        # Landscape 4
			(1240, 2260, 1140, 500)         # Landscape 5
		],
		
		'template_mix9_4p5l_stack_right': [  # 4P stacked right, 5L stacked left
			(1240, 100, 1140, 750),         # Portrait 1
			(1240, 870, 1140, 750),         # Portrait 2
			(1240, 1740, 1140, 750),        # Portrait 3
			(1240, 2610, 1140, 750),        # Portrait 4
			(100, 100, 1140, 500),          # Landscape 1
			(100, 640, 1140, 500),          # Landscape 2
			(100, 1180, 1140, 500),         # Landscape 3
			(100, 1720, 1140, 500),         # Landscape 4
			(100, 2260, 1140, 500)          # Landscape 5
		],
		
		'template_mix9_4p5l_gridband_center': [  # 2x2 P grid center, L band top/bottom
			(100, 100, 760, 400),           # Landscape 1 (Top Left)
			(880, 100, 760, 400),           # Landscape 2 (Top Center)
			(1660, 100, 760, 400),          # Landscape 3 (Top Right)
			(100, 540, 1140, 1000),         # Portrait 1
			(1240, 540, 1140, 1000),        # Portrait 2
			(100, 1580, 1140, 1000),        # Portrait 3
			(1240, 1580, 1140, 1000),       # Portrait 4
			(100, 2700, 1140, 400),         # Landscape 4 (Bottom Left)
			(1240, 2700, 1140, 400)         # Landscape 5 (Bottom Right)
		],
		
		'template_mix9_4p5l_column_wrap': [  # 2P center column, L wrap left/right
			(860, 100, 760, 1000),          # Portrait 1
			(860, 1140, 760, 1000),         # Portrait 2
			(860, 2280, 760, 500),          # Portrait 3
			(860, 2800, 760, 500),          # Portrait 4
			(100, 100, 720, 400),           # Landscape 1 (left)
			(100, 540, 720, 400),           # Landscape 2
			(1660, 100, 720, 400),          # Landscape 3 (right)
			(1660, 540, 720, 400),          # Landscape 4
			(1660, 980, 720, 400)           # Landscape 5
		],
		
		'template_mix9_4p5l_footer_portraits': [  # 5L grid top, 4P bottom stacked
			(100, 100, 560, 500),           # Landscape 1
			(700, 100, 560, 500),           # Landscape 2
			(1300, 100, 560, 500),          # Landscape 3
			(1900, 100, 560, 500),          # Landscape 4
			(100, 640, 2280, 500),          # Landscape 5
			(100, 1180, 1140, 1000),        # Portrait 1
			(1240, 1180, 1140, 1000),       # Portrait 2
			(100, 2280, 1140, 1000),        # Portrait 3
			(1240, 2280, 1140, 1000)        # Portrait 4
		],
		
		'template_mix9_5p4l_stack_left': [  # 5P stacked left, 4L stacked right
			(100, 100, 1140, 620),          # Portrait 1
			(100, 740, 1140, 620),          # Portrait 2
			(100, 1380, 1140, 620),         # Portrait 3
			(100, 2020, 1140, 620),         # Portrait 4
			(100, 2660, 1140, 620),         # Portrait 5
			(1240, 100, 1140, 700),         # Landscape 1
			(1240, 820, 1140, 700),         # Landscape 2
			(1240, 1540, 1140, 700),        # Landscape 3
			(1240, 2260, 1140, 700)         # Landscape 4
		],
		
		'template_mix9_5p4l_stack_right': [  # 5P stacked right, 4L stacked left
			(1240, 100, 1140, 620),         # Portrait 1
			(1240, 740, 1140, 620),         # Portrait 2
			(1240, 1380, 1140, 620),        # Portrait 3
			(1240, 2020, 1140, 620),        # Portrait 4
			(1240, 2660, 1140, 620),        # Portrait 5
			(100, 100, 1140, 700),          # Landscape 1
			(100, 820, 1140, 700),          # Landscape 2
			(100, 1540, 1140, 700),         # Landscape 3
			(100, 2260, 1140, 700)          # Landscape 4
		],
		
		'template_mix9_5p4l_grid_topband': [  # 5P in 2x2+1 top grid, 4L banded below
			(100, 100, 1140, 900),          # Portrait 1
			(1240, 100, 1140, 900),         # Portrait 2
			(100, 1020, 1140, 900),         # Portrait 3
			(1240, 1020, 1140, 900),        # Portrait 4
			(660, 1940, 1140, 500),         # Portrait 5 (centered below)
			(100, 2480, 1140, 400),         # Landscape 1
			(1240, 2480, 1140, 400),        # Landscape 2
			(100, 2920, 1140, 400),         # Landscape 3
			(1240, 2920, 1140, 400)         # Landscape 4
		],
		
		'template_mix9_5p4l_footer_grid': [  # 4L grid top, 5P bottom stacked
			(100, 100, 1140, 500),          # Landscape 1
			(1240, 100, 1140, 500),         # Landscape 2
			(100, 640, 1140, 500),          # Landscape 3
			(1240, 640, 1140, 500),         # Landscape 4
			(100, 1180, 1140, 650),         # Portrait 1
			(1240, 1180, 1140, 650),        # Portrait 2
			(100, 1860, 1140, 650),         # Portrait 3
			(1240, 1860, 1140, 650),        # Portrait 4
			(100, 2540, 2280, 600)          # Portrait 5 (bottom wide)
		],
		
		'template_mix9_5p4l_center_column': [  # 5P center column, 2L left, 2L right
			(860, 100, 760, 600),           # Portrait 1
			(860, 740, 760, 600),           # Portrait 2
			(860, 1380, 760, 600),          # Portrait 3
			(860, 2020, 760, 600),          # Portrait 4
			(860, 2660, 760, 600),          # Portrait 5
			(100, 100, 720, 600),           # Landscape 1 (left top)
			(100, 740, 720, 600),           # Landscape 2
			(1660, 100, 720, 600),          # Landscape 3 (right top)
			(1660, 740, 720, 600)           # Landscape 4
		],
		
		'template_mix9_6p3l_stack_left': [  # 6P stacked left, 3L stacked right
			(100, 100, 1140, 540),           # Portrait 1
			(100, 660, 1140, 540),           # Portrait 2
			(100, 1220, 1140, 540),          # Portrait 3
			(100, 1780, 1140, 540),          # Portrait 4
			(100, 2340, 1140, 540),          # Portrait 5
			(100, 2900, 1140, 540),          # Portrait 6
			(1240, 100, 1140, 900),          # Landscape 1
			(1240, 1020, 1140, 900),         # Landscape 2
			(1240, 1940, 1140, 900)          # Landscape 3
		],
		
		'template_mix9_6p3l_stack_right': [  # 6P stacked right, 3L stacked left
			(1240, 100, 1140, 540),          # Portrait 1
			(1240, 660, 1140, 540),          # Portrait 2
			(1240, 1220, 1140, 540),         # Portrait 3
			(1240, 1780, 1140, 540),         # Portrait 4
			(1240, 2340, 1140, 540),         # Portrait 5
			(1240, 2900, 1140, 540),         # Portrait 6
			(100, 100, 1140, 900),           # Landscape 1
			(100, 1020, 1140, 900),          # Landscape 2
			(100, 1940, 1140, 900)           # Landscape 3
		],
		
		'template_mix9_6p3l_grid_top': [  # 2x3 Portrait grid top, 3L bottom band
			(100, 100, 760, 900),           # Portrait 1
			(880, 100, 760, 900),           # Portrait 2
			(1660, 100, 760, 900),          # Portrait 3
			(100, 1020, 760, 900),          # Portrait 4
			(880, 1020, 760, 900),          # Portrait 5
			(1660, 1020, 760, 900),         # Portrait 6
			(100, 1940, 760, 500),          # Landscape 1
			(880, 1940, 760, 500),          # Landscape 2
			(1660, 1940, 760, 500)          # Landscape 3
		],
		
		'template_mix9_6p3l_band_footer': [  # 3L top band, 6P below stacked
			(100, 100, 760, 500),           # Landscape 1
			(880, 100, 760, 500),           # Landscape 2
			(1660, 100, 760, 500),          # Landscape 3
			(100, 640, 1140, 620),          # Portrait 1
			(1240, 640, 1140, 620),         # Portrait 2
			(100, 1280, 1140, 620),         # Portrait 3
			(1240, 1280, 1140, 620),        # Portrait 4
			(100, 1920, 1140, 620),         # Portrait 5
			(1240, 1920, 1140, 620)         # Portrait 6
		],
		
		'template_mix9_7p2l_stack_left': [  # 7P stacked left, 2L stacked right
			(100, 100, 1140, 460),           # Portrait 1
			(100, 580, 1140, 460),           # Portrait 2
			(100, 1060, 1140, 460),          # Portrait 3
			(100, 1540, 1140, 460),          # Portrait 4
			(100, 2020, 1140, 460),          # Portrait 5
			(100, 2500, 1140, 460),          # Portrait 6
			(100, 2980, 1140, 460),          # Portrait 7
			(1240, 100, 1140, 1100),         # Landscape 1
			(1240, 1240, 1140, 1100)         # Landscape 2
		],
		
		'template_mix9_7p2l_stack_right': [  # 7P stacked right, 2L stacked left
			(1240, 100, 1140, 460),          # Portrait 1
			(1240, 580, 1140, 460),          # Portrait 2
			(1240, 1060, 1140, 460),         # Portrait 3
			(1240, 1540, 1140, 460),         # Portrait 4
			(1240, 2020, 1140, 460),         # Portrait 5
			(1240, 2500, 1140, 460),         # Portrait 6
			(1240, 2980, 1140, 460),         # Portrait 7
			(100, 100, 1140, 1100),          # Landscape 1
			(100, 1240, 1140, 1100)          # Landscape 2
		],
		
		'template_mix9_7p2l_banded_center': [  # 3P top, 2L mid, 4P bottom
			(100, 100, 760, 800),            # Portrait 1
			(880, 100, 760, 800),            # Portrait 2
			(1660, 100, 760, 800),           # Portrait 3
			(100, 920, 1140, 600),           # Landscape 1
			(1240, 920, 1140, 600),          # Landscape 2
			(100, 1560, 760, 800),           # Portrait 4
			(880, 1560, 760, 800),           # Portrait 5
			(1660, 1560, 760, 800),          # Portrait 6
			(100, 2380, 1140, 800)           # Portrait 7 (bottom center)
		],
		
		'template_mix9_8p1l_stack_left': [  # 8P stacked left, 1L full-width right
			(100, 100, 1140, 400),           # Portrait 1
			(100, 520, 1140, 400),           # Portrait 2
			(100, 940, 1140, 400),           # Portrait 3
			(100, 1360, 1140, 400),          # Portrait 4
			(100, 1780, 1140, 400),          # Portrait 5
			(100, 2200, 1140, 400),          # Portrait 6
			(100, 2620, 1140, 400),          # Portrait 7
			(100, 3040, 1140, 400),          # Portrait 8
			(1240, 100, 1140, 3340)          # Landscape (right full-height)
		],
		
		'template_mix9_8p1l_stack_right': [  # 8P stacked right, 1L full-width left
			(1240, 100, 1140, 400),          # Portrait 1
			(1240, 520, 1140, 400),          # Portrait 2
			(1240, 940, 1140, 400),          # Portrait 3
			(1240, 1360, 1140, 400),         # Portrait 4
			(1240, 1780, 1140, 400),         # Portrait 5
			(1240, 2200, 1140, 400),         # Portrait 6
			(1240, 2620, 1140, 400),         # Portrait 7
			(1240, 3040, 1140, 400),         # Portrait 8
			(100, 100, 1140, 3340)           # Landscape (left full-height)
		],
		
		'template_mix9_8p1l_footer_band': [  # 2x4 Portrait grid, Landscape at bottom
			(100, 100, 1140, 800),           # Portrait 1
			(1240, 100, 1140, 800),          # Portrait 2
			(100, 920, 1140, 800),           # Portrait 3
			(1240, 920, 1140, 800),          # Portrait 4
			(100, 1740, 1140, 800),          # Portrait 5
			(1240, 1740, 1140, 800),         # Portrait 6
			(100, 2560, 1140, 800),          # Portrait 7
			(1240, 2560, 1140, 800),         # Portrait 8
			(100, 3380, 2280, 400)           # Landscape (footer band)
		],
		
		'template_mix9_9p_stack_left': [  # 9P stacked left column
			(100, 100, 1140, 360),           # Portrait 1
			(100, 480, 1140, 360),           # Portrait 2
			(100, 860, 1140, 360),           # Portrait 3
			(100, 1240, 1140, 360),          # Portrait 4
			(100, 1620, 1140, 360),          # Portrait 5
			(100, 2000, 1140, 360),          # Portrait 6
			(100, 2380, 1140, 360),          # Portrait 7
			(100, 2760, 1140, 360),          # Portrait 8
			(100, 3140, 1140, 360)           # Portrait 9
		],
		
		'template_mix9_9p_stack_right': [  # 9P stacked right column
			(1240, 100, 1140, 360),          # Portrait 1
			(1240, 480, 1140, 360),          # Portrait 2
			(1240, 860, 1140, 360),          # Portrait 3
			(1240, 1240, 1140, 360),         # Portrait 4
			(1240, 1620, 1140, 360),         # Portrait 5
			(1240, 2000, 1140, 360),         # Portrait 6
			(1240, 2380, 1140, 360),         # Portrait 7
			(1240, 2760, 1140, 360),         # Portrait 8
			(1240, 3140, 1140, 360)          # Portrait 9
		],
		
		'template_mix9_9p_grid_3x3': [  # 3x3 portrait grid
			(100, 100, 760, 1000),           # Row 1: Portrait 1
			(880, 100, 760, 1000),           # Portrait 2
			(1660, 100, 760, 1000),          # Portrait 3
			(100, 1140, 760, 1000),          # Row 2: Portrait 4
			(880, 1140, 760, 1000),          # Portrait 5
			(1660, 1140, 760, 1000),         # Portrait 6
			(100, 2180, 760, 1000),          # Row 3: Portrait 7
			(880, 2180, 760, 1000),          # Portrait 8
			(1660, 2180, 760, 1000)          # Portrait 9
		], 
		
		'template_mix10_6p4l_mosaic_topbottom': [
			(100, 100, 2280, 400),           # Landscape 1 (top full-width)
			
			(100, 520, 760, 800),            # Portrait 1
			(880, 520, 760, 800),            # Portrait 2
			(1660, 520, 760, 800),           # Landscape 2 (right)
			
			(100, 1340, 760, 800),           # Portrait 3
			(880, 1340, 760, 800),           # Portrait 4
			(1660, 1340, 760, 800),          # Portrait 5
			
			(100, 2160, 1140, 800),          # Landscape 3
			(1240, 2160, 1140, 800),         # Portrait 6
			
			(100, 2980, 1140, 800),          # Portrait 7
			(1240, 2980, 1140, 800)          # Landscape 4 (bottom right)
		],
		
		'template_mix10_0p10l_grid_5x2': [  # 5 columns × 2 rows
			(100, 100, 440, 500),           # Top row: L1–L5
			(560, 100, 440, 500),
			(1020, 100, 440, 500),
			(1480, 100, 440, 500),
			(1940, 100, 440, 500),
			(100, 640, 440, 500),           # Bottom row: L6–L10
			(560, 640, 440, 500),
			(1020, 640, 440, 500),
			(1480, 640, 440, 500),
			(1940, 640, 440, 500)
		],
		
		'template_mix10_0p10l_stack_vertical': [  # 10L stacked vertically
			(100, 100, 2280, 360),          # Landscape 1
			(100, 480, 2280, 360),
			(100, 860, 2280, 360),
			(100, 1240, 2280, 360),
			(100, 1620, 2280, 360),
			(100, 2000, 2280, 360),
			(100, 2380, 2280, 360),
			(100, 2760, 2280, 360),
			(100, 3140, 2280, 360),
			(100, 3520, 2280, 360)
		],
		
		'template_mix10_0p10l_grid_3x3_plus_1': [  # 3x3 grid + 1 full-width banner
			(100, 100, 760, 500),           # Grid row 1: L1–L3
			(880, 100, 760, 500),
			(1660, 100, 760, 500),
			(100, 640, 760, 500),           # Grid row 2: L4–L6
			(880, 640, 760, 500),
			(1660, 640, 760, 500),
			(100, 1180, 760, 500),          # Grid row 3: L7–L9
			(880, 1180, 760, 500),
			(1660, 1180, 760, 500),
			(100, 1720, 2280, 500)          # Bottom banner: L10
		],
		
		'template_mix10_0p10l_columns_leftbias': [  # 6L stacked left, 4L block right
			(100, 100, 1140, 400),          # Left stack: L1–L6
			(100, 520, 1140, 400),
			(100, 940, 1140, 400),
			(100, 1360, 1140, 400),
			(100, 1780, 1140, 400),
			(100, 2200, 1140, 400),
			(1240, 100, 1140, 600),         # Right column grid: L7–L10
			(1240, 720, 1140, 600),
			(1240, 1340, 1140, 600),
			(1240, 1960, 1140, 600)
		],
		
		'template_mix10_0p10l_rows_split': [  # 2 rows of 5L with alternating widths
			(100, 100, 560, 500),           # Row 1: L1–L5
			(700, 100, 560, 500),
			(1300, 100, 560, 500),
			(1900, 100, 560, 500),
			(100, 640, 1140, 500),          # Row 2: L6–L10 (some double-wide)
			(1240, 640, 560, 500),
			(1840, 640, 560, 500),
			(100, 1180, 1140, 500),
			(1240, 1180, 1140, 500)
		],
		
		'template_mix10_1p9l_stack_left': [  # 1P left, 9L stacked right
			(100, 100, 760, 3308),            # Portrait (full-height left)
			(880, 100, 1500, 360),            # Landscape 1
			(880, 480, 1500, 360),            # Landscape 2
			(880, 860, 1500, 360),            # Landscape 3
			(880, 1240, 1500, 360),           # Landscape 4
			(880, 1620, 1500, 360),           # Landscape 5
			(880, 2000, 1500, 360),           # Landscape 6
			(880, 2380, 1500, 360),           # Landscape 7
			(880, 2760, 1500, 360),           # Landscape 8
			(880, 3140, 1500, 360)            # Landscape 9
		],
		
		'template_mix10_1p9l_stack_right': [  # 1P right, 9L stacked left
			(1660, 100, 760, 3308),           # Portrait (full-height right)
			(100, 100, 1500, 360),            # Landscape 1
			(100, 480, 1500, 360),            # Landscape 2
			(100, 860, 1500, 360),            # Landscape 3
			(100, 1240, 1500, 360),           # Landscape 4
			(100, 1620, 1500, 360),           # Landscape 5
			(100, 2000, 1500, 360),           # Landscape 6
			(100, 2380, 1500, 360),           # Landscape 7
			(100, 2760, 1500, 360),           # Landscape 8
			(100, 3140, 1500, 360)            # Landscape 9
		],
		
		'template_mix10_1p9l_top_portrait': [  # 1P top banner, 3x3 L grid below
			(100, 100, 2280, 600),            # Portrait (banner)
			(100, 740, 760, 500),             # Row 1: Landscape 1
			(880, 740, 760, 500),             # Landscape 2
			(1660, 740, 760, 500),            # Landscape 3
			(100, 1280, 760, 500),            # Row 2: Landscape 4
			(880, 1280, 760, 500),            # Landscape 5
			(1660, 1280, 760, 500),           # Landscape 6
			(100, 1820, 760, 500),            # Row 3: Landscape 7
			(880, 1820, 760, 500),            # Landscape 8
			(1660, 1820, 760, 500)            # Landscape 9
		],
		
		'template_mix10_1p9l_footer_portrait': [  # 3x3 L grid top, 1P footer
			(100, 100, 760, 500),             # Row 1: Landscape 1
			(880, 100, 760, 500),             # Landscape 2
			(1660, 100, 760, 500),            # Landscape 3
			(100, 640, 760, 500),             # Row 2: Landscape 4
			(880, 640, 760, 500),             # Landscape 5
			(1660, 640, 760, 500),            # Landscape 6
			(100, 1180, 760, 500),            # Row 3: Landscape 7
			(880, 1180, 760, 500),            # Landscape 8
			(1660, 1180, 760, 500),           # Landscape 9
			(100, 1720, 2280, 1000)           # Portrait (footer full-width)
		],
		
		'template_mix10_1p9l_center_column': [  # 1P center, 4L left, 5L right
			(860, 100, 760, 1300),            # Portrait
			(100, 100, 720, 400),             # Landscape 1 (left)
			(100, 540, 720, 400),             # Landscape 2
			(100, 980, 720, 400),             # Landscape 3
			(100, 1420, 720, 400),            # Landscape 4
			(1660, 100, 720, 360),            # Landscape 5 (right)
			(1660, 480, 720, 360),            # Landscape 6
			(1660, 860, 720, 360),            # Landscape 7
			(1660, 1240, 720, 360),           # Landscape 8
			(1660, 1620, 720, 360)            # Landscape 9
		],
		
		'template_mix10_2p8l_stack_left': [  # 2P stacked left, 8L stacked right
			(100, 100, 1140, 1600),         # Portrait 1
			(100, 1740, 1140, 1600),        # Portrait 2
			(1240, 100, 1140, 400),         # Landscape 1
			(1240, 540, 1140, 400),         # Landscape 2
			(1240, 980, 1140, 400),         # Landscape 3
			(1240, 1420, 1140, 400),        # Landscape 4
			(1240, 1860, 1140, 400),        # Landscape 5
			(1240, 2300, 1140, 400),        # Landscape 6
			(1240, 2740, 1140, 400),        # Landscape 7
			(1240, 3180, 1140, 400)         # Landscape 8
		],
		
		'template_mix10_2p8l_stack_right': [  # 2P stacked right, 8L stacked left
			(1240, 100, 1140, 1600),        # Portrait 1
			(1240, 1740, 1140, 1600),       # Portrait 2
			(100, 100, 1140, 400),          # Landscape 1
			(100, 540, 1140, 400),          # Landscape 2
			(100, 980, 1140, 400),          # Landscape 3
			(100, 1420, 1140, 400),         # Landscape 4
			(100, 1860, 1140, 400),         # Landscape 5
			(100, 2300, 1140, 400),         # Landscape 6
			(100, 2740, 1140, 400),         # Landscape 7
			(100, 3180, 1140, 400)          # Landscape 8
		],
		
		'template_mix10_2p8l_grid_topband': [  # 2P top row, 8L grid below
			(100, 100, 1140, 1000),         # Portrait 1
			(1240, 100, 1140, 1000),        # Portrait 2
			(100, 1140, 560, 500),          # Landscape 1
			(700, 1140, 560, 500),          # Landscape 2
			(1300, 1140, 560, 500),         # Landscape 3
			(1900, 1140, 560, 500),         # Landscape 4
			(100, 1680, 560, 500),          # Landscape 5
			(700, 1680, 560, 500),          # Landscape 6
			(1300, 1680, 560, 500),         # Landscape 7
			(1900, 1680, 560, 500)          # Landscape 8
		],
		
		'template_mix10_2p8l_footer_band': [  # 8L grid above, 2P bottom stacked
			(100, 100, 560, 500),           # Landscape 1
			(700, 100, 560, 500),
			(1300, 100, 560, 500),
			(1900, 100, 560, 500),
			(100, 640, 560, 500),           # Landscape 5
			(700, 640, 560, 500),
			(1300, 640, 560, 500),
			(1900, 640, 560, 500),
			(100, 1180, 1140, 1200),        # Portrait 1
			(1240, 1180, 1140, 1200)        # Portrait 2
		],
		
		'template_mix10_2p8l_mosaic_centerwrap': [  # Mixed-size mosaic (mimics your original style)
			(100, 100, 2280, 400),          # Landscape 1 (top banner)
			(100, 520, 760, 800),           # Portrait 1
			(880, 520, 760, 800),           # Landscape 2
			(1660, 520, 720, 800),          # Landscape 3
			(100, 1340, 760, 800),          # Landscape 4
			(880, 1340, 760, 800),          # Portrait 2
			(1660, 1340, 720, 800),         # Landscape 5
			(100, 2160, 1140, 600),         # Landscape 6
			(1240, 2160, 1140, 600),        # Landscape 7
			(100, 2780, 2280, 400)          # Landscape 8 (footer banner)
		],
		
		'template_mix10_3p7l_stack_left': [  # 3P stacked left, 7L stacked right
			(100, 100, 1140, 1000),         # Portrait 1
			(100, 1140, 1140, 1000),        # Portrait 2
			(100, 2280, 1140, 1000),        # Portrait 3
			(1240, 100, 1140, 400),         # Landscape 1
			(1240, 540, 1140, 400),
			(1240, 980, 1140, 400),
			(1240, 1420, 1140, 400),
			(1240, 1860, 1140, 400),
			(1240, 2300, 1140, 400),
			(1240, 2740, 1140, 400)
		],
		
		'template_mix10_3p7l_stack_right': [  # 3P stacked right, 7L stacked left
			(1240, 100, 1140, 1000),        # Portrait 1
			(1240, 1140, 1140, 1000),       # Portrait 2
			(1240, 2280, 1140, 1000),       # Portrait 3
			(100, 100, 1140, 400),          # Landscape 1
			(100, 540, 1140, 400),
			(100, 980, 1140, 400),
			(100, 1420, 1140, 400),
			(100, 1860, 1140, 400),
			(100, 2300, 1140, 400),
			(100, 2740, 1140, 400)
		],
		
		'template_mix10_3p7l_band_grid': [  # 3P top row, 7L in mixed grid below
			(100, 100, 760, 1000),          # Portrait 1
			(880, 100, 760, 1000),
			(1660, 100, 760, 1000),
			(100, 1140, 560, 500),          # Landscape 1
			(700, 1140, 560, 500),
			(1300, 1140, 560, 500),
			(1900, 1140, 560, 500),
			(100, 1680, 760, 500),          # Landscape 5
			(880, 1680, 760, 500),
			(1660, 1680, 760, 500)
		],
		
		'template_mix10_3p7l_footer_portraits': [  # 7L grid top, 3P bottom stacked
			(100, 100, 760, 500),           # Landscape 1
			(880, 100, 760, 500),
			(1660, 100, 760, 500),
			(100, 640, 760, 500),
			(880, 640, 760, 500),
			(1660, 640, 760, 500),
			(100, 1180, 2280, 500),         # Landscape 7
			(100, 1720, 1140, 1000),        # Portrait 1
			(1240, 1720, 1140, 1000),       # Portrait 2
			(100, 2820, 2280, 688)          # Portrait 3 (footer full-width)
		],
		
		'template_mix10_3p7l_mosaic_centerband': [  # Mosaic with L-band + 3P center column
			(100, 100, 760, 400),           # Landscape 1
			(880, 100, 760, 400),
			(1660, 100, 760, 400),
			(100, 540, 760, 400),           # Landscape 4
			(880, 540, 760, 400),
			(1660, 540, 760, 400),
			(100, 980, 760, 400),           # Landscape 7
			(860, 1000, 760, 800),          # Portrait 1 (center)
			(860, 1820, 760, 800),          # Portrait 2 (center)
			(860, 2640, 760, 800)           # Portrait 3 (center)
		], 
		
		'template_mix10_4p6l_stack_left': [  # 4P stacked left, 6L stacked right
			(100, 100, 1140, 800),          # Portrait 1
			(100, 920, 1140, 800),
			(100, 1740, 1140, 800),
			(100, 2560, 1140, 800),
			(1240, 100, 1140, 500),         # Landscape 1
			(1240, 640, 1140, 500),
			(1240, 1180, 1140, 500),
			(1240, 1720, 1140, 500),
			(1240, 2260, 1140, 500),
			(1240, 2800, 1140, 500)
		],
		
		'template_mix10_4p6l_stack_right': [  # 4P stacked right, 6L stacked left
			(1240, 100, 1140, 800),         # Portrait 1
			(1240, 920, 1140, 800),
			(1240, 1740, 1140, 800),
			(1240, 2560, 1140, 800),
			(100, 100, 1140, 500),          # Landscape 1
			(100, 640, 1140, 500),
			(100, 1180, 1140, 500),
			(100, 1720, 1140, 500),
			(100, 2260, 1140, 500),
			(100, 2800, 1140, 500)
		],
		
		'template_mix10_4p6l_grid_top': [  # 2x2 Portrait grid top, 6L grid below
			(100, 100, 1140, 1000),         # Portrait 1
			(1240, 100, 1140, 1000),
			(100, 1140, 1140, 1000),
			(1240, 1140, 1140, 1000),
			(100, 2280, 760, 400),          # Landscape 1
			(880, 2280, 760, 400),
			(1660, 2280, 760, 400),
			(100, 2720, 760, 400),          # Landscape 4
			(880, 2720, 760, 400),
			(1660, 2720, 760, 400)
		],
		
		'template_mix10_4p6l_footer_portraits': [  # 6L grid top, 4P stacked below
			(100, 100, 760, 500),           # Landscape 1
			(880, 100, 760, 500),
			(1660, 100, 760, 500),
			(100, 640, 760, 500),
			(880, 640, 760, 500),
			(1660, 640, 760, 500),
			(100, 1180, 1140, 800),         # Portrait 1
			(1240, 1180, 1140, 800),        # Portrait 2
			(100, 2000, 1140, 800),         # Portrait 3
			(1240, 2000, 1140, 800)         # Portrait 4
		],
		
		'template_mix10_4p6l_mosaic_bandsplit': [  #  Mosaic: top L, middle Ps, bottom Ls
			(100, 100, 2280, 400),          # Landscape 1 (top)
			(100, 520, 1140, 900),          # Portrait 1
			(1240, 520, 1140, 900),         # Portrait 2
			(100, 1440, 1140, 900),         # Portrait 3
			(1240, 1440, 1140, 900),        # Portrait 4
			(100, 2360, 760, 400),          # Landscape 2
			(880, 2360, 760, 400),
			(1660, 2360, 760, 400),         # Landscape 4
			(100, 2800, 1140, 400),         # Landscape 5
			(1240, 2800, 1140, 400)         # Landscape 6
		],
		
		'template_mix10_5p5l_stack_left': [  # 5P stacked left, 5L stacked right
			(100, 100, 1140, 620),           # Portrait 1
			(100, 740, 1140, 620),
			(100, 1380, 1140, 620),
			(100, 2020, 1140, 620),
			(100, 2660, 1140, 620),
			(1240, 100, 1140, 600),          # Landscape 1
			(1240, 720, 1140, 600),
			(1240, 1340, 1140, 600),
			(1240, 1960, 1140, 600),
			(1240, 2580, 1140, 600)
		],
		
		'template_mix10_5p5l_stack_right': [  # 5P stacked right, 5L stacked left
			(1240, 100, 1140, 620),          # Portrait 1
			(1240, 740, 1140, 620),
			(1240, 1380, 1140, 620),
			(1240, 2020, 1140, 620),
			(1240, 2660, 1140, 620),
			(100, 100, 1140, 600),           # Landscape 1
			(100, 720, 1140, 600),
			(100, 1340, 1140, 600),
			(100, 1960, 1140, 600),
			(100, 2580, 1140, 600)
		],
		
		'template_mix10_5p5l_grid_topband': [  # 2x3 Portrait grid top, 5L bottom grid
			(100, 100, 760, 900),            # Portrait 1
			(880, 100, 760, 900),
			(1660, 100, 760, 900),
			(100, 1020, 760, 900),           # Portrait 4
			(880, 1020, 760, 900),           # Portrait 5
			(100, 1940, 880, 500),           # Landscape 1
			(1000, 1940, 880, 500),
			(1900, 1940, 480, 500),          # Landscape 3
			(100, 2480, 1140, 500),
			(1240, 2480, 1140, 500)          # Landscape 5
		],
		
		'template_mix10_5p5l_footer_portraits': [  # 5L grid top, 5P below stacked
			(100, 100, 560, 500),            # Landscape 1
			(700, 100, 560, 500),
			(1300, 100, 560, 500),
			(1900, 100, 560, 500),
			(100, 640, 2280, 500),           # Landscape 5 (band)
			(100, 1180, 1140, 700),          # Portrait 1
			(1240, 1180, 1140, 700),
			(100, 1900, 1140, 700),
			(1240, 1900, 1140, 700),
			(100, 2620, 2280, 500)           # Portrait 5 (footer wide)
		],
		
		'template_mix10_5p5l_mosaic_centerwrap': [  # Mosaic: Ps in middle, L wrap left/right
			(100, 100, 760, 400),            # Landscape 1 (top left)
			(880, 100, 760, 400),            # Landscape 2 (top center)
			(1660, 100, 760, 400),           # Landscape 3 (top right)
			(100, 540, 760, 400),            # Landscape 4
			(1660, 540, 760, 400),           # Landscape 5
			(860, 1000, 760, 620),           # Portrait 1 (center)
			(860, 1640, 760, 620),           # Portrait 2
			(860, 2260, 760, 620),           # Portrait 3
			(100, 2880, 1140, 600),          # Portrait 4 (bottom left)
			(1240, 2880, 1140, 600)          # Portrait 5 (bottom right)
		],
		
		'template_mix10_6p4l_stack_left': [  # 6P stacked left, 4L stacked right
			(100, 100, 1140, 540),       # Portrait 1
			(100, 660, 1140, 540),       # Portrait 2
			(100, 1220, 1140, 540),      # Portrait 3
			(100, 1780, 1140, 540),      # Portrait 4
			(100, 2340, 1140, 540),      # Portrait 5
			(100, 2900, 1140, 540),      # Portrait 6
			(1240, 100, 1140, 700),      # Landscape 1
			(1240, 820, 1140, 700),      # Landscape 2
			(1240, 1540, 1140, 700),     # Landscape 3
			(1240, 2260, 1140, 700)      # Landscape 4
		],
		
		'template_mix10_6p4l_stack_right': [  # 6P stacked right, 4L stacked left
			(1240, 100, 1140, 540),      # Portrait 1
			(1240, 660, 1140, 540),      # Portrait 2
			(1240, 1220, 1140, 540),     # Portrait 3
			(1240, 1780, 1140, 540),     # Portrait 4
			(1240, 2340, 1140, 540),     # Portrait 5
			(1240, 2900, 1140, 540),     # Portrait 6
			(100, 100, 1140, 700),       # Landscape 1
			(100, 820, 1140, 700),       # Landscape 2
			(100, 1540, 1140, 700),      # Landscape 3
			(100, 2260, 1140, 700)       # Landscape 4
		],
		
		'template_mix10_6p4l_topband': [  # 4L in top band, 3x2 Portrait grid below
			(100, 100, 560, 400),        # Landscape 1
			(700, 100, 560, 400),        # Landscape 2
			(1300, 100, 560, 400),       # Landscape 3
			(1900, 100, 560, 400),       # Landscape 4
			(100, 540, 760, 1000),       # Portrait 1
			(880, 540, 760, 1000),       # Portrait 2
			(1660, 540, 760, 1000),      # Portrait 3
			(100, 1580, 760, 1000),      # Portrait 4
			(880, 1580, 760, 1000),      # Portrait 5
			(1660, 1580, 760, 1000)      # Portrait 6
		],
		
		'template_mix10_6p4l_footer_portraits': [  # 4L band top, 6P bottom stacked
			(100, 100, 760, 500),         # Landscape 1
			(880, 100, 760, 500),         # Landscape 2
			(1660, 100, 760, 500),        # Landscape 3
			(100, 640, 2280, 500),        # Landscape 4
			(100, 1180, 1140, 620),       # Portrait 1
			(1240, 1180, 1140, 620),      # Portrait 2
			(100, 1820, 1140, 620),       # Portrait 3
			(1240, 1820, 1140, 620),      # Portrait 4
			(100, 2460, 1140, 620),       # Portrait 5
			(1240, 2460, 1140, 620)       # Portrait 6
		],
		
		'template_mix10_6p4l_center_column': [  # 6P center stack, 2L left, 2L right
			(860, 100, 760, 500),         # Portrait 1
			(860, 640, 760, 500),         # Portrait 2
			(860, 1180, 760, 500),        # Portrait 3
			(860, 1720, 760, 500),        # Portrait 4
			(860, 2260, 760, 500),        # Portrait 5
			(860, 2800, 760, 500),        # Portrait 6
			(100, 100, 720, 700),         # Landscape 1 (left top)
			(100, 820, 720, 700),         # Landscape 2
			(1660, 100, 720, 700),        # Landscape 3 (right top)
			(1660, 820, 720, 700)         # Landscape 4
		],
		
		'template_mix10_7p3l_stack_left': [  # 7P stacked left, 3L stacked right
			(100, 100, 1140, 460),        # Portrait 1
			(100, 580, 1140, 460),
			(100, 1060, 1140, 460),
			(100, 1540, 1140, 460),
			(100, 2020, 1140, 460),
			(100, 2500, 1140, 460),
			(100, 2980, 1140, 460),
			(1240, 100, 1140, 900),       # Landscape 1
			(1240, 1020, 1140, 900),      # Landscape 2
			(1240, 1940, 1140, 900)       # Landscape 3
		],
		
		'template_mix10_7p3l_stack_right': [  # 7P stacked right, 3L stacked left
			(1240, 100, 1140, 460),       # Portrait 1
			(1240, 580, 1140, 460),
			(1240, 1060, 1140, 460),
			(1240, 1540, 1140, 460),
			(1240, 2020, 1140, 460),
			(1240, 2500, 1140, 460),
			(1240, 2980, 1140, 460),
			(100, 100, 1140, 900),        # Landscape 1
			(100, 1020, 1140, 900),       # Landscape 2
			(100, 1940, 1140, 900)        # Landscape 3
		],
		
		'template_mix10_7p3l_grid_top': [  # 3P row top, 2x2 + 2P below, 3L bottom
			(100, 100, 760, 1000),        # Portrait 1
			(880, 100, 760, 1000),
			(1660, 100, 760, 1000),
			(100, 1140, 760, 1000),       # Portrait 4
			(880, 1140, 760, 1000),
			(1660, 1140, 760, 1000),      # Portrait 6
			(100, 2280, 1140, 1000),      # Portrait 7
			(100, 3400, 1140, 400),       # Landscape 1
			(1240, 3400, 1140, 400),      # Landscape 2
			(100, 2920, 2280, 400)        # Landscape 3
		],
		
		'template_mix10_7p3l_footer_portraits': [  # 3L top band, 7P below stacked
			(100, 100, 760, 500),         # Landscape 1
			(880, 100, 760, 500),         # Landscape 2
			(1660, 100, 760, 500),        # Landscape 3
			(100, 640, 1140, 500),        # Portrait 1
			(1240, 640, 1140, 500),       # Portrait 2
			(100, 1180, 1140, 500),       # Portrait 3
			(1240, 1180, 1140, 500),      # Portrait 4
			(100, 1720, 1140, 500),       # Portrait 5
			(1240, 1720, 1140, 500),      # Portrait 6
			(100, 2260, 2280, 600)        # Portrait 7
		],
		
		'template_mix10_7p3l_center_column': [  # 7P center column, 3L split sides
			(860, 100, 760, 500),         # Portrait 1
			(860, 640, 760, 500),         # Portrait 2
			(860, 1180, 760, 500),        # Portrait 3
			(860, 1720, 760, 500),        # Portrait 4
			(860, 2260, 760, 500),        # Portrait 5
			(860, 2800, 760, 500),        # Portrait 6
			(860, 3340, 760, 500),        # Portrait 7
			(100, 100, 720, 900),         # Landscape 1 (left)
			(1660, 100, 720, 900),        # Landscape 2 (right)
			(1660, 1020, 720, 900)        # Landscape 3 (right)
		],
		
		'template_mix10_8p2l_stack_left': [  # 8P stacked left, 2L stacked right
			(100, 100, 1140, 400),         # Portrait 1
			(100, 520, 1140, 400),
			(100, 940, 1140, 400),
			(100, 1360, 1140, 400),
			(100, 1780, 1140, 400),
			(100, 2200, 1140, 400),
			(100, 2620, 1140, 400),
			(100, 3040, 1140, 400),
			(1240, 100, 1140, 1500),       # Landscape 1 (top half)
			(1240, 1640, 1140, 1500)       # Landscape 2 (bottom half)
		],
		
		'template_mix10_8p2l_stack_right': [  # 8P stacked right, 2L stacked left
			(1240, 100, 1140, 400),        # Portrait 1
			(1240, 520, 1140, 400),
			(1240, 940, 1140, 400),
			(1240, 1360, 1140, 400),
			(1240, 1780, 1140, 400),
			(1240, 2200, 1140, 400),
			(1240, 2620, 1140, 400),
			(1240, 3040, 1140, 400),
			(100, 100, 1140, 1500),        # Landscape 1 (top half)
			(100, 1640, 1140, 1500)        # Landscape 2 (bottom half)
		],
		
		'template_mix10_8p2l_footer_band': [  # 2x4 Portrait grid, Landscape footer band
			(100, 100, 1140, 800),         # Portrait 1
			(1240, 100, 1140, 800),        # Portrait 2
			(100, 920, 1140, 800),         # Portrait 3
			(1240, 920, 1140, 800),        # Portrait 4
			(100, 1740, 1140, 800),        # Portrait 5
			(1240, 1740, 1140, 800),       # Portrait 6
			(100, 2560, 1140, 800),        # Portrait 7
			(1240, 2560, 1140, 800),       # Portrait 8
			(100, 3380, 1140, 400),        # Landscape 1 (footer left)
			(1240, 3380, 1140, 400)        # Landscape 2 (footer right)
		],
		
		'template_mix10_8p2l_topband': [  # Landscape strip top, 4x2 Portrait grid below
			(100, 100, 1140, 400),         # Landscape 1 (left)
			(1240, 100, 1140, 400),        # Landscape 2 (right)
			(100, 540, 1140, 800),         # Portrait 1
			(1240, 540, 1140, 800),        # Portrait 2
			(100, 1360, 1140, 800),        # Portrait 3
			(1240, 1360, 1140, 800),       # Portrait 4
			(100, 2180, 1140, 800),        # Portrait 5
			(1240, 2180, 1140, 800),       # Portrait 6
			(100, 3000, 1140, 800),        # Portrait 7
			(1240, 3000, 1140, 800)        # Portrait 8
		],
		
		'template_mix10_9p1l_stack_left': [  # 9P stacked left, 1L full-height right
			(100, 100, 1140, 360),          # Portrait 1
			(100, 480, 1140, 360),          # Portrait 2
			(100, 860, 1140, 360),          # Portrait 3
			(100, 1240, 1140, 360),         # Portrait 4
			(100, 1620, 1140, 360),         # Portrait 5
			(100, 2000, 1140, 360),         # Portrait 6
			(100, 2380, 1140, 360),         # Portrait 7
			(100, 2760, 1140, 360),         # Portrait 8
			(100, 3140, 1140, 360),         # Portrait 9
			(1240, 100, 1140, 3400)         # Landscape (right full-height)
		],
		
		'template_mix10_9p1l_stack_right': [  # 9P stacked right, 1L full-height left
			(1240, 100, 1140, 360),         # Portrait 1
			(1240, 480, 1140, 360),         # Portrait 2
			(1240, 860, 1140, 360),         # Portrait 3
			(1240, 1240, 1140, 360),        # Portrait 4
			(1240, 1620, 1140, 360),        # Portrait 5
			(1240, 2000, 1140, 360),        # Portrait 6
			(1240, 2380, 1140, 360),        # Portrait 7
			(1240, 2760, 1140, 360),        # Portrait 8
			(1240, 3140, 1140, 360),        # Portrait 9
			(100, 100, 1140, 3400)          # Landscape (left full-height)
		],
		
		'template_mix10_9p1l_footer_band': [  # 3x3 Portrait grid, Landscape footer
			(100, 100, 760, 1000),          # Portrait 1
			(880, 100, 760, 1000),          # Portrait 2
			(1660, 100, 760, 1000),         # Portrait 3
			(100, 1140, 760, 1000),         # Portrait 4
			(880, 1140, 760, 1000),         # Portrait 5
			(1660, 1140, 760, 1000),        # Portrait 6
			(100, 2180, 760, 1000),         # Portrait 7
			(880, 2180, 760, 1000),         # Portrait 8
			(1660, 2180, 760, 1000),        # Portrait 9
			(100, 3300, 2280, 400)          # Landscape (footer band)
		],
		
		'template_mix10_10p_stack_left': [  # 10P stacked vertically on the left
			(100, 100, 1140, 330),         # Portrait 1
			(100, 450, 1140, 330),         # Portrait 2
			(100, 800, 1140, 330),         # Portrait 3
			(100, 1150, 1140, 330),        # Portrait 4
			(100, 1500, 1140, 330),        # Portrait 5
			(100, 1850, 1140, 330),        # Portrait 6
			(100, 2200, 1140, 330),        # Portrait 7
			(100, 2550, 1140, 330),        # Portrait 8
			(100, 2900, 1140, 330),        # Portrait 9
			(100, 3250, 1140, 330)         # Portrait 10
		],
		
		'template_mix10_10p_stack_right': [  # 10P stacked vertically on the right
			(1240, 100, 1140, 330),        # Portrait 1
			(1240, 450, 1140, 330),        # Portrait 2
			(1240, 800, 1140, 330),        # Portrait 3
			(1240, 1150, 1140, 330),       # Portrait 4
			(1240, 1500, 1140, 330),       # Portrait 5
			(1240, 1850, 1140, 330),       # Portrait 6
			(1240, 2200, 1140, 330),       # Portrait 7
			(1240, 2550, 1140, 330),       # Portrait 8
			(1240, 2900, 1140, 330),       # Portrait 9
			(1240, 3250, 1140, 330)        # Portrait 10
		],
		
		'template_mix10_10p_grid_2x5': [  # 2x5 Portrait grid (balanced columns)
			(100, 100, 1140, 600),         # Portrait 1 (left col)
			(100, 720, 1140, 600),         # Portrait 2
			(100, 1340, 1140, 600),        # Portrait 3
			(100, 1960, 1140, 600),        # Portrait 4
			(100, 2580, 1140, 600),        # Portrait 5
			(1240, 100, 1140, 600),        # Portrait 6 (right col)
			(1240, 720, 1140, 600),        # Portrait 7
			(1240, 1340, 1140, 600),       # Portrait 8
			(1240, 1960, 1140, 600),       # Portrait 9
			(1240, 2580, 1140, 600)        # Portrait 10
		],
	}
	return layout_map.get(template_key, [])