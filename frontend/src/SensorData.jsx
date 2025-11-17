import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

export default function SensorData() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const API_URL = `http://localhost:4000/api/sensor/data`;

    useEffect(() => {
        fetchList();
        // eslint-disable-next-line
    }, []);

    async function fetchList() {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(API_URL);
            if (!res.ok) throw new Error(`Server responded ${res.status}`);
            const data = await res.json();
            // Handle both direct array and wrapped response
            const sensorData = data.data || data;
            setItems(Array.isArray(sensorData) ? sensorData : []);
        } catch (err) {
            setError(err.message || "Failed to load sensor data");
        } finally {
            setLoading(false);
        }
    }

    function formatDate(ts) {
        try {
            return new Date(ts).toLocaleString(undefined, {
                year: "numeric",
                month: "short",
                day: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit"
            });
        } catch {
            return ts;
        }
    }

    function getTemperatureColor(temp) {
        if (temp >= 30) return "text-red-600";
        if (temp >= 25) return "text-orange-600";
        if (temp >= 20) return "text-green-600";
        return "text-blue-600";
    }

    function getHumidityColor(humidity) {
        if (humidity >= 70) return "text-blue-600";
        if (humidity >= 50) return "text-green-600";
        if (humidity >= 30) return "text-yellow-600";
        return "text-orange-600";
    }

    // Calculate statistics
    const stats = items.length > 0 ? {
        avgTemp: (items.reduce((sum, item) => sum + (item.temperature || 0), 0) / items.length).toFixed(2),
        avgHumidity: (items.reduce((sum, item) => sum + (item.humidity || 0), 0) / items.length).toFixed(2),
        maxTemp: Math.max(...items.map(item => item.temperature || 0)),
        minTemp: Math.min(...items.map(item => item.temperature || 0)),
        maxHumidity: Math.max(...items.map(item => item.humidity || 0)),
        minHumidity: Math.min(...items.map(item => item.humidity || 0))
    } : null;

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-100 to-green-50 px-4 py-8 font-sans text-gray-900">
            <div className="flex justify-between items-center mb-7">
                <div>
                    <div className="flex items-center gap-3 mb-2">
                        <Link
                            to="/"
                            className="text-gray-500 hover:text-gray-700 transition-colors"
                            title="Back to home"
                        >
                            ← Back
                        </Link>
                        <div className="text-2xl font-semibold tracking-tight text-gray-900">Sensor Data</div>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">Temperature and Humidity readings</div>
                </div>
                <button
                    className="bg-white border border-gray-200 px-4 py-2 rounded-xl shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-green-100 transition active:bg-gray-100 disabled:opacity-60"
                    onClick={fetchList}
                    disabled={loading}
                >
                    {loading ? "Loading…" : "Refresh"}
                </button>
            </div>

            {error && (
                <div className="bg-red-100 border border-red-200 rounded-xl px-4 py-3 mb-4 text-red-700 animate-in fade-in">
                    <strong>Error:</strong> {error}
                </div>
            )}

            {/* Statistics Cards */}
            {stats && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                    <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow border border-gray-100 p-4">
                        <div className="text-xs text-gray-500 mb-1">Average Temperature</div>
                        <div className="text-2xl font-bold text-orange-600">{stats.avgTemp}°C</div>
                        <div className="text-xs text-gray-400 mt-1">
                            Range: {stats.minTemp}°C - {stats.maxTemp}°C
                        </div>
                    </div>
                    <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow border border-gray-100 p-4">
                        <div className="text-xs text-gray-500 mb-1">Average Humidity</div>
                        <div className="text-2xl font-bold text-blue-600">{stats.avgHumidity}%</div>
                        <div className="text-xs text-gray-400 mt-1">
                            Range: {stats.minHumidity}% - {stats.maxHumidity}%
                        </div>
                    </div>
                    <div className="bg-white/80 backdrop-blur-sm rounded-xl shadow border border-gray-100 p-4">
                        <div className="text-xs text-gray-500 mb-1">Total Readings</div>
                        <div className="text-2xl font-bold text-gray-700">{items.length}</div>
                        <div className="text-xs text-gray-400 mt-1">Data points collected</div>
                    </div>
                </div>
            )}

            {/* Data Table */}
            <div className="overflow-x-auto rounded-2xl shadow border border-gray-100 bg-white/80 backdrop-blur-sm">
                <table className="min-w-full text-sm text-left">
                    <thead className="bg-gradient-to-b from-slate-50 to-slate-100/80">
                        <tr>
                            <th className="py-4 px-4 font-medium text-gray-500">Temperature (°C)</th>
                            <th className="py-4 px-4 font-medium text-gray-500">Humidity (%)</th>
                            <th className="py-4 px-4 font-medium text-gray-500">Timestamp</th>
                            <th className="py-4 px-4 font-medium text-gray-500">ID</th>
                        </tr>
                    </thead>
                    <tbody>
                        {loading ? (
                            <tr>
                                <td colSpan={4} className="text-center text-gray-400 py-8">
                                    <div className="flex items-center justify-center">
                                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-green-600 mr-2"></div>
                                        Loading sensor data...
                                    </div>
                                </td>
                            </tr>
                        ) : items.length === 0 ? (
                            <tr>
                                <td colSpan={4} className="text-center text-gray-400 py-8">
                                    No sensor data found. Click Refresh to try again.
                                </td>
                            </tr>
                        ) : (
                            items.map((it, idx) => (
                                <tr 
                                    key={it._id || `${it.temperature}-${it.humidity}-${it.timestamp}`}
                                    className="transition hover:bg-green-50/60 border-b border-gray-50"
                                >
                                    <td className="py-4 px-4">
                                        <span className={`font-semibold ${getTemperatureColor(it.temperature || 0)}`}>
                                            {it.temperature !== undefined ? `${it.temperature}°C` : "—"}
                                        </span>
                                    </td>
                                    <td className="py-4 px-4">
                                        <span className={`font-semibold ${getHumidityColor(it.humidity || 0)}`}>
                                            {it.humidity !== undefined ? `${it.humidity}%` : "—"}
                                        </span>
                                    </td>
                                    <td className="py-4 px-4 text-gray-500">{formatDate(it.timestamp)}</td>
                                    <td className="py-4 px-4 text-gray-300 font-mono text-xs">{it._id ? it._id.substring(0, 8) + "..." : "n/a"}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

