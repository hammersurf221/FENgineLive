import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk, ImageDraw
import os
import pyautogui
import threading
import time
import chess
import chess.svg
import cairosvg
from stockfish import Stockfish
import io
from ccn_helper.fen_predictor import load_model, load_image, predict_fen
import subprocess
import sys
import platform
from tkinter import filedialog
import cv2
from PIL import ImageChops
import numpy as np
import keyboard


if getattr(sys, 'frozen', False):
    BASE_PATH = sys._MEIPASS  # Path when bundled by PyInstaller
else:
    BASE_PATH = os.path.abspath(".")

EMPTY_BOARD_PATH = "empty_board.png"

def generate_empty_board(path):
    board = Image.new("RGB", (512, 512), "white")
    draw = ImageDraw.Draw(board)
    for row in range(8):
        for col in range(8):
            color = "#eae9dc" if (row + col) % 2 == 0 else "#8b7355"
            draw.rectangle([col * 32, row * 32, (col + 1) * 32, (row + 1) * 32], fill=color)
    board.save(path)

class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 10
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self.tooltip, text=self.text, bg="lightyellow", relief="solid", borderwidth=1, font=("Segoe UI", 9))
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

    def update_text(self, new_text):
        self.text = new_text


class ChessHelperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CCN Chess Helper")
        self.root.geometry("1024x550")
        self.init_variables()
        self.setup_styles()
        self.setup_layout()
        self.load_default_assets()
        self.setup_controls()
        self.setup_bindings()
        self.init_engine_and_model()

    def init_variables(self):
        self.cached_board_img = None
        self.last_rendered_fen = ""
        self.last_rendered_move = ""
        self.last_board_layout = ""
        self.last_move_color = None
        self.region_box = None
        self.last_fen = ""
        self.last_auto_fen = ""
        self.my_color = "w"
        self.depth = 15
        self.analysis_active = False
        self.is_resizing = False

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("TLabel", font=("Segoe UI", 10))
        self.root.configure(bg="#f5f5f5")
        style.configure("TLabel", background="#f5f5f5", font=("Segoe UI", 10))

    def setup_layout(self):
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Label(self.root, text="♟️ CCN Chess Assistant", font=("Segoe UI", 14, "bold"))
        header.grid(row=0, column=0, columnspan=2, sticky="w", padx=10, pady=(10, 5))

        self.setup_board_ui()
        self.setup_eval_ui()

    def setup_board_ui(self):
        if not os.path.exists(EMPTY_BOARD_PATH):
            generate_empty_board(EMPTY_BOARD_PATH)

        self.board_img = Image.open(EMPTY_BOARD_PATH)
        self.tk_board = ImageTk.PhotoImage(self.board_img.resize((512, 512), Image.LANCZOS))

        self.board_frame = tk.Frame(self.root, bg="#ffffff", highlightthickness=1, highlightbackground="#999999")
        self.board_frame.grid(row=1, column=0, padx=20, pady=20, sticky="nsew")
        self.board_frame.columnconfigure(0, weight=1)
        self.board_frame.rowconfigure(0, weight=1)

        self.board_label = tk.Label(self.board_frame, borderwidth=0, bg="#ffffff")
        self.board_label.grid(row=0, column=0, sticky="nsew")

    def setup_eval_ui(self):
        eval_container = tk.Frame(self.root, bg="#f5f5f5")
        eval_container.grid(row=1, column=0, sticky="ne", padx=(0, 10), pady=20)

        ttk.Label(eval_container, text="Eval", font=("Segoe UI", 10)).pack(anchor="e")
        self.eval_canvas = tk.Canvas(eval_container, width=20, height=200, bg="white", bd=1, relief="sunken")
        self.eval_canvas.pack(anchor="e")
        self.eval_score_label = ttk.Label(eval_container, text="0.00")
        self.eval_score_label.pack(anchor="e", pady=(4, 0))

    def setup_controls(self):
        self.controls_frame = tk.Frame(self.root)
        self.controls_frame.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")
        self.controls_frame.columnconfigure(0, weight=1)
        self.controls_frame.rowconfigure(0, weight=1)

        self.warning_label = ttk.Label(self.controls_frame, text="", foreground="red", font=("Segoe UI", 9, "italic"))
        self.warning_label.pack(pady=(10, 0))

        self.status_label = ttk.Label(self.controls_frame, text="", foreground="#555", font=("Segoe UI", 9, "italic"))
        self.status_label.pack(pady=(10, 0))

        self.scan_status_canvas = tk.Canvas(self.controls_frame, width=20, height=20, highlightthickness=0, bg="#f5f5f5")
        self.scan_status_canvas.pack(pady=(5, 0))
        self.scan_status_dot = self.scan_status_canvas.create_oval(2, 2, 18, 18, fill="red", outline="")
        self.scan_status_tooltip = Tooltip(self.scan_status_canvas, "Stopped or Error")

        self.add_buttons()
        self.add_settings()

    def add_buttons(self):
        self.set_region_button = ttk.Button(self.controls_frame, text="🖱 Set Region", command=self.set_region)
        self.auto_region_button = ttk.Button(self.controls_frame, text="🤖 Auto Detect Region", command=self.auto_detect_region)
        self.auto_region_button.pack(pady=5)
        self.set_region_button.pack(pady=5)

        self.start_button = ttk.Button(self.controls_frame, text="▶️ Start Analysis", command=self.start_analysis)
        self.start_button.pack(pady=5)

        self.pause_button = ttk.Button(self.controls_frame, text="⏸ Pause Analysis", command=self.stop_analysis)
        self.pause_button.pack(pady=5)

        self.restart_stockfish_button = ttk.Button(self.controls_frame, text="🔄 Restart Stockfish", command=self.restart_stockfish)
        self.restart_stockfish_button.pack(pady=5)

        self.choose_model_button = ttk.Button(self.controls_frame, text="🧠 Choose Model", command=self.choose_model)
        self.choose_model_button.pack(pady=5)

    def add_settings(self):
        ttk.Label(self.controls_frame, text="FEN:").pack(anchor="w", pady=(20, 0))
        self.fen_display = tk.Text(self.controls_frame, height=2, width=40, state="disabled")
        self.fen_display.pack()

        ttk.Label(self.controls_frame, text="Best Move:").pack(anchor="w", pady=(10, 0))
        self.best_move_display = ttk.Label(self.controls_frame, text="...", font=("Courier", 12))
        self.best_move_display.pack(anchor="w")

        ttk.Label(self.controls_frame, text="Settings:").pack(anchor="w", pady=(20, 0))
        ttk.Label(self.controls_frame, text="My Color:").pack(anchor="w")
        self.color_var = tk.StringVar(value="w")
        ttk.Radiobutton(self.controls_frame, text="White", variable=self.color_var, value="w", command=self.on_color_change).pack(anchor="w")
        ttk.Radiobutton(self.controls_frame, text="Black", variable=self.color_var, value="b", command=self.on_color_change).pack(anchor="w")

        ttk.Label(self.controls_frame, text="Depth:").pack(anchor="w", pady=(10, 0))
        self.depth_var = tk.IntVar(value=15)
        ttk.Entry(self.controls_frame, textvariable=self.depth_var, width=5).pack(anchor="w")

        ttk.Label(self.controls_frame, text="Cooldown (s):").pack(anchor="w", pady=(10, 0))
        self.cooldown_var = tk.DoubleVar(value=1.5)
        ttk.Entry(self.controls_frame, textvariable=self.cooldown_var, width=5).pack(anchor="w")

        self.auto_move_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(self.controls_frame, text="Auto-Move", variable=self.auto_move_var).pack(anchor="w")

    def setup_bindings(self):
        self.root.bind("<Configure>", self.on_resize)
        self.root.bind("m", lambda e: self.auto_move(self.last_rendered_move))
        self.root.bind("a", self.toggle_auto_move)
        keyboard.add_hotkey("a", self.toggle_auto_move)

    def init_engine_and_model(self):
        model_path = os.path.join(BASE_PATH, "ccn_model_default.pth")
        self.model = load_model(model_path)
        stockfish_path = os.path.join(BASE_PATH, "stockfish.exe")
        self.stockfish = Stockfish(path=stockfish_path, parameters={"Threads": 2, "Minimum Thinking Time": 30})

    def load_default_assets(self):
        if not os.path.exists(EMPTY_BOARD_PATH):
            generate_empty_board(EMPTY_BOARD_PATH)



    def on_resize(self, event):
        self.update_board_image()  # This just resizes the existing cached image



    def restart_stockfish(self):
        print("🔁 Restarting Stockfish...")
        stockfish_path = os.path.join(BASE_PATH, "stockfish.exe")
        self.stockfish = Stockfish(
            path=stockfish_path,
            parameters={"Threads": 2, "Minimum Thinking Time": 30},
        )

    def set_region(self):
        print("🖱 Click and drag to select a region...")
        self.root.withdraw()
        overlay = tk.Toplevel()
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-alpha", 0.3)
        overlay.attributes("-topmost", True)
        overlay.config(bg="black")
        overlay.bind("<Escape>", lambda e: (overlay.destroy(), self.root.deiconify()))
        canvas = tk.Canvas(overlay, highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self.region_start = None
        self.rect_id = None

        def on_mouse_down(event):
            self.region_start = (event.x, event.y)
            if self.rect_id:
                canvas.delete(self.rect_id)

        def on_mouse_drag(event):
            if self.region_start:
                x1, y1 = self.region_start
                x2, y2 = event.x, event.y
                if self.rect_id:
                    canvas.delete(self.rect_id)
                self.rect_id = canvas.create_rectangle(x1, y1, x2, y2, outline="red", width=2)

        def on_mouse_up(event):
            x1, y1 = self.region_start
            x2, y2 = event.x, event.y
            overlay.destroy()
            self.root.deiconify()
            self.region_box = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            print(f"✅ Region set to: {self.region_box}")

        canvas.bind("<ButtonPress-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_drag)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

    def auto_detect_region(self):
        print("🔍 Attempting auto-detection of chess board...")
        screenshot = pyautogui.screenshot()
        img_np = np.array(screenshot)
        img = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)

        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        max_area = 0
        best_rect = None
        for cnt in contours:
            approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(cnt)
                area = w * h
                if area > max_area and 0.8 < w / h < 1.2:  # Prefer square-ish
                    max_area = area
                    best_rect = (x, y, w, h)

        if not best_rect:
            print("❌ Could not detect board region")
            self.set_status("❌ Could not detect board region", color="red")
            return

        x, y, w, h = best_rect

        # Show fullscreen preview overlay
        self.root.withdraw()
        overlay = tk.Toplevel()
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.4)
        overlay.configure(bg="black")

        canvas = tk.Canvas(overlay, bg="black", highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_rectangle(x, y, x + w, y + h, outline="red", width=4)

        def accept():
            self.region_box = (x, y, w, h)
            overlay.destroy()
            self.root.deiconify()
            print(f"✅ Auto-detected region set: {self.region_box}")
            self.set_status("✅ Region confirmed", color="green")

        def cancel():
            overlay.destroy()
            self.root.deiconify()
            print("❌ Region not confirmed")
            self.set_status("❌ Detection canceled", color="red")

        overlay.bind("<Return>", lambda e: accept())
        overlay.bind("<Escape>", lambda e: cancel())

        overlay.lift()
        overlay.attributes("-topmost", True)
        overlay.focus_force()
        overlay.grab_set()



        info = tk.Label(overlay, text="Press Enter to Confirm, Esc to Cancel", fg="white", bg="black", font=("Segoe UI", 16))
        info.place(relx=0.5, rely=0.9, anchor="center")


    def start_analysis(self):
        if not self.region_box:
            print("⚠️ Please set a region first.")
            return
        print("▶️ Starting live analysis...")
        self.analysis_active = True
        threading.Thread(target=self.analysis_loop, daemon=True).start()

    def on_color_change(self):
        print(f"🎨 Color changed to {self.color_var.get()}. Restarting analysis.")
        self.stop_analysis()
        self.start_analysis()

    def stop_analysis(self):
        print("⏹ Stopping analysis.")
        self.analysis_active = False
        self.set_scan_light("red")


    def get_best_move(self, fen):
        try:
            self.stockfish.set_fen_position(fen)
            self.stockfish.set_depth(self.depth_var.get())
            info = self.stockfish.get_evaluation()
            score = info.get("value", 0)
            move = self.stockfish.get_best_move()
            return move or "(no move found)", score
        except Exception as e:
            print("❌ Stockfish evaluation failed:", e)
            self.restart_stockfish()
            return "(error)", 0

    def render_fen_to_board(self, fen, best_move=None, save_path="rendered_board.png", board_size=512):
        if (
            fen == self.last_rendered_fen
            and best_move == self.last_rendered_move
            and self.cached_board_img
            and self.board_label.image is not None
        ):
            print("🔕 Skipping render (same fen & move and board already cached)")
            return



        self.last_rendered_fen = fen
        self.last_rendered_move = best_move

        try:
            board = chess.Board(fen.split()[0])
            if not board.is_valid():
                raise ValueError("Invalid board")
        except Exception as e:
            print(f"❌ Error loading FEN: {e}")
            time.sleep(2)
        from_square = to_square = None
        arrows = []
        squares = []
        if best_move and len(best_move) == 4:
            from_square = chess.parse_square(best_move[:2])
            to_square = chess.parse_square(best_move[2:])
            arrows = [chess.svg.Arrow(from_square, to_square, color="#66cc88")]
            squares = [from_square, to_square]  # don’t mark squares harshly

        svg = chess.svg.board(
            board,
            size=1024,
            arrows=arrows,
            squares=squares,
            orientation=self.color_var.get() == "w",
            colors={
                "square light": "#eae9dc",
                "square dark": "#8b7355",
                "arrow": "#66cc88"
            }
        )

        png_data = cairosvg.svg2png(bytestring=svg)
        img = Image.open(io.BytesIO(png_data)).convert("RGBA")
        with open(save_path, "wb") as f:
            f.write(png_data)

        # Add border
        border = 6
        final_img = Image.new("RGB", (img.width + 2 * border, img.height + 2 * border), "#111111")
        final_img.paste(img, (border, border))

        self.cached_board_img = final_img
        self.update_board_image()

    def choose_model(self):
        file_path = filedialog.askopenfilename(
            title="Select CCN Model",
            filetypes=[("PyTorch Model", "*.pth"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                self.model = load_model(file_path)
                self.set_status(f"✅ Model loaded: {os.path.basename(file_path)}", color="green")
                print(f"Loaded model: {file_path}")
            except Exception as e:
                self.set_status("❌ Failed to load model", color="red")
                print("Error loading model:", e)



    def set_status(self, message, color="#555", duration=2500):
        self.status_label.config(text=message, foreground=color)
        if duration:
            self.root.after(duration, lambda: self.status_label.config(text=""))

    def set_scan_light(self, color):
        if hasattr(self, "scan_status_canvas"):
            self.scan_status_canvas.itemconfig(self.scan_status_dot, fill=color)

            if hasattr(self, "scan_status_tooltip"):
                if color == "green":
                    self.scan_status_tooltip.update_text("Live: Scanning...")
                elif color == "yellow":
                    self.scan_status_tooltip.update_text("Idle: Waiting for move")
                else:
                    self.scan_status_tooltip.update_text("Stopped or Error")



    def update_board_image(self):
        if not self.cached_board_img:
            return

        width = self.board_frame.winfo_width()
        height = self.board_frame.winfo_height()
        size = min(width, height)

        if size < 100:
            return

        scaled = self.cached_board_img.resize((size, size), Image.LANCZOS)
        self.tk_board = ImageTk.PhotoImage(scaled)
        self.board_label.config(image=self.tk_board)
        self.board_label.image = self.tk_board


    def draw_eval_bar(self, score):
        self.eval_canvas.delete("all")
        height = 200

        # Flip if black
        if self.color_var.get() == "b":
            score = -score

        score = max(min(score, 1000), -1000)
        percent = (score + 1000) / 2000
        fill_height = height * percent
        self.eval_canvas.create_rectangle(0, height - fill_height, 20, height, fill="#00cc00" if score >= 0 else "#cc0000")

        # Update numerical display
        display_score = score / 100 if abs(score) < 1000 else ("M" if score > 0 else "-M")
        self.eval_score_label.config(text=str(display_score))

    



    def analysis_loop(self):
        try:
            while self.analysis_active:
                screenshot = pyautogui.screenshot(region=self.region_box)
                resized_img = screenshot.resize((256, 256)).convert("RGB")
                live_frame_path = "live_frame.png"
                my_color = self.color_var.get()

                try:
                    resized_img.save(live_frame_path)
                    # ✅ New safety check (add this!)
                    if not os.path.exists(live_frame_path):
                        print("⚠️ live_frame.png not found. Skipping frame.")
                        time.sleep(self.cooldown_var.get())
                        self.set_scan_light("yellow")
                        continue
                    with open(live_frame_path, "rb") as f:
                        f.read()  # make sure it's fully saved before loading

                    image_tensor = load_image(live_frame_path, my_color=my_color)
                    raw_fen = predict_fen(self.model, image_tensor, my_color=my_color)

                except Exception as e:
                    print(f"❌ Failed to load image {live_frame_path}: {e}")
                    self.root.after(0, lambda: self.set_status("❌ Image read error", color="red"))
                    time.sleep(self.cooldown_var.get())
                    continue


                fen_parts = (raw_fen.strip().split(" ") + ["-"] * 6)[:6]
                board_only_fen = fen_parts[0]

                if not self.last_fen:
                    print("⏳ First FEN seen — stabilizing before first move...")
                    self.last_fen = raw_fen
                    self.last_move_color = None
                    time.sleep(self.cooldown_var.get())
                    continue

                # Detect moved color
                moved_color = self.detect_moved_color(self.last_fen.split(" ")[0], board_only_fen)
                self.last_move_color = moved_color
                if moved_color is None:
                    print("⚠️ Could not detect who moved — skipping")
                    time.sleep(self.cooldown_var.get())
                    self.set_scan_light("yellow")
                    continue

                # Set correct side to move
                turn = "b" if moved_color == "w" else "w"
                fen_parts[1] = turn
                full_fen = " ".join(fen_parts)

                # If board layout hasn't changed, skip
                if full_fen == self.last_fen:
                    print("🟡 FEN unchanged — skipping scan")
                    time.sleep(self.cooldown_var.get())
                    self.set_scan_light("yellow")
                    continue


                if full_fen != self.last_fen:
                    print("🔁 Board changed! New FEN:", full_fen)
                    print("Raw FEN prediction:", raw_fen)
                    print("Final FEN with color:", full_fen)

                try:
                    board = chess.Board(full_fen)
                    if not board.is_valid():
                        print("❌ Rejected invalid board layout")
                        time.sleep(self.cooldown_var.get())
                        self.set_scan_light("red")
                        continue
                except Exception as e:
                    print("❌ Error parsing board:", e)
                    time.sleep(self.cooldown_var.get())
                    self.set_scan_light("red")
                    continue

                    # Always run update_gui, even if the FEN is illegal
                try:
                    self.set_scan_light("green")
                    self.update_gui(full_fen, full_fen)
                    self.last_fen = full_fen
                except Exception as e:
                    print(f"❌ Failed to update GUI for FEN: {full_fen}")
                    print(f"   Reason: {e}")
                    self.root.after(0, lambda: self.set_status("❌ Failed to render", color="red"))
                    self.set_scan_light("red")


                else:
                    print("⏭ No change detected — skipping")
                    self.root.after(0, lambda: self.set_status("⏭ Opponent's turn"))
                    self.set_scan_light("yellow")

                # ✅ Cooldown after each scan
                time.sleep(self.cooldown_var.get())

        except Exception as e:
            print("🔥 Analysis loop crashed:", e)
            self.root.after(0, lambda: self.set_status("❌ Crashed. Restarting...", color="red"))
            self.restart_stockfish()
            time.sleep(1)
            self.start_analysis()




    def expand_row(self, row):
        expanded = ""
        for ch in row:
            if ch.isdigit():
                expanded += "." * int(ch)
            else:
                expanded += ch
        return expanded
    
    def detect_moved_color(self, old_fen, new_fen):
        old_rows = old_fen.split("/")
        new_rows = new_fen.split("/")

        if len(old_rows) != 8 or len(new_rows) != 8:
            print("⚠️ Invalid FEN rows — skipping detection")
            return None

        for r in range(8):
            o_row = self.expand_row(old_rows[r])
            n_row = self.expand_row(new_rows[r])
            for c in range(8):
                if o_row[c] != n_row[c]:
                    if n_row[c].islower():
                        return "b"  # black moved here
                    elif n_row[c].isupper():
                        return "w"  # white moved here
        return None
    
    def toggle_auto_move(self, event=None):
        current = self.auto_move_var.get()
        self.auto_move_var.set(not current)
        state = "ON" if not current else "OFF"
        print(f"⚡ Auto-Move toggled {state}")
        self.set_status(f"Auto-Move {state}", color="#007acc")


    def square_to_pixel(self, square):
        # Converts a square like "e2" to pixel coordinates in the selected screen region
        file = ord(square[0]) - ord('a')  # 0 to 7
        rank = 8 - int(square[1])         # 0 to 7 from top to bottom

        if self.color_var.get() == "b":
            file = 7 - file
            rank = 7 - rank

        x, y, w, h = self.region_box
        tile_w = w / 8
        tile_h = h / 8

        px = int(x + file * tile_w + tile_w / 2)
        py = int(y + rank * tile_h + tile_h / 2)
        return px, py

    def auto_move(self, move):
        if not move or len(move) != 4:
            print("⚠️ Invalid move format:", move)
            return
        try:
            from_sq = move[:2]
            to_sq = move[2:]
            start_pos = self.square_to_pixel(from_sq)
            end_pos = self.square_to_pixel(to_sq)

            pyautogui.moveTo(*start_pos, duration=0.2)
            pyautogui.mouseDown()
            pyautogui.moveTo(*end_pos, duration=0.2)
            pyautogui.mouseUp()

            print(f"🤖 Auto-moved: {move} ({start_pos} → {end_pos})")
        except Exception as e:
            print("❌ Auto-move failed:", e)



    def threaded_render(self, fen, best_move):
        self.render_fen_to_board(fen, best_move)
        self.root.after(0, self.update_board_image)  # safely update GUI


    def update_gui(self, display_fen, full_fen, show_best=True):
        print("📟 update_gui triggered")
        print("   display_fen:", display_fen)
        print("   full_fen:", full_fen)

        try:
            self.fen_display.config(state="normal")
            self.fen_display.delete("1.0", tk.END)
            self.fen_display.insert(tk.END, full_fen)
            self.fen_display.config(state="disabled")
        except Exception as e:
            print("❌ Failed updating FEN text:", e)

        try:
            best_move, eval_score = self.get_best_move(full_fen)
            # Trigger auto-move if it's our turn and the feature is enabled
            if (
                self.auto_move_var.get()
                and self.color_var.get() == full_fen.split()[1]
                and self.last_move_color != self.color_var.get()
                and full_fen != self.last_auto_fen
            ):
                self.last_auto_fen = full_fen
                self.root.after(100, lambda: self.auto_move(best_move))
            print("   best_move:", best_move)
            print("   eval_score:", eval_score)
            self.root.after(0, lambda: self.best_move_display.config(text=best_move))
        except Exception as e:
            print("❌ get_best_move failed:", e)
            return

        try:
            self.is_resizing = True
            threading.Thread(
                target=self.threaded_render,
                args=(display_fen, best_move),
                daemon=True
            ).start()
            self.update_board_image()
            self.is_resizing = False
        except Exception as e:
            print("❌ threaded_render or update_board_image failed:", e)

        try:
            self.root.after(0, lambda: self.draw_eval_bar(eval_score))
        except Exception as e:
            print("❌ draw_eval_bar failed:", e)


if __name__ == "__main__":
    root = tk.Tk()
    app = ChessHelperApp(root)
    root.mainloop()
