#!/usr/bin/env python3
"""
Enhanced License Plate Detection System for Raspberry Pi/PC
Optimized for Indian License Plates
Improved accuracy with multiple detection methods and better preprocessing
With duplicate prevention - each plate is sent only once to API
Modified to work with localhost API
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
import webbrowser
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LicensePlateDetector:
    def __init__(self, api_url=None):
        """Initialize the license plate detector"""
        print("Initializing Enhanced License Plate Detector...")
        
        # API endpoint - use environment variable or parameter or default
        if api_url is None:
            backend_url = os.getenv('BACKEND_API_URL', 'http://localhost:4000')
            self.api_url = f"{backend_url}/api/numbers/numbers"
        else:
            self.api_url = api_url
        print(f"API Endpoint: {self.api_url}")
        
        # Queue for async API requests
        self.api_queue = Queue()
        self.api_thread = None
        self.stop_api_thread = False
        
        # Track sent plates to prevent duplicates
        self.sent_plates = set()
        self.sent_plates_lock = threading.Lock()
        
        # Track plates being processed for payment
        self.pending_payments = {}  # {plate_text: order_id}
        self.pending_payments_lock = threading.Lock()
        
        # Base API URL
        self.base_api_url = api_url.replace('/api/numbers/numbers', '')
        
        # Indian state codes (all valid 2-letter state codes)
        self.indian_state_codes = {
            'AP', 'AR', 'AS', 'BR', 'CG', 'DL', 'GA', 'GJ', 'HR', 'HP',
            'JH', 'JK', 'KA', 'KL', 'LD', 'MH', 'ML', 'MN', 'MP', 'MZ',
            'NL', 'OD', 'PB', 'PY', 'RJ', 'SK', 'TN', 'TR', 'TS', 'UP',
            'UK', 'WB', 'AN', 'CH', 'DN', 'DD', 'LA'
        }
        
        # Initialize EasyOCR reader with better settings for Indian plates
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
                        
                        if response.status_code in [200, 201]:
                            print(f"✓ Data sent successfully to API")
                            print(f"  Response: {response.text}")
                            
                            # Mark as successfully sent
                            with self.sent_plates_lock:
                                self.sent_plates.add(data['numberPlate'])
                        else:
                            print(f"✗ API Error: Status code {response.status_code}")
                            # Don't add to sent_plates if failed, allow retry
                            
                    except requests.exceptions.Timeout:
                        print("✗ API Error: Request timeout")
                    except requests.exceptions.ConnectionError:
                        print("✗ API Error: Connection failed - Is the server running?")
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
    
    def check_plate_in_database(self, plate_text):
        """Check if plate exists in database (whitelisted/registered)"""
        try:
            url = f"{self.base_api_url}/api/numbers/check/{plate_text}"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('exists', False)
            return False
        except Exception as e:
            print(f"✗ Error checking database: {e}")
            return False
    
    def create_payment_qr(self, plate_text):
        """Create payment order and get QR code"""
        try:
            url = f"{self.base_api_url}/api/numbers/payment/create"
            payload = {
                "numberPlate": plate_text,
                "amount": 50  # Default parking fee
            }
            
            print(f"   → Creating payment order for {plate_text}...")
            response = requests.post(url, json=payload, timeout=5)
            
            if response.status_code in [200, 201]:
                data = response.json()
                order_id = data.get('orderId')
                qr_code_url = data.get('qrCodeUrl')
                payment_url = data.get('paymentUrl')  # Frontend payment URL
                
                if not order_id:
                    print(f"✗ Error: No orderId in response")
                    print(f"   Response: {response.text[:200]}")
                    return None, None, None
                
                # Store pending payment
                with self.pending_payments_lock:
                    self.pending_payments[plate_text] = order_id
                
                return order_id, qr_code_url, payment_url
            else:
                # Log detailed error information
                print(f"✗ Payment creation failed: Status {response.status_code}")
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', 'Unknown error')
                    error_type = error_data.get('error', '')
                    
                    print(f"   Error message: {error_message}")
                    
                    # Provide helpful messages for specific errors
                    if error_type == 'RAZORPAY_AUTH_FAILED' or error_type == 'RAZORPAY_CONFIG_MISSING':
                        print(f"   ⚠️  Razorpay credentials issue detected!")
                        print(f"   → Please check your .env file in backend-1/")
                        print(f"   → Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET")
                        print(f"   → Get keys from: https://dashboard.razorpay.com/app/keys")
                    
                    if error_data.get('details'):
                        print(f"   Details: {error_data.get('details')}")
                except:
                    print(f"   Response: {response.text[:200]}")
                return None, None, None
        except requests.exceptions.ConnectionError as e:
            print(f"✗ Connection error: Cannot reach backend at {self.base_api_url}")
            print(f"   Make sure the backend server is running")
            return None, None, None
        except requests.exceptions.Timeout as e:
            print(f"✗ Timeout error: Backend did not respond within 5 seconds")
            return None, None, None
        except Exception as e:
            print(f"✗ Error creating payment: {e}")
            print(f"   Error type: {type(e).__name__}")
            return None, None, None
    
    def check_payment_status(self, order_id):
        """Check if payment is completed"""
        try:
            url = f"{self.base_api_url}/api/numbers/payment/status/{order_id}"
            response = requests.get(url, timeout=3)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('status') == 'completed'
            return False
        except Exception as e:
            print(f"✗ Error checking payment status: {e}")
            return False
    
    def open_gate(self, plate_text, reason="database"):
        """Log gate open action"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'='*60}")
        print(f"🚪 GATE OPEN - {timestamp}")
        print(f"   Plate: {plate_text}")
        print(f"   Reason: {reason}")
        print(f"{'='*60}\n")
    
    def handle_plate_detection(self, plate_text):
        """Handle detected plate: check database, payment flow, gate control"""
        if len(plate_text) != 10:
            return
        
        # Check if already processed
        with self.sent_plates_lock:
            if plate_text in self.sent_plates:
                return
        
        print(f"\n[PROCESSING] Checking plate: {plate_text}")
        
        # Step 1: Check if plate exists in database
        if self.check_plate_in_database(plate_text):
            print(f"✓ Plate found in database (whitelisted)")
            self.open_gate(plate_text, "Found in database")
            
            # Mark as processed
            with self.sent_plates_lock:
                self.sent_plates.add(plate_text)
            return
        
        print(f"✗ Plate NOT found in database - Payment required")
        
        # Step 2: Check if payment already completed
        try:
            url = f"{self.base_api_url}/api/numbers/payment/plate/{plate_text}"
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                data = response.json()
                if data.get('paid', False):
                    print(f"✓ Payment already completed for this plate")
                    self.open_gate(plate_text, "Payment verified")
                    with self.sent_plates_lock:
                        self.sent_plates.add(plate_text)
                    return
        except:
            pass
        
        # Step 3: Create payment and show QR code
        order_id, qr_code_url, payment_url = self.create_payment_qr(plate_text)
        
        if order_id and qr_code_url:
            print(f"\n💳 PAYMENT REQUIRED")
            print(f"   Order ID: {order_id}")
            print(f"   Amount: ₹50")
            print(f"   QR Code generated successfully")
            
            # Open frontend payment page to show QR code (not Razorpay page)
            try:
                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
                frontend_payment_url = f"{frontend_url}/payment?orderId={order_id}&plate={plate_text}"
                
                webbrowser.open(frontend_payment_url)
                print(f"   → Opened QR code page: {frontend_payment_url}")
                print(f"   → Scan QR code to proceed to payment")
            except Exception as e:
                print(f"   → Error opening browser: {e}")
                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
                frontend_payment_url = f"{frontend_url}/payment?orderId={order_id}&plate={plate_text}"
                print(f"   → Please manually visit: {frontend_payment_url}")
                print(f"   → Scan the QR code shown on that page")
            
            # Start polling for payment status in background
            self.start_payment_polling(plate_text, order_id)
        else:
            print(f"✗ Failed to create payment order")
    
    def start_payment_polling(self, plate_text, order_id):
        """Start background thread to poll payment status"""
        def poll_payment():
            max_attempts = 60  # Poll for 5 minutes (60 * 5 seconds)
            attempt = 0
            
            while attempt < max_attempts:
                time.sleep(5)  # Check every 5 seconds
                attempt += 1
                
                if self.check_payment_status(order_id):
                    print(f"\n✓ Payment completed for {plate_text}!")
                    self.open_gate(plate_text, "Payment successful")
                    
                    # Mark as processed
                    with self.sent_plates_lock:
                        self.sent_plates.add(plate_text)
                    
                    # Remove from pending
                    with self.pending_payments_lock:
                        self.pending_payments.pop(plate_text, None)
                    break
                
                if attempt % 12 == 0:  # Every minute
                    print(f"   [Waiting for payment... {attempt * 5}s elapsed]")
            
            if attempt >= max_attempts:
                print(f"\n✗ Payment timeout for {plate_text}")
                with self.pending_payments_lock:
                    self.pending_payments.pop(plate_text, None)
        
        thread = threading.Thread(target=poll_payment, daemon=True)
        thread.start()
    
    def send_to_api(self, plate_text):
        """Send detected plate to backend API (async via queue) - Only 10 character plates"""
        # Double-check: Only send if plate is exactly 10 characters
        if len(plate_text) != 10:
            print(f"✗ Rejected: Plate '{plate_text}' has {len(plate_text)} characters. Only 10-character plates are sent.")
            return
        
        try:
            payload = {
                "numberPlate": plate_text,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to queue for async processing
            self.api_queue.put(payload)
            print(f"→ Queued for API: {plate_text} (10 characters)")
            
        except Exception as e:
            print(f"✗ Error queuing API request: {e}")

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
        """Fast enhancement optimized for Indian license plates"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Fast CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Light denoising for speed
        gray = cv2.bilateralFilter(gray, 5, 50, 50)
        
        return gray
    
    def preprocess_for_contours(self, gray):
        """Fast preprocessing for contour detection"""
        # Single optimized Canny edge detection (faster than multiple)
        edged = cv2.Canny(gray, 50, 150)
        
        # Quick morphological operation to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
        
        return edged
    
    def find_license_plate_contours(self, edged, original_shape):
        """Find potential license plate contours optimized for speed"""
        contours = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = imutils.grab_contours(contours)
        # Process fewer contours for speed (top 15 instead of 30)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:15]
        
        potential_plates = []
        
        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.018 * perimeter, True)
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / float(h) if h > 0 else 0
            area = cv2.contourArea(contour)
            
            # Indian license plate criteria:
            # 1. Should have 4 corners (rectangular)
            # 2. Aspect ratio between 2.5:1 and 5:1 (Indian plates are wider)
            # 3. Area should be reasonable (not too small or too large)
            # 4. Width should be significantly greater than height
            
            if (len(approx) >= 4 and 
                2.5 <= aspect_ratio <= 5.5 and  # Indian plates are typically 3:1 to 4:1
                area > 800 and  # Lower threshold for smaller plates
                area < (original_shape[0] * original_shape[1]) / 3 and
                w > h * 2):  # Width must be at least 2x height
                
                # Calculate rectangularity (how close to rectangle)
                rect_area = w * h
                extent = area / rect_area if rect_area > 0 else 0
                
                if extent > 0.55:  # Slightly lower threshold for Indian plates
                    # Higher confidence for ideal Indian plate aspect ratio (3:1 to 4:1)
                    aspect_bonus = 1.0 if 3.0 <= aspect_ratio <= 4.2 else 0.85
                    potential_plates.append({
                        'contour': approx,
                        'bbox': (x, y, w, h),
                        'area': area,
                        'aspect_ratio': aspect_ratio,
                        'confidence': extent * aspect_bonus
                    })
        
        # Sort by confidence
        potential_plates.sort(key=lambda x: x['confidence'], reverse=True)
        
        return potential_plates[:3]  # Return top 3 candidates for faster processing
    
    def clean_text(self, text):
        """Clean and validate detected text for Indian license plates"""
        if not text:
            return ""
        
        # Remove special characters but keep alphanumeric and spaces
        text = re.sub(r'[^A-Z0-9\s]', '', text.upper())
        
        # Remove spaces and join (Indian plates typically have no spaces)
        text = re.sub(r'\s+', '', text)
        
        # Common OCR mistakes: replace similar-looking characters
        replacements = {
            '0': 'O',  # Sometimes O is read as 0 in state code
            '1': 'I',  # Sometimes I is read as 1
            '5': 'S',  # Sometimes S is read as 5
            '8': 'B',  # Sometimes B is read as 8
        }
        
        # Try to fix common mistakes in first 2 characters (state code)
        if len(text) >= 2:
            state_code = text[:2]
            # Only apply replacements if it results in a valid state code
            for wrong, correct in replacements.items():
                if wrong in state_code:
                    test_code = state_code.replace(wrong, correct)
                    if test_code in self.indian_state_codes:
                        text = test_code + text[2:]
                        break
        
        # Validate Indian license plate format
        # Format: XX##XX#### (old) or XX##XXX#### (new)
        # Where XX = state code (2 letters), ## = district (2 digits), 
        # XX/XXX = series (2-3 letters), #### = number (4 digits)
        
        if len(text) < 8:  # Minimum length for Indian plate
            return ""
        
        # Check if starts with valid state code
        if len(text) >= 2:
            state_code = text[:2]
            if state_code not in self.indian_state_codes:
                # Try to find state code if text has extra characters at start
                for i in range(min(3, len(text) - 1)):
                    potential_state = text[i:i+2]
                    if potential_state in self.indian_state_codes:
                        text = text[i:]  # Remove prefix
                        break
                else:
                    # If still no valid state code found, return empty
                    if text[:2] not in self.indian_state_codes:
                        return ""
        
        # Validate pattern: XX##XX#### or XX##XXX####
        # Pattern: 2 letters + 2 digits + 2-3 letters + 4 digits
        pattern_old = r'^[A-Z]{2}\d{2}[A-Z]{2}\d{4}$'  # Old format: MH12AB1234
        pattern_new = r'^[A-Z]{2}\d{2}[A-Z]{3}\d{4}$'  # New format: MH12ABC1234
        
        # Try to match and fix common OCR errors
        cleaned = text.replace(' ', '').replace('-', '').replace('.', '')
        
        # Check if matches pattern (allowing for some OCR errors)
        if re.match(pattern_old, cleaned) or re.match(pattern_new, cleaned):
            return cleaned
        
        # Try to fix common OCR mistakes and validate again
        # Fix digits in letter positions and letters in digit positions
        if len(cleaned) >= 10:
            # First 2 should be letters (state code)
            if not cleaned[0].isalpha():
                cleaned = cleaned[1:] if len(cleaned) > 10 else cleaned
            if len(cleaned) >= 2 and not cleaned[1].isalpha():
                # Try to fix
                if cleaned[1] in '0123456789':
                    # Might be OCR error, but state codes don't have numbers
                    return ""
            
            # Positions 2-3 should be digits (district)
            if len(cleaned) >= 4:
                if not cleaned[2].isdigit():
                    if cleaned[2] in 'OILZS':
                        cleaned = cleaned[:2] + ('0' if cleaned[2] == 'O' else '1' if cleaned[2] == 'I' else cleaned[2]) + cleaned[3:]
                if not cleaned[3].isdigit():
                    if cleaned[3] in 'OILZS':
                        cleaned = cleaned[:3] + ('0' if cleaned[3] == 'O' else '1' if cleaned[3] == 'I' else cleaned[3]) + cleaned[4:]
            
            # Final validation
            if re.match(pattern_old, cleaned) or re.match(pattern_new, cleaned):
                return cleaned
        
        # If text is close to valid format (8-11 chars, has letters and digits)
        if 8 <= len(cleaned) <= 11 and any(c.isdigit() for c in cleaned) and any(c.isalpha() for c in cleaned):
            # Check if first 2 chars are valid state code
            if len(cleaned) >= 2 and cleaned[:2] in self.indian_state_codes:
                return cleaned
        
        return ""
    
    def extract_text_from_roi(self, frame, bbox):
        """Extract and process text from region of interest - optimized for Indian plates"""
        x, y, w, h = bbox
        
        # Add more padding for Indian plates (they often have borders)
        padding = 8
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(frame.shape[1] - x, w + 2 * padding)
        h = min(frame.shape[0] - y, h + 2 * padding)
        
        roi = frame[y:y+h, x:x+w]
        
        if roi.size == 0:
            return "", 0
        
        # Resize ROI for better OCR (upscale more aggressively for Indian plates)
        min_width = 250  # Indian plates need more width for accurate reading
        if w < min_width:
            scale = min_width / w
            # Limit scale to avoid too much blur
            scale = min(scale, 3.0)
            roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # Convert to grayscale if needed
        if len(roi.shape) == 3:
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        else:
            roi_gray = roi
        
        # Fast preprocessing for Indian plates
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
        roi_gray = clahe.apply(roi_gray)
        
        # Apply only the most effective thresholding methods (reduced from 6 to 3)
        results_list = []
        
        # Method 1: Otsu's thresholding (most reliable)
        _, thresh1 = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # Method 2: Adaptive thresholding (good for varying lighting)
        thresh2 = cv2.adaptiveThreshold(roi_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 2)
        
        # Method 3: Inverted binary (for white text on dark background)
        _, thresh3 = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Try OCR on 3 most effective methods with optimized settings
        for thresh in [thresh1, thresh2, thresh3]:
            try:
                results = self.reader.readtext(
                    thresh, 
                    detail=1, 
                    paragraph=False,
                    allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
                    width_ths=0.7,
                    height_ths=0.7,
                    batch_size=1  # Process one at a time for faster response
                )
                results_list.extend(results)
                
                # Early exit if we find a valid Indian plate with good confidence
                for result in results:
                    text = result[1]
                    confidence = result[2]
                    cleaned = self.clean_text(text)
                    if cleaned and re.match(r'^[A-Z]{2}\d{2}[A-Z]{2,3}\d{4}$', cleaned) and confidence > 0.6:
                        # Found a good match, return immediately
                        return cleaned, min(confidence * 1.2, 1.0)
            except:
                continue
        
        # Find best result with Indian plate validation
        best_text = ""
        best_confidence = 0
        
        for detection in results_list:
            text = detection[1]
            confidence = detection[2]
            
            cleaned = self.clean_text(text)
            if cleaned:
                # Boost confidence if it matches Indian plate pattern perfectly
                if re.match(r'^[A-Z]{2}\d{2}[A-Z]{2,3}\d{4}$', cleaned):
                    confidence *= 1.2  # Boost confidence for valid format
                
                if confidence > best_confidence:
                    best_text = cleaned
                    best_confidence = min(confidence, 1.0)  # Cap at 1.0
        
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
                    
                    # Early exit if we found a high-confidence Indian plate match
                    if confidence > 0.7 and re.match(r'^[A-Z]{2}\d{2}[A-Z]{2,3}\d{4}$', text):
                        break
            
            if best_plate and best_confidence > 0.25:  # Lower threshold for Indian plates (more lenient)
                x, y, w, h = best_plate['bbox']
                
                plate_text = best_plate['text']
                plate_length = len(plate_text)
                is_valid_length = (plate_length == 10)  # Only 10 characters are valid for sending
                
                # Check if already sent (only for valid 10-character plates)
                already_sent = False
                if is_valid_length:
                    already_sent = self.is_plate_already_sent(plate_text)
                
                # Determine color based on status
                if not is_valid_length:
                    color = (0, 165, 255)  # Orange - invalid length (not 10 chars)
                elif already_sent:
                    color = (128, 128, 128)  # Gray - already sent
                else:
                    color = (0, 255, 0)  # Green - valid and ready to send
                
                cv2.drawContours(frame, [best_plate['contour']], -1, color, 3)
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                
                # Display text and confidence with status
                if not is_valid_length:
                    status = f" [INVALID - {plate_length} chars]"
                elif already_sent:
                    status = " [SENT]"
                else:
                    status = " [READY]"
                
                label = f"{plate_text} ({best_confidence:.2%}){status}"
                cv2.putText(frame, label, (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                
                # Print to terminal
                print(f"\n[DETECTED] License Plate: {plate_text}")
                print(f"           Length: {plate_length} characters")
                print(f"           Confidence: {best_confidence:.2%}")
                if not is_valid_length:
                    print(f"           Status: Invalid length - must be 10 characters (not sending)")
                elif already_sent:
                    print(f"           Status: Already sent to API")
                else:
                    print(f"           Status: Valid 10-character plate - Ready to send")
                
                # Handle plate detection: check database, payment, gate control
                # Only if:
                # 1. send_to_api is enabled
                # 2. Not already sent
                # 3. Plate is exactly 10 characters
                if send_to_api and not already_sent and is_valid_length:
                    # Use the new payment flow instead of just sending to API
                    self.handle_plate_detection(plate_text)
                
                detected_plate = plate_text
        
        return detected_plate
    
    def run_detection(self, save_detections=False, output_dir="detections", send_api=True):
        """Run continuous license plate detection optimized for Indian plates"""
        print("Starting Indian License Plate Detection System...")
        print("Optimized for Indian number plate formats (XX##XX#### or XX##XXX####)")
        print("REAL-TIME MODE: Processing every frame for immediate detection")
        print("Press 'q' to quit, 's' to save current frame, 'r' to reset sent history\n")
        print("Tips for better detection:")
        print("  - Ensure good lighting (Indian plates often have reflective surfaces)")
        print("  - Keep plate 2-6 feet from camera")
        print("  - Minimize glare and reflections")
        print("  - Keep camera steady")
        print("  - Ensure plate is clearly visible and not obscured\n")
        
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
        
        # Processing control - process every frame for real-time detection
        PROCESS_EVERY_N_FRAMES = 1  # Process every frame for immediate detection
        
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
                
                # Process every frame for real-time detection
                should_process = (frame_count % PROCESS_EVERY_N_FRAMES == 0)
                
                # Detect license plate in real-time
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
    print("Indian License Plate Detection System")
    print("Optimized for Indian Number Plates")
    print("With Duplicate Prevention")
    print("=" * 60)
    
    # Use backend URL from environment variable
    backend_url = os.getenv('BACKEND_API_URL', 'http://localhost:4000')
    api_url = f"{backend_url}/api/numbers/numbers"
    
    detector = LicensePlateDetector(api_url=api_url)
    
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