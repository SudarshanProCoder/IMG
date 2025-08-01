import os
from PIL import Image, ImageDraw

def create_seal_png(output_path, width=200, height=200):
    """Create a simple gold seal PNG as fallback"""
    try:
        # Create a transparent background
        img = Image.new('RGBA', (width, height), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        
        # Calculate center and radius
        center_x = width // 2
        center_y = height // 2
        outer_radius = min(width, height) // 2 - 5
        inner_radius = outer_radius - 10
        
        # Gold colors
        gold_fill = (249, 212, 35, 255)  # Bright gold
        gold_edge = (230, 180, 35, 255)  # Darker gold for edges
        
        # Draw outer circle (main seal)
        draw.ellipse(
            (center_x - outer_radius, center_y - outer_radius, 
             center_x + outer_radius, center_y + outer_radius), 
            fill=gold_fill, outline=gold_edge, width=2
        )
        
        # Draw inner circle
        draw.ellipse(
            (center_x - inner_radius, center_y - inner_radius, 
             center_x + inner_radius, center_y + inner_radius), 
            outline=(255, 255, 255, 200), width=1
        )
        
        # Draw some decorative points around the seal
        point_length = outer_radius // 4
        for angle in range(0, 360, 30):  # 12 points around the circle
            # Calculate start point (on the circle)
            import math
            rad_angle = math.radians(angle)
            start_x = center_x + int(outer_radius * math.cos(rad_angle))
            start_y = center_y + int(outer_radius * math.sin(rad_angle))
            
            # Calculate end point (outside the circle)
            end_x = center_x + int((outer_radius + point_length) * math.cos(rad_angle))
            end_y = center_y + int((outer_radius + point_length) * math.sin(rad_angle))
            
            # Draw a small triangle
            point_width = point_length // 2
            perp_angle = math.radians(angle + 90)
            p1_x = start_x
            p1_y = start_y
            p2_x = end_x + int(point_width * math.cos(perp_angle) * 0.5)
            p2_y = end_y + int(point_width * math.sin(perp_angle) * 0.5)
            p3_x = end_x - int(point_width * math.cos(perp_angle) * 0.5)
            p3_y = end_y - int(point_width * math.sin(perp_angle) * 0.5)
            
            draw.polygon([(p1_x, p1_y), (p2_x, p2_y), (p3_x, p3_y)], fill=(255, 255, 255, 200))
        
        # Add text
        # Note: PIL's basic text support is limited, so this is simplified
        font_size = width // 15
        draw.text((center_x, center_y - font_size), "OFFICIAL", fill=(255, 255, 255, 255), anchor="mm")
        draw.text((center_x, center_y), "CERTIFICATE", fill=(255, 255, 255, 255), anchor="mm")
        draw.text((center_x, center_y + font_size), "OF ACHIEVEMENT", fill=(255, 255, 255, 255), anchor="mm")
        
        # Save the image
        img.save(output_path, 'PNG')
        print(f"Created fallback seal PNG at {output_path}")
        return True
    except Exception as e:
        print(f"Error creating fallback seal PNG: {e}")
        return False

def create_pattern_png(output_path, width=800, height=600):
    """Create a simple gold pattern PNG as fallback"""
    try:
        # Create a white background
        img = Image.new('RGBA', (width, height), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        # Gold color with transparency
        gold_color = (249, 212, 35, 50)  # Very transparent gold
        
        # Draw wave patterns at top
        wave_height = height // 6
        for y_offset in range(0, height // 2, wave_height):
            # Draw a wavy pattern
            points = []
            for x in range(0, width + 1, width // 8):
                amplitude = wave_height // 2
                if x % (width // 4) == 0:
                    points.append((x, y_offset + amplitude))
                else:
                    points.append((x, y_offset))
            # Close the polygon
            points.append((width, 0))
            points.append((0, 0))
            
            # Draw the wave
            draw.polygon(points, fill=gold_color)
        
        # Draw wave patterns at bottom
        for y_offset in range(height // 2, height, wave_height):
            # Draw a wavy pattern
            points = []
            for x in range(0, width + 1, width // 8):
                amplitude = wave_height // 2
                if x % (width // 4) == 0:
                    points.append((x, y_offset + amplitude))
                else:
                    points.append((x, y_offset))
            # Close the polygon
            points.append((width, height))
            points.append((0, height))
            
            # Draw the wave
            draw.polygon(points, fill=gold_color)
        
        # Draw corner decorations
        corner_size = min(width, height) // 12
        corners = [
            (corner_size, corner_size),  # Top-left
            (width - corner_size, corner_size),  # Top-right
            (corner_size, height - corner_size),  # Bottom-left
            (width - corner_size, height - corner_size)  # Bottom-right
        ]
        
        for cx, cy in corners:
            draw.ellipse(
                (cx - corner_size//2, cy - corner_size//2, 
                 cx + corner_size//2, cy + corner_size//2), 
                outline=(230, 180, 35, 128), width=1
            )
        
        # Add a subtle grid pattern
        grid_spacing = 20
        grid_color = (230, 180, 35, 20)  # Very transparent gold
        
        for x in range(0, width, grid_spacing):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        
        for y in range(0, height, grid_spacing):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)
        
        # Save the image
        img.save(output_path, 'PNG')
        print(f"Created fallback pattern PNG at {output_path}")
        return True
    except Exception as e:
        print(f"Error creating fallback pattern PNG: {e}")
        return False

def main():
    # Base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    images_dir = os.path.join(base_dir, 'static', 'images')
    
    # Create fallback PNGs
    seal_png_path = os.path.join(images_dir, 'certificate_seal.png')
    pattern_png_path = os.path.join(images_dir, 'certificate-pattern.png')
    
    create_seal_png(seal_png_path)
    create_pattern_png(pattern_png_path)

if __name__ == "__main__":
    main()