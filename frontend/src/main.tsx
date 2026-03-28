import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'

import App from './App'
import { AuthProvider } from './auth/AuthContext'
import { AuthGate } from './components/AuthGate'
import './index.css'
import HomePage from './pages/HomePage'
import Landing from './pages/Landing'
import Workspace from './pages/Workspace'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/studio"
            element={(
              <AuthGate>
                <App />
              </AuthGate>
            )}
          >
            <Route index element={<Landing />} />
            <Route path="runs/:runId" element={<Workspace />} />
            <Route path="*" element={<Navigate to="/studio" replace />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  </React.StrictMode>,
)
