import { NavLink, useLocation } from 'react-router-dom'
import { isStaticMode } from '../lib/snapshot'

const allTabs = [
  { to: '/', label: 'Research', primary: true, badge: true },
  { to: '/observatory', label: 'Observatory' },
  { to: '/pipeline', label: 'Pipeline', liveOnly: true },
  { to: '/trades', label: 'Trades' },
]

export default function NavBar({ inboxCount = 0 }) {
  const location = useLocation()
  const isStatic = isStaticMode()
  const tabs = isStatic ? allTabs.filter(t => !t.liveOnly) : allTabs

  return (
    <nav className="nav-bar">
      {tabs.map(tab => {
        const isActive = tab.to === '/'
          ? location.pathname === '/'
          : location.pathname.startsWith(tab.to)

        return (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={[
              'nav-bar__tab',
              tab.primary ? 'nav-bar__tab--primary' : '',
              isActive ? 'nav-bar__tab--active' : '',
            ].filter(Boolean).join(' ')}
          >
            {tab.label}
            {tab.badge && inboxCount > 0 && (
              <span className="nav-bar__badge">{inboxCount}</span>
            )}
          </NavLink>
        )
      })}
    </nav>
  )
}
