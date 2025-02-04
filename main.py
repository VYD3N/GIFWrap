import argparse
from gif_converter import GifConverter

def main():
    parser = argparse.ArgumentParser(description='Convert MP4 to GIF under 15MB')
    parser.add_argument('input', help='Input MP4 file path')
    parser.add_argument('--output', help='Output GIF file path (optional)')
    
    args = parser.parse_args()
    
    converter = GifConverter()
    output_path = converter.convert_to_gif(args.input, args.output)
    print(f"GIF created successfully at: {output_path}")

if __name__ == "__main__":
    main() 