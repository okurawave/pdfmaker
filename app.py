import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:
    DND_FILES = None
    TkinterDnD = None

from PIL import Image
import img2pdf


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
A4_SIZE_PT = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Image Folder to PDF")
        self.root.geometry("820x560")
        self.root.minsize(700, 480)

        self.folder_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Select a folder to begin.")

        self.images = []

        self._build_ui()
        self._setup_dnd()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(4, weight=1)

        title = ttk.Label(container, text="Image Folder to PDF", font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w")

        folder_label = ttk.Label(container, text="Input folder")
        folder_label.grid(row=1, column=0, sticky="w", pady=(12, 4))

        folder_entry = ttk.Entry(container, textvariable=self.folder_path, state="readonly")
        folder_entry.grid(row=1, column=1, sticky="ew", pady=(12, 4))

        folder_button = ttk.Button(container, text="Select Folder", command=self.select_folder)
        folder_button.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(12, 4))

        output_label = ttk.Label(container, text="Output PDF")
        output_label.grid(row=2, column=0, sticky="w", pady=4)

        output_entry = ttk.Entry(container, textvariable=self.output_path)
        output_entry.grid(row=2, column=1, sticky="ew", pady=4)

        output_button = ttk.Button(container, text="Browse", command=self.select_output)
        output_button.grid(row=2, column=2, sticky="ew", padx=(8, 0), pady=4)

        info = ttk.Label(
            container,
            text="Tip: Drag and drop a folder onto this window.",
            foreground="#555555",
        )
        info.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 6))

        list_frame = ttk.Frame(container)
        list_frame.grid(row=4, column=0, columnspan=3, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.listbox = tk.Listbox(list_frame, height=12)
        self.listbox.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.progress = ttk.Progressbar(container, mode="indeterminate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 2))

        self.status_label = ttk.Label(container, textvariable=self.status_text)
        self.status_label.grid(row=6, column=0, columnspan=3, sticky="w")

        self.create_button = ttk.Button(container, text="Create PDF", command=self.create_pdf)
        self.create_button.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self.create_button.state(["disabled"])

    def _setup_dnd(self) -> None:
        if not TkinterDnD or not DND_FILES:
            return
        try:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self.on_drop)
        except Exception:
            pass

    def select_folder(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.set_folder(path)

    def select_output(self) -> None:
        initial = self.output_path.get().strip() or "output.pdf"
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=os.path.basename(initial),
        )
        if path:
            self.output_path.set(path)

    def on_drop(self, event: tk.Event) -> None:
        data = event.data
        try:
            paths = self.root.tk.splitlist(data)
        except Exception:
            paths = [data]
        if not paths:
            return
        path = os.path.normpath(paths[0])
        if os.path.isdir(path):
            self.set_folder(path)

    def set_folder(self, path: str) -> None:
        self.folder_path.set(path)
        self.load_images(path)
        self.output_path.set(self.default_output_path(path))

    def default_output_path(self, folder: str) -> str:
        base = os.path.basename(os.path.normpath(folder)) or "output"
        return os.path.join(folder, f"{base}.pdf")

    def load_images(self, folder: str) -> None:
        try:
            entries = os.listdir(folder)
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to read folder: {exc}")
            return

        images = []
        for name in entries:
            ext = os.path.splitext(name)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                images.append(os.path.join(folder, name))

        images.sort(key=lambda p: os.path.basename(p).lower())
        self.images = images
        self.refresh_list()
        self.update_status()

    def refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        for path in self.images:
            self.listbox.insert(tk.END, os.path.basename(path))

    def update_status(self) -> None:
        if not self.images:
            self.status_text.set("No supported images found.")
            self.create_button.state(["disabled"])
        else:
            self.status_text.set(f"{len(self.images)} image(s) ready.")
            self.create_button.state(["!disabled"])

    def create_pdf(self) -> None:
        if not self.images:
            messagebox.showwarning("No Images", "No supported images found.")
            return

        output = self.output_path.get().strip()
        if not output:
            self.select_output()
            output = self.output_path.get().strip()
            if not output:
                return

        if not output.lower().endswith(".pdf"):
            output += ".pdf"
            self.output_path.set(output)

        self.create_button.state(["disabled"])
        self.progress.start(10)
        self.status_text.set("Generating PDF...")

        thread = threading.Thread(target=self._generate_pdf_thread, args=(output,), daemon=True)
        thread.start()

    def _generate_pdf_thread(self, output: str) -> None:
        warnings = []
        valid_images = []

        for path in self.images:
            try:
                with Image.open(path) as img:
                    img.verify()
                valid_images.append(path)
            except Exception:
                warnings.append(os.path.basename(path))

        if not valid_images:
            self.root.after(0, lambda: self._on_generation_failed("No valid images found."))
            return

        try:
            layout_fun = img2pdf.get_layout_fun(A4_SIZE_PT)
            pdf_bytes = img2pdf.convert(valid_images, layout_fun=layout_fun)
            with open(output, "wb") as f:
                f.write(pdf_bytes)
        except Exception as exc:
            self.root.after(0, lambda: self._on_generation_failed(str(exc)))
            return

        self.root.after(0, lambda: self._on_generation_success(output, warnings))

    def _on_generation_failed(self, message: str) -> None:
        self.progress.stop()
        self.update_status()
        messagebox.showerror("Error", f"Failed to create PDF: {message}")

    def _on_generation_success(self, output: str, warnings: list) -> None:
        self.progress.stop()
        self.update_status()

        warning_text = ""
        if warnings:
            preview = warnings[:5]
            extra = len(warnings) - len(preview)
            warning_text = "\n\nSkipped unreadable files:\n" + "\n".join(preview)
            if extra:
                warning_text += f"\n... and {extra} more"

        messagebox.showinfo("Done", f"PDF created: {output}{warning_text}")


def main() -> None:
    if TkinterDnD:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
