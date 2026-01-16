import React from 'react'
import ReactDOM from 'react-dom/client'
import { NotificationProvider } from './contexts/NotificationContext'
import App from './App.jsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <NotificationProvider>
      <App />
    </NotificationProvider>
  </React.StrictMode>,
)
