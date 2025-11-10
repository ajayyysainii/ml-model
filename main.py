#!/usr/bin/env python3
"""
Enhanced License Plate Detection System for Raspberry Pi/PC
Improved accuracy with multiple detection methods and better preprocessing
With duplicate prevention - each plate is sent only once to API
"""

import cv2
import numpy as np
import easyocr
import imutils
import time
import platform
import requests
import json
from datetime import datetime
import threading
from queue import Queue
import re

class LicensePlateDetector:
    def __init__(self, api_url="https://ajayyysainii.free.beeceptor.com"):
        """Initialize the license plate detector"""
        print("Initializing Enhanced License Plate Detector...")
        
        # API endpoint
        self.api_url = api_url
        print(f"API Endpoint: {self.api_url}")
        
        # Queue for async API requests
        self.api_queue = Queue()
        self.api_thread = None
        self.stop_api_thread = False
        
        # Track sent plates to prevent duplicates
        self.sent_plates = set()
        self.sent_plates_lock = threading.Lock()
        
        # Initialize EasyOCR reader with better settings
        print("Loading OCR model (this may take a moment)...")
        self.reader = easyocr.Reader(['en'], gpu=False, model_storage_directory='./models')
        
        # Initialize camera based on platform
        print("Initializing camera...")
        self.is_raspberry_pi = self._is_raspberry_pi()
        
        if self.is_raspberry_pi:
            try:
                from picamera2 import Picamera2
                self.picam2 = Picamera2()
                config = self.picam2.create_preview_configuration(
                    main={"size": (640, 480)}  # Lower resolution for speed
                )
                self.picam2.configure(config)
                self.picam2.start()
                self.camera = None
                print("Using Raspberry Pi Camera")
            except ImportError:
                print("Picamera2 not found, falling back to USB camera")
                self.camera = cv2.VideoCapture(0)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.picam2 = None
        else:
            # Use regular webcam for PC with moderate resolution
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            self.picam2 = None
            print("Using PC Webcam")
        
        time.sleep(2)  # Allow camera to warm up
        print("Initialization complete!\n")
    
    def _api_worker(self):
        """Background thread worker for processing API requests"""
        print("API worker thread started")
        
        while not self.stop_api_thread:
            try:
                if not self.api_queue.empty():
                    data = self.api_queue.get(timeout=1)
                    
                    try:
                        response = requests.post(
                            self.api_url,
                            json=data,
                            headers={"Content-Type": "application/json"},
                            timeout=5
                        )
                        
                        if response.status_code == 200:
                            print(f"✓ Data sent successfully to API")
                            print(f"  Response: {response.text}")
                            
                            # Mark as successfully sent
                            with self.sent_plates_lock:
                                self.sent_plates.add(data['nameplate'])
                        else:
                            print(f"✗ API Error: Status code {response.status_code}")
                            # Don't add to sent_plates if failed, allow retry
                            
                    except requests.exceptions.Timeout:
                        print("✗ API Error: Request timeout")
                    except requests.exceptions.ConnectionError:
                        print("✗ API Error: Connection failed")
                    except Exception as e:
                        print(f"✗ API Error: {str(e)}")
                    
                    self.api_queue.task_done()
                else:
                    time.sleep(0.1)
                    
            except:
                time.sleep(0.1)
        
        print("API worker thread stopped")
    
    def start_api_thread(self):
        """Start the background API thread"""
        if self.api_thread is None or not self.api_thread.is_alive():
            self.stop_api_thread = False
            self.api_thread = threading.Thread(target=self._api_worker, daemon=True)
            self.api_thread.start()
    
    def stop_api_worker(self):
        """Stop the background API thread"""
        self.stop_api_thread = True
        if self.api_thread is not None:
            self.api_thread.join(timeout=2)
    
    def _is_raspberry_pi(self):
        """Check if running on Raspberry Pi"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    return True
        except:
            pass
        return False
    
    def capture_frame(self):
        """Capture a frame from the appropriate camera"""
        if self.picam2 is not None:
            frame = self.picam2.capture_array()
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        else:
            ret, frame = self.camera.read()
            if not ret:
                return None
        return frame
    
    def is_plate_already_sent(self, plate_text):
        """Check if this plate has already been sent to the API"""
        with self.sent_plates_lock:
            return plate_text in self.sent_plates
    
    def send_to_api(self, plate_text):
        """Queue detected license plate data for async API submission (only if not sent before)"""
        # Check if already sent
        if self.is_plate_already_sent(plate_text):
            print(f"⊗ Skipped (already sent): {plate_text}")
            return False
        
        data = {
            "nameplate": plate_text,
            "timestamp": datetime.now().isoformat(),
            "device": "Raspberry Pi" if self.is_raspberry_pi else "PC"
        }
        
        self.api_queue.put(data)
        print(f"→ Queued for API: {plate_text}")
        return True
    
    def get_sent_plates_count(self):
        """Get count of unique plates sent to API"""
        with self.sent_plates_lock:
            return len(self.sent_plates)
    
    def clear_sent_plates_history(self):
        """Clear the history of sent plates (useful for testing or reset)"""
        with self.sent_plates_lock:
            count = len(self.sent_plates)
            self.sent_plates.clear()
            print(f"Cleared {count} plates from sent history")
    
    def enhance_image(self, frame):
        """Apply multiple enhancement techniques for better detection"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Lighter denoising for speed
        gray = cv2.bilateralFilter(gray, 5, 50, 50)
        
        # Sharpen the image
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        gray = cv2.filter2D(gray, -1, kernel)
        
        return gray
    
    def preprocess_for_contours(self, gray):
        """Preprocess image for contour detection"""
        # Bilateral filter to reduce noise while keeping edges
        filtered = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Apply multiple edge detection techniques
        edged1 = cv2.Canny(filtered, 30, 200)
        edged2 = cv2.Canny(filtered, 50, 150)
        edged3 = cv2.Canny(filtered, 100, 200)
        
        # Combine edge maps
        edged = cv2.bitwise_or(edged1, edged2)
        edged = cv2.bitwise_or(edged, edged3)
        
        # Morphological operations to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
        
        return edged
    
    def find_license_plate_contours(self, edged, original_shape):
        """Find potential license plate contours with multiple criteria"""
        contours = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = imutils.grab_contours(contours)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:30]
        
        potential_plates = []
        
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * perimeter, True)
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h) if h > 0 else 0
            area = cv2.contourArea(contour)
            
            # License plate criteria:
            # 1. Should have 4 corners (rectangular)
            # 2. Aspect ratio between 2:1 and 5:1 (typical for plates)
            # 3. Area should be reasonable (not too small or too large)
            # 4. Width should be greater than height
            
            if (len(approx) >= 4 and 
                2.0 <= aspect_ratio <= 6.0 and
                area > 1000 and
                area < (original_shape[0] * original_shape[1]) / 3 and
                w > h):
                
                # Calculate rectangularity (how close to rectangle)
                rect_area = w * h
                extent = area / rect_area if rect_area > 0 else 0
                
                if extent > 0.6:  # At least 60% filled
                    potential_plates.append({
                        'contour': approx,
                        'bbox': (x, y, w, h),
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'confidence': extent * (1 if 2.5 <= aspect_ratio <= 4.5 else 0.8)
                    })
        
        # Sort by confidence
        potential_plates.sort(key=lambda x: x['confidence'], reverse=True)
        
        return potential_plates[:5]  # Return top 5 candidates
    
    def clean_text(self, text):
        """Clean and validate detected text"""
        if not text:
            return ""
        
        # Remove special characters but keep alphanumeric
        text = re.sub(r'[^A-Z0-9\s]', '', text.upper())
        
        # Remove extra spaces
        text = ' '.join(text.split())
        
        # Typical license plate patterns (adjust for your region)
        # This is a basic validation - customize based on your country's format
        if len(text) >= 4 and any(c.isdigit() for c in text) and any(c.isalpha() for c in text):
            return text
        
        return ""
    
    def extract_text_from_roi(self, frame, bbox):
        """Extract and process text from region of interest"""
        x, y, w, h = bbox
        
        # Add padding
        padding = 5
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(frame.shape[1] - x, w + 2 * padding)
        h = min(frame.shape[0] - y, h + 2 * padding)
        
        roi = frame[y:y+h, x:x+w]
        
        if roi.size == 0:
            return "", 0
        
        # Resize ROI for better OCR (upscale if too small)
        if w < 200:
            scale = 200 / w
            roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Convert to grayscale if needed
        if len(roi.shape) == 3:
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            roi_gray = roi
        
        # Apply thresholding (try multiple methods)
        results_list = []
        
        # Method 1: Otsu's thresholding
        _, thresh1 = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Method 2: Adaptive thresholding
        thresh2 = cv2.adaptiveThreshold(roi_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 2)
        
        # Method 3: Original grayscale
        thresh3 = roi_gray
        
        # Try OCR on all versions
        for thresh in [thresh1, thresh2, thresh3]:
            try:
                results = self.reader.readtext(thresh, detail=1, paragraph=False,
                                              allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
                results_list.extend(results)
            except:
                continue
        
        # Find best result
        best_text = ""
        best_confidence = 0
        
        for detection in results_list:
            text = detection[1]
            confidence = detection[2]
            
            cleaned = self.clean_text(text)
            if cleaned and confidence > best_confidence:
                best_text = cleaned
                best_confidence = confidence
        
        return best_text, best_confidence
    
    def detect_and_display(self, frame, send_to_api=True, process_detection=True):
        """Detect license plate with enhanced accuracy"""
        detected_plate = None
        
        if process_detection:
            # Enhance image
            gray = self.enhance_image(frame)
            
            # Preprocess for contour detection
            edged = self.preprocess_for_contours(gray)
            
            # Find potential license plates
            potential_plates = self.find_license_plate_contours(edged, frame.shape)
            
            best_plate = None
            best_confidence = 0
            
            for plate in potential_plates:
                # Extract text from this region
                text, confidence = self.extract_text_from_roi(frame, plate['bbox'])
                
                if text and confidence > best_confidence:
                    best_plate = {
                        'text': text,
                        'confidence': confidence,
                        'bbox': plate['bbox'],
                        'contour': plate['contour']
                    }
                    best_confidence = confidence
            
            if best_plate and best_confidence > 0.3:  # Minimum confidence threshold for detection
                x, y, w, h = best_plate['bbox']
                
                # Check if already sent
                already_sent = self.is_plate_already_sent(best_plate['text'])
                
                # Check if confidence is high enough for API submission
                high_confidence = best_confidence >= 0.99  # 99% confidence required for API
                
                # Determine color: Green (high conf), Yellow (medium conf), Gray (already sent)
                if already_sent:
                    color = (128, 128, 128)  # Gray
                elif high_confidence:
                    color = (0, 255, 0)  # Green
                else:
                    color = (0, 255, 255)  # Yellow (detected but not confident enough)
                
                cv2.drawContours(frame, [best_plate['contour']], -1, color, 3)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                # Display text and confidence with status
                status = ""
                if already_sent:
                    status = " [SENT]"
                elif high_confidence:
                    status = " [HIGH CONF]"
                else:
                    status = " [LOW CONF]"
                
                label = f"{best_plate['text']} ({best_confidence:.2%}){status}"
                cv2.putText(frame, label, (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                
                # Print to terminal
                print(f"\n[DETECTED] License Plate: {best_plate['text']}")
                print(f"           Confidence: {best_confidence:.2%}")
                if already_sent:
                    print(f"           Status: Already sent to API")
                elif not high_confidence:
                    print(f"           Status: Confidence too low for API (need ≥99%)")
                
                # Send to API only if: not already sent AND confidence >= 99%
                if send_to_api and not already_sent and high_confidence:
                    self.send_to_api(best_plate['text'])
                
                detected_plate = best_plate['text']
        
        return detected_plate
    
    def run_detection(self, save_detections=False, output_dir="detections", send_api=True):
        """Run continuous license plate detection"""
        print("Starting enhanced license plate detection...")
        print("Press 'q' to quit, 's' to save current frame, 'r' to reset sent history\n")
        print("Tips for better detection:")
        print("  - Ensure good lighting")
        print("  - Keep plate 2-6 feet from camera")
        print("  - Minimize glare and reflections")
        print("  - Keep camera steady\n")
        print("PERFORMANCE: Processing every 5th frame for smooth video\n")
        
        if send_api:
            self.start_api_thread()
        
        if save_detections:
            import os
            os.makedirs(output_dir, exist_ok=True)
        
        detection_count = 0
        frame_count = 0
        last_detection = None
        
        # FPS calculation
        fps_start_time = time.time()
        fps_counter = 0
        fps = 0
        
        # Processing control
        PROCESS_EVERY_N_FRAMES = 5  # Process detection every 5 frames for speed
        
        try:
            while True:
                frame = self.capture_frame()
                
                if frame is None:
                    print("Error: Could not capture frame")
                    break
                
                # Calculate FPS
                fps_counter += 1
                if fps_counter >= 30:
                    fps = fps_counter / (time.time() - fps_start_time)
                    fps_start_time = time.time()
                    fps_counter = 0
                
                frame_count += 1
                
                # Only process detection every N frames to improve speed
                should_process = (frame_count % PROCESS_EVERY_N_FRAMES == 0)
                
                # Detect license plate (skip heavy processing on most frames)
                plate_text = self.detect_and_display(frame, 
                                                     send_to_api=send_api,
                                                     process_detection=should_process)
                
                if plate_text:
                    last_detection = plate_text
                
                # Display FPS and sent count
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                sent_count = self.get_sent_plates_count()
                cv2.putText(frame, f"Sent: {sent_count}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                if last_detection:
                    cv2.putText(frame, f"Last: {last_detection}", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
                # Show frame
                cv2.imshow("Enhanced License Plate Detection", frame)
                
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord('q'):
                    break
                elif key == ord('s') and save_detections:
                    detection_count += 1
                    filename = f"{output_dir}/detection_{detection_count}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"Saved: {filename}")
                elif key == ord('r'):
                    self.clear_sent_plates_history()
        
        except KeyboardInterrupt:
            print("\nStopping detection...")
        
        finally:
            if send_api:
                print("Waiting for pending API requests...")
                self.api_queue.join()
                self.stop_api_worker()
            
            print(f"\nTotal unique plates sent to API: {self.get_sent_plates_count()}")
            self.cleanup()
    
    def detect_from_image(self, image_path):
        """Detect license plate from a single image file"""
        frame = cv2.imread(image_path)
        
        if frame is None:
            print(f"Error: Could not load image from {image_path}")
            return None
        
        print(f"\nProcessing image: {image_path}")
        plate_text = self.detect_and_display(frame, send_to_api=False)
        
        cv2.imshow("Enhanced License Plate Detection", frame)
        cv2.waitKey(0)
        
        self.cleanup()
        return plate_text
    
    def cleanup(self):
        """Clean up resources"""
        print("\nCleaning up...")
        
        self.stop_api_worker()
        
        if self.picam2 is not None:
            self.picam2.stop()
        if self.camera is not None:
            self.camera.release()
        cv2.destroyAllWindows()
        print("Done!")


def main():
    """Main function"""
    print("=" * 60)
    print("Enhanced License Plate Detection System")
    print("With Duplicate Prevention")
    print("=" * 60)
    
    detector = LicensePlateDetector()
    
    print("\nSelect mode:")
    print("1. Live camera detection")
    print("2. Detect from image file")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        save_option = input("Save detections? (y/n): ").strip().lower()
        api_option = input("Send data to API? (y/n): ").strip().lower()
        detector.run_detection(
            save_detections=(save_option == 'y'),
            send_api=(api_option == 'y')
        )
    
    elif choice == "2":
        image_path = input("Enter image path: ").strip()
        detector.detect_from_image(image_path)
    
    else:
        print("Invalid choice!")
        detector.cleanup()


if __name__ == "__main__":
    main()