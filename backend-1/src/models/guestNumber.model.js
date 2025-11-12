const mongoose = require('mongoose');

const guestNumberSchema = new mongoose.Schema({
    numberPlate: {
        type: String,
        required: true
    },
    razorpayOrderId: {
        type: String,
        required: true
    },
    razorpayPaymentId: {
        type: String,
        default: null
    },
    amount: {
        type: Number,
        required: true
    },
    transactionId: {
        type: String,
        default: null
    },
    timestamp: {
        type: Date,
        default: Date.now
    },
    paidAt: {
        type: Date,
        default: null
    }
});

module.exports = mongoose.model('GuestNumber', guestNumberSchema);

