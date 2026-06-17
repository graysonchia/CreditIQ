import { BarChart3, BrainCircuit, CreditCard, Gauge, Moon, ShieldAlert, Sun, Users } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAppStore } from "../store/appStore";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: Gauge },
  { to: "/predict/credit-score", label: "Credit Score", icon: BrainCircuit },
  { to: "/predict/loan-default", label: "Loan Default", icon: CreditCard },
  { to: "/predict/fraud", label: "Fraud", icon: ShieldAlert },
  { to: "/analytics/model-monitor", label: "Model Monitor", icon: BarChart3 },
  { to: "/customers", label: "Customers", icon: Users }
];

export function Layout() {
  const { darkMode, toggleDarkMode } = useAppStore();

  return (
    <div className={darkMode ? "app dark" : "app"}>
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="brand">
          <span>CIQ</span>
          <div>
            <strong>CreditIQ</strong>
            <small>Credit intelligence</small>
          </div>
        </div>
        <nav>
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
              <item.icon aria-hidden="true" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div>
            <h1>CreditIQ</h1>
            <p>Portfolio-grade credit risk analytics platform</p>
          </div>
          <button className="icon-btn" onClick={toggleDarkMode} aria-label="Toggle dark mode">
            {darkMode ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
          </button>
        </header>
        <Outlet />
      </div>
    </div>
  );
}
