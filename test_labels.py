import sys
import os
import json
from PIL import Image, ImageDraw

def draw_trapezoids(json_file, image_folder, output_folder):
    # Load labels from JSON file
    with open(json_file, 'r') as f:
        labels = json.load(f)

    # Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Process each label
    for label in labels:
        frame_id = label['frame_id']
        points = label['label']
        if not points or len(points) != 4:
            print(f"Skipping {frame_id}: Invalid number of points.")
            continue

        # Construct image path
        image_path = os.path.join(image_folder, frame_id)
        if not os.path.isfile(image_path):
            print(f"Image file not found: {image_path}")
            continue

        # Open image
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)

        # Draw trapezoid
        trapezoid_points = [(pt[0], pt[1]) for pt in points]
        draw.line([trapezoid_points[0], trapezoid_points[1]], fill='#FF69B4', width=2)
        draw.line([trapezoid_points[1], trapezoid_points[2]], fill='#FF69B4', width=2)
        draw.line([trapezoid_points[2], trapezoid_points[3]], fill='#FF69B4', width=2)
        draw.line([trapezoid_points[3], trapezoid_points[0]], fill='#FF69B4', width=2)

        # Optionally, draw points
        point_colors = ['red', 'green', 'blue', 'yellow']
        for idx, pt in enumerate(trapezoid_points):
            x, y = pt
            r = 5  # Radius of the point marker
            color = point_colors[idx % len(point_colors)]
            draw.ellipse((x - r, y - r, x + r, y + r), fill=color, outline='white')

        # Save image to output folder
        output_path = os.path.join(output_folder, frame_id)
        image.save(output_path)
        print(f"Processed and saved: {output_path}")

if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python draw_trapezoids.py labels.json image_folder output_folder")
        sys.exit(1)

    json_file = sys.argv[1]
    image_folder = sys.argv[2]
    output_folder = sys.argv[3]

    if not os.path.isfile(json_file):
        print(f"JSON file not found: {json_file}")
        sys.exit(1)
    if not os.path.isdir(image_folder):
        print(f"Image folder not found: {image_folder}")
        sys.exit(1)
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)

    draw_trapezoids(json_file, image_folder, output_folder)
