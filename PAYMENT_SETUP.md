# Payment Flow Setup Guide

## Overview
The system now supports automatic gate control with payment integration:
1. **If plate found in database** → Gate opens immediately (logged in terminal)
2. **If plate NOT found** → Razorpay QR code is generated → After payment → Gate opens

## Setup Instructions

### 1. Backend Setup

#### Install Dependencies
```bash
cd backend-1
npm install
```

#### Configure Razorpay
1. Create a `.env` file in `backend-1/` directory:
```env
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_UPI_ID=your-upi@razorpay
```

2. Get Razorpay credentials:
   - Sign up at https://razorpay.com
   - Go to Dashboard → Settings → API Keys
   - Copy Key ID and Key Secret
   - For UPI ID, use your Razorpay UPI handle or merchant UPI ID

#### Start Backend Server
```bash
npm start
# or for development
npm run dev
```

### 2. Frontend Setup

#### Install Dependencies
```bash
cd frontend
npm install
```

#### Start Frontend Server
```bash
npm run dev
```

The frontend will run on `http://localhost:5173`

### 3. Python Detection System

#### Run the Detection Script
```bash
python main.py
```

## How It Works

### Flow Diagram
```
License Plate Detected (10 chars)
    ↓
Check Database
    ↓
    ├─→ Found? → 🚪 GATE OPEN (logged in terminal)
    │
    └─→ Not Found?
            ↓
        Create Payment Order
            ↓
        Generate QR Code
            ↓
        Open Payment Page (browser)
            ↓
        User Scans & Pays
            ↓
        Poll Payment Status (every 5s)
            ↓
        Payment Complete? → 🚪 GATE OPEN (logged in terminal)
```

### API Endpoints

#### Check Plate in Database
```
GET /api/numbers/check/:numberPlate
Response: { exists: true/false, message: "..." }
```

#### Create Payment
```
POST /api/numbers/payment/create
Body: { numberPlate: "MH12AB1234", amount: 50 }
Response: { orderId: "...", qrCodeUrl: "...", amount: 50 }
```

#### Check Payment Status
```
GET /api/numbers/payment/status/:orderId
Response: { status: "pending|completed|failed", payment: {...} }
```

#### Check Payment by Plate
```
GET /api/numbers/payment/plate/:numberPlate
Response: { paid: true/false, payment: {...} }
```

## Testing

### Test with Whitelisted Plate
1. Add a plate to database via API:
```bash
curl -X POST http://localhost:3000/api/numbers/numbers \
  -H "Content-Type: application/json" \
  -d '{"numberPlate": "MH12AB1234"}'
```

2. When this plate is detected → Gate opens immediately

### Test Payment Flow
1. Detect a plate NOT in database
2. Payment page opens automatically in browser
3. Scan QR code with UPI app
4. Complete payment
5. System detects payment → Gate opens

## Terminal Output Examples

### Plate Found in Database
```
[PROCESSING] Checking plate: MH12AB1234
✓ Plate found in database (whitelisted)
============================================================
🚪 GATE OPEN - 2024-01-15 14:30:25
   Plate: MH12AB1234
   Reason: Found in database
============================================================
```

### Payment Required
```
[PROCESSING] Checking plate: DL01AB2345
✗ Plate NOT found in database - Payment required

💳 PAYMENT REQUIRED
   Order ID: order_abc123xyz
   Amount: ₹50
   QR Code URL: https://...
   → Opened payment page in browser
   [Waiting for payment... 60s elapsed]
```

### Payment Successful
```
✓ Payment completed for DL01AB2345!
============================================================
🚪 GATE OPEN - 2024-01-15 14:32:10
   Plate: DL01AB2345
   Reason: Payment successful
============================================================
```

## Troubleshooting

### Payment Not Working
- Check Razorpay credentials in `.env` file
- Verify Razorpay account is activated
- Check backend logs for errors

### QR Code Not Showing
- Ensure frontend is running on port 5173
- Check browser console for errors
- Verify payment order was created successfully

### Gate Not Opening
- Check terminal for "GATE OPEN" message
- Verify payment status endpoint is working
- Check database connection

## Notes

- Payment polling runs for 5 minutes (60 attempts × 5 seconds)
- Each plate is processed only once per session
- Payment status is checked every 5 seconds
- Frontend payment page auto-closes after successful payment

