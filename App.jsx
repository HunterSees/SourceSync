import { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { Dashboard } from './components/Dashboard'
import { DevicesPage } from './components/DevicesPage'
import { SyncPage } from './components/SyncPage'
import { AudioPage } from './components/AudioPage'
import { SystemPage } from './components/SystemPage'
import { ThemeProvider } from './components/ThemeProvider'
import './App.css'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <ThemeProvider defaultTheme="dark" storageKey="syncstream-theme">
      <Router>
        <div className="flex h-screen bg-background">
          <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />
          
          <div className="flex-1 flex flex-col overflow-hidden">
            <main className="flex-1 overflow-x-hidden overflow-y-auto bg-background">
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/devices" element={<DevicesPage />} />
                <Route path="/sync" element={<SyncPage />} />
                <Route path="/audio" element={<AudioPage />} />
                <Route path="/system" element={<SystemPage />} />
              </Routes>
            </main>
          </div>
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App

