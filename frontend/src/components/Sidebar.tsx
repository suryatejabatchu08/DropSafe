import { Link, useLocation } from "react-router-dom";
import { BarChart3, AlertCircle, CreditCard, Map, Zap } from "lucide-react";

export default function Sidebar() {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  return (
    <div className="w-64 bg-slate-900 text-white h-screen flex flex-col fixed left-0 top-0">
      {/* Logo */}
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-2xl font-bold">DropSafe</h1>
        <p className="text-slate-400 text-sm">Insurer Dashboard</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        <Link
          to="/"
          className={`flex items-center gap-3 px-4 py-2 rounded-lg transition ${
            isActive("/")
              ? "bg-yellow-500 text-slate-900 font-semibold"
              : "text-slate-300 hover:bg-slate-800"
          }`}
        >
          <BarChart3 size={20} />
          <span>Overview</span>
        </Link>

        <Link
          to="/zones"
          className={`flex items-center gap-3 px-4 py-2 rounded-lg transition ${
            isActive("/zones")
              ? "bg-yellow-500 text-slate-900 font-semibold"
              : "text-slate-300 hover:bg-slate-800"
          }`}
        >
          <Map size={20} />
          <span>Zones</span>
        </Link>

        <Link
          to="/claims"
          className={`flex items-center gap-3 px-4 py-2 rounded-lg transition ${
            isActive("/claims")
              ? "bg-yellow-500 text-slate-900 font-semibold"
              : "text-slate-300 hover:bg-slate-800"
          }`}
        >
          <AlertCircle size={20} />
          <span>Claims & Fraud</span>
        </Link>

        <Link
          to="/payouts"
          className={`flex items-center gap-3 px-4 py-2 rounded-lg transition ${
            isActive("/payouts")
              ? "bg-yellow-500 text-slate-900 font-semibold"
              : "text-slate-300 hover:bg-slate-800"
          }`}
        >
          <CreditCard size={20} />
          <span>Payouts</span>
        </Link>

        {/* Divider */}
        <div className="my-2 border-t border-slate-700" />

        <Link
          to="/economics"
          className={`flex items-center gap-3 px-4 py-2 rounded-lg transition ${
            isActive("/economics")
              ? "bg-yellow-500 text-slate-900 font-semibold"
              : "text-slate-300 hover:bg-slate-800"
          }`}
        >
          <BarChart3 size={20} />
          <span>Unit Economics</span>
        </Link>

        <Link
          to="/demo"
          className={`flex items-center gap-3 px-4 py-2 rounded-lg transition ${
            isActive("/demo")
              ? "bg-yellow-400 text-slate-900 font-bold"
              : "text-yellow-400 hover:bg-yellow-400/10 font-semibold"
          }`}
        >
          <Zap size={20} />
          <span>⚡ Live Demo</span>
        </Link>
      </nav>

      {/* Bottom indicator */}
      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-slate-400 text-sm">Live</span>
        </div>
        <p className="text-slate-500 text-xs mt-2">
          {new Date().toLocaleTimeString("en-IN", {
            hour: "2-digit",
            minute: "2-digit",
          })}{" "}
          IST
        </p>
      </div>
    </div>
  );
}
