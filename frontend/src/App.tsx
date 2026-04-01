import { BrowserRouter, Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Zones from "./pages/Zones";
import Claims from "./pages/Claims";
import Payouts from "./pages/Payouts";

function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-slate-100">
        {/* Sidebar */}
        <Sidebar />

        {/* Main Content */}
        <main className="flex-1 overflow-auto ml-64">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/zones" element={<Zones />} />
            <Route path="/claims" element={<Claims />} />
            <Route path="/payouts" element={<Payouts />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
