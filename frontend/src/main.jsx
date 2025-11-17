import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import Payment from './Payment.jsx'
import RegisteredPlates from './RegisteredPlates.jsx'
import GuestPlates from './GuestPlates.jsx'
import SensorData from './SensorData.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/payment" element={<Payment />} />
        <Route path="/registered" element={<RegisteredPlates />} />
        <Route path="/guests" element={<GuestPlates />} />
        <Route path="/sensor" element={<SensorData />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
