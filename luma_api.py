import requests
import os
import time
import logging
from datetime import datetime
from config import (
    LUMA_API_KEY,
    IMGBB_API_KEY,
    LUMA_API_BASE,
    IMGBB_API_BASE
)
import queue

# Setup logging
logging.basicConfig(
    filename=f'luma_api_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class LumaAPI:
    def __init__(self):
        logging.info("Initializing LumaAPI")
        self.headers = {
            'accept': 'application/json',
            'authorization': f'Bearer luma-{LUMA_API_KEY}',
            'content-type': 'application/json'
        }
        self.base_url = "https://api.lumalabs.ai/dream-machine/v1"
        self.callback_url = None
        logging.debug(f"Base URL: {self.base_url}")
    
    def setup_callback(self, port=5000):
        """Setup callback server"""
        try:
            from callback_server import start_callback_server, callback_queue
            self.callback_url = start_callback_server(port)
            self.callback_queue = callback_queue
            logging.info(f"Callback server started at {self.callback_url}")
        except ImportError as e:
            logging.warning(f"Could not setup callback server (missing Flask?): {str(e)}")
            logging.info("Falling back to polling mode")
        except Exception as e:
            logging.warning(f"Callback server setup failed: {str(e)}")
            logging.info("Falling back to polling mode")
    
    def generate_video(self, prompt, **kwargs):
        """Generate video from text prompt"""
        try:
            logging.info(f"Starting video generation with prompt: {prompt}")
            logging.debug(f"Generation options: {kwargs}")
            
            # Basic payload
            payload = {
                'prompt': prompt,
                'loop': kwargs.get('loop', True),
                'aspect_ratio': kwargs.get('aspect_ratio', '16:9')
            }
            
            # Add Ray-2 model if selected
            if kwargs.get('use_ray2', False):
                payload['model'] = 'ray-2'
            
            logging.debug(f"Final payload: {payload}")
            
            response = requests.post(
                f"{self.base_url}/generations",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logging.info(f"Generation started with ID: {result.get('id')}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to start generation: {str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg)
    
    def generate_from_image(self, prompt, keyframes, **kwargs):
        """Generate video from image"""
        try:
            logging.info(f"Starting image-based generation with prompt: {prompt}")
            logging.debug(f"Keyframes: {keyframes}")
            
            # First, upload images to ImgBB
            processed_keyframes = {}
            for frame_key, frame_data in keyframes.items():
                try:
                    logging.info(f"Processing {frame_key}: {frame_data}")
                    # Upload to ImgBB
                    with open(frame_data['url'], 'rb') as file:
                        files = {'image': file}
                        response = requests.post(
                            f"{IMGBB_API_BASE}/upload",
                            params={'key': IMGBB_API_KEY},
                            files=files,
                            timeout=30
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        if not result.get('success'):
                            raise Exception(f"ImgBB upload failed: {result.get('error', 'Unknown error')}")
                        
                        image_url = result['data']['url']
                        logging.info(f"Image uploaded successfully: {image_url}")
                        
                        processed_keyframes[frame_key] = image_url
                        
                except Exception as e:
                    error_msg = f"Failed to process {frame_key}: {str(e)}"
                    logging.error(error_msg)
                    raise Exception(error_msg)
            
            # Create generation payload
            payload = {
                'prompt': prompt,
                'loop': kwargs.get('loop', True),
                'keyframes': {
                    'frame0': {
                        'type': 'image',
                        'url': processed_keyframes.get('frame0', '')
                    }
                }
            }
            
            # Add Ray-2 model if selected
            if kwargs.get('use_ray2', False):
                payload['model'] = 'ray-2'
            
            # Add end frame if provided
            if 'frame1' in processed_keyframes:
                payload['keyframes']['frame1'] = {
                    'type': 'image',
                    'url': processed_keyframes['frame1']
                }
            
            logging.debug(f"Request payload: {payload}")
            response = requests.post(
                f"{self.base_url}/generations",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logging.info(f"Generation started with ID: {result.get('id')}")
            return result
            
        except Exception as e:
            error_msg = f"Failed to start image-based generation: {str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg)
    
    def check_generation_status(self, generation_id):
        """Check status of a generation"""
        try:
            logging.debug(f"Checking status for generation {generation_id}")
            response = requests.get(
                f"{self.base_url}/generations/{generation_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            logging.debug(f"Status response: {result}")
            return result
        except requests.Timeout:
            raise Exception("Status check timed out")
        except requests.RequestException as e:
            if hasattr(e.response, 'text'):
                raise Exception(f"Status check failed: {e.response.text}")
            raise Exception(f"Status check failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to check generation status: {str(e)}")
    
    def download_video(self, video_url, output_path):
        """Download generated video"""
        try:
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return output_path
        except Exception as e:
            raise Exception(f"Failed to download video: {str(e)}")
    
    def wait_for_generation(self, generation, callback=None):
        """Wait for generation to complete with status updates"""
        try:
            generation_id = generation['id']
            logging.info(f"Waiting for generation {generation_id}")
            
            attempts = 0
            max_attempts = 200  # Increase max attempts (10 minutes at 3s intervals)
            
            while attempts < max_attempts:
                try:
                    # Get generation status
                    status = self.check_generation_status(generation_id)
                    current_state = status.get('state', '')
                    logging.debug(f"Generation status: {current_state}")
                    
                    if current_state == "completed":
                        logging.info(f"Generation {generation_id} completed")
                        return status
                    elif current_state == "failed":
                        error_msg = f"Generation failed: {status.get('failure_reason', 'Unknown error')}"
                        logging.error(error_msg)
                        raise Exception(error_msg)
                    elif current_state in ["queued", "dreaming"]:
                        if callback:
                            callback(current_state)
                    else:
                        logging.warning(f"Unknown state: {current_state}")
                    
                    attempts += 1
                    time.sleep(3)  # Wait 3 seconds between checks
                    
                except Exception as e:
                    logging.error(f"Error checking status: {str(e)}")
                    if attempts > max_attempts / 2:
                        raise  # Only raise if we've tried a while
                    time.sleep(5)  # Wait longer on error
            
            error_msg = f"Generation timed out after {max_attempts * 3} seconds"
            logging.error(error_msg)
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Error while waiting for generation: {str(e)}"
            logging.error(error_msg)
            raise Exception(error_msg) 