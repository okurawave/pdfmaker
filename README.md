# pdfmaker

A lightweight Windows GUI app that merges images in a folder into a single PDF.

## Requirements
- Python 3.10+
- Tkinter (bundled with standard Python on Windows)

Install dependencies:
```
pip install -r requirements.txt
```

## Run
```
python app.py
```

## Notes
- Default order: filename order (case-insensitive).
- Supported image types: jpg, jpeg, png, bmp, gif (first frame only).
- Drag and drop a folder onto the window to load images.
