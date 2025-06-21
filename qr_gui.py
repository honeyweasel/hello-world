#!/usr/bin/env python3
"""Simple GUI wrapper for the pure Python QR generator."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

from qr_generator import generate_qr


def _generate():
    data = entry.get()
    if not data:
        messagebox.showerror("Error", "Please enter text to encode")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".ppm", filetypes=[("PPM image", "*.ppm")]
    )
    if not path:
        return
    try:
        generate_qr(data, path)
    except Exception as exc:  # pragma: no cover - user feedback only
        messagebox.showerror("Error", str(exc))
    else:
        messagebox.showinfo("Success", f"QR code saved to {path}")


root = tk.Tk()
root.title("QR Generator")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack()

label = tk.Label(frame, text="Text to encode:")
label.pack(anchor="w")

entry = tk.Entry(frame, width=40)
entry.pack(fill="x")

button = tk.Button(frame, text="Generate", command=_generate)
button.pack(pady=5)

root.mainloop()
