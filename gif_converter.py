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
    MIN_FPS = 12
    MAX_FPS = 30

    def __init__(self):
        self.min_scale = 0.1
        self.max_scale = 1.0
        self._current_fps = None

    def set_fps(self, fps):
        """Set specific FPS for conversion"""
        self.MIN_FPS = fps
        self.MAX_FPS = fps
        self._current_fps = fps

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
        try:
            diff = frame2.astype(float) - frame1.astype(float)
            
            # Apply FFT to difference
            fft = fftpack.fft2(np.mean(diff, axis=2))
            spectrum = np.abs(fftpack.fftshift(fft))
            
            # Ensure spectrum is not empty
            if spectrum.size == 0:
                return {
                    'high_freq_motion': 0.0,
                    'low_freq_motion': 0.0
                }
            
            # Calculate percentiles safely
            high_freq_mask = spectrum > np.percentile(spectrum, 90)
            if high_freq_mask.any():
                high_freq = float(np.mean(spectrum[high_freq_mask]))
            else:
                high_freq = 0.0
                
            low_freq_mask = spectrum <= np.percentile(spectrum, 90)
            if low_freq_mask.any():
                low_freq = float(np.mean(spectrum[low_freq_mask]))
            else:
                low_freq = 0.0
            
            return {
                'high_freq_motion': high_freq,
                'low_freq_motion': low_freq
            }
        except Exception as e:
            print(f"Warning: Motion analysis failed: {str(e)}")
            return {
                'high_freq_motion': 0.0,
                'low_freq_motion': 0.0
            }

    def _analyze_video(self, video) -> dict:
        """Enhanced video analysis with all metrics"""
        try:
            # Basic properties
            duration = video.duration
            frame_count = max(1, int(video.fps * duration))
            original_size = max(1, os.path.getsize(video.filename))
            pixels_per_frame = max(1, video.w * video.h)
            
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
                try:
                    frame = video.get_frame(t)
                    if frame is None:
                        continue
                    
                    # Advanced color analysis
                    color_analysis = self._analyze_color_palette(frame)
                    if color_analysis:  # Ensure we got valid results
                        color_analyses.append(color_analysis)
                    
                    # Advanced edge analysis
                    edge_analysis = self._analyze_edge_complexity(frame)
                    if edge_analysis:  # Ensure we got valid results
                        edge_analyses.append(edge_analysis)
                    
                    # Perceptual complexity
                    complexity = self._analyze_frame_complexity(frame)
                    if complexity is not None:  # Ensure we got valid results
                        perceptual_complexities.append(float(complexity))
                    
                    # Motion patterns
                    if last_frame is not None:
                        motion_pattern = self._analyze_motion_patterns(last_frame, frame)
                        if motion_pattern:  # Ensure we got valid results
                            motion_patterns.append(motion_pattern)
                    
                    last_frame = frame
                except Exception as e:
                    print(f"Warning: Frame analysis failed: {str(e)}")
                    continue
            
            # Ensure we have at least some data
            if not color_analyses:
                color_analyses = [{'color_spread': 0.5}]  # Default value
            if not edge_analyses:
                edge_analyses = [{'fine_edges': 0.5}]  # Default value
            
            # Calculate metrics with safe type conversion
            try:
                color_difficulty = float(np.mean([float(c['color_spread']) for c in color_analyses]))
            except:
                color_difficulty = 0.5  # Default if calculation fails
            
            try:
                edge_difficulty = float(np.mean([float(e['fine_edges']) for e in edge_analyses]))
            except:
                edge_difficulty = 0.5  # Default if calculation fails
            
            try:
                motion_difficulty = float(np.mean([float(m['high_freq_motion']) for m in motion_patterns])) if motion_patterns else 0.0
            except:
                motion_difficulty = 0.0  # Default if calculation fails
            
            try:
                perceptual_difficulty = float(np.mean(perceptual_complexities)) if perceptual_complexities else 0.0
            except:
                perceptual_difficulty = 0.0  # Default if calculation fails
            
            # Weighted compression factor calculation with minimum bounds
            base_compression = 0.35
            compression_factor = base_compression * (
                1.0 - color_difficulty * 0.3
                - edge_difficulty * 0.2
                - motion_difficulty * 0.3
                - perceptual_difficulty * 0.2
            )
            
            # Ensure compression factor stays in reasonable bounds
            compression_factor = max(0.2, min(0.8, compression_factor))
            
            # Calculate target dimension with minimum bounds
            target_bytes = (self.TARGET_MIN_MB + self.TARGET_MAX_MB) / 2 * 1024 * 1024
            bytes_per_pixel = max(0.001, original_size / (pixels_per_frame * frame_count))
            target_pixels_per_frame = target_bytes / (bytes_per_pixel * frame_count * compression_factor)
            
            # Set reasonable minimum dimension
            min_dimension = 200  # Minimum reasonable dimension
            estimated_dimension = max(min_dimension, int(math.sqrt(target_pixels_per_frame)))
            
            # Cap the estimate with reasonable bounds
            max_dim = min(900, max(video.w, video.h))  # Don't exceed original size or 900px
            estimated_dimension = min(max(min_dimension, estimated_dimension), max_dim)
            
            print(f"Debug: compression_factor={compression_factor:.2f}, "
                  f"bytes_per_pixel={bytes_per_pixel:.6f}, "
                  f"target_pixels={target_pixels_per_frame:.0f}")
            
            return {
                'duration': float(duration),
                'frame_count': int(frame_count),
                'bytes_per_pixel': float(bytes_per_pixel),
                'estimated_dimension': int(estimated_dimension),
                'compression_factor': float(compression_factor),
                'color_difficulty': float(color_difficulty),
                'edge_difficulty': float(edge_difficulty),
                'motion_difficulty': float(motion_difficulty),
                'perceptual_difficulty': float(perceptual_difficulty)
            }
        except Exception as e:
            print(f"Analysis failed: {str(e)}")
            # Return safe default values with reasonable dimensions
            return {
                'duration': float(video.duration),
                'frame_count': int(video.fps * video.duration),
                'bytes_per_pixel': 0.1,
                'estimated_dimension': 500,  # Safe middle ground
                'compression_factor': 0.35,
                'color_difficulty': 0.5,
                'edge_difficulty': 0.5,
                'motion_difficulty': 0.0,
                'perceptual_difficulty': 0.0
            }

    def _optimize_video(self, input_path: str) -> str:
        """Optimize any video format for GIF conversion"""
        print("Optimizing video format...")
        try:
            # Create a temporary directory that will persist
            temp_dir = tempfile.mkdtemp()
            mp4_path = os.path.join(temp_dir, "temp.mp4")
            
            # Load video file
            video = VideoFileClip(input_path)
            
            # Calculate optimal bitrate based on resolution
            pixels = video.w * video.h
            base_bitrate = '1000k'  # Default bitrate
            if pixels > 1920 * 1080:
                base_bitrate = '4000k'
            elif pixels > 1280 * 720:
                base_bitrate = '2500k'
            elif pixels > 854 * 480:
                base_bitrate = '1500k'
            
            # Write optimized MP4
            video.write_videofile(
                mp4_path,
                codec='libx264',
                audio=False,
                verbose=False,
                logger=None,
                bitrate=base_bitrate,
                preset='medium',
                ffmpeg_params=[
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                    '-tune', 'film',
                    '-profile:v', 'main',
                    '-level', '3.1',
                    '-refs', '4',
                    '-bf', '2',
                    '-g', '30',
                ]
            )
            video.close()
            
            return mp4_path, temp_dir  # Return both the file path and directory
        except Exception as e:
            if 'temp_dir' in locals() and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            raise Exception(f"Error optimizing video: {str(e)}")

    def _get_video_info(self, video: VideoFileClip) -> dict:
        """Get video information and verify it can be read"""
        try:
            # Test frame reading
            test_frame = video.get_frame(0)
            if test_frame is None:
                raise Exception("Could not read video frames")
            
            return {
                'duration': video.duration,
                'size': video.size,
                'fps': video.fps,
                'frame_count': int(video.duration * video.fps),
                'frame_size': test_frame.shape
            }
        except Exception as e:
            raise Exception(f"Error reading video: {str(e)}")

    def convert_to_gif(self, input_path: str, output_path: str = None) -> str:
        if not output_path:
            output_path = str(Path(input_path).with_suffix('.gif'))

        try:
            print("Loading video...")
            video = VideoFileClip(input_path)
            
            # Verify video can be read
            info = self._get_video_info(video)
            print(f"Video loaded: {info['duration']:.2f}s, {info['frame_count']} frames")
            
            # Verify video loaded correctly
            if video is None or not hasattr(video, 'get_frame'):
                raise Exception("Failed to load video file")
            
            # Verify we can read frames
            try:
                test_frame = video.get_frame(0)
                if test_frame is None:
                    raise Exception("Cannot read video frames")
            except Exception as e:
                raise Exception(f"Error reading video frames: {str(e)}")
            
            video.close()  # Close the initial test load
            
            # Now optimize the video
            temp_mp4 = None
            temp_dir = None
            try:
                temp_mp4, temp_dir = self._optimize_video(input_path)
                
                # Load the optimized video for conversion
                video = VideoFileClip(temp_mp4)
                
                # Get video analysis and continue with conversion...
                analysis = self._analyze_video(video)
                print(f"Video Analysis:")
                print(f"Duration: {analysis['duration']:.2f}s")
                print(f"Frame count: {analysis['frame_count']}")
                print(f"Bytes per pixel: {analysis['bytes_per_pixel']:.6f}")
                print(f"Estimated optimal dimension: {analysis['estimated_dimension']}px")
                
                # Calculate initial dimensions maintaining aspect ratio
                aspect_ratio = video.w / video.h
                
                # Start with conservative settings
                fps = self._current_fps or self.MIN_FPS
                best_settings = None
                best_size = 0
                
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_output = os.path.join(temp_dir, "temp.gif")
                    
                    # Modify the binary search bounds
                    low_dim = 50  # Lower minimum dimension
                    high_dim = max(video.w, video.h)
                    
                    # Use analyzed dimension as starting point
                    current_dim = min(analysis['estimated_dimension'], high_dim)
                    
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
                        print(f"Converting at {fps} FPS...")
                        success, size = self._safe_write_gif(resized, temp_output, fps)
                        resized.close()
                        
                        if success:
                            known_results[current_dim] = size
                            print(f"Size: {size / (1024 * 1024):.2f}MB")
                            
                            if size <= self.TARGET_MAX_BYTES:
                                best_settings = (current_width, current_height, fps)
                                if os.path.exists(temp_output):
                                    try:
                                        shutil.copy2(temp_output, output_path)
                                    except Exception as e:
                                        raise Exception(f"Failed to copy file to destination: {str(e)}")
                                break
                            else:  # size > TARGET_MAX_BYTES
                                last_too_big = current_dim
                                high_dim = current_dim
                                
                                # Calculate next dimension
                                size_ratio = math.sqrt(self.TARGET_MAX_BYTES / size)
                                current_dim = int(current_dim * size_ratio)
                                current_dim = max(current_dim, low_dim)

                        # Break if dimensions get too small
                        if current_dim < 50:  # Absolute minimum to prevent infinite loops
                            if best_settings:
                                break
                            else:
                                raise Exception("Could not achieve target file size")

                        # Prevent infinite loop
                        if current_dim == last_too_big:
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

            except Exception as e:
                # Add more specific error message
                if '.mov' in input_path.lower():
                    raise Exception("MOV file format error. Try converting to MP4 first or use a different format (MP4, AVI, WMV)")
                else:
                    raise Exception(f"Error loading video: {str(e)}")

        except Exception as e:
            raise Exception(f"Error in convert_to_gif: {str(e)}")

    def convert_to_thumbnail(self, input_path: str, output_path: str = None) -> str:
        """Convert video to thumbnail GIF (under 2MB)"""
        original_min_dim = 50
        original_target_min = self.TARGET_MIN_BYTES
        original_target_max = self.TARGET_MAX_BYTES
        original_target_min_mb = self.TARGET_MIN_MB
        original_target_max_mb = self.TARGET_MAX_MB
        
        # Temporarily change the target sizes
        self.TARGET_MIN_BYTES = self.THUMB_MIN_BYTES
        self.TARGET_MAX_BYTES = self.THUMB_MAX_BYTES
        self.TARGET_MIN_MB = self.THUMB_MIN_MB
        self.TARGET_MAX_MB = self.THUMB_MAX_MB
        
        try:
            result = self.convert_to_gif(input_path, output_path)
        finally:
            # Restore original values
            self.TARGET_MIN_BYTES = original_target_min
            self.TARGET_MAX_BYTES = original_target_max
            self.TARGET_MIN_MB = original_target_min_mb
            self.TARGET_MAX_MB = original_target_max_mb
        
        return result 