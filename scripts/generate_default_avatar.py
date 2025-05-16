from PIL import Image, ImageDraw, ImageFont
import os

def create_default_avatar():
    # Create a 200x200 image with a light blue background
    size = (200, 200)
    background_color = (13, 110, 253)  # Bootstrap primary blue
    image = Image.new('RGB', size, background_color)
    draw = ImageDraw.Draw(image)

    # Draw a white circle for the avatar
    circle_color = (255, 255, 255)
    circle_radius = 80
    circle_center = (size[0] // 2, size[1] // 2)
    draw.ellipse(
        [
            circle_center[0] - circle_radius,
            circle_center[1] - circle_radius,
            circle_center[0] + circle_radius,
            circle_center[1] + circle_radius
        ],
        fill=circle_color
    )

    # Add a user icon
    try:
        # Try to load a font, fall back to default if not available
        font = ImageFont.truetype("arial.ttf", 100)
    except:
        font = ImageFont.load_default()

    # Draw a user icon (simplified as a circle with a dot)
    icon_color = (13, 110, 253)  # Bootstrap primary blue
    # Draw head
    head_radius = 30
    draw.ellipse(
        [
            circle_center[0] - head_radius,
            circle_center[1] - head_radius - 10,
            circle_center[0] + head_radius,
            circle_center[1] + head_radius - 10
        ],
        fill=icon_color
    )
    # Draw body
    body_height = 40
    draw.rectangle(
        [
            circle_center[0] - 20,
            circle_center[1] + head_radius - 10,
            circle_center[0] + 20,
            circle_center[1] + head_radius + body_height - 10
        ],
        fill=icon_color
    )

    # Ensure the static/images directory exists
    os.makedirs('static/images', exist_ok=True)

    # Save the image
    image.save('static/images/default_avatar.png', 'PNG')
    print("Default avatar generated successfully!")

if __name__ == '__main__':
    create_default_avatar() 