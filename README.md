# Audio & Video Tools for YouTube and Vinyl

A collection of Python GUI tools for processing audio files, particularly useful for cleaning up vinyl rips, YouTube downloads, and batch audio conversions.

## Tools Included

### 1. Audio Silence Trimmer (RMS-based)
**File:** `audio_silence_trimmer_RMS.py`

Automatically detects and removes silence from the beginning and end of audio files using RMS loudness analysis. Perfect for cleaning up vinyl rips or recordings with unwanted silence.

#### Features
- **Smart RMS Detection**: Analyzes audio loudness to find when actual music starts and ends
- **Multi-format Support**: Works with WAV, MP3, M4A, FLAC, OGG, MP4, and more
- **FFmpeg Fallback**: Automatically handles M4A/AAC files using FFmpeg when needed
- **Batch Processing**: Process entire folders recursively
- **Optional Normalization**: Normalize audio to target peak level
- **Preserve Structure**: Maintains folder hierarchy in output
- **Overwrite Mode**: Option to replace original files

#### Usage
1. Select input folder containing audio files
2. Choose output folder or enable "Overwrite original files"
3. Select input format (e.g., .m4a, .wav)
4. Choose output format (original, MP3 320kbps, or WAV 24-bit)
5. Optionally enable normalization
6. Click "Process Files"

---

### 2. Audio Format Converter
**File:** `audio_format_converter.py`

Batch convert audio files between formats with selectable input types and quality settings.

#### Features
- **Selective Input Formats**: Choose which formats to process via checkboxes
  - Supported: WAV, MP3, M4A, FLAC, OGG, AAC, MP4, WMA, AIFF
- **High-Quality Output**:
  - MP3: 320kbps CBR
  - WAV: 24-bit PCM
- **Flat Output Structure**: All converted files go to a single output folder
- **Duplicate Handling**: Automatically renames duplicates
- **Batch Processing**: Process entire folders recursively
- **Optional Normalization**: Normalize audio during conversion

#### Usage
1. Select input folder containing audio files
2. Choose output folder (all files will be placed here)
3. Select which input formats to process (checkboxes)
4. Choose output format (MP3 or WAV)
5. Optionally enable normalization
6. Click "Convert Files"

---

### 3. Click/Pop Remover
**File:** `audio_click_pop_remover.py`

Remove vinyl clicks, pops, and other audio artifacts using FFmpeg's declicking and denoising filters.

#### Features
- **Declicking Filter**: Removes vinyl clicks and pops
- **Denoising**: Reduces background noise
- **Adjustable Settings**: Control threshold and filter strength
- **Batch Processing**: Process multiple files at once
- **High-Quality Output**: MP3 320kbps or WAV 24-bit

#### Usage
1. Select input folder
2. Choose output folder
3. Adjust threshold and denoising settings
4. Select output format
5. Click "Process Files"

---

## Installation

### Requirements
- Python 3.7 or higher
- FFmpeg (must be in PATH or specify path in application)

### Python Dependencies
```bash
pip install numpy soundfile
```

### Installing FFmpeg

**Windows:**
1. Download from [ffmpeg.org](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add to PATH or specify path in the application

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg  # Debian/Ubuntu
sudo yum install ffmpeg      # CentOS/RHEL
```

---

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/OKylieanG/audio_video_tools_YT_Vinyl.git
cd audio_video_tools_YT_Vinyl
```

2. Install dependencies:
```bash
pip install numpy soundfile
```

3. Run any tool:
```bash
python audio_silence_trimmer_RMS.py
python audio_format_converter.py
python audio_click_pop_remover.py
```

---

## Common Use Cases

### Cleaning Vinyl Rips
1. Use **Click/Pop Remover** to remove surface noise
2. Use **Audio Silence Trimmer** to remove lead-in/lead-out silence
3. Use **Audio Format Converter** to convert to desired format

### Processing YouTube Downloads
1. Use **Audio Silence Trimmer** to remove intro/outro silence
2. Use **Audio Format Converter** to normalize and convert format

### Batch Format Conversion
1. Use **Audio Format Converter** with recursive processing
2. Select specific input formats to convert
3. All files output to single folder for easy organization

---

## Technical Details

### Audio Silence Trimmer Algorithm
The RMS-based silence detection works by:
1. Calculating overall RMS loudness of the entire track
2. Analyzing audio in frames (0.5s coarse, 0.1s fine)
3. Comparing frame RMS to overall track RMS
4. Finding start/end points where audio is within 50% of track RMS
5. Two-phase detection (coarse → fine) for precision

### Supported Formats

**Input:** WAV, MP3, M4A, FLAC, OGG, AAC, MP4, WMA, AIFF
**Output:** MP3 (320kbps CBR), WAV (24-bit PCM)

### FFmpeg Integration
- M4A/AAC files are decoded via FFmpeg when soundfile can't read them
- All encoding uses FFmpeg for maximum compatibility
- Normalization uses FFmpeg's loudnorm filter

---

## Troubleshooting

### "FFmpeg not found" Error
- Ensure FFmpeg is installed and in your PATH
- Or specify the full path to ffmpeg in the application settings

### "Format not recognised" Error
- This should auto-fallback to FFmpeg
- If it persists, ensure FFmpeg is properly installed

### Out of Memory Error
- The silence trimmer automatically uses chunked reading for large files
- Try closing other applications to free up RAM

### Files Not Processing
- Check file permissions
- Ensure input/output folders exist and are writable
- Check progress log for specific errors

---

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

### Development
- Tools are built with tkinter for cross-platform GUI
- FFmpeg is used for all audio processing
- RMS analysis uses numpy and soundfile

---

## License

This project is open source and available under the MIT License.

---

## Credits

Developed with assistance from Claude (Anthropic).

Special thanks to:
- FFmpeg team for the excellent audio processing library
- soundfile/libsndfile for Python audio I/O

---

## Changelog

### Latest (2026-01-20)
- Added audio format converter with selectable input formats
- Added FFmpeg-based M4A/AAC support to silence trimmer
- Fixed FFmpeg command argument ordering
- Improved error handling for directory creation
- Added checkbox UI for format selection

### Previous
- Added click/pop remover tool
- Implemented RMS-based silence detection
- Added normalization support
- Added recursive folder processing

---

## Support

For issues or questions, please open an issue on GitHub:
https://github.com/OKylieanG/audio_video_tools_YT_Vinyl/issues