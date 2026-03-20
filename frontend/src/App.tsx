import { useEffect, useState } from 'react'
import axios from 'axios'
import { CloudRain, ShieldCheck, Zap, AlertTriangle, IndianRupee, Truck } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card'
import { Button } from './components/ui/button'
import { Label } from './components/ui/label'
import { Slider } from './components/ui/slider'

// Types based on backend responses
interface Trigger {
  trigger_type: string
  zone: string
  severity: number
  timestamp: string
}

interface CalculateResponse {
  weekly_premium: number
}

function App() {
  // Calculator State
  const [zoneRisk, setZoneRisk] = useState<number>(1.0)
  const [hours, setHours] = useState<number>(40)
  const [season, setSeason] = useState<string>('normal')
  const [premium, setPremium] = useState<number | null>(null)
  
  // Data Feed State
  const [triggers, setTriggers] = useState<Trigger[]>([])
  const [apiStatus, setApiStatus] = useState<string>('Checking...')

  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'https://dropsafe-qimn.onrender.com'

  useEffect(() => {
    // Check Health
    axios.get(`${BACKEND_URL}/health`)
      .then(() => setApiStatus('Online'))
      .catch(() => setApiStatus('Offline'))

    // Fetch Triggers
    axios.get(`${BACKEND_URL}/triggers/mock`)
      .then(res => setTriggers(res.data))
      .catch(err => console.error("Failed to fetch triggers", err))
  }, [])

  const handleCalculate = async () => {
    try {
      const response = await axios.post<CalculateResponse>(`${BACKEND_URL}/premium/calculate`, {
        zone_risk: zoneRisk,
        declared_hours: hours,
        season: season
      })
      setPremium(response.data.weekly_premium)
    } catch (error) {
      console.error("Calculation failed", error)
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      {/* Navbar */}
      <nav className="border-b border-border bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-8 w-8 text-primary" />
            <div>
              <h1 className="text-xl font-bold tracking-tight text-white leading-none">DropSafe</h1>
              <p className="text-xs text-muted-foreground">Parametric Income Protection</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <span className={`text-xs px-2 py-1 rounded-full ${apiStatus === 'Online' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
              System: {apiStatus}
            </span>
            <Button variant="outline" size="sm">Partner Login</Button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="py-12 md:py-20 px-4">
        <div className="container mx-auto text-center max-w-3xl">
          <h2 className="text-4xl md:text-6xl font-extrabold tracking-tight mb-6">
            When the storm stops deliveries, <span className="text-primary">we start paying.</span>
          </h2>
          <p className="text-lg text-muted-foreground mb-8">
            Automatic income protection for Q-Commerce delivery partners. 
            Instant payouts triggered by rain, heatwaves, and pollution based on local data.
          </p>
          <div className="flex justify-center gap-4">
            <Button size="lg" className="bg-primary text-black hover:bg-primary/90">Get Protected</Button>
            <Button size="lg" variant="outline">View Coverage Map</Button>
          </div>
        </div>
      </section>

      {/* Main Content Grid */}
      <div className="container mx-auto px-4 py-12 grid md:grid-cols-2 gap-8">
        
        {/* Left: Premium Calculator */}
        <Card className="border-primary/20 bg-card/50 backdrop-blur-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <IndianRupee className="h-5 w-5 text-primary" />
              Weekly Premium Calculator
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <div className="flex justify-between">
                <Label>Zone Risk: <span className="text-primary font-bold">{zoneRisk.toFixed(2)}</span></Label>
                <span className="text-xs text-muted-foreground">High Risk Zones cost more</span>
              </div>
              <Slider 
                min={0.75} 
                max={1.60} 
                step={0.05} 
                value={zoneRisk} 
                onChange={(e) => setZoneRisk(parseFloat(e.target.value))}
              />
            </div>

            <div className="space-y-2">
              <div className="flex justify-between">
                <Label>Declared Hours/Week: <span className="text-primary font-bold">{hours}h</span></Label>
              </div>
              <Slider 
                min={10} 
                max={80} 
                step={5} 
                value={hours} 
                onChange={(e) => setHours(parseInt(e.target.value))}
              />
            </div>

            <div className="space-y-2">
              <Label>Season</Label>
              <select 
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 text-foreground"
                value={season}
                onChange={(e) => setSeason(e.target.value)}
              >
                <option value="normal">Normal Season</option>
                <option value="monsoon">Monsoon (Heavy Rain)</option>
                <option value="aqi_season">AQI Alert Season (Pollution)</option>
              </select>
            </div>

            <Button onClick={handleCalculate} className="w-full text-lg h-12">
              Calculate Premium
            </Button>

            {premium != null && (
              <div className="mt-6 p-4 bg-primary/10 rounded-lg border border-primary/20 text-center animate-in fade-in slide-in-from-bottom-2">
                <p className="text-sm text-muted-foreground mb-1">Estimated Weekly Cost</p>
                <p className="text-4xl font-bold text-primary">₹{premium.toFixed(2)}</p>
                <p className="text-xs text-muted-foreground mt-2">Base rate applies. Coverage up to ₹500/day.</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right: Live Trigger Feed */}
        <div className="space-y-6">
          <Card className="h-full border-border bg-card/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="h-5 w-5 text-yellow-500" />
                Live Trigger Feed
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {triggers.length === 0 ? (
                  <div className="text-center text-muted-foreground py-8">
                    Waiting for events...
                  </div>
                ) : (
                  triggers.map((trigger, idx) => (
                    <div key={idx} className="flex items-start gap-4 p-4 rounded-lg bg-background border border-border/50 hover:border-primary/50 transition-colors">
                      <div className="p-2 rounded-full bg-secondary text-primary">
                        {trigger.trigger_type === 'rain' ? <CloudRain className="h-5 w-5" /> : 
                         trigger.trigger_type === 'aqi' ? <AlertTriangle className="h-5 w-5" /> : 
                         <Zap className="h-5 w-5" />}
                      </div>
                      <div className="flex-1">
                        <div className="flex justify-between items-start">
                          <h4 className="font-semibold text-foreground capitalize">{trigger.trigger_type} Alert</h4>
                          <span className="text-xs text-muted-foreground">{new Date(trigger.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">
                          Zone: <span className="text-foreground font-medium">{trigger.zone}</span> • 
                          Severity: <span className={`font-medium ${trigger.severity > 0.8 ? 'text-red-400' : 'text-yellow-400'}`}>
                            {(trigger.severity * 100).toFixed(0)}%
                          </span>
                        </p>
                      </div>
                    </div>
                  ))
                )}
                
                <div className="mt-4 p-4 rounded-lg bg-blue-900/20 border border-blue-800 text-blue-200 text-sm flex gap-2">
                  <Truck className="h-5 w-5 flex-shrink-0" />
                  <p>System automatically detects triggers from 12,000+ IoT sensors across partner zones.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default App
