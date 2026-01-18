#!/usr/bin/env python3
"""
Audio Click and Pop Remover
Removes clicks and pops from vinyl recordings using median filter detection
and cubic interpolation. Preserves music quality while removing transient artifacts.
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import List
import threading
import uuid
import traceback
import numpy as np
import soundfile as sf
from scipy import signal
from scipy.interpolate import interp1d


class AudioClickPopRemover:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Click & Pop Remover")
        self.root.geometry("800x700")
        self.root.resizable(True, True)

        # Variables
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.input_format = tk.StringVar(value=".wav")
        self.output_format = tk.StringVar(value="original")
        self.overwrite_originals = tk.BooleanVar(value=False)
        self.recursive = tk.BooleanVar(value=True)

        # Detection parameters
        self.window_size = tk.StringVar(value="9")
        self.threshold_multiplier = tk.StringVar(value="4.0")
        self.max_click_length = tk.StringVar(value="8")

        self.processing = False

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
        output_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Entry(output_frame, textvariable=self.output_folder, width=70).pack(
            side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(output_frame, text="Browse...", command=self.browse_output).pack(
            side=tk.LEFT, padx=(5, 0))
        row += 1

        ttk.Checkbutton(content, text="Overwrite original files (ignore output folder)",
                       variable=self.overwrite_originals).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        row += 1

        # File format selection
        format_frame = ttk.LabelFrame(content, text="File Formats", padding="10")
        format_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        row += 1

        ttk.Label(format_frame, text="Input Format:").grid(row=0, column=0, sticky=tk.W)
        input_formats = [".wav", ".flac", ".aiff", ".m4a"]
        input_combo = ttk.Combobox(format_frame, textvariable=self.input_format,
                                   values=input_formats, width=15, state='readonly')
        input_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        ttk.Label(format_frame, text="Output Format:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        output_formats = ["original", ".wav", ".flac"]
        output_combo = ttk.Combobox(format_frame, textvariable=self.output_format,
                                    values=output_formats, width=15, state='readonly')
        output_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))

        ttk.Label(format_frame, text="(WAV: 24-bit, FLAC: lossless)",
                 font=('Arial', 8, 'italic')).grid(row=2, column=0, columnspan=2,
                                                   sticky=tk.W, pady=(5, 0))

        # Detection settings
        detect_frame = ttk.LabelFrame(content, text="Click/Pop Detection Settings", padding="10")
        detect_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1

        # Window size
        ttk.Label(detect_frame, text="Window Size (samples):").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(detect_frame, textvariable=self.window_size, width=10).grid(
            row=0, column=1, sticky=tk.W, padx=(10, 0))
        ttk.Label(detect_frame, text="(5-15, default: 9)",
                 font=('Arial', 8, 'italic')).grid(row=0, column=2, sticky=tk.W, padx=(5, 0))

        # Threshold
        ttk.Label(detect_frame, text="Sensitivity Threshold:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(detect_frame, textvariable=self.threshold_multiplier, width=10).grid(
            row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        ttk.Label(detect_frame, text="(3.0-6.0, default: 4.0, lower = more sensitive)",
                 font=('Arial', 8, 'italic')).grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=(10, 0))

        # Max click length
        ttk.Label(detect_frame, text="Max Click Length (samples):").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Entry(detect_frame, textvariable=self.max_click_length, width=10).grid(
            row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        ttk.Label(detect_frame, text="(3-15, default: 8)",
                 font=('Arial', 8, 'italic')).grid(row=2, column=2, sticky=tk.W, padx=(5, 0), pady=(10, 0))

        # Info text
        info_text = ("Median filter detects sudden amplitude spikes. Lower threshold = more aggressive.\n"
                    "Test on a small section first to find optimal settings for your vinyl!")
        ttk.Label(detect_frame, text=info_text, font=('Arial', 9), justify=tk.LEFT,
                 foreground='blue').grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))

        # Preset buttons
        preset_frame = ttk.LabelFrame(content, text="Quick Presets", padding="10")
        preset_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1

        ttk.Button(preset_frame, text="Light (Less Aggressive)",
                  command=self.preset_light).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(preset_frame, text="Medium (Recommended)",
                  command=self.preset_medium).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(preset_frame, text="Heavy (Very Damaged)",
                  command=self.preset_heavy).grid(row=0, column=2, padx=5, pady=5)

        # Additional options
        options_frame = ttk.LabelFrame(content, text="Additional Options", padding="10")
        options_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        row += 1

        ttk.Checkbutton(options_frame, text="Process subfolders recursively",
                       variable=self.recursive).grid(row=0, column=0, sticky=tk.W)

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

        self.progress_text = tk.Text(progress_container, height=10, width=85,
                                     yscrollcommand=progress_scroll.set,
                                     state='disabled', wrap=tk.WORD)
        self.progress_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        progress_scroll.config(command=self.progress_text.yview)

        # Process button
        self.process_button = ttk.Button(content, text="Process Files",
                                        command=self.start_processing)
        self.process_button.grid(row=row, column=0, columnspan=2, pady=(0, 10))

    def preset_light(self):
        """Light processing for lightly damaged vinyl."""
        self.window_size.set("7")
        self.threshold_multiplier.set("5.0")
        self.max_click_length.set("5")
        self.log("Preset applied: Light (Less Aggressive)")

    def preset_medium(self):
        """Medium processing - recommended default."""
        self.window_size.set("9")
        self.threshold_multiplier.set("4.0")
        self.max_click_length.set("8")
        self.log("Preset applied: Medium (Recommended)")

    def preset_heavy(self):
        """Heavy processing for badly damaged vinyl."""
        self.window_size.set("11")
        self.threshold_multiplier.set("3.0")
        self.max_click_length.set("12")
        self.log("Preset applied: Heavy (Very Damaged)")

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

    def detect_clicks(self, audio: np.ndarray, sample_rate: int,
                     window_size: int, threshold: float, max_length: int) -> List[tuple]:
        """
        Detect clicks and pops using median filter approach.

        Args:
            audio: Audio signal array
            sample_rate: Sample rate in Hz
            window_size: Window size for median filter (samples)
            threshold: Number of standard deviations for detection
            max_length: Maximum length of a click (samples)

        Returns:
            List of tuples (start_idx, end_idx) marking detected clicks
        """
        # Apply median filter to get smoothed signal
        filtered = signal.medfilt(audio, kernel_size=window_size)

        # Calculate difference between original and filtered
        difference = np.abs(audio - filtered)

        # Calculate threshold using median absolute deviation (more robust than std)
        median_diff = np.median(difference)
        mad = np.median(np.abs(difference - median_diff))
        threshold_value = median_diff + threshold * mad * 1.4826  # 1.4826 makes MAD equal to std for normal dist

        # Find samples exceeding threshold
        outliers = difference > threshold_value

        # Group consecutive outliers into clicks
        clicks = []
        in_click = False
        click_start = 0

        for i in range(len(outliers)):
            if outliers[i] and not in_click:
                # Start of a new click
                in_click = True
                click_start = i
            elif not outliers[i] and in_click:
                # End of click
                click_length = i - click_start
                if click_length <= max_length:
                    clicks.append((click_start, i))
                in_click = False
            elif in_click and (i - click_start) > max_length:
                # Click too long, probably not a click
                in_click = False

        # Handle click extending to end of file
        if in_click:
            click_length = len(outliers) - click_start
            if click_length <= max_length:
                clicks.append((click_start, len(outliers)))

        return clicks

    def interpolate_clicks(self, audio: np.ndarray, clicks: List[tuple]) -> np.ndarray:
        """
        Replace detected clicks with interpolated values.

        Args:
            audio: Audio signal array
            clicks: List of (start_idx, end_idx) tuples

        Returns:
            Corrected audio signal
        """
        corrected = audio.copy()

        for start, end in clicks:
            # Get surrounding context (5 samples on each side)
            context = 5
            pre_start = max(0, start - context)
            post_end = min(len(audio), end + context)

            # Create interpolation points
            # Use points before and after the click
            x_points = list(range(pre_start, start)) + list(range(end, post_end))
            y_points = list(audio[pre_start:start]) + list(audio[end:post_end])

            if len(x_points) < 2:
                # Not enough points for interpolation, skip
                continue

            # Create cubic interpolator
            try:
                interpolator = interp1d(x_points, y_points, kind='cubic',
                                       fill_value='extrapolate')
                # Interpolate the click region
                x_interp = range(start, end)
                corrected[start:end] = interpolator(x_interp)
            except Exception:
                # If cubic fails, fall back to linear
                try:
                    interpolator = interp1d(x_points, y_points, kind='linear',
                                           fill_value='extrapolate')
                    x_interp = range(start, end)
                    corrected[start:end] = interpolator(x_interp)
                except Exception:
                    # If all else fails, skip this click
                    continue

        return corrected

    def process_file(self, file_path: Path, output_dir: Path, output_ext: str):
        """Process a single audio file."""
        try:
            self.log(f"\nProcessing: {file_path.name}")

            # Get parameters
            try:
                window_size = int(self.window_size.get())
                threshold = float(self.threshold_multiplier.get())
                max_length = int(self.max_click_length.get())
            except ValueError:
                self.log(f"  Error: Invalid parameter values")
                return

            # Validate parameters
            if window_size < 3 or window_size > 25:
                self.log(f"  Error: Window size must be between 3 and 25")
                return
            if window_size % 2 == 0:
                window_size += 1  # Must be odd for median filter
                self.log(f"  Adjusted window size to {window_size} (must be odd)")

            # Load audio (use float32 to save memory)
            self.log(f"  Loading audio file...")
            try:
                audio, sample_rate = sf.read(file_path, dtype='float32')
            except (MemoryError, np._core._exceptions._ArrayMemoryError):
                # File too large, try with memory mapping
                self.log(f"  File is large, using memory-efficient processing...")
                try:
                    with sf.SoundFile(file_path) as f:
                        sample_rate = f.samplerate
                        # Read in chunks to avoid memory issues
                        chunk_size = 10 * sample_rate  # 10 seconds at a time
                        audio_chunks = []
                        while True:
                            chunk = f.read(chunk_size, dtype='float32')
                            if len(chunk) == 0:
                                break
                            audio_chunks.append(chunk)
                        audio = np.concatenate(audio_chunks, axis=0)
                except Exception as e:
                    self.log(f"  Error: Unable to load file even with chunked reading: {str(e)}")
                    return

            # Get original shape
            original_shape = audio.shape
            is_stereo = len(original_shape) > 1 and original_shape[1] > 1

            self.log(f"  Sample rate: {sample_rate} Hz")
            self.log(f"  Channels: {'Stereo' if is_stereo else 'Mono'}")
            self.log(f"  Duration: {len(audio) / sample_rate:.2f}s")

            # Process each channel separately
            if is_stereo:
                self.log(f"  Processing left channel...")
                clicks_left = self.detect_clicks(audio[:, 0], sample_rate,
                                                window_size, threshold, max_length)
                self.log(f"    Detected {len(clicks_left)} clicks")
                audio[:, 0] = self.interpolate_clicks(audio[:, 0], clicks_left)

                self.log(f"  Processing right channel...")
                clicks_right = self.detect_clicks(audio[:, 1], sample_rate,
                                                 window_size, threshold, max_length)
                self.log(f"    Detected {len(clicks_right)} clicks")
                audio[:, 1] = self.interpolate_clicks(audio[:, 1], clicks_right)

                total_clicks = len(clicks_left) + len(clicks_right)
            else:
                self.log(f"  Detecting clicks...")
                clicks = self.detect_clicks(audio, sample_rate,
                                          window_size, threshold, max_length)
                self.log(f"    Detected {len(clicks)} clicks")
                audio = self.interpolate_clicks(audio, clicks)
                total_clicks = len(clicks)

            # Determine output file
            if output_ext == "original":
                output_ext = file_path.suffix

            if self.overwrite_originals.get():
                # Create temporary file
                temp_name = f"{file_path.stem}_{uuid.uuid4().hex[:8]}_temp{output_ext}"
                output_path = file_path.parent / temp_name
            else:
                # Preserve directory structure in output folder
                try:
                    rel_path = file_path.parent.relative_to(Path(self.input_folder.get()))
                except ValueError:
                    rel_path = Path(".")
                output_subdir = output_dir / rel_path
                output_subdir.mkdir(parents=True, exist_ok=True)
                output_path = output_subdir / f"{file_path.stem}_declick{output_ext}"

            # Save processed audio
            self.log(f"  Saving cleaned audio...")
            # Use appropriate subtype based on output format
            if output_ext.lower() == '.flac':
                sf.write(output_path, audio, sample_rate, subtype='PCM_24')
            elif output_ext.lower() == '.wav':
                sf.write(output_path, audio, sample_rate, subtype='PCM_24')
            else:
                # Let soundfile choose default subtype for other formats
                sf.write(output_path, audio, sample_rate)

            self.log(f"  Saved to: {output_path}")

            # If overwriting, replace original file
            if self.overwrite_originals.get():
                try:
                    file_path.unlink()
                    output_path.rename(file_path)
                    self.log(f"  Replaced original file")
                except Exception as e:
                    self.log(f"  Error replacing original: {str(e)}")
                    if output_path.exists():
                        output_path.unlink()

            if total_clicks == 0:
                self.log(f"  Completed! No clicks detected - file was clean.")
            else:
                self.log(f"  Completed! Removed {total_clicks} clicks/pops")

        except Exception as e:
            self.log(f"  Error processing file: {str(e)}")
            self.log(f"  {traceback.format_exc()}")

    def process_files(self):
        """Main processing function."""
        try:
            input_dir = Path(self.input_folder.get())
            if not input_dir.exists():
                messagebox.showerror("Error", "Input folder does not exist!")
                return

            if not self.overwrite_originals.get():
                output_folder_str = self.output_folder.get().strip()
                if not output_folder_str:
                    messagebox.showerror("Error", "Output folder path is empty!")
                    return
                output_dir = Path(output_folder_str)
                if not output_dir.exists():
                    output_dir.mkdir(parents=True, exist_ok=True)
            else:
                output_dir = input_dir

            # Find files
            input_ext = self.input_format.get()
            output_ext = self.output_format.get()

            if self.recursive.get():
                files = list(input_dir.rglob(f"*{input_ext}"))
            else:
                files = list(input_dir.glob(f"*{input_ext}"))

            # Filter out already processed files
            files = [f for f in files if not f.stem.endswith("_declick")]

            if not files:
                messagebox.showinfo("Info", f"No {input_ext} files found in the input folder.")
                return

            self.log(f"Found {len(files)} file(s) to process.\n")
            self.log("=" * 70)

            # Process each file
            for i, file_path in enumerate(files, 1):
                self.log(f"\n[{i}/{len(files)}]")
                self.process_file(file_path, output_dir, output_ext)

            self.log("\n" + "=" * 70)
            self.log(f"\nProcessing complete! Processed {len(files)} file(s).")
            messagebox.showinfo("Success", f"Processing complete!\nProcessed {len(files)} file(s).")

        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            self.log(f"\n{error_msg}")
            messagebox.showerror("Error", error_msg)
        finally:
            self.processing = False
            self.process_button.config(state='normal', text="Process Files")

    def start_processing(self):
        """Start processing in a separate thread."""
        if self.processing:
            return

        # Validate inputs
        if not self.input_folder.get():
            messagebox.showwarning("Warning", "Please select an input folder.")
            return

        if not self.overwrite_originals.get() and not self.output_folder.get():
            messagebox.showwarning("Warning",
                "Please select an output folder or enable 'Overwrite original files'.")
            return

        # Validate parameters
        try:
            window_size = int(self.window_size.get())
            threshold = float(self.threshold_multiplier.get())
            max_length = int(self.max_click_length.get())
        except ValueError:
            messagebox.showerror("Error", "All detection parameters must be valid numbers.")
            return

        self.processing = True
        self.process_button.config(state='disabled', text="Processing...")
        self.clear_log()

        # Run in separate thread to keep GUI responsive
        thread = threading.Thread(target=self.process_files, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    app = AudioClickPopRemover(root)
    root.mainloop()


if __name__ == "__main__":
    main()
