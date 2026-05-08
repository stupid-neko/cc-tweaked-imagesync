import math
import os
import tomllib
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk


# Load config.toml
def load_config():
    if not os.path.exists("config.toml"):
        messagebox.showerror("ERROR", "config.toml not found")
        exit(1)
    
    # Loading vars
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
    
    # Getting vars
    screen_w = {int(k): v for k, v in config["screen_w_map"].items()}
    screen_h = {int(k): v for k, v in config["screen_h_map"].items()}
    palette = {k: tuple(v) for k, v in config["palette_rgb"].items()}
    char_size = tuple(config["char_correction"]["char_size_wh"])

    # Returning vars
    return screen_w, screen_h, palette, char_size

try:
    SCREEN_W_MAP, SCREEN_H_MAP, CC_PALETTE, CHAR_SIZE = load_config()
except Exception as e:
    print(f"Error while loading config.toml : {e}")
    exit(1)

COLOR_CACHE = {}


def get_closest_cc_color(rgb):
    if rgb in COLOR_CACHE:
        return COLOR_CACHE[rgb]
    r, g, b = rgb

    best_diff = float('inf')
    best_char = 'f'
    best_rgb = (17, 17, 17)

    for char, cc_rgb in CC_PALETTE.items():
        cr, cg, cb = cc_rgb
        diff = (r - cr)**2 + (g - cg)**2 + (b - cb)**2  # Mean sqr
        if diff < best_diff:
            best_diff = diff
            best_char = char
            best_rgb = cc_rgb
    
    COLOR_CACHE[rgb] = (best_char, best_rgb)
    return best_char, best_rgb

