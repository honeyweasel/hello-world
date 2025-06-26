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
    # Automatically add mailto: if input looks like an email address
    if "@" in data and not data.lower().startswith("mailto:") and "." in data.split("@")[-1]:
        data = f"mailto:{data}"
    path = filedialog.asksaveasfilename(
        defaultextension=".jpg", filetypes=[("JPEG image", "*.jpg;*.jpeg")]
    )
    if not path:
        return
    # Ensure file extension is .jpg if not present
    if not (path.lower().endswith('.jpg') or path.lower().endswith('.jpeg')):
        path += ".jpg"
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
