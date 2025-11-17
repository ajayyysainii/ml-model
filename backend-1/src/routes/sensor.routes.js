// This file defines the routes for sensor data (temperature and humidity)

const express = require('express');
const router = express.Router();
const SensorModel = require('../models/sensor.model');

// Route to create a new sensor data entry
router.post('/data', async (req, res) => {
    try {
        const { temperature, humidity } = req.body;
        
        // Validate required fields
        if (temperature === undefined || humidity === undefined) {
            return res.status(400).json({ 
                message: 'Temperature and humidity are required' 
            });
        }

        // Create new sensor data entry with timestamp
        // If timestamp is provided in request, use it; otherwise use current time
        const timestamp = req.body.timestamp ? new Date(req.body.timestamp) : Date.now();
        
        const sensorData = new SensorModel({
            temperature,
            humidity,
            timestamp: timestamp
        });

        await sensorData.save();
        
        res.status(201).json({
            success: true,
            data: sensorData,
            message: 'Sensor data saved successfully'
        });
    } catch (error) {
        res.status(500).json({ 
            success: false,
            message: error.message 
        });
    }
});

// Route to get all sensor data entries
router.get('/data', async (req, res) => {
    try {
        const sensorData = await SensorModel.find().sort({ timestamp: -1 });
        res.status(200).json({
            success: true,
            data: sensorData,
            count: sensorData.length
        });
    } catch (error) {
        res.status(500).json({ 
            success: false,
            message: error.message 
        });
    }
});

// Route to get latest sensor data entry
router.get('/data/latest', async (req, res) => {
    try {
        const latestData = await SensorModel.findOne().sort({ timestamp: -1 });
        if (!latestData) {
            return res.status(404).json({ 
                success: false,
                message: 'No sensor data found' 
            });
        }
        res.status(200).json({
            success: true,
            data: latestData
        });
    } catch (error) {
        res.status(500).json({ 
            success: false,
            message: error.message 
        });
    }
});

module.exports = router;

