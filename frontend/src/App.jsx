import React, { useState } from "react";
import RegisteredPlates from "./RegisteredPlates";
import GuestPlates from "./GuestPlates";

export default function App() {
    const [activeTab, setActiveTab] = useState("registered");

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-100 to-blue-50 font-sans text-gray-900">
            <div className="px-4 py-6">
                <div className="mb-6">
                    <h1 className="text-3xl font-bold tracking-tight text-gray-900 mb-2">License Plate Management</h1>
                    <p className="text-sm text-gray-500">View registered and guest number plates</p>
                </div>
                
                {/* Tab Navigation */}
                <div className="flex space-x-2 mb-6 border-b border-gray-200">
                    <button
                        onClick={() => setActiveTab("registered")}
                        className={`px-6 py-3 font-medium text-sm transition-colors ${
                            activeTab === "registered"
                                ? "text-blue-600 border-b-2 border-blue-600"
                                : "text-gray-500 hover:text-gray-700"
                        }`}
                    >
                        Registered Plates
                    </button>
                    <button
                        onClick={() => setActiveTab("guests")}
                        className={`px-6 py-3 font-medium text-sm transition-colors ${
                            activeTab === "guests"
                                ? "text-purple-600 border-b-2 border-purple-600"
                                : "text-gray-500 hover:text-gray-700"
                        }`}
                    >
                        Guest Plates
                    </button>
                </div>

                {/* Tab Content */}
                <div>
                    {activeTab === "registered" ? <RegisteredPlates /> : <GuestPlates />}
                </div>
            </div>
        </div>
    );
}
