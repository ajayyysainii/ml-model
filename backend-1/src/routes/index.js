// This file defines the routes for the application, handling requests related to the number model.

const express = require('express');
const router = express.Router();
const NumberModel = require('../models/number.model'); // This will be used for registered plates
const GuestNumberModel = require('../models/guestNumber.model'); // For guest plates with payment
const PaymentModel = require('../models/payment.model');
const Razorpay = require('razorpay');
const QRCode = require('qrcode');
require('dotenv').config();

// Initialize Razorpay (use environment variables or defaults for testing)
const razorpayKeyId = process.env.RAZORPAY_KEY_ID || 'rzp_test_1234567890';
const razorpayKeySecret = process.env.RAZORPAY_KEY_SECRET || 'your_secret_key';

// Validate Razorpay credentials
if (!razorpayKeyId || razorpayKeyId === 'rzp_test_1234567890' || 
    !razorpayKeySecret || razorpayKeySecret === 'your_secret_key') {
    console.warn('⚠️  WARNING: Razorpay credentials not properly configured!');
    console.warn('   Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in your .env file');
    console.warn('   Get your keys from: https://dashboard.razorpay.com/app/keys');
}

const razorpay = new Razorpay({
    key_id: razorpayKeyId,
    key_secret: razorpayKeySecret
});

