// File: /backend/src/index.js

require('dotenv').config();
const express = require('express');
const bodyParser = require('body-parser');
const mongoose = require('mongoose');
const numberRoutes = require('./routes/index');
const sensorRoutes = require('./routes/sensor.routes');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 4000;

// MongoDB Connection (from environment variables)
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb+srv://ajaysaini:ajaysaini@sahyog.2z6va4e.mongodb.net/softcomputing';
mongoose.connect(MONGODB_URI, {
    useNewUrlParser: true,
    useUnifiedTopology: true
});

app.use(cors());

// Middleware
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Routes
app.use('/api/numbers', numberRoutes);
app.use('/api/sensor', sensorRoutes);

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something went wrong!' });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({ error: 'Route not found' });
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});