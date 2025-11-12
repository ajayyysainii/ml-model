import React, { useEffect, useState } from "react";

export default function RegisteredPlates() {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const API_URL = `${import.meta.env.VITE_API_URL || "http://localhost:4000/api/numbers"}/registered`;

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
            setItems(Array.isArray(data) ? data : []);
        } catch (err) {
            setError(err.message || "Failed to load");
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
                minute: "2-digit"
            });
        } catch {
            return ts;
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-100 to-blue-50 px-4 py-8 font-sans text-gray-900">
            <div className="flex justify-between items-center mb-7">
                <div>
                    <div className="text-2xl font-semibold tracking-tight text-gray-900">Registered Number Plates</div>
                    <div className="text-xs text-gray-400 mt-1">Whitelisted plates that don't require payment</div>
                </div>
                <button
                    className="bg-white border border-gray-200 px-4 py-2 rounded-xl shadow-sm hover:bg-gray-50 focus:ring-2 focus:ring-blue-100 transition active:bg-gray-100 disabled:opacity-60"
                    onClick={fetchList}
                    disabled={loading}
                >
                    {loading ? "Loading…" : "Refresh"}
                </button>
            </div>
            {error && (
                <div className="bg-red-100 border border-red-200 rounded px-3 py-2 mb-3 text-red-700 animate-in fade-in">
                    Error: {error}
                </div>
            )}
            <div className="overflow-x-auto rounded-2xl shadow border border-gray-100 bg-white/80 backdrop-blur-sm">
                <table className="min-w-full text-sm text-left">
                    <thead className="bg-gradient-to-b from-slate-50 to-slate-100/80">
                        <tr>
                            <th className="py-4 px-2 font-medium text-gray-500">Number Plate</th>
                            <th className="py-4 px-2 font-medium text-gray-500">Registered Date</th>
                            <th className="py-4 px-2 font-medium text-gray-500">ID</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.length === 0 && !loading ? (
                            <tr>
                                <td colSpan={3} className="text-center text-gray-400 py-8">
                                    No registered plates found. Click Refresh to try again.
                                </td>
                            </tr>
                        ) : (
                            items.map((it, idx) => (
                                <tr key={it._id || `${it.numberPlate}-${it.timestamp}`}
                                    className="transition hover:bg-blue-50/60">
                                    <td className="py-4 px-2 font-semibold text-gray-700">{it.numberPlate || "—"}</td>
                                    <td className="py-4 px-2 text-gray-500">{formatDate(it.timestamp)}</td>
                                    <td className="py-4 px-2 text-gray-300">{it._id || "n/a"}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

