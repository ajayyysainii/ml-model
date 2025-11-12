import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

export default function Payment() {
    const [searchParams] = useSearchParams();
    const orderId = searchParams.get("orderId");
    const plate = searchParams.get("plate");
    const [paymentData, setPaymentData] = useState(null);
    const [status, setStatus] = useState("pending");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const API_URL = import.meta.env.VITE_API_URL || "http://localhost:4000/api/numbers";

    useEffect(() => {
        if (orderId) {
            fetchPaymentData();
            // Poll for payment status every 3 seconds
            const interval = setInterval(() => {
                checkPaymentStatus();
            }, 3000);
            return () => clearInterval(interval);
        }
    }, [orderId]); // eslint-disable-line react-hooks/exhaustive-deps
    
    // Also check payment status when status changes
    useEffect(() => {
        if (orderId && status !== 'completed') {
            // Continue polling if not completed
        }
    }, [status, orderId]);

    async function fetchPaymentData() {
        try {
            // First try to get payment data from status endpoint
            const response = await fetch(`${API_URL}/payment/status/${orderId}`);
            if (!response.ok) throw new Error("Failed to fetch payment data");
            const data = await response.json();
            
            // If no QR code, try to create/fetch it from create endpoint
            if (!data.payment?.qrCodeUrl && orderId && plate) {
                try {
                    console.log('No QR code found, fetching from create endpoint...');
                    const createResponse = await fetch(`${API_URL}/payment/create`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            numberPlate: plate,
                            amount: data.payment?.amount || 50
                        })
                    });
                    if (createResponse.ok) {
                        const createData = await createResponse.json();
                        console.log('QR code received:', createData.qrCodeUrl ? 'Yes' : 'No', createData.qrCodeUrl?.substring(0, 50));
                        if (createData.qrCodeUrl) {
                            setPaymentData({
                                ...data.payment,
                                qrCodeUrl: createData.qrCodeUrl,
                                paymentUrl: createData.paymentUrl || data.payment?.paymentUrl
                            });
                            setStatus(data.status);
                            return;
                        }
                    }
                } catch (e) {
                    console.error('Error fetching QR code:', e);
                }
            }
            
            setPaymentData(data.payment);
            setStatus(data.status);
            
            // Log QR code info for debugging
            if (data.payment?.qrCodeUrl) {
                console.log('QR code found in payment data:', data.payment.qrCodeUrl.substring(0, 50));
            }
        } catch (err) {
            console.error('Error in fetchPaymentData:', err);
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    async function checkPaymentStatus() {
        try {
            const response = await fetch(`${API_URL}/payment/status/${orderId}`);
            if (!response.ok) {
                console.error('Payment status check failed:', response.status);
                return;
            }
            const data = await response.json();
            
            // Update status immediately
            if (data.status !== status) {
                console.log('Payment status changed:', status, '->', data.status);
                setStatus(data.status);
            }
            
            // Update payment data
            if (data.payment) {
                setPaymentData(data.payment);
            }
            
            // If payment completed, show success and close after delay
            if (data.status === "completed") {
                console.log('Payment completed!');
                // Don't close immediately, let user see the success message
                setTimeout(() => {
                    // Only close if it's a popup window
                    if (window.opener) {
                        window.close();
                    }
                }, 5000);
            }
        } catch (err) {
            console.error("Error checking payment:", err);
        }
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">Loading payment...</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 flex items-center justify-center">
                <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md text-center">
                    <div className="text-red-500 text-5xl mb-4">✗</div>
                    <h2 className="text-2xl font-bold text-gray-800 mb-2">Error</h2>
                    <p className="text-gray-600">{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-2xl p-8 max-w-md w-full">
                {status === "completed" ? (
                    <div className="text-center">
                        <div className="text-green-500 text-6xl mb-4">✓</div>
                        <h2 className="text-3xl font-bold text-gray-800 mb-2">Payment Successful!</h2>
                        <p className="text-gray-600 mb-2">Gate will open automatically</p>
                        <p className="text-sm text-green-600 mb-4">Number plate saved to database</p>
                        <div className="bg-green-50 rounded-lg p-4 mt-4">
                            <p className="text-sm text-gray-600">Plate: <span className="font-semibold">{plate}</span></p>
                            <p className="text-sm text-gray-600 mt-1">Order ID: <span className="font-mono text-xs">{orderId}</span></p>
                        </div>
                        <p className="text-sm text-gray-500 mt-4">This window will close automatically...</p>
                    </div>
                ) : (
                    <div className="text-center">
                        <h2 className="text-2xl font-bold text-gray-800 mb-2">Parking Payment</h2>
                        <p className="text-gray-600 mb-6">Scan QR code to pay ₹{paymentData?.amount || 50}</p>
                        
                        {paymentData && paymentData.qrCodeUrl ? (
                            <div className="mb-6">
                                <div className="flex justify-center mb-4">
                                    <img 
                                        src={paymentData.qrCodeUrl} 
                                        alt="Payment QR Code" 
                                        className="border-4 border-gray-200 rounded-lg shadow-lg bg-white"
                                        style={{ 
                                            width: '300px', 
                                            height: '300px', 
                                            objectFit: 'contain',
                                            display: 'block'
                                        }}
                                        onLoad={() => {
                                            console.log('QR code image loaded successfully');
                                        }}
                                        onError={(e) => {
                                            console.error('QR code image failed to load');
                                            e.target.style.display = 'none';
                                        }}
                                    />
                                </div>
                                <p className="text-sm font-semibold text-gray-700 mb-2">Scan this QR code to pay</p>
                                <p className="text-xs text-gray-500 mb-3">
                                    Use any QR scanner app or payment app (PhonePe, Google Pay, Paytm, etc.)
                                </p>
                                <p className="text-xs text-gray-400 italic">
                                    Scanning will open Razorpay payment page
                                </p>
                                {paymentData.paymentUrl && (
                                    <div className="mt-4 pt-4 border-t border-gray-200">
                                        <p className="text-xs text-gray-500 mb-2">Or click to pay directly:</p>
                                        <a 
                                            href={paymentData.paymentUrl} 
                                            target="_blank" 
                                            rel="noopener noreferrer" 
                                            className="inline-block bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700 transition"
                                        >
                                            Open Payment Page
                                        </a>
                                    </div>
                                )}
                            </div>
                        ) : paymentData && paymentData.paymentUrl ? (
                            <div className="mb-6">
                                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                                    <p className="text-sm text-yellow-800 mb-2">QR code not available. Click below to pay:</p>
                                    <a 
                                        href={paymentData.paymentUrl} 
                                        target="_blank" 
                                        rel="noopener noreferrer"
                                        className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
                                    >
                                        Pay ₹{paymentData.amount || 50}
                                    </a>
                                </div>
                            </div>
                        ) : null}
                        
                        {paymentData && paymentData.paymentUrl && (
                            <div className="mb-4">
                                <a 
                                    href={paymentData.paymentUrl} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="text-blue-600 hover:text-blue-800 text-sm underline"
                                >
                                    Or click here to open payment page
                                </a>
                            </div>
                        )}
                        
                        <div className="bg-blue-50 rounded-lg p-4 mb-4">
                            <p className="text-sm text-gray-600">License Plate</p>
                            <p className="text-2xl font-bold text-gray-800">{plate}</p>
                        </div>
                        
                        <div className="bg-gray-50 rounded-lg p-4 mb-4">
                            <p className="text-sm text-gray-600">Amount</p>
                            <p className="text-2xl font-bold text-blue-600">₹{paymentData?.amount || 50}</p>
                        </div>
                        
                        <div className="bg-yellow-50 rounded-lg p-3 mb-4">
                            <p className="text-xs text-gray-600">
                                <span className="animate-pulse">●</span> Waiting for payment...
                            </p>
                        </div>
                        
                        <p className="text-xs text-gray-500">
                            Order ID: <span className="font-mono">{orderId}</span>
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}

