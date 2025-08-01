import os
import sys

# Add the project root to the path so we can import from utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the conversion function from certificate_generator
from utils.certificate_generator import convert_svg_to_png

def main():
    # Base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    images_dir = os.path.join(base_dir, 'static', 'images')
    
    # SVG files to convert
    svg_files = [
        {'name': 'certificate-pattern.svg', 'width': 800, 'height': 600},
        {'name': 'certificate_seal.svg', 'width': 200, 'height': 200}
    ]
    
    for svg_file in svg_files:
        svg_path = os.path.join(images_dir, svg_file['name'])
        # Create PNG filename by replacing .svg with .png
        png_file = os.path.splitext(svg_file['name'])[0] + '.png'
        png_path = os.path.join(images_dir, png_file)
        
        # Force recreation of PNG by removing existing file
        if os.path.exists(png_path):
            print(f"Removing existing PNG: {png_path}")
            os.remove(png_path)
        
        if os.path.exists(svg_path):
            print(f"Converting {svg_file['name']} to PNG...")
            result = convert_svg_to_png(
                svg_path, 
                png_path, 
                width=svg_file['width'], 
                height=svg_file['height']
            )
            
            if result:
                print(f"Successfully converted {svg_file['name']} to PNG")
            else:
                print(f"Failed to convert {svg_file['name']} to PNG")
        else:
            print(f"SVG file not found: {svg_path}")

if __name__ == "__main__":
    main()