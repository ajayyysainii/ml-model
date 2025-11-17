# Sensor Endpoint Usage Guide

## Endpoint Details

**Base URL:** `http://localhost:4000/api/sensor` (or your server IP)

## Available Endpoints

### 1. POST `/api/sensor/data` - Send Sensor Data
Sends temperature and humidity data to the server. Timestamp is automatically added.

### 2. GET `/api/sensor/data` - Get All Sensor Data
Retrieves all sensor data entries sorted by timestamp (newest first).

### 3. GET `/api/sensor/data/latest` - Get Latest Sensor Data
Retrieves the most recent sensor data entry.

---

## Usage Examples

### 📝 Method 1: Using cURL (Command Line)

#### Send Sensor Data:
```bash
curl -X POST http://localhost:4000/api/sensor/data \
  -H "Content-Type: application/json" \
  -d '{
    "temperature": 25.5,
    "humidity": 60.0
  }'
```

#### Get All Data:
```bash
curl http://localhost:4000/api/sensor/data
```

#### Get Latest Data:
```bash
curl http://localhost:4000/api/sensor/data/latest
```

---

### 🐍 Method 2: Using Python (requests library)

#### Send Sensor Data:
```python
import requests

url = "http://localhost:4000/api/sensor/data"
data = {
    "temperature": 25.5,
    "humidity": 60.0
}

response = requests.post(url, json=data)
print(response.json())
```

#### Get All Data:
```python
import requests

url = "http://localhost:4000/api/sensor/data"
response = requests.get(url)
print(response.json())
```

#### Get Latest Data:
```python
import requests

url = "http://localhost:4000/api/sensor/data/latest"
response = requests.get(url)
print(response.json())
```

#### Example: Continuous Sensor Reading (for Raspberry Pi)
```python
import requests
import time
import random  # Replace with actual sensor reading

BACKEND_URL = "http://localhost:4000"  # Change to your server IP

def send_sensor_data(temperature, humidity):
    """Send sensor data to the backend"""
    url = f"{BACKEND_URL}/api/sensor/data"
    data = {
        "temperature": temperature,
        "humidity": humidity
    }
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 201:
            print(f"✓ Data sent: Temp={temperature}°C, Humidity={humidity}%")
            return True
        else:
            print(f"✗ Error: {response.status_code} - {response.json()}")
            return False
    except Exception as e:
        print(f"✗ Connection error: {e}")
        return False

# Example: Send data every 5 seconds
while True:
    # Replace with actual sensor readings
    temp = random.uniform(20, 30)  # Example: 20-30°C
    humidity = random.uniform(40, 80)  # Example: 40-80%
    
    send_sensor_data(temp, humidity)
    time.sleep(5)  # Wait 5 seconds before next reading
```

---

### 🌐 Method 3: Using JavaScript (fetch API)

#### Send Sensor Data:
```javascript
fetch('http://localhost:4000/api/sensor/data', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    temperature: 25.5,
    humidity: 60.0
  })
})
.then(response => response.json())
.then(data => {
  console.log('Success:', data);
})
.catch(error => {
  console.error('Error:', error);
});
```

#### Get All Data:
```javascript
fetch('http://localhost:4000/api/sensor/data')
  .then(response => response.json())
  .then(data => {
    console.log('Sensor Data:', data);
  })
  .catch(error => {
    console.error('Error:', error);
  });
```

#### Using async/await:
```javascript
async function sendSensorData(temperature, humidity) {
  try {
    const response = await fetch('http://localhost:4000/api/sensor/data', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        temperature: temperature,
        humidity: humidity
      })
    });
    
    const data = await response.json();
    console.log('Success:', data);
    return data;
  } catch (error) {
    console.error('Error:', error);
    return null;
  }
}

// Usage
sendSensorData(25.5, 60.0);
```

---

### 🔧 Method 4: Using Postman or API Testing Tools

1. **Method:** POST
2. **URL:** `http://localhost:4000/api/sensor/data`
3. **Headers:**
   - `Content-Type: application/json`
4. **Body (raw JSON):**
```json
{
  "temperature": 25.5,
  "humidity": 60.0
}
```

---

## Response Format

### Success Response (POST):
```json
{
  "success": true,
  "data": {
    "_id": "507f1f77bcf86cd799439011",
    "temperature": 25.5,
    "humidity": 60.0,
    "timestamp": "2024-01-15T10:30:00.000Z"
  },
  "message": "Sensor data saved successfully"
}
```

### Success Response (GET):
```json
{
  "success": true,
  "data": [
    {
      "_id": "507f1f77bcf86cd799439011",
      "temperature": 25.5,
      "humidity": 60.0,
      "timestamp": "2024-01-15T10:30:00.000Z"
    }
  ],
  "count": 1
}
```

### Error Response:
```json
{
  "success": false,
  "message": "Temperature and humidity are required"
}
```

---

## Important Notes

1. **Server URL:** Replace `localhost:4000` with your actual server IP address if accessing from another device (like Raspberry Pi)
   - Example: `http://192.168.1.100:4000` or `http://10.122.220.83:4000`

2. **Data Types:** 
   - `temperature` and `humidity` should be numbers (can be integers or floats)
   - `timestamp` is automatically generated by the server using `Date.now()`

3. **Required Fields:** Both `temperature` and `humidity` are required in the request body

4. **CORS:** The server has CORS enabled, so you can make requests from any origin

---

## Testing the Endpoint

### Quick Test with cURL:
```bash
# Send test data
curl -X POST http://localhost:4000/api/sensor/data \
  -H "Content-Type: application/json" \
  -d '{"temperature": 25.5, "humidity": 60.0}'

# Get all data
curl http://localhost:4000/api/sensor/data

# Get latest
curl http://localhost:4000/api/sensor/data/latest
```

