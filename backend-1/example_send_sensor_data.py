#!/usr/bin/env python3
"""
Example script to send sensor data to the backend API
Usage: python3 example_send_sensor_data.py
"""

import requests
import time
import random
import os

# Configuration
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:4000')  # Change to your server IP
SENSOR_ENDPOINT = f"{BACKEND_URL}/api/sensor/data"

def send_sensor_data(temperature, humidity):
    """
    Send temperature and humidity data to the backend
    
    Args:
        temperature (float): Temperature value
        humidity (float): Humidity value
    
    Returns:
        dict: Response from the server or None if error
    """
    data = {
        "temperature": temperature,
        "humidity": humidity
    }
    
    try:
        response = requests.post(SENSOR_ENDPOINT, json=data, timeout=5)
        response.raise_for_status()  # Raise an exception for bad status codes
        result = response.json()
        print(f"✓ Success: Temp={temperature}°C, Humidity={humidity}%")
        print(f"  Response: {result.get('message', 'Data saved')}")
        return result
    except requests.exceptions.ConnectionError:
        print(f"✗ Error: Could not connect to {BACKEND_URL}")
        print("  Make sure the server is running!")
        return None
    except requests.exceptions.Timeout:
        print("✗ Error: Request timed out")
        return None
    except requests.exceptions.RequestException as e:
        print(f"✗ Error: {e}")
        if hasattr(e.response, 'json'):
            print(f"  Details: {e.response.json()}")
        return None

def get_all_sensor_data():
    """Get all sensor data from the backend"""
    try:
        response = requests.get(SENSOR_ENDPOINT, timeout=5)
        response.raise_for_status()
        result = response.json()
        print(f"\n✓ Retrieved {result.get('count', 0)} sensor data entries")
        return result
    except Exception as e:
        print(f"✗ Error retrieving data: {e}")
        return None

def get_latest_sensor_data():
    """Get the latest sensor data entry"""
    try:
        url = f"{BACKEND_URL}/api/sensor/data/latest"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        result = response.json()
        if result.get('success') and result.get('data'):
            data = result['data']
            print(f"\n✓ Latest reading:")
            print(f"  Temperature: {data.get('temperature')}°C")
            print(f"  Humidity: {data.get('humidity')}%")
            print(f"  Timestamp: {data.get('timestamp')}")
        return result
    except Exception as e:
        print(f"✗ Error retrieving latest data: {e}")
        return None

def main():
    """Main function with example usage"""
    print("=" * 50)
    print("Sensor Data API Example")
    print("=" * 50)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Endpoint: {SENSOR_ENDPOINT}\n")
    
    # Example 1: Send a single reading
    print("\n[Example 1] Sending a single sensor reading...")
    send_sensor_data(25.5, 60.0)
    
    # Example 2: Send multiple readings (simulating continuous monitoring)
    print("\n[Example 2] Sending multiple readings (simulated)...")
    for i in range(3):
        # Simulate sensor readings (replace with actual sensor code)
        temp = random.uniform(20, 30)
        humidity = random.uniform(40, 80)
        send_sensor_data(round(temp, 2), round(humidity, 2))
        time.sleep(1)  # Wait 1 second between readings
    
    # Example 3: Get all data
    print("\n[Example 3] Retrieving all sensor data...")
    all_data = get_all_sensor_data()
    
    # Example 4: Get latest data
    print("\n[Example 4] Retrieving latest sensor data...")
    get_latest_sensor_data()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("=" * 50)

if __name__ == "__main__":
    main()

