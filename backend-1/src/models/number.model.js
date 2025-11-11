const mongoose = require('mongoose');

const numberSchema = new mongoose.Schema({
    numberPlate: {
        type: String,
        required: true
    },
    timestamp: {
        type: Date,
        default: Date.now
    }
});

module.exports = mongoose.model('Number', numberSchema);