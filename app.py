import json
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import zipfile
from tkinter import filedialog, messagebox, ttk
from urllib.request import Request, urlopen

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except Exception:
    DND_FILES = None
    TkinterDnD = None

from PIL import Image, ImageTk
import img2pdf


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
A4_SIZE_PT = (img2pdf.mm_to_pt(210), img2pdf.mm_to_pt(297))
APP_VERSION = "0.1.8"
UPDATE_API_URL = "https://api.github.com/repos/okurawave/pdfmaker/releases/latest"
UPDATE_ASSET_NAME = "pdfmaker-setup.exe"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Image Folder to PDF")
        self.root.geometry("820x560")
        self.root.minsize(700, 480)

        self.folder_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.status_text = tk.StringVar(value="Select a folder to begin.")
        self.progress_text = tk.StringVar(value="")
        self.page_mode = tk.StringVar(value="A4 (fit)")
        self.use_fixed_output = tk.BooleanVar(value=True)
        self.fixed_output_dir = tk.StringVar(value=default_output_dir())
        self.batch_mode = tk.BooleanVar(value=False)

        self.images = []
        self.display_names = []
        self.batch_folders = []
        self.input_is_zip = False
        self.active_folder = ""
        self.temp_dir = None
        self.preview_image = None

        self.load_settings()
        self._build_ui()
        self._setup_dnd()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(600, self.start_update_check)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(4, weight=1)
        container.rowconfigure(5, weight=0)
        container.rowconfigure(6, weight=0)

        title = ttk.Label(container, text="Image Folder to PDF", font=("Segoe UI", 14, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w")

        settings_button = ttk.Button(container, text="Settings", command=self.open_settings)
        settings_button.grid(row=0, column=2, sticky="e")

        folder_label = ttk.Label(container, text="Input folder or zip")
        folder_label.grid(row=1, column=0, sticky="w", pady=(12, 4))

        folder_entry = ttk.Entry(container, textvariable=self.folder_path, state="readonly")
        folder_entry.grid(row=1, column=1, sticky="ew", pady=(12, 4))

        input_button_frame = ttk.Frame(container)
        input_button_frame.grid(row=1, column=2, sticky="ew", padx=(8, 0), pady=(12, 4))
        input_button_frame.columnconfigure(0, weight=1)

        folder_button = ttk.Button(input_button_frame, text="Select Folder", command=self.select_folder)
        folder_button.grid(row=0, column=0, sticky="ew")

        zip_button = ttk.Button(input_button_frame, text="Select Zip", command=self.select_zip)
        zip_button.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        output_label = ttk.Label(container, text="Output PDF")
        output_label.grid(row=2, column=0, sticky="w", pady=4)

        self.output_entry = ttk.Entry(container, textvariable=self.output_path)
        self.output_entry.grid(row=2, column=1, sticky="ew", pady=4)

        self.output_button = ttk.Button(container, text="Browse", command=self.select_output)
        self.output_button.grid(row=2, column=2, sticky="ew", padx=(8, 0), pady=4)

        page_label = ttk.Label(container, text="Page size")
        page_label.grid(row=3, column=0, sticky="w", pady=(4, 6))

        page_mode = ttk.Combobox(
            container,
            textvariable=self.page_mode,
            state="readonly",
            values=["A4 (fit)", "A4 (no upscale)", "Original size"],
        )
        page_mode.grid(row=3, column=1, sticky="w", pady=(4, 6))

        info = ttk.Label(
            container,
            text="Tip: Drag and drop a folder or zip file.",
            foreground="#555555",
        )
        info.grid(row=3, column=2, sticky="e", pady=(4, 6))

        list_frame = ttk.Frame(container)
        list_frame.grid(row=4, column=0, columnspan=2, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)

        controls_frame = ttk.Frame(list_frame)
        controls_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        controls_frame.columnconfigure(0, weight=1)

        batch_frame = ttk.Frame(controls_frame)
        batch_frame.grid(row=0, column=0, sticky="w")

        batch_check = ttk.Checkbutton(
            batch_frame,
            text="Batch mode",
            variable=self.batch_mode,
            command=self.on_mode_change,
        )
        batch_check.grid(row=0, column=0, sticky="w")

        self.add_folder_button = ttk.Button(
            batch_frame, text="Add Folder", command=self.add_batch_folder
        )
        self.add_folder_button.grid(row=0, column=1, padx=(8, 0))

        self.clear_batch_button = ttk.Button(
            batch_frame, text="Clear", command=self.clear_batch_folders
        )
        self.clear_batch_button.grid(row=0, column=2, padx=(6, 0))

        reorder_frame = ttk.Frame(controls_frame)
        reorder_frame.grid(row=0, column=1, sticky="e")

        self.move_up_button = ttk.Button(reorder_frame, text="Up", command=lambda: self.move_selected(-1))
        self.move_up_button.grid(row=0, column=0, padx=(0, 6))

        self.move_down_button = ttk.Button(reorder_frame, text="Down", command=lambda: self.move_selected(1))
        self.move_down_button.grid(row=0, column=1)

        self.listbox = tk.Listbox(list_frame, height=12)
        self.listbox.grid(row=1, column=0, sticky="nsew")
        self.listbox.bind("<<ListboxSelect>>", self.on_select_image)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        preview_frame = ttk.Labelframe(container, text="Preview")
        preview_frame.grid(row=4, column=2, sticky="nsew", padx=(8, 0))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.preview_label = ttk.Label(preview_frame, text="No image selected", anchor="center")
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)

        self.progress = ttk.Progressbar(container, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 2))

        self.progress_label = ttk.Label(container, textvariable=self.progress_text)
        self.progress_label.grid(row=6, column=0, columnspan=3, sticky="w")

        self.status_label = ttk.Label(container, textvariable=self.status_text)
        self.status_label.grid(row=7, column=0, columnspan=3, sticky="w")

        self.create_button = ttk.Button(container, text="Create PDF", command=self.create_pdf)
        self.create_button.grid(row=8, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        self.create_button.state(["disabled"])
        self.update_output_controls()

        version_label = ttk.Label(container, text=f"v{APP_VERSION}", foreground="#666666")
        version_label.grid(row=9, column=2, sticky="e", pady=(6, 0))
        self.on_mode_change()

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
            if self.batch_mode.get():
                self.add_batch_folder(path)
            else:
                self.set_input(path)

    def select_zip(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Zip files", "*.zip")],
        )
        if path:
            if self.batch_mode.get():
                messagebox.showwarning("Batch Mode", "Zip input is not available in batch mode.")
                return
            self.set_input(path)

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
        norm_paths = [os.path.normpath(p) for p in paths]
        folders = [p for p in norm_paths if os.path.isdir(p)]
        zips = [p for p in norm_paths if self._is_zip_file(p)]
        if self.batch_mode.get() or len(folders) > 1:
            for folder in folders:
                self.add_batch_folder(folder)
            if zips:
                messagebox.showwarning("Batch Mode", "Zip input is not available in batch mode.")
            return
        if folders:
            self.set_input(folders[0])
        elif zips:
            self.set_input(zips[0])

    def _is_zip_file(self, path: str) -> bool:
        return os.path.isfile(path) and path.lower().endswith(".zip")

    def _clear_temp_dir(self) -> None:
        if self.temp_dir:
            try:
                self.temp_dir.cleanup()
            except Exception:
                pass
            self.temp_dir = None

    def set_input(self, path: str) -> None:
        self._clear_temp_dir()
        self.input_is_zip = False
        self.active_folder = ""

        if self._is_zip_file(path):
            try:
                temp_dir = tempfile.TemporaryDirectory(prefix="pdfmaker_zip_")
                with zipfile.ZipFile(path, "r") as zf:
                    zf.extractall(temp_dir.name)
                self.temp_dir = temp_dir
                self.input_is_zip = True
                self.active_folder = temp_dir.name
            except Exception as exc:
                self._clear_temp_dir()
                messagebox.showerror("Error", f"Failed to read zip file: {exc}")
                return
        elif os.path.isdir(path):
            self.active_folder = path
        else:
            messagebox.showwarning("Input", "Please select a folder or a zip file.")
            return

        self.folder_path.set(path)
        self.load_images(self.active_folder, recursive=self.input_is_zip)
        self.apply_output_path()

    def default_output_path(self, folder: str) -> str:
        base = os.path.basename(os.path.normpath(folder)) or "output"
        return os.path.join(folder, f"{base}.pdf")

    def _input_base_name(self, path: str) -> str:
        base = os.path.basename(os.path.normpath(path)) or "output"
        if self._is_zip_file(path):
            base = os.path.splitext(base)[0] or "output"
        return base

    def _input_output_dir(self, path: str) -> str:
        if self._is_zip_file(path):
            return os.path.dirname(path)
        return path

    def apply_output_path(self) -> None:
        input_path = self.folder_path.get().strip()
        if not input_path:
            return
        base = self._input_base_name(input_path)
        if self.use_fixed_output.get() and self.fixed_output_dir.get().strip():
            output_dir = self.fixed_output_dir.get().strip()
        else:
            output_dir = self._input_output_dir(input_path)
        self.output_path.set(os.path.join(output_dir, f"{base}.pdf"))

    def collect_images(self, folder: str, recursive: bool = False) -> tuple[list, list]:
        try:
            entries = os.listdir(folder)
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to read folder: {exc}")
            return [], []

        images = []
        display_names = []
        if recursive:
            for root, _, files in os.walk(folder):
                for name in files:
                    ext = os.path.splitext(name)[1].lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        path = os.path.join(root, name)
                        images.append(path)
                        display_names.append(os.path.relpath(path, folder))
            if images:
                images, display_names = zip(
                    *sorted(zip(images, display_names), key=lambda t: t[1].lower())
                )
        else:
            for name in entries:
                ext = os.path.splitext(name)[1].lower()
                if ext in SUPPORTED_EXTENSIONS:
                    images.append(os.path.join(folder, name))
                    display_names.append(name)
            if images:
                images, display_names = zip(
                    *sorted(zip(images, display_names), key=lambda t: t[1].lower())
                )

        return list(images) if images else [], list(display_names) if display_names else []

    def load_images(self, folder: str, recursive: bool = False) -> None:
        images, display_names = self.collect_images(folder, recursive=recursive)
        self.images = images
        self.display_names = display_names
        self.refresh_list()
        self.update_status()

    def refresh_list(self) -> None:
        self.listbox.delete(0, tk.END)
        if self.batch_mode.get():
            for path in self.batch_folders:
                self.listbox.insert(tk.END, path)
        else:
            for name in self.display_names:
                self.listbox.insert(tk.END, name)
        if not self.batch_mode.get() and self.images:
            self.listbox.selection_set(0)
            self.on_select_image()
        else:
            self.preview_label.configure(text="No image selected", image="")
            self.preview_image = None

    def update_status(self) -> None:
        if self.batch_mode.get():
            if not self.batch_folders:
                self.status_text.set("No batch folders selected.")
                self.create_button.state(["disabled"])
            else:
                self.status_text.set(f"{len(self.batch_folders)} folder(s) ready.")
                self.create_button.state(["!disabled"])
        else:
            if not self.images:
                self.status_text.set("No supported images found.")
                self.create_button.state(["disabled"])
            else:
                self.status_text.set(f"{len(self.images)} image(s) ready.")
                self.create_button.state(["!disabled"])

    def on_select_image(self, event: tk.Event | None = None) -> None:
        if self.batch_mode.get():
            return
        selection = self.listbox.curselection()
        if not selection:
            return
        path = self.images[selection[0]]
        self.update_preview(path)

    def update_preview(self, path: str) -> None:
        try:
            with Image.open(path) as img:
                img_copy = img.copy()
        except Exception:
            self.preview_label.configure(text="Preview unavailable", image="")
            self.preview_image = None
            return

        max_width = 280
        max_height = 360
        img_copy.thumbnail((max_width, max_height))
        self.preview_image = ImageTk.PhotoImage(img_copy)
        self.preview_label.configure(image=self.preview_image, text="")

    def get_layout_fun(self):
        mode = self.page_mode.get()
        if mode == "A4 (no upscale)":
            return img2pdf.get_layout_fun(A4_SIZE_PT, fit=img2pdf.FitMode.shrink)
        if mode == "Original size":
            return img2pdf.get_layout_fun()
        return img2pdf.get_layout_fun(A4_SIZE_PT, fit=img2pdf.FitMode.into)

    def create_pdf(self) -> None:
        output = self.output_path.get().strip()
        if self.use_fixed_output.get() and not self.fixed_output_dir.get().strip():
            messagebox.showwarning("Output Folder", "Set a fixed output folder in Settings.")
            self.open_settings()
            return
        if self.batch_mode.get():
            if not self.batch_folders:
                messagebox.showwarning("No Folders", "No folders selected for batch.")
                return
            self.create_button.state(["disabled"])
            self.progress.stop()
            self.progress.configure(value=0, maximum=len(self.batch_folders))
            self.status_text.set("Generating PDFs...")
            self.progress_text.set("Preparing batch...")
            thread = threading.Thread(target=self._generate_batch_thread, daemon=True)
            thread.start()
            return

        if not self.images:
            messagebox.showwarning("No Images", "No supported images found.")
            return
        if not output:
            self.select_output()
            output = self.output_path.get().strip()
            if not output:
                return

        output = self._ensure_pdf_extension(output)
        self.output_path.set(output)
        self._ensure_output_dir(output)

        self.create_button.state(["disabled"])
        self.progress.stop()
        self.progress.configure(value=0, maximum=len(self.images))
        self.status_text.set("Generating PDF...")
        self.progress_text.set("Preparing...")

        thread = threading.Thread(target=self._generate_pdf_thread, args=(output,), daemon=True)
        thread.start()

    def _generate_pdf_thread(self, output: str) -> None:
        valid_images, warnings = self._validate_images(self.images)
        if not valid_images:
            self.root.after(0, lambda: self._on_generation_failed("No valid images found."))
            return
        if not self._write_pdf(output, valid_images):
            return
        self.root.after(0, lambda: self._on_generation_success(output, warnings))

    def _generate_batch_thread(self) -> None:
        results = []
        total = len(self.batch_folders)
        for index, folder in enumerate(self.batch_folders, start=1):
            self.root.after(
                0,
                lambda i=index, t=total, f=folder: self._update_progress(
                    i, t, f"Processing {i}/{t}: {os.path.basename(f)}"
                ),
            )
            images, _ = self.collect_images(folder, recursive=False)
            if not images:
                results.append((folder, "No supported images found."))
                continue
            valid_images, warnings = self._validate_images(images)
            if not valid_images:
                results.append((folder, "No valid images found."))
                continue

            output = self._output_path_for_input(folder)
            output = self._ensure_pdf_extension(output)
            self._ensure_output_dir(output)
            if not self._write_pdf(output, valid_images):
                results.append((folder, "Failed to write PDF."))
                continue
            if warnings:
                results.append((folder, f"Skipped {len(warnings)} unreadable file(s)."))
            else:
                results.append((folder, "OK"))

        self.root.after(0, lambda: self._on_batch_complete(results))

    def _output_path_for_input(self, input_path: str) -> str:
        base = self._input_base_name(input_path)
        if self.use_fixed_output.get() and self.fixed_output_dir.get().strip():
            output_dir = self.fixed_output_dir.get().strip()
        else:
            output_dir = self._input_output_dir(input_path)
        return os.path.join(output_dir, f"{base}.pdf")

    def _ensure_pdf_extension(self, output: str) -> str:
        return output if output.lower().endswith(".pdf") else output + ".pdf"

    def _ensure_output_dir(self, output: str) -> None:
        try:
            os.makedirs(os.path.dirname(output), exist_ok=True)
        except Exception:
            pass

    def _validate_images(self, images: list) -> tuple[list, list]:
        warnings = []
        valid_images = []
        total = len(images)
        for index, path in enumerate(images, start=1):
            self.root.after(
                0,
                lambda i=index, p=path, t=total: self._update_progress(
                    i, t, f"Checking {i}/{t}: {os.path.basename(p)}"
                ),
            )
            try:
                with Image.open(path) as img:
                    img.verify()
                valid_images.append(path)
            except Exception:
                warnings.append(os.path.basename(path))
        return valid_images, warnings

    def _write_pdf(self, output: str, images: list) -> bool:
        try:
            layout_fun = self.get_layout_fun()
            self.root.after(0, lambda: self._update_progress(len(images), len(images), "Generating PDF..."))
            pdf_bytes = img2pdf.convert(images, layout_fun=layout_fun)
            with open(output, "wb") as f:
                f.write(pdf_bytes)
            return True
        except Exception as exc:
            self.root.after(0, lambda: self._on_generation_failed(str(exc)))
            return False

    def start_update_check(self) -> None:
        thread = threading.Thread(target=self._check_update_thread, daemon=True)
        thread.start()

    def _check_update_thread(self) -> None:
        try:
            latest = fetch_latest_release()
        except Exception:
            return

        if not latest:
            return

        latest_version = latest.get("tag_name", "").lstrip("v")
        if not is_version_newer(latest_version, APP_VERSION):
            return

        self.root.after(0, lambda: self._prompt_update(latest))

    def _prompt_update(self, release_info: dict) -> None:
        if not getattr(sys, "frozen", False):
            messagebox.showinfo(
                "Update Available",
                "A new version is available. Please download the latest release.",
            )
            return

        if messagebox.askyesno(
            "Update Available",
            "A new version is available. Update now?",
        ):
            self.progress.start(10)
            self.status_text.set("Downloading update...")
            thread = threading.Thread(
                target=self._download_update_thread, args=(release_info,), daemon=True
            )
            thread.start()

    def _download_update_thread(self, release_info: dict) -> None:
        try:
            asset = find_asset(release_info, UPDATE_ASSET_NAME)
            if not asset:
                raise RuntimeError("Update asset not found.")
            download_url = asset["browser_download_url"]
            temp_path = download_file(download_url)
            self.root.after(0, lambda: self._apply_update(temp_path))
        except Exception as exc:
            self.root.after(0, lambda: self._on_update_failed(str(exc)))

    def _apply_update(self, temp_path: str) -> None:
        if not getattr(sys, "frozen", False):
            self._on_update_failed("Auto-update is only available in the packaged app.")
            return

        target_exe = sys.executable
        updater_path = os.path.join(tempfile.gettempdir(), "pdfmaker_update.bat")
        pid = os.getpid()

        with open(updater_path, "w", encoding="ascii") as f:
            f.write("@echo off\n")
            f.write("setlocal enabledelayedexpansion\n")
            f.write(f"set TARGET=\"{target_exe}\"\n")
            f.write(f"set INSTALLER=\"{temp_path}\"\n")
            f.write(f"set PID={pid}\n")
            f.write(":waitloop\n")
            f.write("tasklist /FI \"PID eq %PID%\" | find \"%PID%\" >nul\n")
            f.write("if %errorlevel%==0 (\n")
            f.write("  timeout /t 1 /nobreak >nul\n")
            f.write("  goto waitloop\n")
            f.write(")\n")
            f.write("start /wait \"\" %INSTALLER% /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER\n")
            f.write("del /f /q %INSTALLER%\n")
            f.write("start \"\" %TARGET%\n")
            f.write("del /f /q \"%~f0\"\n")

        try:
            subprocess.Popen(
                ["cmd", "/c", updater_path],
                creationflags=0x08000000,
                close_fds=True,
            )
        except Exception:
            pass

        self.root.after(0, self.root.destroy)

    def _on_update_failed(self, message: str) -> None:
        self.progress.stop()
        self.progress_text.set("")
        self.update_status()
        messagebox.showerror("Update Failed", message)

    def _on_generation_failed(self, message: str) -> None:
        self.progress.stop()
        self.progress_text.set("")
        self.update_status()
        messagebox.showerror("Error", f"Failed to create PDF: {message}")

    def _on_generation_success(self, output: str, warnings: list) -> None:
        self.progress.stop()
        self.progress_text.set("")
        self.update_status()

        warning_text = ""
        if warnings:
            preview = warnings[:5]
            extra = len(warnings) - len(preview)
            warning_text = "\n\nSkipped unreadable files:\n" + "\n".join(preview)
            if extra:
                warning_text += f"\n... and {extra} more"

        messagebox.showinfo("Done", f"PDF created: {output}{warning_text}")

    def _on_batch_complete(self, results: list) -> None:
        self.progress.stop()
        self.progress_text.set("")
        self.update_status()

        ok = [r for r in results if r[1] == "OK"]
        errors = [r for r in results if r[1] != "OK"]
        lines = [f"{os.path.basename(path)}: {status}" for path, status in results]
        summary = f"Completed {len(ok)}/{len(results)} folder(s)."
        messagebox.showinfo("Batch Done", summary + "\n\n" + "\n".join(lines))

    def _update_progress(self, value: int, total: int, message: str) -> None:
        self.progress.configure(maximum=max(total, 1))
        self.progress.configure(value=value)
        self.progress_text.set(message)

    def open_settings(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.resizable(False, False)

        frame = ttk.Frame(dialog, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)

        fixed_check = ttk.Checkbutton(
            frame,
            text="Use fixed output folder",
            variable=self.use_fixed_output,
        )
        fixed_check.grid(row=0, column=0, columnspan=3, sticky="w")

        folder_label = ttk.Label(frame, text="Fixed output folder")
        folder_label.grid(row=1, column=0, sticky="w", pady=(8, 4))

        folder_entry = ttk.Entry(frame, textvariable=self.fixed_output_dir)
        folder_entry.grid(row=1, column=1, sticky="ew", pady=(8, 4))

        browse_button = ttk.Button(frame, text="Browse", command=self.select_fixed_output_folder)
        browse_button.grid(row=1, column=2, padx=(8, 0), pady=(8, 4))

        update_button = ttk.Button(frame, text="Check for updates", command=self.check_updates_now)
        update_button.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(10, 0))

        save_button = ttk.Button(frame, text="Save", command=lambda: self.save_settings_and_close(dialog))
        save_button.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(6, 0))

        dialog.transient(self.root)
        dialog.grab_set()

    def select_fixed_output_folder(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.fixed_output_dir.set(path)

    def save_settings_and_close(self, dialog: tk.Toplevel) -> None:
        self.save_settings()
        self.update_output_controls()
        self.apply_output_path()
        dialog.destroy()

    def update_output_controls(self) -> None:
        if self.use_fixed_output.get() or self.batch_mode.get():
            self.output_entry.state(["disabled"])
            self.output_button.state(["disabled"])
        else:
            self.output_entry.state(["!disabled"])
            self.output_button.state(["!disabled"])

    def load_settings(self) -> None:
        path = settings_path()
        if not os.path.exists(path):
            self.use_fixed_output.set(True)
            self.fixed_output_dir.set(default_output_dir())
            return
        try:
            with open(path, "r", encoding="ascii") as f:
                data = json.load(f)
        except Exception:
            return
        self.use_fixed_output.set(bool(data.get("use_fixed_output", True)))
        fixed_dir = str(data.get("fixed_output_dir", "")).strip()
        if not fixed_dir:
            fixed_dir = default_output_dir()
        self.fixed_output_dir.set(fixed_dir)

    def save_settings(self) -> None:
        path = settings_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "use_fixed_output": self.use_fixed_output.get(),
            "fixed_output_dir": self.fixed_output_dir.get(),
        }
        with open(path, "w", encoding="ascii") as f:
            json.dump(data, f)

    def on_close(self) -> None:
        self._clear_temp_dir()
        self.root.destroy()

    def on_mode_change(self) -> None:
        if self.batch_mode.get():
            self.preview_label.configure(text="Batch mode enabled", image="")
            self.preview_image = None
        self.refresh_list()
        self.update_output_controls()
        self.update_status()

    def add_batch_folder(self, path: str | None = None) -> None:
        if path is None:
            path = filedialog.askdirectory()
        if not path:
            return
        if not os.path.isdir(path):
            messagebox.showwarning("Input", "Please select a folder.")
            return
        if path not in self.batch_folders:
            self.batch_folders.append(path)
        self.refresh_list()
        self.update_status()

    def clear_batch_folders(self) -> None:
        self.batch_folders = []
        self.refresh_list()
        self.update_status()

    def move_selected(self, direction: int) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        index = selection[0]
        items = self.batch_folders if self.batch_mode.get() else self.images
        names = None if self.batch_mode.get() else self.display_names
        if not items:
            return
        new_index = index + direction
        if new_index < 0 or new_index >= len(items):
            return
        items[index], items[new_index] = items[new_index], items[index]
        if names is not None:
            names[index], names[new_index] = names[new_index], names[index]
        self.refresh_list()
        self.listbox.selection_set(new_index)
        if not self.batch_mode.get():
            self.on_select_image()

    def check_updates_now(self) -> None:
        self.progress.start(10)
        self.status_text.set("Checking for updates...")
        thread = threading.Thread(target=self._check_update_now_thread, daemon=True)
        thread.start()

    def _check_update_now_thread(self) -> None:
        try:
            latest = fetch_latest_release()
            if not latest:
                self.root.after(0, lambda: self._on_update_check_complete("Update information unavailable."))
                return
            latest_version = latest.get("tag_name", "").lstrip("v")
            if is_version_newer(latest_version, APP_VERSION):
                self.root.after(0, lambda: self._prompt_update(latest))
            else:
                self.root.after(0, lambda: self._on_update_check_complete("No updates available."))
        except Exception as exc:
            self.root.after(0, lambda: self._on_update_check_complete(f"Update check failed: {exc}"))

    def _on_update_check_complete(self, message: str) -> None:
        self.progress.stop()
        self.progress_text.set("")
        self.update_status()
        messagebox.showinfo("Update", message)


def fetch_latest_release() -> dict:
    req = Request(UPDATE_API_URL, headers={"User-Agent": "pdfmaker"})
    with urlopen(req, timeout=6) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def parse_version(value: str) -> tuple:
    parts = []
    for piece in value.split("."):
        try:
            parts.append(int(piece))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def is_version_newer(candidate: str, current: str) -> bool:
    if not candidate:
        return False
    return parse_version(candidate) > parse_version(current)


def find_asset(release_info: dict, name: str) -> dict | None:
    for asset in release_info.get("assets", []):
        if asset.get("name") == name:
            return asset
    return None


def download_file(url: str) -> str:
    req = Request(url, headers={"User-Agent": "pdfmaker"})
    with urlopen(req, timeout=30) as response:
        data = response.read()
    fd, temp_path = tempfile.mkstemp(prefix="pdfmaker_update_", suffix=".exe")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    return temp_path


def settings_path() -> str:
    base = os.getenv("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, "pdfmaker", "settings.json")


def default_output_dir() -> str:
    base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "pdfmaker", "output")


def main() -> None:
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    if TkinterDnD:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
