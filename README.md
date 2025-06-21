# hello-world
First repository

## QR Generator

This repository now includes a simple QR code generator written entirely in
Python without external dependencies.

The `qr_generator.py` script is marked as executable so it can be run directly.

### Usage

```bash
./qr_generator.py "Hello World" hello.ppm
```

The output image is a plain PPM file which can be viewed with many image
viewers. No additional Python packages are required.


### GUI version

A simple graphical interface is provided in `qr_gui.py`. Run the script to
enter the text to encode and choose an output file interactively:

```bash
./qr_gui.py
```

The script uses Tkinter, so it runs with the default Python installation.

To bundle the GUI as a standalone executable, install `pyinstaller` and run:

```bash
pyinstaller --onefile qr_gui.py
```

The resulting executable will be placed in the `dist` directory.
