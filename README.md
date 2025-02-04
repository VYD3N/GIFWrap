# GIFWrap

A simple and efficient tool for converting videos to optimized GIFs with specific size targets.

## Features

- Convert videos to high-quality GIFs (15MB target)
- Create thumbnail GIFs (2MB target)
- Smart resolution optimization
- User-friendly GUI interface
- Maintains aspect ratio
- Automatic frame rate optimization

## Installation

1. Clone the repository:

bash
git clone https://github.com/VYD3N/GIFWrap.git

2. Install dependencies:

bash
pip install -r requirements.txt

## Usage

Run the application:
```bash
python GIFWrap.py
```

1. Click "Browse" to select your input video
2. Choose your output location
3. Click either:
   - "Convert to GIF (15MB)" for full-size GIFs (outputs as filename_Sub15.gif)
   - "Create Thumbnail (2MB)" for smaller previews (outputs as filename_Sub2.gif)

The application will automatically optimize the resolution and frame rate to meet the target file size while maintaining quality.

## Features in Detail

- **Smart Size Optimization**: Automatically calculates optimal dimensions and frame rate
- **Quality Preservation**: Uses advanced analysis to maintain visual quality while meeting size targets
- **Batch Processing**: Coming soon!
- **Format Support**: Handles MP4, AVI, MOV, and WMV input formats

## Requirements

- Python 3.8+
- moviepy
- numpy
- opencv-python
- scikit-learn
- imagehash
- scipy
- Pillow

## Development

This project uses several advanced techniques for optimal GIF conversion:
- Color palette optimization
- Edge complexity analysis
- Motion pattern detection
- Perceptual quality assessment

## License

MIT License

## Credits

Created by [VYD3N]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

