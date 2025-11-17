#!/usr/bin/env python3
"""
Raspberry Pi Servo Motor Control Script
Continuously checks backend endpoint and controls servo motor based on response
"""

import time
import requests
from datetime import datetime
import sys
import os

# Try to import GPIO libraries (for Raspberry Pi)
GPIO_AVAILABLE = False
Servo = None
PiGPIOFactory = None
GPIO = None

try:
    from gpiozero import Servo
    try:
        from gpiozero.pins.pigpio import PiGPIOFactory
    except ImportError:
        # PiGPIOFactory not available, will use default factory
        PiGPIOFactory = None
    GPIO_AVAILABLE = True
except ImportError:
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO_AVAILABLE = True
    except ImportError:
        GPIO_AVAILABLE = False
        print("Warning: GPIO libraries not available. Running in simulation mode.")

# Configuration
# IMPORTANT: Set BACKEND_URL to your laptop's IP address, not localhost!
# Example: BACKEND_URL=http://192.168.1.100:4000 python3 raspeberry.py
# Or edit the line below with your laptop's IP address
BACKEND_URL = os.getenv('BACKEND_URL', 'http://10.122.220.83:4000')  # Change to your laptop's IP address
ENDPOINT = os.getenv('ENDPOINT', '/api/numbers/trigger-gate')  # Endpoint to check for gate trigger
CHECK_INTERVAL = 2  # Check every 2 seconds
SERVO_PIN = 17  # GPIO pin for servo (change if needed)
SERVO_ROTATION_TIME = 10  # Time to continuously rotate servo (seconds)


