# FormForge

Fill scanned paper forms from a template. Upload a blank form image, draw boxes
where text or marks should go, save it as a reusable template, then generate
filled copies one at a time or in bulk from an Excel sheet. Arabic (right to
left, properly shaped) and English work in the same box.

## Features

- Visual editor: draw field boxes directly on your form image.
- Field types:
  - Text (Arabic or English, direction detected automatically)
  - Date (one box with separate day / month / year slots, so you fill printed
    cells without a hardcoded separator)
  - Multiple choice (places a mark on the selected option; styles: x, check,
    circle, dot)
  - Number cells (one digit per box, for ID or phone numbers)
- Per box font and color pickers, so you can see and change what each box uses.
- Reusable named templates, tied to the form image by content hash.
- Bulk generation from an .xlsx: one row per form, output named by a serial
  column or by row number.
- Runs as a desktop window or in the browser.

## Requirements

- Python 3.10 or newer
- `pip install -r requirements.txt`
- At least one font file in `fonts/` (any .ttf or .otf). For Arabic, Playpen
  Sans Arabic (SIL Open Font License, free on Google Fonts) works well; drop the
  file into `fonts/` and it shows up in the per box font dropdown.

## Run

Desktop window:

    python app.py

Or in a browser:

    python template_tool.py
    # then open http://localhost:8000

## Using it

1. Upload your blank form image (Base img).
2. Switch to Define boxes, pick a box type, and drag rectangles on the form.
   - Date: place the day, month, and year slots.
   - Multiple choice: place a mark box for each option and pick the mark style.
   - Number cells: set how many cells.
3. Set each box's font and color from its dropdowns.
4. Type a template name and Save.
5. Fill values and Render for one form, or use the bulk flow below.

## Bulk generation from Excel

1. Click Download XLSX to get a sheet with one column per field. A date field
   becomes three columns (`name.day`, `name.month`, `name.year`); a choice
   column holds the selected option key.
2. Fill one row per form.
3. Pick the file and click Generate from XLSX.
4. Images land in `output/<template>/`, each named by a field whose name
   contains "serial" if present, otherwise by row number.

## Template format

Templates are JSON. See `fields.example.json`. A field looks like:

    {
      "name": "full_name",
      "type": "text",
      "box": [x0, y0, x1, y1],
      "value": "",
      "font": "fonts/YourFont.ttf",
      "color": "#112233"
    }

`type` is one of `text`, `date`, `choice`, `digits`. `font` and `color` are
optional and fall back to the global defaults.

## Build a Windows executable

    pip install pyinstaller
    python build_exe.py

This produces `dist/FormTemplateEditor.exe`, a single double click file.
Working files (templates, output, your fonts) are created next to the exe on
first run, so keep it in its own folder.

## How Arabic rendering works

This build of Pillow has no HarfBuzz, so text is shaped with `arabic-reshaper`
and `python-bidi`. A font aware fallback swaps any presentation form glyph a
font does not include for an equivalent it does, so different fonts render
without missing letters.

## License

MIT. See LICENSE.
