import { Link, useLocation } from 'react-router-dom'
import { 
  LayoutDashboard, 
  LayoutFolder, 
  LayoutClock, 
  LayoutSettings 
} from 'lucide-react'

export default function Layout({ children }) {
  const location = useLocation()

  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/folders', icon: LayoutFolder, label: 'Folders' },
    { path: '/jobs', icon: LayoutClock, label: 'Jobs' },
    { path: '/logs', icon: LayoutSettings, label: 'Logs' },
    { path: '/import', icon: LayoutSettings, label: 'Import' },
  ]

  return (
    <div className="layout">
      <aside className="sidebar">
        <nav>
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <Link 
                key={item.path} 
                to={item.path}
                className={location.pathname === item.path ? 'active' : ''}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </Link>
            )
          })}
        </nav>
      </aside>
      <main className="main-content">
        {children}
      </main>
    </div>
  )
}
