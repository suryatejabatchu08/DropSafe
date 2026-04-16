import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Zones from "./pages/Zones";
import Claims from "./pages/Claims";
import Payouts from "./pages/Payouts";
import SimulationDemo from "./pages/SimulationDemo";
import WorkerDashboard from "./pages/WorkerDashboard";
import UnitEconomics from "./pages/UnitEconomics";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Worker Dashboard — full page, no sidebar */}
        <Route path="/worker/:workerId" element={<WorkerDashboard />} />

        {/* Insurer Dashboard — with sidebar */}
        <Route
          path="/*"
          element={
            <div className="flex h-screen bg-slate-100">
              <Sidebar />
              <main className="flex-1 overflow-auto ml-64">
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/zones" element={<Zones />} />
                  <Route path="/claims" element={<Claims />} />
                  <Route path="/payouts" element={<Payouts />} />
                  <Route path="/economics" element={<UnitEconomics />} />
                  <Route path="/demo" element={<SimulationDemo />} />
                </Routes>
              </main>
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
