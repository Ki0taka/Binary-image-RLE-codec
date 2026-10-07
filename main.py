"""Tkinter editor for drawing and compressing binary images with RLE."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

from image_file import (
    load_compressed_with_trace,
    load_image,
    load_png,
    MAX_EDITOR_SIDE,
    FILE_HEADER,
    save_compressed_with_trace,
    save_image,
    save_png,
)
from rle_codec import CodecError, encode_with_trace

CELL = 18
MIN_SIDE = 1
MAX_SIDE = MAX_EDITOR_SIDE


class BinaryImageApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Codec RLE — Image binaire")
        self.minsize(520, 420)
        self.width_var = tk.IntVar(value=32)
        self.height_var = tk.IntVar(value=24)
        self.img_w = 32
        self.img_h = 24
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
        tk.Button(actions, text="Exporter PNG", command=self.save_png_file).pack(side="left", padx=5)
        tk.Button(actions, text="Compresser et enregistrer", command=self.save_rle).pack(side="left", padx=5)
        tk.Button(actions, text="Décompresser / ouvrir", command=self.open_rle).pack(side="left", padx=5)
        tk.Button(actions, text="Étapes de compression", command=self.show_encode_steps).pack(side="left", padx=5)

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

    def _requested_dimensions(self) -> tuple[int, int]:
        width, height = self.width_var.get(), self.height_var.get()
        if not (MIN_SIDE <= width <= MAX_SIDE and MIN_SIDE <= height <= MAX_SIDE):
            raise ValueError(f"Dimensions must be between {MIN_SIDE} and {MAX_SIDE}")
        return width, height

    def _dimensions(self) -> tuple[int, int]:
        """Return dimensions matching the committed pixel buffer."""
        return self.img_w, self.img_h

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
            width, height = self._requested_dimensions()
        except (ValueError, tk.TclError) as error:
            messagebox.showerror("Dimensions invalides", str(error))
            self.width_var.set(self.img_w)
            self.height_var.set(self.img_h)
            return
        self.img_w, self.img_h = width, height
        self.pixels = bytearray([255] * (width * height))
        self._draw_grid()
        self._update_status()

    def _install_image(self, width: int, height: int, pixels: bytes) -> None:
        if not (MIN_SIDE <= width <= MAX_SIDE and MIN_SIDE <= height <= MAX_SIDE):
            raise CodecError(
                f"Image trop grande ({width} × {height}); limite : {MAX_SIDE} pixels par côté"
            )
        if len(pixels) != width * height:
            raise CodecError("Pixel count does not match image dimensions")
        if any(pixel not in (0, 255) for pixel in pixels):
            raise CodecError("Image contains a value other than 0 or 255")
        self.img_w, self.img_h = width, height
        self.width_var.set(width)
        self.height_var.set(height)
        self.pixels = bytearray(pixels)
        self._draw_grid()
        self._update_status()

    def open_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Ouvrir une image",
            filetypes=[("Images prises en charge", "*.bimg *.png *.jpg *.jpeg *.bmp"), ("Tous les fichiers", "*.*")],
        )
        if not path:
            return
        try:
            if path.lower().endswith(".bimg"):
                image = load_image(path, max_side=MAX_SIDE)
            else:
                image = load_png(path)
            self._install_image(*image)
        except (OSError, CodecError, tk.TclError) as error:
            messagebox.showerror("Ouverture impossible", str(error))

    def open_rle(self) -> None:
        path = filedialog.askopenfilename(
            title="Ouvrir une image compressée", filetypes=[("Image RLE", "*.rle"), ("Tous les fichiers", "*.*")]
        )
        if not path:
            return
        try:
            width, height, pixels, trace = load_compressed_with_trace(path, max_side=MAX_SIDE)
            self._install_image(width, height, pixels)
            self._show_steps("Étapes de décompression RLE", trace)
        except (OSError, CodecError, tk.TclError) as error:
            messagebox.showerror("Décompression impossible", str(error))

    def save_plain(self) -> None:
        self._save(compressed=False)

    def save_png_file(self) -> None:
        try:
            width, height = self._dimensions()
        except (ValueError, tk.TclError) as error:
            messagebox.showerror("Dimensions invalides", str(error))
            return
        path = filedialog.asksaveasfilename(
            title="Exporter en PNG", defaultextension=".png",
            filetypes=[("Image PNG", "*.png")],
        )
        if not path:
            return
        try:
            if Path(path).suffix.lower() != ".png":
                messagebox.showerror("Format invalide", "Le fichier exporté doit avoir l’extension .png")
                return
            save_png(path, width, height, bytes(self.pixels))
        except (OSError, CodecError) as error:
            messagebox.showerror("Export PNG impossible", str(error))

    def save_rle(self) -> None:
        self._save(compressed=True)

    def show_encode_steps(self) -> None:
        encoded, trace = encode_with_trace(bytes(self.pixels))
        self._show_steps("Étapes de compression RLE", trace, encoded)

    def _show_steps(
        self, title: str, trace: list[str], encoded: bytes | None = None
    ) -> None:
        window = tk.Toplevel(self)
        window.title(title)
        window.geometry("760x520")
        text = tk.Text(window, wrap="word", font=("TkFixedFont", 10))
        scrollbar = tk.Scrollbar(window, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        width, height = self._dimensions()
        text.insert("end", f"Image : {width} × {height} = {width * height} pixels\n")
        text.insert(
            "end",
            "Rule: runs of 3+ equal pixels use flag 1 + 15-bit count + color byte. "
            "Other pixels are grouped in literals with flag 0 + 15-bit count + pixel bytes.\n\n",
        )
        if encoded is not None:
            raw_file_size = FILE_HEADER.size + len(self.pixels)
            compressed_file_size = FILE_HEADER.size + len(encoded)
            preview = " ".join(f"{value:02X}" for value in encoded[:64])
            if len(encoded) > 64:
                preview += " …"
            text.insert(
                "end",
                f"Original: {raw_file_size} bytes as .bimg; compressed: "
                f"{compressed_file_size} bytes as .rle.\n"
                f"Encoded packet stream ({len(encoded)} bytes; first 64): {preview}\n\n",
            )
        text.insert("end", "\n\n".join(trace) if trace else "Aucun pixel à coder.")
        text.configure(state="disabled")

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
                encoded, trace = save_compressed_with_trace(path, width, height, bytes(self.pixels))
                packed_size = Path(path).stat().st_size
                raw_size = FILE_HEADER.size + len(self.pixels)
                self.status.set(
                    f"Fichier .rle : {packed_size} octets; fichier .bimg : {raw_size} octets"
                )
                self._show_steps("Étapes de compression RLE", trace, encoded)
            else:
                save_image(path, width, height, bytes(self.pixels))
                self._update_status()
        except (OSError, CodecError) as error:
            messagebox.showerror("Enregistrement impossible", str(error))


if __name__ == "__main__":
    BinaryImageApp().mainloop()
