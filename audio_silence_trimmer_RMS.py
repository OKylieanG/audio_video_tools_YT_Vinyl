#!/usr/bin/env python3
"""
Audio Silence Trimmer
Automatically detects and removes silence from the beginning and end of audio files.
Uses RMS loudness analysis to find when actual music starts.
"""

import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import Optional, Tuple
import threading
import uuid
import traceback
import numpy as np
import soundfile as sf


class AudioSilenceTrimmer:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Silence Trimmer")
        self.root.geometry("750x600")
        self.root.resizable(True, True)
        
        # Variables
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.input_format = tk.StringVar(value=".m4a")
        self.output_format = tk.StringVar(value="original")
        self.enable_normalization = tk.BooleanVar(value=False)
        self.normalization_level = tk.StringVar(value="-1.0")
        self.overwrite_originals = tk.BooleanVar(value=False)
        self.recursive = tk.BooleanVar(value=True)
        self.ffmpeg_path = tk.StringVar(value="ffmpeg")
        
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
        input_formats = [".wav", ".mp3", ".ogg", ".flac", ".m4a", ".mp4"]
        input_combo = ttk.Combobox(format_frame, textvariable=self.input_format, 
                                   values=input_formats, width=15, state='readonly')
        input_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(format_frame, text="Output Format:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        output_formats = ["original", ".mp3", ".wav"]
        output_combo = ttk.Combobox(format_frame, textvariable=self.output_format, 
                                    values=output_formats, width=15, state='readonly')
        output_combo.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        
        ttk.Label(format_frame, text="(MP3: 320kbps, WAV: 24-bit)", 
                 font=('Arial', 8, 'italic')).grid(row=2, column=0, columnspan=2, 
                                                   sticky=tk.W, pady=(5, 0))
        
        # Detection settings info
        info_frame = ttk.LabelFrame(content, text="Detection Method", padding="10")
        info_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 15))
        row += 1

        info_text = ("Uses RMS loudness analysis to detect when actual music starts.\n"
                    "Analyzes audio in frames and compares to overall track loudness.\n"
                    "No manual settings needed - fully automatic!")
        ttk.Label(info_frame, text=info_text, font=('Arial', 9), justify=tk.LEFT).grid(
            row=0, column=0, sticky=tk.W)
        
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
        self.process_button = ttk.Button(content, text="Process Files", 
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
    
    def detect_silence(self, file_path: str) -> Tuple[Optional[float], Optional[float], float]:
        """
        Detect when actual music starts and ends in an audio file using RMS loudness analysis.
        For vinyl rips, analyzes RMS loudness to find when sustained loud audio begins/ends.
        Returns: (start_time, end_time, total_duration)
        """
        try:
            self.log(f"  Loading audio file...")

            # Load the audio file
            try:
                audio, sample_rate = sf.read(file_path, dtype='float32')
            except (MemoryError, Exception) as mem_err:
                if 'allocate' not in str(mem_err).lower():
                    raise  # Re-raise if not a memory error
                # File too large, try chunked reading
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
                    return None, None, 0

            # Convert to mono if stereo
            if len(audio.shape) > 1:
                audio = np.mean(audio, axis=1)

            total_length = len(audio) / sample_rate
            self.log(f"  Duration: {total_length:.2f}s, Sample rate: {sample_rate}Hz")

            # Calculate overall RMS loudness of the entire track
            overall_rms = np.sqrt(np.mean(audio ** 2))
            overall_db = 20 * np.log10(overall_rms + 1e-10)  # Add small value to avoid log(0)
            self.log(f"  Overall track RMS: {overall_db:.2f} dB")

            # Phase 1: Analyze in 0.5 second frames from the beginning
            coarse_frame_size = 0.5  # seconds
            coarse_samples = int(coarse_frame_size * sample_rate)

            self.log(f"  Phase 1: Analyzing in {coarse_frame_size}s frames...")

            # Threshold: consider a frame "close enough" to track RMS if within 50% of overall RMS
            threshold_multiplier = 0.5
            track_start_coarse = 0

            for i in range(0, len(audio), coarse_samples):
                frame = audio[i:i + coarse_samples]
                if len(frame) < coarse_samples * 0.5:  # Skip if frame is too small
                    break

                frame_rms = np.sqrt(np.mean(frame ** 2))
                frame_db = 20 * np.log10(frame_rms + 1e-10)

                # Calculate how close this frame is to the overall track RMS
                distance_to_track = abs(frame_rms - overall_rms)
                distance_ratio = distance_to_track / overall_rms

                time_pos = i / sample_rate
                self.log(f"    Frame at {time_pos:.2f}s: {frame_db:.2f} dB (distance ratio: {distance_ratio:.3f})")

                # If this frame is within threshold of the track RMS, we found the start
                if distance_ratio <= threshold_multiplier:
                    track_start_coarse = i / sample_rate
                    self.log(f"  → Coarse start found at {track_start_coarse:.2f}s")
                    break

            # Phase 2: Fine-tune by analyzing in 0.1 second frames starting from coarse position
            fine_frame_size = 0.1  # seconds
            fine_samples = int(fine_frame_size * sample_rate)

            self.log(f"  Phase 2: Fine-tuning in {fine_frame_size}s frames...")

            # Start from a bit before the coarse position to catch the exact start
            start_sample = max(0, int(track_start_coarse * sample_rate) - coarse_samples)
            track_start_fine = track_start_coarse

            for i in range(start_sample, min(start_sample + coarse_samples * 2, len(audio)), fine_samples):
                frame = audio[i:i + fine_samples]
                if len(frame) < fine_samples * 0.5:  # Skip if frame is too small
                    break

                frame_rms = np.sqrt(np.mean(frame ** 2))
                frame_db = 20 * np.log10(frame_rms + 1e-10)

                # Calculate how close this frame is to the overall track RMS
                distance_to_track = abs(frame_rms - overall_rms)
                distance_ratio = distance_to_track / overall_rms

                time_pos = i / sample_rate
                self.log(f"    Frame at {time_pos:.2f}s: {frame_db:.2f} dB (distance ratio: {distance_ratio:.3f})")

                # If this frame is within threshold of the track RMS, we found the start
                if distance_ratio <= threshold_multiplier:
                    track_start_fine = i / sample_rate
                    self.log(f"  → Fine start found at {track_start_fine:.2f}s")
                    break

            track_start = track_start_fine

            # For the end, do the same thing but working backwards
            self.log(f"  Phase 3: Finding track end (analyzing from end)...")

            # Coarse pass from the end
            track_end_coarse = total_length

            for i in range(len(audio) - coarse_samples, 0, -coarse_samples):
                frame = audio[i:i + coarse_samples]
                if len(frame) < coarse_samples * 0.5:
                    break

                frame_rms = np.sqrt(np.mean(frame ** 2))
                frame_db = 20 * np.log10(frame_rms + 1e-10)

                distance_to_track = abs(frame_rms - overall_rms)
                distance_ratio = distance_to_track / overall_rms

                time_pos = i / sample_rate
                self.log(f"    Frame at {time_pos:.2f}s: {frame_db:.2f} dB (distance ratio: {distance_ratio:.3f})")

                # If this frame is within threshold of the track RMS, we found the end
                if distance_ratio <= threshold_multiplier:
                    track_end_coarse = (i + coarse_samples) / sample_rate
                    self.log(f"  → Coarse end found at {track_end_coarse:.2f}s")
                    break

            # Fine-tune the end
            self.log(f"  Phase 4: Fine-tuning track end...")

            end_sample = min(len(audio), int(track_end_coarse * sample_rate) + coarse_samples)
            track_end_fine = track_end_coarse

            for i in range(end_sample - fine_samples, max(end_sample - coarse_samples * 2, 0), -fine_samples):
                frame = audio[i:i + fine_samples]
                if len(frame) < fine_samples * 0.5:
                    break

                frame_rms = np.sqrt(np.mean(frame ** 2))
                frame_db = 20 * np.log10(frame_rms + 1e-10)

                distance_to_track = abs(frame_rms - overall_rms)
                distance_ratio = distance_to_track / overall_rms

                time_pos = i / sample_rate
                self.log(f"    Frame at {time_pos:.2f}s: {frame_db:.2f} dB (distance ratio: {distance_ratio:.3f})")

                # If this frame is within threshold of the track RMS, we found the end
                if distance_ratio <= threshold_multiplier:
                    track_end_fine = (i + fine_samples) / sample_rate
                    self.log(f"  → Fine end found at {track_end_fine:.2f}s")
                    break

            track_end = track_end_fine

            self.log(f"  ✓ Final result: Start={track_start:.2f}s, End={track_end:.2f}s")

            return track_start, track_end, total_length

        except Exception as e:
            self.log(f"Error detecting silence in {file_path}: {str(e)}")
            self.log(traceback.format_exc())
            return None, None, 0
    
    def get_output_codec(self, output_ext: str) -> list:
        """Get the appropriate ffmpeg codec settings for the output format."""
        # If normalizing, we can't use codec copy - must re-encode
        if self.enable_normalization.get():
            if output_ext == '.mp3':
                return ['-acodec', 'libmp3lame', '-b:a', '320k']
            elif output_ext == '.wav':
                return ['-acodec', 'pcm_s24le']  # 24-bit PCM
            elif output_ext == '.m4a':
                return ['-acodec', 'aac', '-b:a', '320k']
            elif output_ext == '.ogg':
                return ['-acodec', 'libvorbis', '-q:a', '10']
            elif output_ext == '.flac':
                return ['-acodec', 'flac']
            else:
                return ['-acodec', 'libmp3lame', '-b:a', '320k']  # Default to MP3
        else:
            # No normalization, can use codec copy for same format
            if output_ext == '.mp3':
                return ['-acodec', 'libmp3lame', '-b:a', '320k']
            elif output_ext == '.wav':
                return ['-acodec', 'pcm_s24le']  # 24-bit PCM
            else:
                return ['-acodec', 'copy']  # Copy codec for same format
    
    def process_file(self, file_path: Path, output_dir: Path, output_ext: str):
        """Process a single audio file."""
        try:
            self.log(f"\nProcessing: {file_path.name}")
            
            # Detect silence
            track_start, track_end, total_length = self.detect_silence(str(file_path))
            
            if track_start is None or track_end is None:
                self.log(f"  Skipped: Could not detect silence")
                return
            
            duration = track_end - track_start
            
            if duration <= 0:
                self.log(f"  Skipped: Invalid duration ({duration}s)")
                return
            
            self.log(f"  Total length: {total_length:.2f}s")

            # Calculate how much will be removed
            trimmed_start = track_start
            trimmed_end = total_length - track_end

            # Check if any actual trimming will occur
            if track_start == 0 and track_end == total_length:
                self.log(f"  No silence to trim (file is already clean)")
                # Still process for format conversion or normalization if requested
            else:
                self.log(f"  Will trim from {track_start:.2f}s to {track_end:.2f}s (keeping {duration:.2f}s)")
                self.log(f"  Removing: {trimmed_start:.2f}s from start, {trimmed_end:.2f}s from end")
            
            # Determine output file
            if output_ext == "original":
                output_ext = file_path.suffix
            
            if self.overwrite_originals.get():
                # Create a truly temporary file in the same directory
                temp_name = f"{file_path.stem}_{uuid.uuid4().hex[:8]}_temp{output_ext}"
                output_path = file_path.parent / temp_name
            else:
                # Preserve directory structure in output folder
                try:
                    rel_path = file_path.parent.relative_to(Path(self.input_folder.get()))
                except ValueError:
                    # If relative path fails, just use the filename
                    rel_path = Path(".")
                output_subdir = output_dir / rel_path
                output_subdir.mkdir(parents=True, exist_ok=True)
                output_path = output_subdir / f"{file_path.stem}_trimmed{output_ext}"
            
            # Build ffmpeg command
            ffmpeg = self.ffmpeg_path.get()
            codec_settings = self.get_output_codec(output_ext)
            
            # Build filter chain
            filters = []
            
            # Add normalization if enabled
            if self.enable_normalization.get():
                try:
                    target_db = float(self.normalization_level.get())
                    # Use volume filter to normalize to peak level
                    # First pass would ideally measure, but for simplicity we'll use a two-pass approach
                    # For real-time we'll use a simpler loudnorm filter
                    filters.append(f"loudnorm=I=-16:TP={target_db}:LRA=11")
                    self.log(f"  Normalizing to {target_db} dB")
                except ValueError:
                    self.log(f"  Warning: Invalid normalization level, skipping normalization")
            
            # Construct command
            cmd = [
                ffmpeg, '-i', str(file_path),
                '-ss', str(track_start),
                '-t', str(duration)
            ]
            
            # Add filters if any
            if filters:
                cmd.extend(['-af', ','.join(filters)])
            
            # Add codec settings
            cmd.extend(codec_settings)
            
            # Add output file (use absolute path to avoid issues)
            cmd.extend([str(output_path.absolute()), '-y'])
            
            # Log the command for debugging
            self.log(f"  Running: {' '.join(cmd)}")
            
            # Run ffmpeg
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            if result.returncode == 0:
                self.log(f"  ✓ Saved to: {output_path}")
                
                # If overwriting, replace original file
                if self.overwrite_originals.get():
                    try:
                        # Delete original and rename temp file
                        file_path.unlink()
                        output_path.rename(file_path)
                        self.log(f"  ✓ Replaced original file")
                    except Exception as e:
                        self.log(f"  ✗ Error replacing original: {str(e)}")
                        # Clean up temp file if rename failed
                        if output_path.exists():
                            output_path.unlink()
            else:
                self.log(f"  ✗ FFmpeg error:")
                # Show last few lines of error
                error_lines = result.stdout.split('\n')[-10:]
                for line in error_lines:
                    if line.strip():
                        self.log(f"    {line}")
                        
        except Exception as e:
            self.log(f"  ✗ Error processing file: {str(e)}")
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
            
            # Check ffmpeg
            try:
                subprocess.run([self.ffmpeg_path.get(), '-version'], 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            except Exception:
                messagebox.showerror("Error", 
                    "FFmpeg not found! Please install FFmpeg or specify the correct path.")
                return
            
            # Find files
            input_ext = self.input_format.get()
            output_ext = self.output_format.get()
            
            if self.recursive.get():
                files = list(input_dir.rglob(f"*{input_ext}"))
            else:
                files = list(input_dir.glob(f"*{input_ext}"))
            
            # Filter out already trimmed files
            files = [f for f in files if not f.stem.endswith("_trimmed")]
            
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
            self.log(f"\n✓ Processing complete! Processed {len(files)} file(s).")
            messagebox.showinfo("Success", f"Processing complete!\nProcessed {len(files)} file(s).")
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}"
            self.log(f"\n✗ {error_msg}")
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
        
        try:
            if self.enable_normalization.get():
                float(self.normalization_level.get())
        except ValueError:
            messagebox.showerror("Error", "Normalization level must be a valid number.")
            return
        
        self.processing = True
        self.process_button.config(state='disabled', text="Processing...")
        self.clear_log()
        
        # Run in separate thread to keep GUI responsive
        thread = threading.Thread(target=self.process_files, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    app = AudioSilenceTrimmer(root)
    root.mainloop()


if __name__ == "__main__":
    main()