class ServoController:
    """Controls servo motor using gpiozero or RPi.GPIO"""
    
    def __init__(self, pin=18):
        self.pin = pin
        self.is_rotating = False
        
        if not GPIO_AVAILABLE:
            print("Running in simulation mode - no actual servo control")
            self.servo = None
            return
        
        try:
            # Try using gpiozero (preferred method)
            if Servo is not None:
                try:
                    if PiGPIOFactory is not None:
                        # Use PiGPIOFactory if available
                        factory = PiGPIOFactory()
                        self.servo = Servo(pin, pin_factory=factory)
                    else:
                        # Use default factory
                        self.servo = Servo(pin)
                    self.method = 'gpiozero'
                    print(f"✓ Servo initialized on GPIO {pin} using gpiozero (default settings)")
                except Exception as e:
                    print(f"gpiozero failed: {e}, trying RPi.GPIO...")
                    # Fallback to RPi.GPIO with PWM
                    if GPIO is not None:
                        GPIO.setup(pin, GPIO.OUT)
                        self.servo = GPIO.PWM(pin, 50)  # 50Hz frequency (20ms period)
                        self.servo.start(0)
                        time.sleep(0.1)  # Small delay for PWM to stabilize
                        self.method = 'RPi.GPIO'
                        print(f"✓ Servo initialized on GPIO {pin} using RPi.GPIO (default settings)")
                    else:
                        raise Exception("Neither gpiozero nor RPi.GPIO available")
            elif GPIO is not None:
                # Use RPi.GPIO directly
                GPIO.setup(pin, GPIO.OUT)
                self.servo = GPIO.PWM(pin, 50)  # 50Hz frequency (20ms period)
                self.servo.start(0)
                time.sleep(0.1)  # Small delay for PWM to stabilize
                self.method = 'RPi.GPIO'
                print(f"✓ Servo initialized on GPIO {pin} using RPi.GPIO (default settings)")
            else:
                raise Exception("No GPIO libraries available")
        except Exception as e:
            print(f"Error initializing servo: {e}")
            self.servo = None
            self.method = None
    
    def set_position(self, angle):
        """Set servo to specific angle (0-180 degrees)"""
        if self.servo is None:
            print(f"[SIMULATION] Servo would move to {angle} degrees")
            self.current_position = angle
            return
        
        # Clamp angle to valid range
        angle = max(0, min(180, angle))
        
        try:
            if self.method == 'gpiozero':
                # gpiozero uses -1 to 1 range
                # Convert 0-180 degrees to -1 to 1 range
                # Formula: value = (angle - 90) / 90.0
                # 0° -> -1, 90° -> 0, 180° -> 1
                value = (angle - 90.0) / 90.0
                value = max(-1.0, min(1.0, value))  # Clamp to -1 to 1
                self.servo.value = value
                time.sleep(0.1)  # Small delay to allow servo to move
            elif self.method == 'RPi.GPIO':
                # RPi.GPIO uses duty cycle percentage
                # Standard servo: 0° = 2.5%, 90° = 7.5%, 180° = 12.5%
                # Formula: duty_cycle = 2.5 + (angle / 180.0) * 10.0
                duty_cycle = 2.5 + (angle / 180.0) * 10.0
                self.servo.ChangeDutyCycle(duty_cycle)
                time.sleep(0.2)  # Give servo time to move to position
                # Keep PWM running (don't stop it, as that can cause issues)
            
            self.current_position = angle
            print(f"Servo moved to {angle} degrees (method: {self.method})")
        except Exception as e:
            print(f"Error moving servo: {e}")
            import traceback
            traceback.print_exc()
    
    def start_continuous_rotation(self):
        """Start continuous rotation of servo"""
        if self.is_rotating:
            print("Servo already rotating, skipping...")
            return  # Already rotating, ignore
        
        self.is_rotating = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting continuous rotation...")
        
        if self.servo is None:
            print(f"[SIMULATION] Servo would rotate continuously")
            return
        
        try:
            if self.method == 'gpiozero':
                # Set to maximum value for continuous rotation (1 = full speed one direction)
                self.servo.value = 1.0
            elif self.method == 'RPi.GPIO':
                # Set duty cycle for continuous rotation (higher than neutral 7.5%)
                # 10% duty cycle for rotation (adjust if needed: 5-10% for slow, 10-15% for fast)
                self.servo.ChangeDutyCycle(10.0)
        except Exception as e:
            print(f"Error starting rotation: {e}")
            self.is_rotating = False
    
    def stop_rotation(self):
        """Stop continuous rotation and return to neutral position"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Stopping rotation...")
        
        if self.servo is None:
            self.is_rotating = False
            return
        
        try:
            if self.method == 'gpiozero':
                # Set to neutral (0 = stop)
                self.servo.value = 0.0
            elif self.method == 'RPi.GPIO':
                # Set to neutral duty cycle (7.5% = stop for continuous rotation servo)
                self.servo.ChangeDutyCycle(7.5)
            time.sleep(0.2)  # Small delay to ensure servo stops
        except Exception as e:
            print(f"Error stopping rotation: {e}")
        
        self.is_rotating = False
    
    def test_servo(self):
        """Test servo by moving through different positions"""
        if self.servo is None:
            print("Cannot test - servo not initialized")
            return
        
        print("\n=== Testing Servo ===")
        test_positions = [0, 45, 90, 135, 180, 90, 0]
        for pos in test_positions:
            print(f"Moving to {pos} degrees...")
            self.set_position(pos)
            time.sleep(0.5)
        print("=== Test Complete ===\n")
    
    def cleanup(self):
        """Clean up GPIO resources"""
        if self.servo is not None:
            try:
                if self.method == 'gpiozero':
                    self.servo.close()
                elif self.method == 'RPi.GPIO':
                    # Return to center position before stopping
                    self.servo.ChangeDutyCycle(7.5)  # 90 degrees
                    time.sleep(0.2)
                    self.servo.stop()
                    GPIO.cleanup()
                print("Servo cleaned up")
            except Exception as e:
                print(f"Error cleaning up servo: {e}")


def check_backend(url):
    """Check backend endpoint for gate trigger"""
    try:
        response = requests.get(url, timeout=5)
        
        # Check if response is successful
        if response.status_code == 200:
            data = response.json()
            
            # Check if gate trigger is active
            if isinstance(data, dict) and data.get('triggered', False):
                plate = data.get('plate', 'UNKNOWN')
                reason = data.get('message', 'Gate trigger')
                timestamp = data.get('timestamp', 'N/A')
                print(f"[DEBUG] Trigger response: {data}")  # Debug output
                return True, f"Gate trigger activated for plate: {plate}"
            else:
                # Debug: log when no trigger (but only occasionally to avoid spam)
                return False, "No gate trigger active"
        else:
            print(f"[DEBUG] HTTP Error: {response.status_code}")
            return False, f"HTTP {response.status_code}"
    
    except requests.exceptions.ConnectionError as e:
        # Don't spam connection errors - they'll be logged periodically
        return False, "Connection error"
    except requests.exceptions.RequestException as e:
        # Don't spam connection errors
        return False, "Connection error"
    except Exception as e:
        print(f"[DEBUG] Error: {str(e)}")
        return False, f"Error: {str(e)}"


def main():
    """Main loop to check backend and control servo"""
    print("=" * 60)
    print("Raspberry Pi Servo Control Script")
    print("=" * 60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Full URL: {BACKEND_URL}{ENDPOINT}")
    print(f"Check Interval: {CHECK_INTERVAL} seconds")
    print(f"Servo Pin: {SERVO_PIN}")
    print(f"Rotation Duration: {SERVO_ROTATION_TIME} seconds")
    print("=" * 60)
    print("\nPress Ctrl+C to stop\n")
    
    # Initialize servo
    servo = ServoController(pin=SERVO_PIN)
    
    if servo.servo is None:
        print("ERROR: Servo not initialized. Please check:")
        print("  1. GPIO libraries are installed (gpiozero or RPi.GPIO)")
        print("  2. You're running on a Raspberry Pi")
        print("  3. GPIO pin is correct and not in use")
        sys.exit(1)
    
    # Set servo to neutral/stop position
    print("Setting servo to neutral position...")
    if servo.servo is not None:
        try:
            if servo.method == 'gpiozero':
                servo.servo.value = 0.0  # Neutral position
            elif servo.method == 'RPi.GPIO':
                servo.servo.ChangeDutyCycle(7.5)  # Neutral for continuous rotation servo
        except:
            pass
    time.sleep(0.5)  # Give servo time to settle
    
    # Optional: Uncomment to test servo on startup
    # print("\nRunning servo test sequence...")
    # servo.test_servo()
    
    full_url = f"{BACKEND_URL}{ENDPOINT}"
    
    # Test backend connection
    print("\nTesting backend connection...")
    test_response, test_message = check_backend(full_url)
    if "Connection error" in test_message or "Error" in test_message:
        print(f"⚠ WARNING: Backend connection test failed!")
        print(f"   Cannot connect to: {BACKEND_URL}")
        print(f"   Make sure:")
        print(f"   1. Backend is running on your laptop")
        print(f"   2. BACKEND_URL is set to your laptop's IP address (not localhost)")
        print(f"   3. Both devices are on the same network")
        print(f"   4. Firewall allows connections on port 4000")
        print(f"\n   To set the correct IP address:")
        print(f"   BACKEND_URL=http://YOUR_LAPTOP_IP:4000 python3 raspeberry.py")
        print(f"   Or edit BACKEND_URL in the script")
        print(f"\n   Continuing anyway, but servo won't work until connection is fixed...\n")
    else:
        print(f"✓ Backend connection OK\n")
    
    print(f"Starting to poll for gate triggers...\n")
    
    try:
        poll_count = 0
        while True:
            # Check backend for gate trigger
            has_trigger, message = check_backend(full_url)
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            poll_count += 1
            
            if has_trigger:
                # Gate trigger detected - rotate servo continuously
                print(f"[{timestamp}] ✓ {message}")
                print(f"[DEBUG] Poll count: {poll_count}, Trigger detected!")
                servo.start_continuous_rotation()
                
                # Keep rotating for the specified duration
                time.sleep(SERVO_ROTATION_TIME)
                
                # Stop rotation
                servo.stop_rotation()
                time.sleep(0.5)  # Small delay after stopping
                poll_count = 0  # Reset counter after successful trigger
            else:
                # Log periodically every 10 polls (20 seconds) to show it's working
                if poll_count % 10 == 0:
                    if "Connection error" in message:
                        print(f"[{timestamp}] ⚠ Connection error - cannot reach backend at {BACKEND_URL}")
                        print(f"   Make sure backend is running and BACKEND_URL is correct")
                    else:
                        print(f"[{timestamp}] Polling... (poll #{poll_count}, waiting for trigger)")
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL)
    
    except KeyboardInterrupt:
        print("\n\nStopping...")
        servo.stop_rotation()
        time.sleep(0.5)
        servo.cleanup()
        print("Script stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        servo.cleanup()
        sys.exit(1)


if __name__ == "__main__":
    main()

