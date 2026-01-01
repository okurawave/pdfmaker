# Image-to-PDF GUI App Spec

## Overview
A lightweight Windows desktop GUI app (Python + Tkinter) that merges image files inside a user-selected folder into a single PDF. The default page order is the filename order of the images.

## Goals
- Let a user pick a folder and generate one PDF from images inside it.
- Default ordering is by image filename.
- Simple, reliable UX with minimal steps.
- Keep the app lightweight on Windows.

## Non-goals
- No OCR or text extraction.
- No image editing features beyond fitting to pages.
- No cloud storage or upload.

## Primary User Flow
1. User launches the app.
2. User selects a folder that contains image files.
3. App lists detected images in filename order.
4. User sets optional output name and destination.
5. User clicks "Create PDF".
6. App generates the PDF and shows success or error.

## Functional Requirements
- Folder selection via standard OS picker.
- Folder drag-and-drop onto the app to set the input folder.
- Detect supported image files in the selected folder (non-recursive by default).
- Default ordering: sort by filename (lexicographic, case-insensitive).
- Allow manual reordering (nice-to-have, optional).
- Allow user to set output PDF name and destination.
- Allow user to fix the output folder in Settings; if unset, output in the input folder.
- Generate a single PDF with one image per page.
- Fit image to page while preserving aspect ratio.
- Provide progress feedback during generation with current file.
- On launch, check for updates and prompt user to update if available.

## Supported Formats
- Input images: .jpg, .jpeg, .png, .bmp, .gif (first frame only).
- Output: .pdf

## PDF Layout
- Page size: selectable (A4 fit, A4 no-upscale, or original image size).
- Image placement: center on page, fit to page bounds, preserve aspect ratio.
- Background: white.

## Sorting Rules
- Default: filename order (lexicographic, case-insensitive).
- If filenames contain numbers, no special natural sort unless explicitly added later.
- Files with unsupported extensions are ignored.

## Error Handling
- Empty folder: show "No supported images found".
- Read failure: skip file and show a warning in a report.
- Write failure: show error and do not delete partial output.

## UX Notes
- Keep the main window minimal: folder picker, output path, list preview, action button.
- Support dropping a folder onto the main window.
- Provide a preview pane for the selected image.
- Disable "Create PDF" until a valid folder and at least one image are selected.
- Show a clear success message with the output path.
- When an update is available, ask user to update and perform the update automatically on confirmation.

## Open Questions
- None.