class CCImageTool:
    def __init__(self, root):
        self.root = root
        self.root.title("CC:Tweaked ImageSync - Cropper")

        self.original_image = None
        self.display_image = None
        self.display_scale = 1.0

        self.crop_cx = 0
        self.crop_cy = 0
        self.crop_zoom = 1.0

        self.target_w_chars = SCREEN_W_MAP[8]
        self.target_h_chars = SCREEN_H_MAP[6]

        self.setup_ui()
    

    def setup_ui(self):
        # Top Frame
        top_frame = tk.Frame(self.root, pady=5)
        top_frame.pack(fill=tk.X)

        tk.Button(top_frame, text="Open Image...", command=self.load_image).pack(side=tk.LEFT, padx=5)
        tk.Label(top_frame, text="Screens (W):").pack(side=tk.LEFT)
        self.w_var = tk.IntVar(value=8)
        w_cb = ttk.Combobox(top_frame, textvariable=self.w_var, values=list(SCREEN_W_MAP.keys()), width=3, state="readonly")
        w_cb.pack(side=tk.LEFT)
        w_cb.bind("<<ComboboxSelected>>", self.on_size_change)

        tk.Label(top_frame, text="Screens (H):").pack(side=tk.LEFT, padx=(10,0))
        self.h_var = tk.IntVar(value=6)
        h_cb = ttk.Combobox(top_frame, textvariable=self.h_var, values=list(SCREEN_H_MAP.keys()), width=3, state="readonly")
        h_cb.pack(side=tk.LEFT)
        h_cb.bind("<<ComboboxSelected>>", self.on_size_change)

        tk.Button(top_frame, text="Export (.txt and .png)", command=self.export).pack(side=tk.RIGHT, padx=10)

        # Main Frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas Original Image
        self.canvas = tk.Canvas(main_frame, bg="#2b2b2b", cursor="crosshair")
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.on_scroll)
        self.canvas.bind("<Button-4>", self.on_scroll)
        self.canvas.bind("<Button-5>", self.on_scroll)

        # Overview panel
        right_frame = tk.Frame(main_frame, width=350, bg='#1e1e1e')
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        tk.Label(right_frame, text="Simulation on CC screen (5x8) :", fg="white", bg="#1e1e1e", pady=10).pack()
        self.preview_label = tk.Label(right_frame, bg="black")
        self.preview_label.pack(padx=10)
    

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if not path: return
        self.original_image = Image.open(path).convert('RGB')

        w, h = self.original_image.size
        self.display_scale = min(800/w, 600/h)
        if self.display_scale > 1: self.display_scale = 1.0

        new_w, new_h = int(w * self.display_scale), int(h * self.display_scale)
        self.display_image = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        self.tk_image = ImageTk.PhotoImage(self.display_image)
        self.canvas.config(scrollregion=(0,0,new_w,new_h))
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image, tags="img")

        self.crop_cx, self.crop_cy = new_w/2, new_h/2

        # Base zoom initial
        self.crop_zoom = 1.0
        self.update_canvas()
        self.update_preview()
    

    def on_size_change(self, event=None):
        self.target_w_chars = SCREEN_W_MAP[self.w_var.get()]
        self.target_h_chars = SCREEN_H_MAP[self.h_var.get()]
        self.update_canvas()
        self.update_preview()
    
    
    def get_crop_box(self):
        # Physical screen to CC pixels
        char_w, char_h = CHAR_SIZE
        physical_w = self.target_w_chars * char_w
        physical_h = self.target_h_chars * char_h
        w_half = (physical_w * self.crop_zoom) /2
        h_half = (physical_h * self.crop_zoom) /2
        return (
            self.crop_cx - w_half,
            self.crop_cy - h_half,
            self.crop_cx + w_half,
            self.crop_cy + h_half
        )
    

    def update_canvas(self):
        self.canvas.delete("rect")
        if not self.original_image: return
        x1, y1, x2, y2 = self.get_crop_box()
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00ff00", width=2, tags="rect")

        # Dark mask
        self.canvas.create_rectangle(0, 0, x1, 10000, fill="black", stipple="gray50", tags="rect")
        self.canvas.create_rectangle(x2, 0, 10000, 10000, fill="black", stipple="gray50", tags="rect")
        self.canvas.create_rectangle(x1, 0, x2, y1, fill="black", stipple="gray50", tags="rect")
        self.canvas.create_rectangle(x1, y2, x2, 10000, fill="black", stipple="gray50", tags="rect")

    
    def on_press(self, event):
        self.last_x, self.last_y = event.x, event.y
    

    def on_drag(self, event):
        self.crop_cx += (event.x - self.last_x)
        self.crop_cy += (event.y - self.last_y)
        self.last_x, self.last_y = event.x, event.y
        self.update_canvas()
    

    def on_release(self, event):
        self.update_preview()
    

    def on_scroll(self, event):
        if event.delta > 0 or event.num == 4:
            self.crop_zoom *= 0.9  # Zoom In
        elif event.delta < 0 or event.num == 5:
            self.crop_zoom *= 1.1  # Zoom Out
        self.update_canvas()
        self.update_preview()
    

    def generate_cc_data(self):
        x1, y1, x2, y2 = self.get_crop_box()
        s = self.display_scale
        orig_box = (int(x1/s), int(y1/s), int(x2/s), int(y2/s))

        # 1. Cut image with proportions
        cropped = self.original_image.crop(orig_box)

        # 2. Resize on target char limit
        resized = cropped.resize((self.target_w_chars, self.target_h_chars), Image.Resampling.LANCZOS)

        txt_lines = []
        cc_img = Image.new("RGB", resized.size)
        pixels = resized.load()
        out_pixels = cc_img.load()

        for y in range(self.target_h_chars):
            line_chars = []
            for x in range(self.target_w_chars):
                char, rgb = get_closest_cc_color(pixels[x, y])
                line_chars.append(char)
                out_pixels[x, y] = rgb
            txt_lines.append("".join(line_chars))
        
        return txt_lines, cc_img
    

    def update_preview(self):
        if not self.original_image: return
        _, cc_img = self.generate_cc_data()

        # CC Tweaked render (1x1 px -> 5x8 px)
        char_w, char_h = CHAR_SIZE
        physical_w = self.target_w_chars * char_w
        physical_h = self.target_h_chars * char_h

        # Nearest AA -> No blur
        preview_stretched = cc_img.resize((physical_w, physical_h), Image.Resampling.NEAREST)
        
        # Resize preview
        max_preview_width = 330
        if physical_w > max_preview_width:
            scale_down = max_preview_width / physical_w
            preview_stretched = preview_stretched.resize((int(physical_w * scale_down), int(physical_h * scale_down)), Image.Resampling.NEAREST)
        
        self.preview_tk = ImageTk.PhotoImage(preview_stretched)
        self.preview_label.config(image=self.preview_tk)
    

    def export(self):
        if not self.original_image: return

        # Create outputs folder
        os.makedirs("outputs", exist_ok=True)

        file_path = filedialog.asksaveasfilename(
            initialdir="outputs",
            title="Save Export As...",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="export.txt"
        )

        if not file_path: return

        txt_lines, cc_img = self.generate_cc_data()

        with open(file_path, "w") as f:
            f.write("\n".join(txt_lines))

        messagebox.showinfo("SUCCESS", "Export finished ! Image should appear flat and its normal :)")


if __name__ == "__main__":
    root = tk.Tk()
    app = CCImageTool(root)
    root.geometry("1100x700")
    root.mainloop()
