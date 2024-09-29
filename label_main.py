import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
import json
from typing import List, Tuple, Optional

class ImageLabeler:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.master.title("Image Labeler")
        self.master.geometry("800x600")
        self.master.minsize(600, 400)

        # Initialize variables
        self.image_folder: str = ''
        self.output_folder: str = ''
        self.image_prefix: str = ''
        self.image_extension: str = ''
        self.images: List[str] = []
        self.image_index: int = 0
        self.labels: List[dict] = []
        self.points: List[List[float]] = []  # Should always have 4 points in order
        self.copy_previous = tk.BooleanVar()
        self.load_saved = tk.BooleanVar()
        self.use_filename_as_id = tk.BooleanVar()
        self.image_on_canvas = None
        self.canvas_image = None

        self.original_image: Optional[Image.Image] = None
        self.display_image: Optional[Image.Image] = None
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0

        self.point_radius: int = 5  # Radius of the point markers
        self.dragging_point: Optional[int] = None  # Index of the point being dragged

        # Create menu bar
        self.create_menu()

        # Create widgets
        self.create_widgets()

        # Show welcome screen
        self.show_welcome_screen()

        # Bind events
        self.bind_events()

    def create_menu(self) -> None:
        # Create a menu bar
        self.menu_bar = tk.Menu(self.master)
        self.master.config(menu=self.menu_bar)

        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Select Image Folder", command=self.select_folder)
        file_menu.add_command(label="Set Output Folder", command=self.set_output_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Load Saved Labels", command=self.load_labels)
        file_menu.add_command(label="Save Labels", command=self.save_labels)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # Options menu
        options_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_checkbutton(label="Copy Previous", variable=self.copy_previous)
        options_menu.add_checkbutton(label="Use Image Filename as ID", variable=self.use_filename_as_id)

        # Help menu
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_command(label="About", command=self.show_about)

    def create_widgets(self) -> None:
        # Create a frame for buttons
        button_frame = ttk.Frame(self.master)
        button_frame.pack(side='top', fill='x')

        # Create buttons and checkbuttons
        self.folder_button = ttk.Button(
            button_frame, text="Select Image Folder", command=self.select_folder)
        self.folder_button.pack(side='left', padx=5, pady=5)

        self.output_button = ttk.Button(
            button_frame, text="Set Output Folder", command=self.set_output_folder)
        self.output_button.pack(side='left', padx=5, pady=5)

        self.copy_prev_check = ttk.Checkbutton(
            button_frame, text="Copy Previous", variable=self.copy_previous)
        self.copy_prev_check.pack(side='left', padx=5, pady=5)

        self.load_saved_button = ttk.Button(
            button_frame, text="Load Saved Labels", command=self.load_labels)
        self.load_saved_button.pack(side='left', padx=5, pady=5)

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

        # Create status bar frame
        status_frame = ttk.Frame(self.master, relief='sunken')
        status_frame.pack(side='bottom', fill='x')

        # Progress label
        self.progress_label = ttk.Label(status_frame, text="Image: 0 of 0", anchor='w')
        self.progress_label.pack(side='left', padx=5)

        # Status label
        self.status_label = ttk.Label(status_frame, text="Welcome to Image Labeler", anchor='w')
        self.status_label.pack(side='left', padx=10)

    def bind_events(self) -> None:
        # Bind key events
        self.master.bind('<Left>', self.prev_image)
        self.master.bind('<Right>', self.next_image)
        self.master.bind('a', self.prev_image)
        self.master.bind('d', self.next_image)
        self.master.bind('s', self.save_labels_shortcut)
        self.master.bind('r', self.reset_current_frame_shortcut)
        self.master.bind('c', self.toggle_copy_previous)
        self.master.bind('u', self.toggle_use_filename_as_id)
        self.master.bind('l', self.load_labels_shortcut)
        self.master.bind('<Escape>', self.on_closing)
        self.master.bind('q', self.on_closing)

        # Bind mouse events
        self.canvas.bind('<Button-1>', self.on_mouse_click)
        self.canvas.bind('<Button-3>', self.on_right_click)  # Right mouse button
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_release)

        # Bind window resize event
        self.master.bind('<Configure>', self.on_resize)

    def show_welcome_screen(self) -> None:
        # Create a top-level window for the welcome screen
        self.welcome_screen = tk.Toplevel(self.master)
        self.welcome_screen.title("Welcome to Image Labeler")
        self.welcome_screen.grab_set()
        self.welcome_screen.transient(self.master)

        # Center the welcome screen
        self.welcome_screen.geometry("+{}+{}".format(
            int(self.master.winfo_screenwidth() / 2 - 300),
            int(self.master.winfo_screenheight() / 2 - 200)
        ))

        # Create a frame for the form
        form_frame = ttk.Frame(self.welcome_screen, padding=20)
        form_frame.pack(fill='both', expand=True)

        # Header Label
        header_label = ttk.Label(
            form_frame,
            text="Welcome to Image Labeler",
            font=('Helvetica', 16, 'bold')
        )
        header_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Image Folder Selection
        ttk.Label(form_frame, text="Select Image Folder:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.image_folder_entry = ttk.Entry(form_frame, width=50)
        self.image_folder_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(form_frame, text="Browse", command=self.browse_image_folder).grid(row=1, column=2, padx=5, pady=5)

        # Image Prefix
        ttk.Label(form_frame, text="Image Prefix (optional):").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.image_prefix_entry = ttk.Entry(form_frame, width=50)
        self.image_prefix_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky='w')

        # Image Extension
        ttk.Label(form_frame, text="Image Extension (e.g., .png, .jpg) (optional):").grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.image_extension_entry = ttk.Entry(form_frame, width=50)
        self.image_extension_entry.grid(row=3, column=1, columnspan=2, padx=5, pady=5, sticky='w')

        # Output Folder Selection
        ttk.Label(form_frame, text="Output Folder for Labels:").grid(row=4, column=0, sticky='e', padx=5, pady=5)
        self.output_folder_entry = ttk.Entry(form_frame, width=50)
        self.output_folder_entry.grid(row=4, column=1, padx=5, pady=5)
        ttk.Button(form_frame, text="Browse", command=self.browse_output_folder).grid(row=4, column=2, padx=5, pady=5)

        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=20)

        start_button = ttk.Button(button_frame, text="Start Labeling", command=self.start_labeling)
        start_button.pack(side='left', padx=10)

        cancel_button = ttk.Button(button_frame, text="Cancel", command=self.welcome_screen.destroy)
        cancel_button.pack(side='left', padx=10)

        # Set grid weights
        self.welcome_screen.columnconfigure(0, weight=1)
        form_frame.columnconfigure(1, weight=1)

    def browse_image_folder(self) -> None:
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.image_folder_entry.delete(0, tk.END)
            self.image_folder_entry.insert(0, folder_selected)

    def browse_output_folder(self) -> None:
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder_entry.delete(0, tk.END)
            self.output_folder_entry.insert(0, folder_selected)

    def start_labeling(self) -> None:
        self.image_folder = self.image_folder_entry.get()
        self.image_prefix = self.image_prefix_entry.get()
        self.image_extension = self.image_extension_entry.get()
        self.output_folder = self.output_folder_entry.get()

        if not self.image_folder or not os.path.isdir(self.image_folder):
            messagebox.showerror("Error", "Please select a valid image folder.")
            return
        if not self.output_folder or not os.path.isdir(self.output_folder):
            messagebox.showerror("Error", "Please select a valid output folder.")
            return

        self.welcome_screen.destroy()
        self.load_images()
        if self.images:
            self.image_index = 0
            self.show_image()
            self.update_status(f"Loaded {len(self.images)} images.")
            self.update_progress()
        else:
            messagebox.showerror("Error", "No images found with the specified criteria.")

    def select_folder(self) -> None:
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.image_folder = folder_selected
            self.load_images()
            if self.images:
                self.image_index = 0
                self.show_image()
                self.update_status(f"Selected image folder: {self.image_folder}")
                self.update_progress()
            else:
                messagebox.showerror("Error", "No images found in the selected folder.")
        else:
            messagebox.showwarning("Warning", "No folder selected.")

    def set_output_folder(self) -> None:
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder = folder_selected
            self.update_status(f"Set output folder: {self.output_folder}")
        else:
            messagebox.showwarning("Warning", "No output folder selected.")

    def load_images(self) -> None:
        # Load images from the selected folder with optional prefix and extension filtering
        self.images = []
        for f in sorted(os.listdir(self.image_folder)):
            if self.image_prefix and not f.startswith(self.image_prefix):
                continue
            if self.image_extension and not f.lower().endswith(self.image_extension.lower()):
                continue
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                self.images.append(f)
        if not self.images:
            messagebox.showerror("Error", "No images found with the specified criteria.")
        else:
            # Reset labels and points when a new folder is selected
            self.labels = []
            self.points = []

    def show_image(self) -> None:
        # Load and display the current image
        image_path = os.path.join(self.image_folder, self.images[self.image_index])
        self.original_image = Image.open(image_path)
        # Resize image to fit the canvas while keeping aspect ratio
        self.update_image()
        self.update_status(f"Displaying image: {self.images[self.image_index]}")
        self.update_progress()

    def update_image(self) -> None:
        # Get canvas size
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
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
            (canvas_width - display_width) // 2,
            (canvas_height - display_height) // 2,
            anchor='nw',
            image=self.tk_image,
            tags="bg_image"
        )

        # Load points for the current image
        self.load_points_for_current_image()

        # Draw the points and lines
        self.draw_polygon_and_points()

    def load_points_for_current_image(self) -> None:
        # Load points for the current image, considering copy_previous option
        # First, check if there are saved points for the current image
        if self.image_index < len(self.labels):
            # There are saved labels for this image
            self.points = [list(pt) for pt in self.labels[self.image_index]['label']]
        else:
            # No saved labels for this image
            if self.copy_previous.get() and self.image_index > 0:
                # Copy from previous image
                prev_index = self.image_index - 1
                if prev_index < len(self.labels):
                    prev_label = self.labels[prev_index]
                    self.points = [list(pt) for pt in prev_label['label']]
                else:
                    self.points = []
            else:
                # Start with empty points
                self.points = []

    def draw_polygon_and_points(self) -> None:
        # First, remove any existing points and polygons
        self.canvas.delete("point")
        self.canvas.delete("polygon")

        if not self.points:
            return

        # Colors for the points
        point_colors = ['red', 'green', 'blue', 'yellow']
        # Transform points to display coordinates
        display_points: List[Tuple[float, float]] = []
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

    def get_offset_x(self) -> float:
        canvas_width = self.canvas.winfo_width()
        display_width = self.display_image.width
        return (canvas_width - display_width) // 2

    def get_offset_y(self) -> float:
        canvas_height = self.canvas.winfo_height()
        display_height = self.display_image.height
        return (canvas_height - display_height) // 2

    def on_resize(self, event: tk.Event) -> None:
        if self.original_image:
            self.update_image()

    def on_mouse_click(self, event: tk.Event) -> None:
        # Map display coordinates to original image coordinates
        x_original, y_original = self.display_to_original_coords(event.x, event.y)

        # Check if click is near an existing point
        for idx, pt in enumerate(self.points):
            x_pt, y_pt = pt
            dist = ((x_original - x_pt) ** 2 + (y_original - y_pt) ** 2) ** 0.5
            if dist * self.scale_x <= self.point_radius * 2:
                # Start dragging this point
                self.dragging_point = idx
                self.update_status(f"Started dragging point {idx}.")
                return

        # If not near an existing point, add a new point at the correct index
        if len(self.points) < 4:
            self.points.append([x_original, y_original])
            self.save_current_label()
            self.draw_polygon_and_points()
            self.update_status(f"Added point {len(self.points) - 1}.")
        else:
            # Maximum 4 points allowed
            self.update_status("Maximum of 4 points reached.")

    def on_mouse_drag(self, event: tk.Event) -> None:
        if self.dragging_point is not None:
            # Update the position of the dragging point
            x_original, y_original = self.display_to_original_coords(event.x, event.y)
            self.points[self.dragging_point] = [x_original, y_original]
            self.save_current_label()
            self.draw_polygon_and_points()
            self.update_status(f"Moved point {self.dragging_point}.")

    def on_mouse_release(self, event: tk.Event) -> None:
        if self.dragging_point is not None:
            # Finish dragging
            self.update_status(f"Released point {self.dragging_point}.")
            self.dragging_point = None

    def on_right_click(self, event: tk.Event) -> None:
        # Save labels without prompting and fast
        self.save_current_label()
        self.auto_save_labels()
        self.update_status("Labels saved via right-click.")

    def display_to_original_coords(self, x_display: float, y_display: float) -> Tuple[float, float]:
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

    def next_image(self, event: Optional[tk.Event] = None) -> None:
        if not self.images:
            return
        self.save_current_label()
        self.auto_save_labels()  # Auto-save to labels.json
        if self.image_index < len(self.images) - 1:
            self.image_index += 1
            self.show_image()
            self.update_status("Moved to next image.")
        else:
            messagebox.showinfo("Info", "This is the last image.")
            self.update_status("At last image.")
        self.update_progress()

    def prev_image(self, event: Optional[tk.Event] = None) -> None:
        if not self.images:
            return
        self.save_current_label()
        self.auto_save_labels()  # Auto-save to labels.json
        if self.image_index > 0:
            self.image_index -= 1
            self.show_image()
            self.update_status("Moved to previous image.")
        else:
            messagebox.showinfo("Info", "This is the first image.")
            self.update_status("At first image.")
        self.update_progress()

    def save_current_label(self) -> None:
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

    def load_labels(self, event: Optional[tk.Event] = None) -> None:
        # Load labels from a JSON file
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
            self.update_status("Loaded labels from file.")

    def save_labels(self, event: Optional[tk.Event] = None) -> None:
        # Save labels to a JSON file (manual save)
        if self.labels:
            save_path = filedialog.asksaveasfilename(
                title="Save Labels As", defaultextension=".json", filetypes=(("JSON files", "*.json"),))
            if save_path:
                with open(save_path, 'w') as f:
                    json.dump(self.labels, f, indent=2)
                messagebox.showinfo("Success", f"Labels saved to {save_path}")
                self.update_status(f"Labels saved to {save_path}")
            else:
                messagebox.showwarning("Warning", "Save operation cancelled.")
                self.update_status("Save operation cancelled.")

    def save_labels_shortcut(self, event: tk.Event) -> None:
        self.save_labels()

    def load_labels_shortcut(self, event: tk.Event) -> None:
        self.load_labels()

    def reset_current_frame(self) -> None:
        # Reset points for the current frame
        self.points = []
        self.save_current_label()
        self.draw_polygon_and_points()
        self.update_status("Reset current frame.")

    def reset_current_frame_shortcut(self, event: tk.Event) -> None:
        self.reset_current_frame()

    def toggle_copy_previous(self, event: tk.Event) -> None:
        # Toggle the copy_previous option
        self.copy_previous.set(not self.copy_previous.get())
        status = "enabled" if self.copy_previous.get() else "disabled"
        self.update_status(f"Copy Previous {status}.")

    def toggle_use_filename_as_id(self, event: tk.Event) -> None:
        # Toggle the use_filename_as_id option
        self.use_filename_as_id.set(not self.use_filename_as_id.get())
        status = "enabled" if self.use_filename_as_id.get() else "disabled"
        self.update_status(f"Use Image Filename as ID {status}.")

    def auto_save_labels(self) -> None:
        # Automatically save labels to the output folder as JSON
        if self.labels and self.output_folder:
            save_path = os.path.join(self.output_folder, 'labels.json')
            with open(save_path, 'w') as f:
                json.dump(self.labels, f, indent=2)
            self.update_status("Labels auto-saved.")

    def on_closing(self, event: Optional[tk.Event] = None) -> None:
        # Save labels when closing
        self.save_current_label()
        self.auto_save_labels()
        self.update_status("Application closed.")
        self.master.destroy()

    def update_status(self, message: str) -> None:
        self.status_label.config(text=message)

    def update_progress(self) -> None:
        # Update the progress label
        total_images = len(self.images)
        current_image = self.image_index + 1  # 1-based indexing for display
        self.progress_label.config(text=f"Image: {current_image} of {total_images}")

    def show_shortcuts(self) -> None:
        # Create a top-level window for the shortcuts
        shortcuts_window = tk.Toplevel(self.master)
        shortcuts_window.title("Keyboard Shortcuts")
        shortcuts_window.geometry("400x300")
        shortcuts_window.resizable(False, False)

        # Add a Text widget with the shortcuts
        text_widget = tk.Text(shortcuts_window, wrap='word', font=('Arial', 12), padx=10, pady=10)
        text_widget.pack(fill='both', expand=True)

        shortcuts_text = (
            "Keyboard Shortcuts:\n\n"
            "Left Arrow or 'a':\tPrevious Image\n"
            "Right Arrow or 'd':\tNext Image\n"
            "s:\tSave Labels\n"
            "r:\tReset Current Frame\n"
            "c:\tToggle Copy Previous\n"
            "u:\tToggle Use Image Filename as ID\n"
            "l:\tLoad Saved Labels\n"
            "q or Esc:\tQuit Application\n\n"
            "Mouse Actions:\n"
            "Right Click on Image:\tSave Labels, without prompt\n"
        )

        text_widget.insert('1.0', shortcuts_text)
        text_widget.config(state='disabled')  # Make the text read-only

    def show_about(self) -> None:
        messagebox.showinfo("About", "Image Labeler\nVersion 1.0\n\nBy, Pronay Sarkar\nhttps://github.com/rainfall64")

if __name__ == '__main__':
    root = tk.Tk()
    app = ImageLabeler(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
