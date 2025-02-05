# Try alternative import
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    import moviepy
    from moviepy.editor import VideoFileClip
import os
from pathlib import Path
from PIL import Image
import math
import tempfile
import numpy as np
import cv2
from sklearn.cluster import MiniBatchKMeans
import imagehash
from scipy import fftpack
import shutil

# Add this at the top to patch PIL.Image.ANTIALIAS
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

class GifConverter:
    TARGET_MIN_MB = 14.8
    TARGET_MAX_MB = 14.99
    THUMB_MIN_MB = 1.8
    THUMB_MAX_MB = 1.99
    TARGET_MIN_BYTES = int(TARGET_MIN_MB * 1024 * 1024)
    TARGET_MAX_BYTES = int(TARGET_MAX_MB * 1024 * 1024)
    THUMB_MIN_BYTES = int(THUMB_MIN_MB * 1024 * 1024)
    THUMB_MAX_BYTES = int(THUMB_MAX_MB * 1024 * 1024)
    MIN_DIMENSION = 700
    THUMB_MIN_DIMENSION = 200
    MIN_FPS = 12
    MAX_FPS = 30

    def __init__(self):
        self.min_scale = 0.1
        self.max_scale = 1.0

    def _safe_write_gif(self, clip, output_path: str, fps: int) -> tuple[bool, int]:
        """Safely write GIF and return success status and file size"""
        try:
            clip.write_gif(
                output_path,
                fps=fps,
                opt='nq',
                logger=None
            )
            if os.path.exists(output_path):
                return True, os.path.getsize(output_path)
            return False, 0
        except Exception as e:
            print(f"Warning: GIF writing failed with error: {str(e)}")
            return False, 0

    def _analyze_color_palette(self, frame):
        """Advanced color analysis using k-means clustering"""
        # Reshape and sample pixels for faster clustering
        pixels = frame.reshape(-1, 3)
        sample_size = min(10000, len(pixels))
        sampled_pixels = pixels[np.random.choice(len(pixels), sample_size)]
        
        # Cluster colors to simulate GIF palette
        kmeans = MiniBatchKMeans(n_clusters=256, random_state=0)
        kmeans.fit(sampled_pixels)
        
        # Calculate quantization error and cluster distribution
        labels = kmeans.predict(sampled_pixels)
        cluster_sizes = np.bincount(labels)
        color_spread = np.std(cluster_sizes) / np.mean(cluster_sizes)
        
        return {
            'quantization_error': kmeans.inertia_ / sample_size,
            'color_spread': color_spread
        }

    def _analyze_edge_complexity(self, frame):
        """Advanced edge analysis using Canny edge detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame.astype(np.uint8), cv2.COLOR_RGB2GRAY)
        
        # Multi-scale edge detection
        edges1 = cv2.Canny(gray, 100, 200)
        edges2 = cv2.Canny(gray, 50, 100)
        
        # Calculate edge density at different scales
        edge_density1 = np.mean(edges1) / 255.0
        edge_density2 = np.mean(edges2) / 255.0
        
        return {
            'fine_edges': edge_density1,
            'coarse_edges': edge_density2
        }

    def _analyze_frame_complexity(self, frame):
        """Analyze visual complexity using perceptual hashing"""
        # Convert frame to PIL Image
        pil_image = Image.fromarray(frame.astype('uint8'))
        
        # Calculate different types of perceptual hashes
        phash = imagehash.average_hash(pil_image)
        dhash = imagehash.dhash(pil_image)
        
        # Compare hashes to measure complexity
        complexity = (phash - dhash) / 64.0  # Normalized difference
        return complexity

    def _analyze_motion_patterns(self, frame1, frame2):
        """Analyze motion patterns using Fourier analysis"""
        diff = frame2.astype(float) - frame1.astype(float)
        
        # Apply FFT to difference
        fft = fftpack.fft2(np.mean(diff, axis=2))
        spectrum = np.abs(fftpack.fftshift(fft))
        
        # Analyze frequency components
        high_freq = np.mean(spectrum[spectrum > np.percentile(spectrum, 90)])
        low_freq = np.mean(spectrum[spectrum <= np.percentile(spectrum, 90)])
        
        return {
            'high_freq_motion': high_freq,
            'low_freq_motion': low_freq
        }

    def _analyze_video(self, video) -> dict:
        """Enhanced video analysis with all metrics"""
        # Basic properties
        duration = video.duration
        frame_count = max(1, int(video.fps * duration))  # Ensure non-zero
        original_size = max(1, os.path.getsize(video.filename))  # Ensure non-zero
        pixels_per_frame = max(1, video.w * video.h)  # Ensure non-zero
        
        # Sample frames for analysis
        sample_frames = min(20, frame_count)
        frame_times = np.linspace(0, duration, sample_frames)
        
        # Analysis accumulators
        color_analyses = []
        edge_analyses = []
        perceptual_complexities = []
        motion_patterns = []
        
        print("Analyzing video characteristics...")
        
        # Analyze frames
        last_frame = None
        for i, t in enumerate(frame_times):
            frame = video.get_frame(t)
            
            # Advanced color analysis
            color_analysis = self._analyze_color_palette(frame)
            color_analyses.append(color_analysis)
            
            # Advanced edge analysis
            edge_analysis = self._analyze_edge_complexity(frame)
            edge_analyses.append(edge_analysis)
            
            # Perceptual complexity
            complexity = self._analyze_frame_complexity(frame)
            perceptual_complexities.append(complexity)
            
            # Motion patterns
            if last_frame is not None:
                motion_pattern = self._analyze_motion_patterns(last_frame, frame)
                motion_patterns.append(motion_pattern)
            
            last_frame = frame
        
        # Calculate comprehensive metrics
        color_difficulty = np.mean([c['color_spread'] for c in color_analyses])
        edge_difficulty = np.mean([e['fine_edges'] for e in edge_analyses])
        motion_difficulty = np.mean([m['high_freq_motion'] for m in motion_patterns]) if motion_patterns else 0
        perceptual_difficulty = np.mean(perceptual_complexities)
        
        # Weighted compression factor calculation
        base_compression = 0.35
        compression_factor = base_compression * (
            1.0 - color_difficulty * 0.3    # Color impact
            - edge_difficulty * 0.2         # Edge impact
            - motion_difficulty * 0.3       # Motion impact
            - perceptual_difficulty * 0.2   # Perceptual complexity impact
        )
        
        # Calculate target dimension with safety checks
        target_bytes = (self.TARGET_MIN_MB + self.TARGET_MAX_MB) / 2 * 1024 * 1024
        bytes_per_pixel = max(0.0001, original_size / (pixels_per_frame * frame_count))  # Minimum value
        
        # Ensure compression_factor is positive and non-zero
        compression_factor = max(0.01, compression_factor)  # Minimum compression factor
        
        # Apply advanced adjustments with safety
        if frame_count > 60:
            compression_factor *= 1.1
        if bytes_per_pixel < 0.1:
            compression_factor *= 1.2
        
        # Safe calculation of target pixels
        target_pixels_per_frame = max(1, target_bytes / (bytes_per_pixel * frame_count * compression_factor))
        estimated_dimension = int(math.sqrt(target_pixels_per_frame))
        
        # Cap the estimate with safety checks
        max_dim = int(900 * max(0.1, (1.0 - (color_difficulty + motion_difficulty) / 2)))
        estimated_dimension = min(max(self.MIN_DIMENSION, estimated_dimension), max_dim)
        
        return {
            'duration': duration,
            'frame_count': frame_count,
            'bytes_per_pixel': bytes_per_pixel,
            'estimated_dimension': estimated_dimension,
            'compression_factor': compression_factor,
            'color_difficulty': float(color_difficulty),  # Ensure float
            'edge_difficulty': float(edge_difficulty),    # Ensure float
            'motion_difficulty': float(motion_difficulty),# Ensure float
            'perceptual_difficulty': float(perceptual_difficulty)  # Ensure float
        }

    def convert_to_gif(self, input_path: str, output_path: str = None) -> str:
        if not output_path:
            output_path = str(Path(input_path).with_suffix('.gif'))

        video = VideoFileClip(input_path)
        
        # Get video analysis
        analysis = self._analyze_video(video)
        print(f"Video Analysis:")
        print(f"Duration: {analysis['duration']:.2f}s")
        print(f"Frame count: {analysis['frame_count']}")
        print(f"Bytes per pixel: {analysis['bytes_per_pixel']:.6f}")
        print(f"Estimated optimal dimension: {analysis['estimated_dimension']}px")
        
        # Calculate initial dimensions maintaining aspect ratio
        aspect_ratio = video.w / video.h
        
        # Start with conservative settings
        fps = self.MIN_FPS
        best_settings = None
        best_size = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = os.path.join(temp_dir, "temp.gif")
            
            # Modify the binary search bounds
            low_dim = self.MIN_DIMENSION  # Start from minimum dimension
            high_dim = max(video.w, video.h)
            
            # Use analyzed dimension as starting point, but respect minimum
            current_dim = max(
                self.MIN_DIMENSION,
                min(analysis['estimated_dimension'], high_dim)
            )
            last_too_big = None
            last_too_small = None
            
            # Store results to improve predictions
            known_results = {}  # dimension -> size mapping
            
            while True:
                # Calculate width and height maintaining aspect ratio
                if aspect_ratio > 1:
                    current_width = current_dim
                    current_height = int(current_dim / aspect_ratio)
                else:
                    current_height = current_dim
                    current_width = int(current_dim * aspect_ratio)

                print(f"Trying {current_width}x{current_height} at {fps}fps...")
                
                resized = video.resize((current_width, current_height))
                success, size = self._safe_write_gif(resized, temp_output, fps)
                resized.close()
                
                if success:
                    known_results[current_dim] = size
                    print(f"Size: {size / (1024 * 1024):.2f}MB")
                    
                    if self.TARGET_MIN_BYTES <= size <= self.TARGET_MAX_BYTES:
                        best_settings = (current_width, current_height, fps)
                        if os.path.exists(temp_output):
                            try:
                                shutil.copy2(temp_output, output_path)
                            except Exception as e:
                                raise Exception(f"Failed to copy file to destination: {str(e)}")
                        break
                    elif size < self.TARGET_MIN_BYTES:
                        last_too_small = current_dim
                        low_dim = current_dim
                        best_settings = (current_width, current_height, fps)
                        best_size = size
                        
                        if len(known_results) >= 2:
                            # Use quadratic interpolation from known results
                            dims = sorted(known_results.keys())
                            sizes = [known_results[d] for d in dims]
                            
                            # Calculate size-to-dimension ratio for interpolation
                            target_size = (self.TARGET_MIN_MB + self.TARGET_MAX_MB) / 2 * 1024 * 1024
                            
                            # Use the two closest points for quadratic estimation
                            d1, d2 = dims[-2:]
                            s1, s2 = sizes[-2:]
                            
                            # Calculate quadratic scaling factor
                            scale_factor = math.sqrt(s2/s1) / (d2/d1)
                            
                            # Estimate next dimension
                            size_ratio = target_size / size
                            dim_ratio = math.pow(size_ratio, 1/(2 * scale_factor))
                            current_dim = int(current_dim * dim_ratio)
                        else:
                            # First attempt - use simple ratio
                            size_ratio = math.sqrt(self.TARGET_MIN_BYTES / size)
                            current_dim = int(current_dim * size_ratio)
                        
                        current_dim = min(current_dim, high_dim)
                        if last_too_big is not None:
                            current_dim = min(current_dim, last_too_big - 1)
                            
                    else:  # size > TARGET_MAX_BYTES
                        last_too_big = current_dim
                        high_dim = current_dim
                        
                        if len(known_results) >= 2:
                            # Similar quadratic interpolation for too-big case
                            dims = sorted(known_results.keys())
                            sizes = [known_results[d] for d in dims]
                            
                            d1, d2 = dims[-2:]
                            s1, s2 = sizes[-2:]
                            scale_factor = math.sqrt(s2/s1) / (d2/d1)
                            
                            size_ratio = self.TARGET_MAX_BYTES / size
                            dim_ratio = math.pow(size_ratio, 1/(2 * scale_factor))
                            current_dim = int(current_dim * dim_ratio)
                        else:
                            size_ratio = math.sqrt(self.TARGET_MAX_BYTES / size)
                            current_dim = int(current_dim * size_ratio)
                        
                        current_dim = max(current_dim, low_dim)
                        if last_too_small is not None:
                            current_dim = max(current_dim, last_too_small + 1)

                # Break if we can't find a better size
                if last_too_big is not None and last_too_small is not None:
                    if last_too_big - last_too_small <= 1:
                        break

                # Prevent infinite loop
                if current_dim == last_too_small or current_dim == last_too_big:
                    break

        video.close()

        if not best_settings:
            raise Exception("Could not create GIF with acceptable settings")

        width, height, fps = best_settings
        if not os.path.exists(output_path):
            # Create final GIF with best settings
            resized = video.resize((width, height))
            success, size = self._safe_write_gif(resized, output_path, fps)
            resized.close()
            if not success:
                raise Exception("Failed to create final GIF")

        final_size = os.path.getsize(output_path)
        print(f"Final GIF: {width}x{height} at {fps}fps")
        print(f"File size: {final_size / (1024 * 1024):.2f}MB")

        return output_path

    def convert_to_thumbnail(self, input_path: str, output_path: str = None) -> str:
        """Convert video to thumbnail GIF (under 2MB)"""
        original_min_dim = self.MIN_DIMENSION
        original_target_min = self.TARGET_MIN_BYTES
        original_target_max = self.TARGET_MAX_BYTES
        original_target_min_mb = self.TARGET_MIN_MB
        original_target_max_mb = self.TARGET_MAX_MB
        
        # Temporarily change the target sizes
        self.MIN_DIMENSION = self.THUMB_MIN_DIMENSION
        self.TARGET_MIN_BYTES = self.THUMB_MIN_BYTES
        self.TARGET_MAX_BYTES = self.THUMB_MAX_BYTES
        self.TARGET_MIN_MB = self.THUMB_MIN_MB
        self.TARGET_MAX_MB = self.THUMB_MAX_MB
        
        try:
            result = self.convert_to_gif(input_path, output_path)
        finally:
            # Restore original values
            self.MIN_DIMENSION = original_min_dim
            self.TARGET_MIN_BYTES = original_target_min
            self.TARGET_MAX_BYTES = original_target_max
            self.TARGET_MIN_MB = original_target_min_mb
            self.TARGET_MAX_MB = original_target_max_mb
        
        return result 