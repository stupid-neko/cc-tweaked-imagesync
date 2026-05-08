import sys
import os
import tomllib
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk


# Load TOML
def load_config():
    if not os.path.exists("config.toml"):
        messagebox.showerror("ERROR", "config.toml not found")
        sys.exit()
        
    with open("config.toml", "rb") as f:
        config = tomllib.load(f)
        
    palette = {k: tuple(v) for k, v in config["palette_rgb"].items()}
    char_size = tuple(config["char_correction"]["char_size_wh"])
    
    reverse_w_map = {int(v): int(k) for k, v in config["screen_w_map"].items()}
    reverse_h_map = {int(v): int(k) for k, v in config["screen_h_map"].items()}

    return palette, char_size, reverse_w_map, reverse_h_map

try:
    CC_PALETTE, CHAR_SIZE, REVERSE_W_MAP, REVERSE_H_MAP = load_config()
except Exception as e:
    print(f"Error while loading config.toml : {e}")
    sys.exit()

class CCViewerApp:
    def __init__(self, root, initial_file=None):
        self.root = root
        self.root.title("CC:Tweaked ImageSync - Viewer")
        
        self.setup_ui()
        
        if initial_file and os.path.exists(initial_file):
            self.load_and_display(initial_file)


    def setup_ui(self):
        # Toolbox
        top_frame = tk.Frame(self.root, pady=10)
        top_frame.pack(fill=tk.X)
        tk.Button(top_frame, text="Open txt file...", command=self.ask_file).pack()

        # Main display zone
        right_frame = tk.Frame(self.root, bg="#1e1e1e", relief="sunken", borderwidth=2)
        right_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        tk.Label(right_frame, text=f"Simulation", fg="white", bg="#1e1e1e", font=("Arial", 12, "bold")).pack(pady=5)
        
        # Label for detected configuration
        self.lbl_info = tk.Label(right_frame, text="Load a file to see dimensions", fg="#aaaaaa", bg="#1e1e1e", font=("Arial", 10))
        self.lbl_info.pack(pady=(0, 5))
        
        self.lbl_cc = tk.Label(right_frame, bg="black")
        self.lbl_cc.pack(expand=True)

    def ask_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text file", "*.txt")])
        if path:
            self.load_and_display(path)

    def load_and_display(self, file_path):
        with open(file_path, "r") as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
            
        if not lines:
            messagebox.showwarning("EMPTY", "The selected text file is empty")
            return

        width = len(lines[0])
        height = len(lines)

        # Detect image configuration
        screens_w = REVERSE_W_MAP.get(width, "?")
        screens_h = REVERSE_H_MAP.get(height, "?")
        
        info_text = f"Detected config: {screens_w}x{screens_h} screens ({width}x{height})."
        print(f"Loaded {os.path.basename(file_path)} -> {info_text}")
        self.lbl_info.config(text=info_text)

        # Image creation
        img_raw = Image.new("RGB", (width, height))
        pixels = img_raw.load()

        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                if x < width:
                    pixels[x, y] = CC_PALETTE.get(char, (0, 0, 0))

        # Display in the window
        max_display_height = 500
        char_w, char_h = CHAR_SIZE

        # CC render (5:8)
        physical_w = width * char_w
        physical_h = height * char_h
        scale_cc = max(1, max_display_height // physical_h)
        
        img_cc = img_raw.resize((physical_w * scale_cc, physical_h * scale_cc), Image.Resampling.NEAREST)

        # Display in TK
        self.tk_cc = ImageTk.PhotoImage(img_cc)
        self.lbl_cc.config(image=self.tk_cc)
        
        self.root.title(f"CC:Tweaked ImageSync - Viewer [{os.path.basename(file_path)}]")

if __name__ == "__main__":
    # Drag & drop / CLI
    initial_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    root = tk.Tk()
    root.geometry("1000x650")
    app = CCViewerApp(root, initial_path)
    root.mainloop()
