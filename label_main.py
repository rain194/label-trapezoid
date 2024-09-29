import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import json

class ImageLabeler:
    def __init__(self, master):
        self.master = master
        self.master.title("Image Labeler")
        self.master.geometry("800x600")
        self.master.minsize(600, 400)

        # Initialize variables
        self.image_folder = ''
        self.images = []
        self.image_index = 0
        self.labels = []
        self.points = []  # Should always have 4 points in order
        self.copy_previous = tk.BooleanVar()
        self.load_saved = tk.BooleanVar()
        self.use_filename_as_id = tk.BooleanVar()
        self.image_on_canvas = None
        self.canvas_image = None

        self.original_image = None
        self.display_image = None
        self.scale_x = 1
        self.scale_y = 1

        self.point_radius = 5  # Radius of the point markers
        self.dragging_point = None  # Index of the point being dragged

        # Create widgets
        self.create_widgets()

        # Bind events
        self.bind_events()

    def create_widgets(self):
        # Create a frame for buttons
        button_frame = ttk.Frame(self.master)
        button_frame.pack(side='top', fill='x')

        # Create buttons and checkbuttons
        self.folder_button = ttk.Button(
            button_frame, text="Select Image Folder", command=self.select_folder)
        self.folder_button.pack(side='left', padx=5, pady=5)

        self.copy_prev_check = ttk.Checkbutton(
            button_frame, text="Copy Previous", variable=self.copy_previous)
        self.copy_prev_check.pack(side='left', padx=5, pady=5)

        self.load_saved_check = ttk.Checkbutton(
            button_frame, text="Load Saved Labels", variable=self.load_saved, command=self.load_labels)
        self.load_saved_check.pack(side='left', padx=5, pady=5)

        self.filename_id_check = ttk.Checkbutton(
            button_frame, text="Use Image Filename as ID", variable=self.use_filename_as_id)
        self.filename_id_check.pack(side='left', padx=5, pady=5)

        self.reset_button = ttk.Button(
            button_frame, text="Reset Current Frame", command=self.reset_current_frame)
        self.reset_button.pack(side='left', padx=5, pady=5)

        self.save_button = ttk.Button(
            button_frame, text="Save Labels", command=self.save_labels)
        self.save_button.pack(side='left', padx=5, pady=5)

        # Create canvas
        self.canvas = tk.Canvas(self.master, bg='gray')
        self.canvas.pack(fill='both', expand=True)

    def bind_events(self):
        # Bind key events
        self.master.bind('<Left>', self.prev_image)
        self.master.bind('<Right>', self.next_image)

        # Bind mouse events
        self.canvas.bind('<Button-1>', self.on_mouse_click)
        self.canvas.bind('<Button-3>', self.on_right_click)  # Right mouse button
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_release)

        # Bind window resize event
        self.master.bind('<Configure>', self.on_resize)

    def select_folder(self):
        # Open a dialog to select the image folder
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.image_folder = folder_selected
            self.load_images()
            if self.images:
                self.image_index = 0
                self.show_image()
            else:
                messagebox.showerror("Error", "No images found in the selected folder.")
        else:
            messagebox.showwarning("Warning", "No folder selected.")

    def load_images(self):
        # Load images from the selected folder
        self.images = [f for f in sorted(os.listdir(self.image_folder))
                       if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if not self.images:
            messagebox.showerror("Error", "No images found in the selected folder.")
        else:
            # Reset labels and points when a new folder is selected
            self.labels = []
            self.points = []

    def show_image(self):
        # Load and display the current image
        image_path = os.path.join(self.image_folder, self.images[self.image_index])
        self.original_image = Image.open(image_path)
        # Resize image to fit the canvas while keeping aspect ratio
        self.update_image()

    def update_image(self):
        # Get canvas size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <=1:
            # Canvas has not been fully initialized yet
            self.master.after(100, self.update_image)
            return

        # Calculate the scaling factor to fit the image to the canvas
        original_width, original_height = self.original_image.size
        ratio = min(canvas_width / original_width, canvas_height / original_height)
        display_width = int(original_width * ratio)
        display_height = int(original_height * ratio)
        self.scale_x = ratio
        self.scale_y = ratio

        # Resize the image
        self.display_image = self.original_image.resize((display_width, display_height), Image.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)

        # Update the canvas
        self.canvas.delete("all")
        self.canvas_image = self.canvas.create_image(
            (canvas_width - display_width)//2, (canvas_height - display_height)//2, anchor='nw', image=self.tk_image, tags="bg_image")

        # Load points for the current image
        self.load_points_for_current_image()

        # Draw the points and lines
        self.draw_polygon_and_points()

    def load_points_for_current_image(self):
        # Load points based on copy_previous and saved labels
        if self.copy_previous.get():
            if self.image_index > 0:
                prev_index = self.image_index - 1
                if prev_index < len(self.labels):
                    prev_label = self.labels[prev_index]
                    self.points = [list(pt) for pt in prev_label['label']]
                else:
                    self.points = []
            else:
                # First image, no previous to copy from
                self.points = []
        else:
            if self.image_index < len(self.labels):
                self.points = [list(pt) for pt in self.labels[self.image_index]['label']]
            else:
                self.points = []

    def draw_polygon_and_points(self):
        # First, remove any existing points and polygons
        self.canvas.delete("point")
        self.canvas.delete("polygon")

        if not self.points:
            return

        # Colors for the points
        point_colors = ['red', 'green', 'blue', 'yellow']
        # Transform points to display coordinates
        display_points = []
        for idx, pt in enumerate(self.points):
            x = pt[0] * self.scale_x + self.get_offset_x()
            y = pt[1] * self.scale_y + self.get_offset_y()
            display_points.append((x, y))
            # Draw point marker with different colors
            color = point_colors[idx % len(point_colors)]
            self.canvas.create_oval(
                x - self.point_radius, y - self.point_radius,
                x + self.point_radius, y + self.point_radius,
                fill=color, outline='white', width=1, tag="point")
            # Display the point index next to the point
            self.canvas.create_text(
                x + self.point_radius + 5, y, text=str(idx), fill='white', font=('Arial', 10), tag="point")

        # Draw lines between specified points
        if len(display_points) == 4:
            edges = [(0, 1), (1, 2), (2, 3), (3, 0)]
            for i, j in edges:
                x1, y1 = display_points[i]
                x2, y2 = display_points[j]
                self.canvas.create_line(
                    x1, y1, x2, y2, fill='#FF69B4', width=2, tag="polygon")

    def get_offset_x(self):
        canvas_width = self.canvas.winfo_width()
        display_width = self.display_image.width
        return (canvas_width - display_width) // 2

    def get_offset_y(self):
        canvas_height = self.canvas.winfo_height()
        display_height = self.display_image.height
        return (canvas_height - display_height) // 2

    def on_resize(self, event):
        if self.original_image:
            self.update_image()

    def on_mouse_click(self, event):
        # Map display coordinates to original image coordinates
        x_original, y_original = self.display_to_original_coords(event.x, event.y)

        # Check if click is near an existing point
        for idx, pt in enumerate(self.points):
            x_pt, y_pt = pt
            dist = ((x_original - x_pt)**2 + (y_original - y_pt)**2) ** 0.5
            if dist * self.scale_x <= self.point_radius * 2:
                # Start dragging this point
                self.dragging_point = idx
                return

        # If not near an existing point, add a new point at the correct index
        if len(self.points) < 4:
            self.points.append([x_original, y_original])
            self.save_current_label()
            self.draw_polygon_and_points()
        else:
            # Maximum 4 points allowed
            pass

    def on_mouse_drag(self, event):
        if self.dragging_point is not None:
            # Update the position of the dragging point
            x_original, y_original = self.display_to_original_coords(event.x, event.y)
            self.points[self.dragging_point] = [x_original, y_original]
            self.save_current_label()
            self.draw_polygon_and_points()

    def on_mouse_release(self, event):
        if self.dragging_point is not None:
            # Finish dragging
            self.dragging_point = None

    def on_right_click(self, event):
        # Save labels without prompting
        self.save_current_label()
        self.auto_save_labels()

    def display_to_original_coords(self, x_display, y_display):
        offset_x = self.get_offset_x()
        offset_y = self.get_offset_y()
        x_display -= offset_x
        y_display -= offset_y
        x_original = x_display / self.scale_x
        y_original = y_display / self.scale_y
        # Clamp coordinates to image boundaries
        x_original = max(0, min(self.original_image.width, x_original))
        y_original = max(0, min(self.original_image.height, y_original))
        return x_original, y_original

    def next_image(self, event=None):
        if not self.images:
            return
        self.save_current_label()
        self.auto_save_labels()  # Auto-save to labels.json
        if self.image_index < len(self.images) - 1:
            self.image_index += 1
            self.show_image()

    def prev_image(self, event=None):
        if not self.images:
            return
        self.save_current_label()
        self.auto_save_labels()  # Auto-save to labels.json
        if self.image_index > 0:
            self.image_index -= 1
            self.show_image()

    def save_current_label(self):
        # Save current label
        if self.use_filename_as_id.get():
            frame_id = self.images[self.image_index]
        else:
            frame_id = self.image_index

        label = {'frame_id': frame_id, 'label': self.points}
        if self.image_index < len(self.labels):
            self.labels[self.image_index] = label
        else:
            # Fill labels up to current index
            while len(self.labels) < self.image_index:
                if self.use_filename_as_id.get():
                    fid = self.images[len(self.labels)]
                else:
                    fid = len(self.labels)
                self.labels.append({'frame_id': fid, 'label': []})
            self.labels.append(label)

    def load_labels(self):
        # Load labels from a JSON file
        if self.load_saved.get():
            label_file = filedialog.askopenfilename(
                title="Select Label File", filetypes=(("JSON files", "*.json"),))
            if label_file:
                with open(label_file, 'r') as f:
                    self.labels = json.load(f)

                # Update image_index to match labels if using filenames as IDs
                if self.use_filename_as_id.get():
                    # Create a mapping from image filenames to their indices
                    image_name_to_index = {name: idx for idx, name in enumerate(self.images)}
                    # Create a new labels list with the correct order
                    new_labels = [None] * len(self.images)
                    for label in self.labels:
                        frame_id = label['frame_id']
                        if isinstance(frame_id, str):
                            if frame_id in image_name_to_index:
                                index = image_name_to_index[frame_id]
                                new_labels[index] = label
                            else:
                                messagebox.showwarning(
                                    "Warning", f"Image {frame_id} not found in folder.")
                    # Replace labels with new_labels, filling in missing labels
                    self.labels = []
                    for idx in range(len(self.images)):
                        if new_labels[idx]:
                            self.labels.append(new_labels[idx])
                        else:
                            fid = self.images[idx] if self.use_filename_as_id.get() else idx
                            self.labels.append({'frame_id': fid, 'label': []})
                    self.image_index = 0
                self.show_image()

    def save_labels(self):
        # Save labels to a JSON file (manual save)
        if self.labels:
            save_path = filedialog.asksaveasfilename(
                title="Save Labels As", defaultextension=".json", filetypes=(("JSON files", "*.json"),))
            if save_path:
                with open(save_path, 'w') as f:
                    json.dump(self.labels, f, indent=2)
                messagebox.showinfo("Success", f"Labels saved to {save_path}")
            else:
                messagebox.showwarning("Warning", "Save operation cancelled.")

    def auto_save_labels(self):
        # Automatically save labels to labels.json without prompting
        if self.labels:
            with open('labels.json', 'w') as f:
                json.dump(self.labels, f, indent=2)

    def reset_current_frame(self):
        # Reset points for the current frame
        self.points = []
        self.save_current_label()
        self.draw_polygon_and_points()

    def on_closing(self):
        # Save labels when closing
        self.save_current_label()
        self.auto_save_labels()
        self.master.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = ImageLabeler(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