// Route to create a new registered number entry
router.post('/numbers', async (req, res) => {
    try {
        const { numberPlate, timestamp } = req.body;
        const newNumber = new NumberModel({ numberPlate, timestamp });
        await newNumber.save();
        res.status(201).json(newNumber);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Route to get all registered number entries
router.get('/numbers', async (req, res) => {
    try {
        const numbers = await NumberModel.find().sort({ timestamp: -1 });
        res.status(200).json(numbers);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Route to get all registered number plates
router.get('/registered', async (req, res) => {
    try {
        const numbers = await NumberModel.find().sort({ timestamp: -1 });
        res.status(200).json(numbers);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Route to get all guest number plates (with payment data)
router.get('/guests', async (req, res) => {
    try {
        const guests = await GuestNumberModel.find().sort({ timestamp: -1 });
        res.status(200).json(guests);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Route to get a number entry by ID
router.get('/numbers/:id', async (req, res) => {
    try {
        const number = await NumberModel.findById(req.params.id);
        if (!number) {
            return res.status(404).json({ message: 'Number not found' });
        }
        res.status(200).json(number);
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Route to delete a number entry by ID
router.delete('/numbers/:id', async (req, res) => {
    try {
        const number = await NumberModel.findByIdAndDelete(req.params.id);
        if (!number) {
            return res.status(404).json({ message: 'Number not found' });
        }
        res.status(204).send();
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Route to check if license plate exists in database (registered/whitelisted)
router.get('/check/:numberPlate', async (req, res) => {
    try {
        const { numberPlate } = req.params;
        const plate = await NumberModel.findOne({ numberPlate: numberPlate.toUpperCase() });
        
        if (plate) {
            // Trigger gate/servo when plate is found in database
            gateTriggerFlag = true;
            gateTriggerTimestamp = new Date();
            gateTriggerPlate = numberPlate.toUpperCase();
            gateTriggerExpiry = new Date(Date.now() + 10000); // Expires in 10 seconds
            
            console.log(`[GATE TRIGGER] ✓ Plate found in database - Gate trigger activated for: ${gateTriggerPlate}`);
            console.log(`[GATE TRIGGER]   Trigger will expire at: ${gateTriggerExpiry.toISOString()}`);
            
            res.status(200).json({ 
                exists: true, 
                message: 'Plate found in database',
                plate: plate
            });
        } else {
            res.status(200).json({ 
                exists: false, 
                message: 'Plate not found in database - payment required'
            });
        }
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Route to create payment order and QR code
router.post('/payment/create', async (req, res) => {
    try {
        const { numberPlate, amount = 50 } = req.body;
        
        if (!numberPlate || numberPlate.length !== 10) {
            return res.status(400).json({ message: 'Invalid number plate (must be 10 characters)' });
        }

        // Check if there's a pending payment for this plate
        const existingPayment = await PaymentModel.findOne({ 
            numberPlate: numberPlate.toUpperCase(), 
            status: 'pending' 
        });

        if (existingPayment) {
            // If QR code exists, return it; otherwise regenerate if payment URL exists
            let qrCodeDataUrl = existingPayment.qrCodeUrl;
            if (!qrCodeDataUrl && existingPayment.paymentUrl) {
                try {
                    qrCodeDataUrl = await QRCode.toDataURL(existingPayment.paymentUrl, {
                        width: 300,
                        margin: 2
                    });
                } catch (err) {
                    console.error('QR regeneration error:', err);
                }
            }
            
            return res.status(200).json({
                orderId: existingPayment.razorpayOrderId,
                qrCodeUrl: qrCodeDataUrl,
                paymentUrl: existingPayment.paymentUrl,
                amount: existingPayment.amount,
                message: 'Existing pending payment found'
            });
        }

        // Validate Razorpay credentials before creating order
        if (!razorpayKeyId || razorpayKeyId === 'rzp_test_1234567890' || 
            !razorpayKeySecret || razorpayKeySecret === 'your_secret_key') {
            return res.status(500).json({ 
                message: 'Razorpay credentials not configured. Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env file',
                error: 'RAZORPAY_CONFIG_MISSING'
            });
        }

        // Create Razorpay order
        const orderOptions = {
            amount: amount * 100, // Convert to paise
            currency: 'INR',
            receipt: `plate_${numberPlate}_${Date.now()}`,
            notes: {
                numberPlate: numberPlate.toUpperCase()
            }
        };

        let order;
        try {
            order = await razorpay.orders.create(orderOptions);
        } catch (razorpayError) {
            console.error('Razorpay order creation error:', razorpayError);
            
            // Check if it's an authentication error
            if (razorpayError.statusCode === 401 || 
                (razorpayError.error && razorpayError.error.code === 'BAD_REQUEST_ERROR')) {
                return res.status(401).json({ 
                    message: 'Razorpay authentication failed. Please check your RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env file',
                    error: 'RAZORPAY_AUTH_FAILED',
                    details: razorpayError.error || razorpayError.message
                });
            }
            
            // Re-throw other errors to be caught by outer catch
            throw razorpayError;
        }

        // Create payment URL - use Razorpay checkout or payment link
        const frontendUrl = process.env.FRONTEND_URL || 'http://localhost:5173';
        const callbackUrl = `${frontendUrl}/payment?orderId=${order.id}&plate=${encodeURIComponent(numberPlate.toUpperCase())}`;
        
        // Try to create Razorpay payment link first
        let paymentLinkUrl;
        let paymentLinkId = null;
        try {
            const paymentLink = await razorpay.paymentLink.create({
                amount: amount * 100,
                currency: 'INR',
                description: `Parking fee for ${numberPlate.toUpperCase()}`,
                customer: {
                    name: `Vehicle ${numberPlate.toUpperCase()}`,
                },
                notify: {
                    sms: false,
                    email: false
                },
                reminder_enable: false,
                callback_url: callbackUrl,
                callback_method: 'get'
            });
            paymentLinkUrl = paymentLink.short_url || paymentLink.url || paymentLink.hosted_page?.url;
            paymentLinkId = paymentLink.id;
            console.log('Payment link created:', paymentLinkUrl);
            console.log('Payment link ID:', paymentLinkId);
        } catch (linkError) {
            console.error('Payment link creation error:', linkError.message || linkError);
            // Fallback: Create a Razorpay checkout URL
            const keyId = process.env.RAZORPAY_KEY_ID || 'rzp_test_1234567890';
            paymentLinkUrl = `https://checkout.razorpay.com/v1/checkout.js?key=${keyId}&order_id=${order.id}`;
            console.log('Using fallback checkout URL:', paymentLinkUrl);
        }

        // Generate QR code using qrcode npm package
        // QR code will contain the Razorpay payment link URL
        // When scanned, user will be taken to Razorpay payment page
        let qrCodeDataUrl;
        
        try {
            // Ensure payment link URL is valid
            if (!paymentLinkUrl || paymentLinkUrl.length > 2000) {
                throw new Error('Invalid payment link URL');
            }
            
            // Generate QR code with Razorpay payment link
            // This will open Razorpay payment page when scanned
            qrCodeDataUrl = await QRCode.toDataURL(paymentLinkUrl, {
                width: 300,
                margin: 2,
                errorCorrectionLevel: 'H', // High error correction for better scanning
                color: {
                    dark: '#000000',
                    light: '#FFFFFF'
                }
            });
            
            console.log('QR code generated successfully, length:', qrCodeDataUrl.length);
            console.log('QR code contains Razorpay payment link:', paymentLinkUrl);
        } catch (qrError) {
            console.error('QR code generation error:', qrError.message || qrError);
            qrCodeDataUrl = null;
        }

        // Save payment record
        const payment = new PaymentModel({
            numberPlate: numberPlate.toUpperCase(),
            razorpayOrderId: order.id,
            razorpayPaymentLinkId: paymentLinkId, // Store payment link ID
            amount: amount,
            qrCodeUrl: qrCodeDataUrl, // Store as data URL
            paymentUrl: paymentLinkUrl, // Razorpay payment link
            status: 'pending'
        });

        await payment.save();

        // Prepare response
        const response = {
            orderId: order.id,
            qrCodeUrl: qrCodeDataUrl, // Base64 data URL (data:image/png;base64,...)
            paymentUrl: paymentLinkUrl, // Direct Razorpay payment link
            amount: amount,
            numberPlate: numberPlate.toUpperCase(),
            message: 'Payment order created successfully'
        };
        
        // Log for debugging
        if (qrCodeDataUrl) {
            console.log('QR code data URL starts with:', qrCodeDataUrl.substring(0, 50));
            console.log('QR code data URL length:', qrCodeDataUrl.length);
        } else {
            console.warn('WARNING: QR code was not generated!');
        }
        
        res.status(201).json(response);
    } catch (error) {
        console.error('Payment creation error:', error);
        
        // Provide more specific error messages
        if (error.statusCode === 401 || (error.error && error.error.code === 'BAD_REQUEST_ERROR')) {
            return res.status(401).json({ 
                message: 'Razorpay authentication failed. Please check your credentials in .env file',
                error: 'RAZORPAY_AUTH_FAILED',
                details: error.error || error.message
            });
        }
        
        res.status(500).json({ 
            message: error.message || 'Failed to create payment',
            error: error.name || 'UNKNOWN_ERROR'
        });
    }
});

// Helper function to save number plate to guest collection after payment
async function saveGuestNumberPlateAfterPayment(payment) {
    try {
        const plateUpper = payment.numberPlate.toUpperCase();
        // Check if guest plate already exists
        const existingGuest = await GuestNumberModel.findOne({ 
            numberPlate: plateUpper,
            razorpayOrderId: payment.razorpayOrderId
        });
        
        if (!existingGuest) {
            const guestNumber = new GuestNumberModel({
                numberPlate: plateUpper,
                razorpayOrderId: payment.razorpayOrderId,
                razorpayPaymentId: payment.razorpayPaymentId || null,
                amount: payment.amount,
                transactionId: payment.razorpayPaymentId || payment.razorpayOrderId,
                paidAt: payment.paidAt || new Date(),
                timestamp: new Date()
            });
            await guestNumber.save();
            console.log(`✓ Guest number plate ${plateUpper} saved to guest database after payment`);
            return true;
        } else {
            console.log(`ℹ Guest number plate ${plateUpper} already exists in guest database`);
            return true; // Return true even if exists, as it's already saved
        }
    } catch (error) {
        console.error(`✗ Error saving guest number plate ${payment.numberPlate}:`, error.message || error);
        return false;
    }
}

// Route to verify payment status
router.get('/payment/status/:orderId', async (req, res) => {
    try {
        const { orderId } = req.params;
        
        const payment = await PaymentModel.findOne({ razorpayOrderId: orderId });
        
        if (!payment) {
            return res.status(404).json({ message: 'Payment not found' });
        }

        // If already completed, return immediately with saved plate info
        if (payment.status === 'completed') {
            return res.status(200).json({
                status: 'completed',
                payment: payment,
                message: 'Payment completed'
            });
        }

        // Check with Razorpay API - try multiple methods
        try {
            console.log(`Checking payment status for order: ${orderId}`);
            
            // Method 1: Check order payments
            const order = await razorpay.orders.fetch(orderId);
            console.log('Order status:', order.status);
            
            const payments = await razorpay.orders.fetchPayments(orderId);
            console.log('Payments found:', payments.items?.length || 0);
            
            if (payments.items && payments.items.length > 0) {
                const latestPayment = payments.items[0];
                console.log('Latest payment status:', latestPayment.status);
                console.log('Latest payment ID:', latestPayment.id);
                
                if (latestPayment.status === 'captured' || latestPayment.status === 'authorized') {
                    // Update payment status
                    payment.status = 'completed';
                    payment.razorpayPaymentId = latestPayment.id;
                    payment.paidAt = new Date();
                    await payment.save();
                    console.log(`✓ Payment status updated to completed`);
                    
                    // Save number plate to guest database after successful payment
                    const saved = await saveGuestNumberPlateAfterPayment(payment);
                    console.log(`✓ Payment verified via order payments. Plate saved: ${saved}`);
                    
                    return res.status(200).json({
                        status: 'completed',
                        payment: payment,
                        message: 'Payment successful'
                    });
                } else {
                    console.log(`ℹ Payment status is: ${latestPayment.status} (not captured/authorized yet)`);
                }
            } else {
                console.log('ℹ No payments found for this order yet');
            }
            
            // Method 2: Check order status directly
            if (order.status === 'paid') {
                console.log('Order is marked as paid');
                payment.status = 'completed';
                payment.paidAt = new Date();
                await payment.save();
                
                const saved = await saveGuestNumberPlateAfterPayment(payment);
                console.log(`✓ Payment verified via order status. Plate saved: ${saved}`);
                
                return res.status(200).json({
                    status: 'completed',
                    payment: payment,
                    message: 'Payment successful'
                });
            }
            
            // Method 3: If payment link was used, check payment link status
            if (payment.razorpayPaymentLinkId) {
                try {
                    console.log(`Checking payment link: ${payment.razorpayPaymentLinkId}`);
                    const paymentLink = await razorpay.paymentLink.fetch(payment.razorpayPaymentLinkId);
                    console.log('Payment link status:', paymentLink.status);
                    console.log('Payment link payments:', paymentLink.payments?.length || 0);
                    
                    if (paymentLink.status === 'paid' && paymentLink.payments && paymentLink.payments.length > 0) {
                        const latestPayment = paymentLink.payments[0];
                        console.log('Payment link payment ID:', latestPayment.id);
                        console.log('Payment link payment status:', latestPayment.status);
                        
                        if (latestPayment.status === 'captured' || latestPayment.status === 'authorized') {
                            payment.status = 'completed';
                            payment.razorpayPaymentId = latestPayment.id;
                            payment.paidAt = new Date();
                            await payment.save();
                            
                            const saved = await saveGuestNumberPlateAfterPayment(payment);
                            console.log(`✓ Payment verified via payment link. Plate saved: ${saved}`);
                            
                            return res.status(200).json({
                                status: 'completed',
                                payment: payment,
                                message: 'Payment successful'
                            });
                        }
                    }
                } catch (linkError) {
                    console.error('Payment link check error:', linkError.message || linkError);
                }
            }
            
            // Method 4: Search all payments by amount and number plate (fallback)
            if (!payment.razorpayPaymentId) {
                try {
                    console.log('Searching payments by amount and metadata...');
                    // Get all payments and filter by amount
                    const allPayments = await razorpay.payments.all({
                        count: 100
                    });
                    
                    // Find payment matching our order amount and timestamp
                    const matchingPayment = allPayments.items.find(p => {
                        return p.amount === (amount * 100) && 
                               p.status === 'captured' &&
                               new Date(p.created_at * 1000) > new Date(payment.createdAt) - 60000; // Within 1 minute of creation
                    });
                    
                    if (matchingPayment) {
                        console.log('Found matching payment:', matchingPayment.id);
                        payment.status = 'completed';
                        payment.razorpayPaymentId = matchingPayment.id;
                        payment.paidAt = new Date();
                        await payment.save();
                        
                        const saved = await saveGuestNumberPlateAfterPayment(payment);
                        console.log(`✓ Payment verified via payment search. Plate saved: ${saved}`);
                        
                        return res.status(200).json({
                            status: 'completed',
                            payment: payment,
                            message: 'Payment successful'
                        });
                    }
                } catch (searchError) {
                    console.error('Payment search error:', searchError.message || searchError);
                }
            }
        } catch (razorpayError) {
            console.error('✗ Razorpay API error:', razorpayError.message || razorpayError);
            if (razorpayError.error) {
                console.error('Razorpay error details:', JSON.stringify(razorpayError.error, null, 2));
            }
        }

        res.status(200).json({
            status: payment.status,
            payment: payment,
            message: payment.status === 'completed' ? 'Payment completed' : 'Payment pending'
        });
    } catch (error) {
        console.error('Payment status check error:', error);
        res.status(500).json({ message: error.message });
    }
});

// Route to verify payment by number plate
router.get('/payment/plate/:numberPlate', async (req, res) => {
    try {
        const { numberPlate } = req.params;
        
        const payment = await PaymentModel.findOne({ 
            numberPlate: numberPlate.toUpperCase(),
            status: 'completed'
        }).sort({ paidAt: -1 }); // Get latest completed payment
        
        if (payment) {
            res.status(200).json({
                paid: true,
                payment: payment,
                message: 'Payment found and verified'
            });
        } else {
            res.status(200).json({
                paid: false,
                message: 'No completed payment found for this plate'
            });
        }
    } catch (error) {
        res.status(500).json({ message: error.message });
    }
});

// Razorpay webhook endpoint to handle payment events
router.post('/payment/webhook', async (req, res) => {
    try {
        console.log('\n=== WEBHOOK RECEIVED ===');
        console.log('Headers:', JSON.stringify(req.headers, null, 2));
        console.log('Body:', JSON.stringify(req.body, null, 2));
        
        const crypto = require('crypto');
        const webhookSecret = process.env.RAZORPAY_WEBHOOK_SECRET || '';
        
        const signature = req.headers['x-razorpay-signature'];
        const body = JSON.stringify(req.body);
        
        // Verify webhook signature (optional but recommended for production)
        if (webhookSecret && signature) {
            const expectedSignature = crypto
                .createHmac('sha256', webhookSecret)
                .update(body)
                .digest('hex');
            
            if (signature !== expectedSignature) {
                console.error('✗ Webhook signature verification failed');
                console.error('Expected:', expectedSignature);
                console.error('Received:', signature);
                return res.status(400).json({ message: 'Invalid signature' });
            }
            console.log('✓ Webhook signature verified');
        } else {
            console.log('⚠ Webhook signature verification skipped (no secret configured)');
        }
        
        const event = req.body;
        
        // Handle payment events
        console.log('Event type:', event.event);
        console.log('Full event structure:', JSON.stringify(event, null, 2));
        
        // Handle payment.captured event
        if (event.event === 'payment.captured' || event.event === 'order.paid' || event.event === 'payment_link.paid') {
            let orderId = null;
            let paymentId = null;
            let paymentLinkId = null;
            
            // Extract order ID, payment ID, and payment link ID from different event structures
            if (event.payload?.payment?.entity) {
                orderId = event.payload.payment.entity.order_id;
                paymentId = event.payload.payment.entity.id;
                paymentLinkId = event.payload.payment.entity.payment_link_id;
                console.log('Extracted from payment.entity:', { orderId, paymentId, paymentLinkId });
            } else if (event.payload?.payment) {
                orderId = event.payload.payment.order_id;
                paymentId = event.payload.payment.id;
                paymentLinkId = event.payload.payment.payment_link_id;
                console.log('Extracted from payment:', { orderId, paymentId, paymentLinkId });
            } else if (event.payload?.payment_link?.entity) {
                paymentLinkId = event.payload.payment_link.entity.id;
                paymentId = event.payload.payment_link.entity.payments?.[0]?.id;
                console.log('Extracted from payment_link.entity:', { paymentLinkId, paymentId });
            } else if (event.payload?.order?.entity) {
                orderId = event.payload.order.entity.id;
                console.log('Extracted from order.entity:', { orderId });
            } else if (event.payload?.order_id) {
                orderId = event.payload.order_id;
                console.log('Extracted from order_id:', { orderId });
            } else {
                console.log('⚠ Could not extract IDs. Full payload:', JSON.stringify(event.payload, null, 2));
            }
            
            // Try to find payment by order ID first
            let payment = null;
            if (orderId) {
                console.log(`Looking for payment with order ID: ${orderId}`);
                payment = await PaymentModel.findOne({ razorpayOrderId: orderId });
            }
            
            // If not found by order ID, try payment link ID
            if (!payment && paymentLinkId) {
                console.log(`Looking for payment with payment link ID: ${paymentLinkId}`);
                payment = await PaymentModel.findOne({ razorpayPaymentLinkId: paymentLinkId });
            }
            
            // If still not found, try to find by payment ID (if we have it)
            if (!payment && paymentId) {
                console.log(`Looking for payment with payment ID: ${paymentId}`);
                payment = await PaymentModel.findOne({ razorpayPaymentId: paymentId });
            }
            
            if (payment) {
                console.log(`Found payment record: ${payment.numberPlate}, Status: ${payment.status}`);
                
                if (payment.status !== 'completed') {
                    // Update payment status
                    payment.status = 'completed';
                    if (paymentId) {
                        payment.razorpayPaymentId = paymentId;
                    }
                    if (paymentLinkId && !payment.razorpayPaymentLinkId) {
                        payment.razorpayPaymentLinkId = paymentLinkId;
                    }
                    payment.paidAt = new Date();
                    await payment.save();
                    console.log(`✓ Payment status updated to completed`);
                    
                    // Save number plate to guest database after successful payment
                    const saved = await saveGuestNumberPlateAfterPayment(payment);
                    console.log(`✓ Payment webhook: Payment completed for ${payment.numberPlate}. Plate saved: ${saved}`);
                    console.log('=== WEBHOOK PROCESSED SUCCESSFULLY ===\n');
                } else {
                    console.log(`ℹ Payment already marked as completed`);
                }
            } else {
                console.log(`⚠ Webhook: Payment record not found`);
                console.log(`  Searched with: orderId=${orderId}, paymentLinkId=${paymentLinkId}, paymentId=${paymentId}`);
            }
        } else {
            console.log(`ℹ Webhook event '${event.event}' is not a payment completion event`);
        }
        
        res.status(200).json({ received: true, message: 'Webhook processed' });
    } catch (error) {
        console.error('✗ Webhook error:', error);
        console.error('Error stack:', error.stack);
        res.status(500).json({ message: error.message });
    }
});

// Manual payment verification endpoint (for testing/debugging)
router.post('/payment/verify/:orderId', async (req, res) => {
    try {
        const { orderId } = req.params;
        console.log(`\n=== MANUAL PAYMENT VERIFICATION ===`);
        console.log(`Order ID: ${orderId}`);
        
        const payment = await PaymentModel.findOne({ razorpayOrderId: orderId });
        
        if (!payment) {
            return res.status(404).json({ message: 'Payment not found' });
        }
        
        console.log(`Current payment status: ${payment.status}`);
        console.log(`Number plate: ${payment.numberPlate}`);
        
        // Force check with Razorpay - try multiple methods
        try {
            // Method 1: Check payment link if available
            if (payment.razorpayPaymentLinkId) {
                try {
                    console.log(`Checking payment link: ${payment.razorpayPaymentLinkId}`);
                    const paymentLink = await razorpay.paymentLink.fetch(payment.razorpayPaymentLinkId);
                    console.log(`Payment link status: ${paymentLink.status}`);
                    
                    if (paymentLink.status === 'paid' && paymentLink.payments && paymentLink.payments.length > 0) {
                        const latestPayment = paymentLink.payments[0];
                        if (latestPayment.status === 'captured' || latestPayment.status === 'authorized') {
                            if (payment.status !== 'completed') {
                                payment.status = 'completed';
                                payment.razorpayPaymentId = latestPayment.id;
                                payment.paidAt = new Date();
                                await payment.save();
                                
                                const saved = await saveGuestNumberPlateAfterPayment(payment);
                                console.log(`✓ Payment verified via payment link. Plate saved: ${saved}`);
                                
                                return res.status(200).json({
                                    success: true,
                                    status: 'completed',
                                    payment: payment,
                                    message: 'Payment verified and plate saved'
                                });
                            } else {
                                return res.status(200).json({
                                    success: true,
                                    status: 'completed',
                                    payment: payment,
                                    message: 'Payment already verified'
                                });
                            }
                        }
                    }
                } catch (linkError) {
                    console.error('Payment link check error:', linkError.message || linkError);
                }
            }
            
            // Method 2: Check order payments
            const order = await razorpay.orders.fetch(orderId);
            const payments = await razorpay.orders.fetchPayments(orderId);
            
            console.log(`Razorpay order status: ${order.status}`);
            console.log(`Payments count: ${payments.items?.length || 0}`);
            
            if (payments.items && payments.items.length > 0) {
                const latestPayment = payments.items[0];
                console.log(`Latest payment status: ${latestPayment.status}`);
                
                if (latestPayment.status === 'captured' || latestPayment.status === 'authorized' || order.status === 'paid') {
                    if (payment.status !== 'completed') {
                        payment.status = 'completed';
                        payment.razorpayPaymentId = latestPayment.id;
                        payment.paidAt = new Date();
                        await payment.save();
                        
                        const saved = await saveGuestNumberPlateAfterPayment(payment);
                        console.log(`✓ Payment verified and plate saved: ${saved}`);
                        
                        return res.status(200).json({
                            success: true,
                            status: 'completed',
                            payment: payment,
                            message: 'Payment verified and plate saved'
                        });
                    } else {
                        return res.status(200).json({
                            success: true,
                            status: 'completed',
                            payment: payment,
                            message: 'Payment already verified'
                        });
                    }
                }
            }
            
            return res.status(200).json({
                success: false,
                status: payment.status,
                orderStatus: order.status,
                payments: payments.items?.length || 0,
                paymentLinkId: payment.razorpayPaymentLinkId,
                message: 'Payment not yet completed'
            });
        } catch (error) {
            console.error('Verification error:', error);
            return res.status(500).json({ 
                success: false,
                message: error.message 
            });
        }
    } catch (error) {
        console.error('Manual verification error:', error);
        res.status(500).json({ message: error.message });
    }
});

// Gate trigger mechanism - simple flag that gets set when plate is detected
// Raspberry Pi polls this endpoint to check if gate should open
let gateTriggerFlag = false;
let gateTriggerTimestamp = null;
let gateTriggerPlate = null;
let gateTriggerExpiry = null; // When the trigger expires (10 seconds after being set)

// Route to trigger gate (called by main.py when registered plate detected or payment verified)
router.post('/trigger-gate', async (req, res) => {
    try {
        const { numberPlate, reason } = req.body;
        
        // Set trigger flag with 10 second expiry (gives Raspberry Pi time to poll)
        gateTriggerFlag = true;
        gateTriggerTimestamp = new Date();
        gateTriggerPlate = numberPlate || 'UNKNOWN';
        gateTriggerExpiry = new Date(Date.now() + 10000); // Expires in 10 seconds
        
        console.log(`[GATE TRIGGER] ✓ Gate trigger ACTIVATED for plate: ${gateTriggerPlate}, Reason: ${reason || 'N/A'}`);
        console.log(`[GATE TRIGGER]   Trigger will expire at: ${gateTriggerExpiry.toISOString()}`);
        
        res.status(200).json({
            success: true,
            message: 'Gate trigger activated',
            plate: gateTriggerPlate,
            timestamp: gateTriggerTimestamp,
            expiresAt: gateTriggerExpiry
        });
    } catch (error) {
        console.error('Gate trigger error:', error);
        res.status(500).json({ message: error.message });
    }
});

// Route to check gate trigger status (polled by Raspberry Pi)
router.get('/trigger-gate', async (req, res) => {
    try {
        const now = new Date();
        
        // Check if trigger has expired
        if (gateTriggerFlag && gateTriggerExpiry && now > gateTriggerExpiry) {
            console.log(`[GATE TRIGGER] Trigger expired for plate: ${gateTriggerPlate}`);
            gateTriggerFlag = false;
            gateTriggerTimestamp = null;
            gateTriggerPlate = null;
            gateTriggerExpiry = null;
        }
        
        if (gateTriggerFlag) {
            // Return trigger status and clear it (one-time trigger)
            const response = {
                triggered: true,
                message: 'Gate should open',
                plate: gateTriggerPlate,
                timestamp: gateTriggerTimestamp,
                expiresAt: gateTriggerExpiry
            };
            
            // Clear the flag after reading (one-time trigger)
            gateTriggerFlag = false;
            gateTriggerTimestamp = null;
            gateTriggerPlate = null;
            gateTriggerExpiry = null;
            
            console.log(`[GATE TRIGGER] ✓ Trigger READ by Raspberry Pi for plate: ${response.plate}`);
            
            res.status(200).json(response);
        } else {
            // No trigger active
            res.status(200).json({
                triggered: false,
                message: 'No gate trigger active'
            });
        }
    } catch (error) {
        console.error('Gate trigger check error:', error);
        res.status(500).json({ message: error.message });
    }
});

module.exports = router;