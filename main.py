import math
import os
import tomllib
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageEnhance


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


# CONSTANT GO HERE
COLOR_CACHE = {}

BAYER_4X4 = (
    ( 0,  8,  2, 10),
    (12,  4, 14,  6),
    ( 3, 11,  1,  9),
    (15,  7, 13,  5)
)


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

        # Addition for Slider and live change
        self.w_var = tk.IntVar(value=8)
        self.h_var = tk.IntVar(value=4)

        # Image settings centered at 1.0
        self.brightness_var = tk.DoubleVar(value=1.0)
        self.contrast_var = tk.DoubleVar(value=1.0)
        self.saturation_var = tk.DoubleVar(value=1.0)
        self.gamma_var = tk.DoubleVar(value=1.0)
        self.dither_var = tk.DoubleVar(value=0.0)

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
        w_cb = ttk.Combobox(top_frame, textvariable=self.w_var, values=list(SCREEN_W_MAP.keys()), width=3, state="readonly")
        w_cb.pack(side=tk.LEFT)
        w_cb.bind("<<ComboboxSelected>>", self.on_size_change)

        tk.Label(top_frame, text="Screens (H):").pack(side=tk.LEFT, padx=(10,0))
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
        
        # Mouse bindings (Win / Linux)
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<MouseWheel>", self.on_scroll)
        self.canvas.bind("<Button-4>", self.on_scroll)
        self.canvas.bind("<Button-5>", self.on_scroll)

        # Overview panel
        right_frame = tk.Frame(main_frame, width=350, bg='#1e1e1e')
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Simulated overview
        preview_container = tk.Frame(right_frame, bg="#1e1e1e")
        preview_container.pack(side=tk.TOP, fill=tk.Y, padx=10, pady=(10,0))
        tk.Label(preview_container, text="Render on CC screen :", fg="white", bg="#1e1e1e", pady=10).pack()
        self.preview_label = tk.Label(preview_container, bg="black")
        self.preview_label.pack(padx=10)

        # Slider frame
        slider_frame = tk.LabelFrame(right_frame, text="Image settings", fg="white", bg="#1e1e1e", pady=10)
        slider_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0,10))

        def on_adjust_change(event=None):
            self.on_adjustments_change()
        
        # Sliders with labels
        # Brightness
        tk.Label(slider_frame, text="Luminosity", fg="white", bg="#1e1e1e").pack()
        self.brightness_scale = tk.Scale(slider_frame, from_=0.0, to=3.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.brightness_var, bg="#1e1e1e", fg="white", troughcolor="#333", highlightthickness=0, command=on_adjust_change)
        self.brightness_scale.pack(fill=tk.X, padx=5, pady=(0, 10))
    
        # Contrast
        tk.Label(slider_frame, text="Contrast", fg="white", bg="#1e1e1e").pack()
        self.contrast_scale = tk.Scale(slider_frame, from_=0.0, to=3.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.contrast_var, bg="#1e1e1e", fg="white", troughcolor="#333", highlightthickness=0, command=on_adjust_change)
        self.contrast_scale.pack(fill=tk.X, padx=5, pady=(0, 10))
    
        # Saturation
        tk.Label(slider_frame, text="Saturation", fg="white", bg="#1e1e1e").pack()
        self.saturation_scale = tk.Scale(slider_frame, from_=0.0, to=3.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.saturation_var, bg="#1e1e1e", fg="white", troughcolor="#333", highlightthickness=0, command=on_adjust_change)
        self.saturation_scale.pack(fill=tk.X, padx=5, pady=(0, 10))
    
        # Gamma
        tk.Label(slider_frame, text="Gamma", fg="white", bg="#1e1e1e").pack()
        self.gamma_scale = tk.Scale(slider_frame, from_=0.0, to=5.0, resolution=0.01, orient=tk.HORIZONTAL, variable=self.gamma_var, bg="#1e1e1e", fg="white", troughcolor="#333", highlightthickness=0, command=on_adjust_change)
        self.gamma_scale.pack(fill=tk.X, padx=5, pady=(0, 10))

        # Dithering
        tk.Label(slider_frame, text="Dithering", fg="green", bg="#1e1e1e").pack()
        self.dither_scale = tk.Scale(slider_frame, from_=0.0, to=2.0, resolution=0.05, orient=tk.HORIZONTAL, variable=self.dither_var, bg="#1e1e1e", fg="green", troughcolor="#333", highlightthickness=0, command=on_adjust_change)
        self.dither_scale.pack(fill=tk.X, padx=5, pady=(0, 10))
    

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")])
        if not path: return
        self.original_image = Image.open(path)

        # Copy first frame
        frame0 = self.original_image.copy().convert('RGB')

        w, h = frame0.size
        self.display_scale = min(800/w, 600/h)
        if self.display_scale > 1: self.display_scale = 1.0

        new_w, new_h = int(w * self.display_scale), int(h * self.display_scale)
        self.display_image = frame0.resize((new_w, new_h), Image.Resampling.LANCZOS)

        self.tk_image = ImageTk.PhotoImage(self.display_image)
        self.canvas.config(scrollregion=(0,0,new_w,new_h))
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image, tags="img")

        self.crop_cx, self.crop_cy = new_w/2, new_h/2
        self.crop_zoom = 1.0

        self.update_canvas()
        self.update_preview()
    

    def on_size_change(self, event=None):
        self.target_w_chars = SCREEN_W_MAP[self.w_var.get()]
        self.target_h_chars = SCREEN_H_MAP[self.h_var.get()]
        self.update_canvas()
        self.update_preview()

    
    def on_adjustments_change(self):
        # Empty color cache to force actualization
        global COLOR_CACHE
        COLOR_CACHE = {}
        # Update preview
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
        self.update_canvas()  # No realtime
    

    def on_release(self, event):
        self.update_preview()
    

    def on_scroll(self, event):
        if event.delta > 0 or event.num == 4:
            self.crop_zoom *= 0.9  # Zoom In
        elif event.delta < 0 or event.num == 5:
            self.crop_zoom *= 1.1  # Zoom Out
        self.update_canvas()
        self.update_preview()
    

    def process_single_image(self, img_obj):
        x1, y1, x2, y2 = self.get_crop_box()
        s = self.display_scale
        orig_box = (int(x1/s), int(y1/s), int(x2/s), int(y2/s))

        # 1. Cut image with proportions
        cropped = img_obj.crop(orig_box).convert('RGB')

        # Image correction
        gamma = self.gamma_var.get()
        if gamma != 1.0:
            if gamma == 0.0:
                inv_gamma = 100  # Min value = 0.01 ?
            else:
                inv_gamma = 1.0 / gamma
            table = [int(pow(i / 255.0, inv_gamma) * 255.0) for i in range(256)]
            cropped = cropped.point(table * 3)  # Table *3 spreads single lookup table across RGB channels
        
        saturation = self.saturation_var.get()
        if saturation != 1.0:
            enhancer = ImageEnhance.Color(cropped)
            cropped = enhancer.enhance(saturation)
        
        contrast = self.contrast_var.get()
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(cropped)
            cropped = enhancer.enhance(contrast)
        
        brightness = self.brightness_var.get()
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(cropped)
            cropped = enhancer.enhance(brightness)
            
        # 2. Resize on target char limit
        resized = cropped.resize((self.target_w_chars, self.target_h_chars), Image.Resampling.LANCZOS)

        txt_lines = []
        cc_img = Image.new("RGB", resized.size)
        pixels = resized.load()
        out_pixels = cc_img.load()

        # Dithering logic here I think
        dither_strength = self.dither_var.get() * 64.0

        for y in range(self.target_h_chars):
            line_chars = []
            for x in range(self.target_w_chars):
                r, g, b = pixels[x, y]
                if dither_strength > 0:
                    # Normalize between +/- 0.5 and shift values
                    bayer_val = (BAYER_4X4[y % 4][x % 4] / 16.0) - 0.5
                    r = max(0, min(255, int(r + bayer_val * dither_strength)))
                    g = max(0, min(255, int(g + bayer_val * dither_strength)))
                    b = max(0, min(255, int(b + bayer_val * dither_strength)))

                char, rgb = get_closest_cc_color((r, g, b))
                line_chars.append(char)
                out_pixels[x, y] = rgb
            txt_lines.append("".join(line_chars))
        
        return txt_lines, cc_img
    

    def generate_cc_data(self):
        # Return only frame 0
        return self.process_single_image(self.original_image)
    

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
        os.makedirs("outputs", exist_ok=True)

        file_path = filedialog.asksaveasfilename(
            initialdir="outputs",
            title="Export As...",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")],
            initialfile="export.txt"
        )

        if not file_path: return

        is_animated = getattr(self.original_image, "is_animated", False)
        n_frames = self.original_image.n_frames if is_animated else 1
        duration = self.original_image.info.get('duration', 100) if is_animated else 0
        
        # Make the header
        header = f"{self.target_w_chars},{self.target_h_chars},{n_frames},{duration}"

        # Make user wait and not think its a crash
        self.root.config(cursor="watch")
        self.root.update()

        try:
            with open(file_path, "w") as f:
                f.write(header + "\n")

                if is_animated:
                    for i in range(n_frames):
                        self.original_image.seek(i)
                        txt_lines, cc_img = self.process_single_image(self.original_image)
                        f.write("\n".join(txt_lines) + "\n")
                        if i == 0: first_frame_img = cc_img
                    else:
                        txt_lines, cc_img = self.process_single_image(self.original_image)
                        f.write("\n".join(txt_lines) + "\n")
                        first_frame_img = cc_img
                
            # # If you want to have png preview, uncomment this
            # base_path = os.path.splitext(file_path)[0]
            # png_path = f"{base_path}_raw.png"
            # first_frame_img.save(png_path)

            messagebox.showinfo("SUCCESS", f"Exported {n_frames} frames !")
        
        finally:
            self.original_image.seek(0)  # Reset gif
            self.root.config(cursor="")


def main():
    root = tk.Tk()
    app = CCImageTool(root)
    root.geometry("1100x700")
    root.mainloop()


if __name__ == "__main__":
    main()
