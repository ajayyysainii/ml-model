import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function RegisterPlate() {
    const [numberPlate, setNumberPlate] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(false);
    const navigate = useNavigate();

    const API_URL = `http://localhost:4000/api/numbers/numbers`;

    function formatPlateNumber(value) {
        // Remove spaces and convert to uppercase
        return value.replace(/\s/g, "").toUpperCase();
    }

    async function handleSubmit(e) {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setSuccess(false);

        // Format the plate number
        const formattedPlate = formatPlateNumber(numberPlate);

        // Validate plate number (basic validation - adjust as needed)
        if (!formattedPlate || formattedPlate.length < 2) {
            setError("Please enter a valid number plate");
            setLoading(false);
            return;
        }

        try {
            const res = await fetch(API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    numberPlate: formattedPlate,
                }),
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.message || `Server responded ${res.status}`);
            }

            const data = await res.json();
            setSuccess(true);
            setNumberPlate(""); // Clear form

            // Show success message for 3 seconds, then optionally redirect
            setTimeout(() => {
                setSuccess(false);
                // Optionally navigate to registered plates page
                // navigate("/registered");
            }, 3000);
        } catch (err) {
            setError(err.message || "Failed to register plate");
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-100 to-blue-50 px-4 py-8 font-sans text-gray-900">
            <div className="max-w-2xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <div className="flex items-center gap-3 mb-2">
                        <button
                            onClick={() => navigate("/")}
                            className="text-gray-500 hover:text-gray-700 transition-colors"
                            title="Back to home"
                        >
                            ← Back
                        </button>
                        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Register Number Plate</h1>
                    </div>
                    <p className="text-sm text-gray-500 mt-1">
                        Add a new number plate to the whitelist (registered plates don't require payment)
                    </p>
                </div>

                {/* Success Message */}
                {success && (
                    <div className="bg-green-100 border border-green-200 rounded-xl px-4 py-3 mb-6 text-green-700 animate-in fade-in">
                        <div className="flex items-center gap-2">
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path
                                    fillRule="evenodd"
                                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                                    clipRule="evenodd"
                                />
                            </svg>
                            <span className="font-medium">Number plate registered successfully!</span>
                        </div>
                    </div>
                )}

                {/* Error Message */}
                {error && (
                    <div className="bg-red-100 border border-red-200 rounded-xl px-4 py-3 mb-6 text-red-700 animate-in fade-in">
                        <div className="flex items-center gap-2">
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path
                                    fillRule="evenodd"
                                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                                    clipRule="evenodd"
                                />
                            </svg>
                            <span className="font-medium">Error: {error}</span>
                        </div>
                    </div>
                )}

                {/* Registration Form */}
                <div className="bg-white/80 backdrop-blur-sm rounded-2xl shadow border border-gray-100 p-8">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div>
                            <label htmlFor="numberPlate" className="block text-sm font-medium text-gray-700 mb-2">
                                Number Plate
                            </label>
                            <input
                                type="text"
                                id="numberPlate"
                                value={numberPlate}
                                onChange={(e) => {
                                    const formatted = formatPlateNumber(e.target.value);
                                    setNumberPlate(formatted);
                                }}
                                placeholder="e.g., MH20EE7602"
                                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition text-lg font-semibold tracking-wider uppercase"
                                maxLength={20}
                                disabled={loading}
                                required
                            />
                            <p className="mt-2 text-xs text-gray-500">
                                Enter the vehicle number plate (will be automatically converted to uppercase)
                            </p>
                        </div>

                        <div className="flex gap-4">
                            <button
                                type="submit"
                                disabled={loading || !numberPlate.trim()}
                                className="flex-1 bg-blue-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
                            >
                                {loading ? (
                                    <span className="flex items-center justify-center gap-2">
                                        <svg
                                            className="animate-spin h-5 w-5"
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                        >
                                            <circle
                                                className="opacity-25"
                                                cx="12"
                                                cy="12"
                                                r="10"
                                                stroke="currentColor"
                                                strokeWidth="4"
                                            ></circle>
                                            <path
                                                className="opacity-75"
                                                fill="currentColor"
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                                            ></path>
                                        </svg>
                                        Registering...
                                    </span>
                                ) : (
                                    "Register Plate"
                                )}
                            </button>
                            <button
                                type="button"
                                onClick={() => navigate("/registered")}
                                className="px-6 py-3 border border-gray-300 rounded-xl font-medium text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition"
                            >
                                View All Plates
                            </button>
                        </div>
                    </form>
                </div>

                {/* Info Section */}
                <div className="mt-8 bg-blue-50 border border-blue-200 rounded-xl p-6">
                    <h3 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path
                                fillRule="evenodd"
                                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                                clipRule="evenodd"
                            />
                        </svg>
                        About Registered Plates
                    </h3>
                    <ul className="text-sm text-blue-800 space-y-2">
                        <li>• Registered plates are whitelisted and don't require payment</li>
                        <li>• The gate will automatically open when a registered plate is detected</li>
                        <li>• Plates are automatically converted to uppercase</li>
                        <li>• You can view all registered plates in the "Registered Plates" section</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}

