#!/usr/bin/env python3
"""
Audio Format Converter
Converts audio files from various formats to a specified output format.
Collects all files into a single output folder regardless of input folder structure.
"""

import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading
import traceback


class AudioFormatConverter:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Format Converter")
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        # Variables
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.output_format = tk.StringVar(value=".mp3")
        self.enable_normalization = tk.BooleanVar(value=False)
        self.normalization_level = tk.StringVar(value="-1.0")
        self.recursive = tk.BooleanVar(value=True)
        self.ffmpeg_path = tk.StringVar(value="ffmpeg")

        self.processing = False

        # Supported input formats with checkboxes
        self.format_vars = {
            '.wav': tk.BooleanVar(value=True),
            '.mp3': tk.BooleanVar(value=True),
            '.m4a': tk.BooleanVar(value=True),
            '.flac': tk.BooleanVar(value=True),
            '.ogg': tk.BooleanVar(value=False),
            '.aac': tk.BooleanVar(value=False),
            '.mp4': tk.BooleanVar(value=False),
            '.wma': tk.BooleanVar(value=False),
            '.aiff': tk.BooleanVar(value=False),
        }

        self.setup_ui()

    def setup_ui(self):
        # Configure main window for grid
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Create main scrollable frame
        main_canvas = tk.Canvas(self.root, highlightthickness=0)
        main_canvas.grid(row=0, column=0, sticky="nsew")

        v_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky="ns")

        main_canvas.configure(yscrollcommand=v_scrollbar.set)

        # Create inner frame
        inner_frame = ttk.Frame(main_canvas)
        canvas_window = main_canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        # Configure canvas scrolling
        def configure_scroll_region(event):
            main_canvas.configure(scrollregion=main_canvas.bbox("all"))

        def configure_canvas_width(event):
            main_canvas.itemconfig(canvas_window, width=event.width)

        inner_frame.bind("<Configure>", configure_scroll_region)
        main_canvas.bind("<Configure>", configure_canvas_width)

        # Mouse wheel binding
        def on_mouse_wheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        main_canvas.bind("<MouseWheel>", on_mouse_wheel)

        # Content frame with padding
        content = ttk.Frame(inner_frame, padding="15")
        content.grid(row=0, column=0, sticky="nsew")

        row = 0

        # Input folder selection
        ttk.Label(content, text="Input Folder:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        row += 1

        input_frame = ttk.Frame(content)
        input_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Entry(input_frame, textvariable=self.input_folder, width=70).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(input_frame, text="Browse...", command=self.browse_input).pack(
            side=tk.LEFT, padx=(5, 0))
        row += 1

        # Output folder selection
        ttk.Label(content, text="Output Folder:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        row += 1

        output_frame = ttk.Frame(content)
        output_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))

        ttk.Entry(output_frame, textvariable=self.output_folder, width=70).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Browse...", command=self.browse_output).pack(
            side=tk.LEFT, padx=(5, 0))
        row += 1

        # Input file types selection
        input_types_frame = ttk.LabelFrame(content, text="Input File Types to Process", padding="10")
        input_types_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1

        ttk.Label(input_types_frame, text="Select which formats to convert:",
                 font=('Arial', 9)).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        # Create checkboxes in a grid layout
        checkbox_row = 1
        checkbox_col = 0
        for fmt, var in self.format_vars.items():
            ttk.Checkbutton(input_types_frame, text=fmt, variable=var).grid(
                row=checkbox_row, column=checkbox_col, sticky=tk.W, padx=(0, 15), pady=2)
            checkbox_col += 1
            if checkbox_col > 2:  # 3 columns
                checkbox_col = 0
                checkbox_row += 1

        # Select/Deselect all buttons
        button_row = checkbox_row + 1
        button_frame = ttk.Frame(input_types_frame)
        button_frame.grid(row=button_row, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        ttk.Button(button_frame, text="Select All", command=self.select_all_formats).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Deselect All", command=self.deselect_all_formats).pack(side=tk.LEFT)

        # Output format selection
        format_frame = ttk.LabelFrame(content, text="Output Format", padding="10")
        format_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        row += 1

        ttk.Label(format_frame, text="Convert to:").grid(row=0, column=0, sticky=tk.W)
        output_formats = [".mp3", ".wav"]
        output_combo = ttk.Combobox(format_frame, textvariable=self.output_format,
                                    values=output_formats, width=15, state='readonly')
        output_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        ttk.Label(format_frame, text="(MP3: 320kbps, WAV: 24-bit)",
                 font=('Arial', 8, 'italic')).grid(row=1, column=0, columnspan=2,
                                                   sticky=tk.W, pady=(5, 0))

        # Normalization settings
        norm_frame = ttk.LabelFrame(content, text="Normalization (Optional)", padding="10")
        norm_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        row += 1

        ttk.Checkbutton(norm_frame, text="Enable Normalization",
                       variable=self.enable_normalization).grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))

        ttk.Label(norm_frame, text="Target Peak Level (dB):").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(norm_frame, textvariable=self.normalization_level, width=15).grid(
            row=1, column=1, sticky=tk.W, padx=(10, 0))
        ttk.Label(norm_frame, text="(e.g., -1.0 for near-maximum)",
                 font=('Arial', 8, 'italic')).grid(
            row=1, column=2, sticky=tk.W, padx=(5, 0))

        # Additional options
        options_frame = ttk.LabelFrame(content, text="Additional Options", padding="10")
        options_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        row += 1

        ttk.Checkbutton(options_frame, text="Process subfolders recursively",
                       variable=self.recursive).grid(row=0, column=0, sticky=tk.W)

        ttk.Label(options_frame, text="FFmpeg Path:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(options_frame, textvariable=self.ffmpeg_path, width=50).grid(
            row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        ttk.Label(options_frame, text="(Leave as 'ffmpeg' if it's in your PATH)",
                 font=('Arial', 8, 'italic')).grid(row=3, column=0, sticky=tk.W, pady=(2, 0))

        # Info label
        info_label = ttk.Label(content,
            text="Note: All converted files will be placed directly in the output folder,\n"
                 "regardless of their original folder structure.",
            font=('Arial', 9, 'italic'), foreground='blue')
        info_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1

        # Progress section
        ttk.Label(content, text="Progress:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, sticky=tk.W, pady=(0, 5))
        row += 1

        # Progress text with its own scrollbar
        progress_container = ttk.Frame(content)
        progress_container.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        row += 1

        progress_scroll = ttk.Scrollbar(progress_container)
        progress_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.progress_text = tk.Text(progress_container, height=8, width=85,
                                     yscrollcommand=progress_scroll.set,
                                     state='disabled', wrap=tk.WORD)
        self.progress_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        progress_scroll.config(command=self.progress_text.yview)

        # Process button
        self.process_button = ttk.Button(content, text="Convert Files",
                                        command=self.start_processing)
        self.process_button.grid(row=row, column=0, columnspan=2, pady=(0, 10))

    def browse_input(self):
        folder = filedialog.askdirectory(title="Select Input Folder")
        if folder:
            self.input_folder.set(folder)

    def browse_output(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder.set(folder)

    def log(self, message):
        self.progress_text.config(state='normal')
        self.progress_text.insert(tk.END, message + "\n")
        self.progress_text.see(tk.END)
        self.progress_text.config(state='disabled')
        self.root.update_idletasks()

    def clear_log(self):
        self.progress_text.config(state='normal')
        self.progress_text.delete(1.0, tk.END)
        self.progress_text.config(state='disabled')

    def select_all_formats(self):
        """Select all input format checkboxes."""
        for var in self.format_vars.values():
            var.set(True)

    def deselect_all_formats(self):
        """Deselect all input format checkboxes."""
        for var in self.format_vars.values():
            var.set(False)

    def get_selected_formats(self):
        """Get list of selected input formats."""
        return [fmt for fmt, var in self.format_vars.items() if var.get()]

    def get_output_codec(self, output_ext: str) -> list:
        """Get the appropriate ffmpeg codec settings for the output format."""
        if output_ext == '.mp3':
            return ['-acodec', 'libmp3lame', '-b:a', '320k']
        elif output_ext == '.wav':
            return ['-acodec', 'pcm_s24le']  # 24-bit PCM
        else:
            return ['-acodec', 'libmp3lame', '-b:a', '320k']  # Default to MP3

    def convert_file(self, file_path: Path, output_dir: Path, output_ext: str):
        """Convert a single audio file."""
        try:
            self.log(f"\nConverting: {file_path.name}")

            # Create output path (all files go directly into output folder)
            output_path = output_dir / f"{file_path.stem}{output_ext}"

            # Handle duplicate filenames by adding a number
            counter = 1
            original_output_path = output_path
            while output_path.exists():
                output_path = output_dir / f"{file_path.stem}_{counter}{output_ext}"
                counter += 1

            if counter > 1:
                self.log(f"  File exists, saving as: {output_path.name}")

            # Build ffmpeg command
            ffmpeg = self.ffmpeg_path.get()
            codec_settings = self.get_output_codec(output_ext)

            # Build filter chain
            filters = []

            # Add normalization if enabled
            if self.enable_normalization.get():
                try:
                    target_db = float(self.normalization_level.get())
                    filters.append(f"loudnorm=I=-16:TP={target_db}:LRA=11")
                    self.log(f"  Normalizing to {target_db} dB")
                except ValueError:
                    self.log(f"  Warning: Invalid normalization level, skipping normalization")

            # Construct command
            cmd = [
                ffmpeg, '-i', str(file_path)
            ]

            # Add filters if any
            if filters:
                cmd.extend(['-af', ','.join(filters)])

            # Add codec settings
            cmd.extend(codec_settings)

            # Add output file with overwrite flag
            cmd.extend(['-y', str(output_path)])

            # Run ffmpeg
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

            if result.returncode == 0:
                self.log(f"  ✓ Saved to: {output_path.name}")
            else:
                self.log(f"  ✗ FFmpeg error:")
                # Show last few lines of error
                error_lines = result.stdout.split('\n')[-10:]
                for line in error_lines:
                    if line.strip():
                        self.log(f"    {line}")

        except Exception as e:
            self.log(f"  ✗ Error converting file: {str(e)}")
            self.log(f"  {traceback.format_exc()}")

    def process_files(self):
        """Main processing function."""
        try:
            input_dir = Path(self.input_folder.get())
            if not input_dir.exists():
                messagebox.showerror("Error", "Input folder does not exist!")
                return

            output_folder_str = self.output_folder.get().strip()
            if not output_folder_str:
                messagebox.showerror("Error", "Output folder path is empty!")
                return

            output_dir = Path(output_folder_str)
            try:
                if not output_dir.exists():
                    output_dir.mkdir(parents=True, exist_ok=True)
                    self.log(f"Created output directory: {output_dir}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output directory: {str(e)}")
                return

            # Check ffmpeg
            try:
                subprocess.run([self.ffmpeg_path.get(), '-version'],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except Exception:
                messagebox.showerror("Error",
                    "FFmpeg not found! Please install FFmpeg or specify the correct path.")
                return

            # Get selected input formats
            selected_formats = self.get_selected_formats()
            if not selected_formats:
                messagebox.showwarning("Warning", "Please select at least one input file type to process.")
                return

            # Find all audio files
            output_ext = self.output_format.get()
            files = []

            if self.recursive.get():
                for ext in selected_formats:
                    files.extend(list(input_dir.rglob(f"*{ext}")))
            else:
                for ext in selected_formats:
                    files.extend(list(input_dir.glob(f"*{ext}")))

            if not files:
                messagebox.showinfo("Info", f"No audio files found in the input folder matching selected formats.")
                return

            self.log(f"Found {len(files)} audio file(s) to convert.")
            self.log(f"Output format: {output_ext}")
            self.log("=" * 70)

            # Process each file
            for i, file_path in enumerate(files, 1):
                self.log(f"\n[{i}/{len(files)}]")
                self.convert_file(file_path, output_dir, output_ext)

            self.log("\n" + "=" * 70)
            self.log(f"\n✓ Conversion complete! Converted {len(files)} file(s).")
            messagebox.showinfo("Success", f"Conversion complete!\nConverted {len(files)} file(s).")

        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            self.log(f"\n✗ {error_msg}")
            messagebox.showerror("Error", error_msg)
        finally:
            self.processing = False
            self.process_button.config(state='normal', text="Convert Files")

    def start_processing(self):
        """Start processing in a separate thread."""
        if self.processing:
            return

        # Validate inputs
        if not self.input_folder.get():
            messagebox.showwarning("Warning", "Please select an input folder.")
            return

        if not self.output_folder.get():
            messagebox.showwarning("Warning", "Please select an output folder.")
            return

        try:
            if self.enable_normalization.get():
                float(self.normalization_level.get())
        except ValueError:
            messagebox.showerror("Error", "Normalization level must be a valid number.")
            return

        self.processing = True
        self.process_button.config(state='disabled', text="Converting...")
        self.clear_log()

        # Run in separate thread to keep GUI responsive
        thread = threading.Thread(target=self.process_files, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    app = AudioFormatConverter(root)
    root.mainloop()


if __name__ == "__main__":
    main()