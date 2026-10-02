"""Tkinter editor for drawing and compressing binary images with RLE."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

from image_file import load_compressed, load_image, save_compressed, save_image
from rle_codec import CodecError

CELL = 18
MIN_SIDE = 1
MAX_SIDE = 256


class BinaryImageApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Codec RLE — Image binaire")
        self.minsize(520, 420)
        self.width_var = tk.IntVar(value=32)
        self.height_var = tk.IntVar(value=24)
        self.pixels = bytearray([255] * (32 * 24))
        self._build_controls()
        self._build_canvas()
        self._draw_grid()
        self._update_status()

    def _build_controls(self) -> None:
        bar = tk.Frame(self, padx=8, pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="Largeur").pack(side="left")
        tk.Spinbox(bar, from_=MIN_SIDE, to=MAX_SIDE, width=5,
                   textvariable=self.width_var).pack(side="left", padx=(4, 10))
        tk.Label(bar, text="Hauteur").pack(side="left")
        tk.Spinbox(bar, from_=MIN_SIDE, to=MAX_SIDE, width=5,
                   textvariable=self.height_var).pack(side="left", padx=(4, 8))
        tk.Button(bar, text="Nouvelle image", command=self.new_image).pack(side="left")

        actions = tk.Frame(self, padx=8)
        actions.pack(fill="x")
        tk.Button(actions, text="Ouvrir", command=self.open_file).pack(side="left", padx=(0, 5))
        tk.Button(actions, text="Enregistrer l’image", command=self.save_plain).pack(side="left", padx=5)
        tk.Button(actions, text="Compresser et enregistrer", command=self.save_rle).pack(side="left", padx=5)
        tk.Button(actions, text="Décompresser / ouvrir", command=self.open_rle).pack(side="left", padx=5)

        self.status = tk.StringVar()
        tk.Label(self, textvariable=self.status, anchor="w", padx=8, pady=6).pack(fill="x", side="bottom")

    def _build_canvas(self) -> None:
        wrapper = tk.Frame(self)
        wrapper.pack(fill="both", expand=True, padx=8, pady=8)
        self.canvas = tk.Canvas(wrapper, background="#dddddd", highlightthickness=0)
        xbar = tk.Scrollbar(wrapper, orient="horizontal", command=self.canvas.xview)
        ybar = tk.Scrollbar(wrapper, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ybar.grid(row=0, column=1, sticky="ns")
        xbar.grid(row=1, column=0, sticky="ew")
        wrapper.rowconfigure(0, weight=1)
        wrapper.columnconfigure(0, weight=1)
        self.canvas.bind("<Button-1>", self._paint)
        self.canvas.bind("<B1-Motion>", self._paint)
        self.canvas.bind("<Button-3>", self._erase)
        self.canvas.bind("<B3-Motion>", self._erase)

    def _dimensions(self) -> tuple[int, int]:
        width, height = self.width_var.get(), self.height_var.get()
        if not (MIN_SIDE <= width <= MAX_SIDE and MIN_SIDE <= height <= MAX_SIDE):
            raise ValueError(f"Dimensions must be between {MIN_SIDE} and {MAX_SIDE}")
        return width, height

    def _draw_grid(self) -> None:
        width, height = self._dimensions()
        self.canvas.delete("all")
        for y in range(height):
            for x in range(width):
                value = self.pixels[y * width + x]
                color = "white" if value == 255 else "black"
                self.canvas.create_rectangle(
                    x * CELL, y * CELL, (x + 1) * CELL, (y + 1) * CELL,
                    fill=color, outline="#b5b5b5", tags=f"pixel-{x}-{y}",
                )
        self.canvas.configure(scrollregion=(0, 0, width * CELL, height * CELL))

    def _paint_at(self, event: tk.Event, value: int) -> None:
        width, height = self._dimensions()
        x = int(self.canvas.canvasx(event.x) // CELL)
        y = int(self.canvas.canvasy(event.y) // CELL)
        if 0 <= x < width and 0 <= y < height:
            self.pixels[y * width + x] = value
            color = "white" if value == 255 else "black"
            self.canvas.itemconfigure(f"pixel-{x}-{y}", fill=color)
            self._update_status()

    def _paint(self, event: tk.Event) -> None:
        self._paint_at(event, 0)

    def _erase(self, event: tk.Event) -> None:
        self._paint_at(event, 255)

    def _update_status(self) -> None:
        width, height = self._dimensions()
        black = self.pixels.count(0)
        self.status.set(f"{width} × {height} pixels    Noir : {black}    Blanc : {len(self.pixels) - black}")

    def new_image(self) -> None:
        try:
            width, height = self._dimensions()
        except (ValueError, tk.TclError) as error:
            messagebox.showerror("Dimensions invalides", str(error))
            return
        self.pixels = bytearray([255] * (width * height))
        self._draw_grid()
        self._update_status()

    def _install_image(self, width: int, height: int, pixels: bytes) -> None:
        self.width_var.set(width)
        self.height_var.set(height)
        self.pixels = bytearray(pixels)
        self._draw_grid()
        self._update_status()

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Ouvrir une image", filetypes=[("Image binaire", "*.bimg"), ("Tous les fichiers", "*.*")]
        )
        if not path:
            return
        try:
            self._install_image(*load_image(path))
        except (OSError, CodecError, tk.TclError) as error:
            messagebox.showerror("Ouverture impossible", str(error))

    def open_rle(self) -> None:
        path = filedialog.askopenfilename(
            title="Ouvrir une image compressée", filetypes=[("Image RLE", "*.rle"), ("Tous les fichiers", "*.*")]
        )
        if not path:
            return
        try:
            self._install_image(*load_compressed(path))
        except (OSError, CodecError, tk.TclError) as error:
            messagebox.showerror("Décompression impossible", str(error))

    def save_plain(self) -> None:
        self._save(compressed=False)

    def save_rle(self) -> None:
        self._save(compressed=True)

    def _save(self, compressed: bool) -> None:
        try:
            width, height = self._dimensions()
        except (ValueError, tk.TclError) as error:
            messagebox.showerror("Dimensions invalides", str(error))
            return
        extension = ".rle" if compressed else ".bimg"
        path = filedialog.asksaveasfilename(
            title="Enregistrer l’image", defaultextension=extension,
            filetypes=[("Image RLE" if compressed else "Image binaire", f"*{extension}"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        try:
            if compressed:
                save_compressed(path, width, height, bytes(self.pixels))
                packed_size = Path(path).stat().st_size
                raw_size = 12 + len(self.pixels)
                self.status.set(f"Image compressée : {packed_size} octets (original : {raw_size} octets)")
            else:
                save_image(path, width, height, bytes(self.pixels))
                self._update_status()
        except (OSError, CodecError) as error:
            messagebox.showerror("Enregistrement impossible", str(error))


if __name__ == "__main__":
    BinaryImageApp().mainloop()
