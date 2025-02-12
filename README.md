# GIFWrap

A tool for converting videos to GIFs and generating AI videos using Luma Labs API.

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/GIFWrap.git
cd GIFWrap
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up API keys:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Get your Luma Labs API key:
     1. Go to [Luma Labs Dashboard](https://lumalabs.ai/dashboard)
     2. Sign up or log in
     3. Find your API key in the dashboard
     4. Remove the 'luma-' prefix if present
     5. Add it to your `.env` file

   - Get your ImgBB API key:
     1. Go to [ImgBB API](https://api.imgbb.com/)
     2. Sign up or log in
     3. Get your API key
     4. Add it to your `.env` file

4. Run the application:
```bash
python GIFWrap.py
```

## Features

- Convert videos to GIFs with customizable settings
- Generate AI videos using text prompts
- Generate AI videos using keyframe images
- Control video looping and aspect ratio
- Support for both default and Ray-2 models

## Usage

### GIF Conversion
1. Select input video
2. Choose output location
3. Select conversion options (size, FPS)
4. Click convert

### AI Video Generation
1. Enter text prompt
2. Select output directory
3. Choose generation options:
   - Loop video
   - Aspect ratio (for text generation)
   - Use Ray-2 model (optional)
4. Add keyframe images (optional)
5. Click generate

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)

