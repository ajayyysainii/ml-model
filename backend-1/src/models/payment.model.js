const mongoose = require('mongoose');

const paymentSchema = new mongoose.Schema({
    numberPlate: {
        type: String,
        required: true
    },
    razorpayOrderId: {
        type: String,
        required: true,
        unique: true
    },
    razorpayPaymentId: {
        type: String,
        default: null
    },
    amount: {
        type: Number,
        required: true,
        default: 50 // Default parking fee in rupees
    },
    status: {
        type: String,
        enum: ['pending', 'completed', 'failed'],
        default: 'pending'
    },
    qrCodeUrl: {
        type: String,
        default: null
    },
    paymentUrl: {
        type: String,
        default: null
    },
    razorpayPaymentLinkId: {
        type: String,
        default: null
    },
    createdAt: {
        type: Date,
        default: Date.now
    },
    paidAt: {
        type: Date,
        default: null
    }
});

module.exports = mongoose.model('Payment', paymentSchema);

