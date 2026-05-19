import AI from "./AI";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { ImageWithFallback } from "./figma/ImageWithFallback";
import {
  Sprout,
  Thermometer,
  Droplets,
  FlaskConical,
  Calendar,
  Leaf,
  Bell,
  Gauge,
  Fan,
  Droplet,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export function Dashboard() {
  // Mock data for the main crop
  const cropData = {
    day: 27,
    growthStage: "Late Vegetative",
    health: "Healthy",
    daysToHarvest: 3,
    temperature: 29,
    tempMin: 25,
    tempMax: 30,
    humidity: 55,
    humidityMin: 50,
    humidityMax: 70,
    soilMoisture: 42,
    moistureMin: 40,
    moistureMax: 60,
    npkStatus: "NORMAL",
    npkLevel: "Balanced",
    leafCount: 12,
    growthScore: 88,
    suggestion: "Increase humidity slightly",
  };

  const last24HoursData = [
    { time: "0h", soilMoisture: 45, temp: 26 },
    { time: "4h", soilMoisture: 44, temp: 25 },
    { time: "8h", soilMoisture: 42, temp: 27 },
    { time: "12h", soilMoisture: 40, temp: 29 },
    { time: "16h", soilMoisture: 39, temp: 30 },
    { time: "20h", soilMoisture: 41, temp: 28 },
    { time: "24h", soilMoisture: 42, temp: 29 },
  ];

  const devices = [
    { name: "Irrigation Pump", status: "OFF", icon: Droplet },
    { name: "Exhaust Fan", status: "OFF", icon: Fan },
    { name: "Humidifier", status: "OFF", icon: Droplets },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-7xl mx-auto p-4 lg:p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 lg:w-14 lg:h-14 rounded-full overflow-hidden bg-green-100 flex items-center justify-center">
                <ImageWithFallback
                  src="https://images.unsplash.com/photo-1693667660431-827eb63f228d?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjaGluZXNlJTIwY2FiYmFnZSUyMG5hcGElMjB2ZWdldGFibGV8ZW58MXx8fHwxNzc2MjM0NTQwfDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                  alt="Chinese cabbage"
                  className="w-full h-full object-cover"
                />
              </div>
              <div>
                <h1 className="font-bold text-lg lg:text-xl">Chinese Cabbage Monitor</h1>
                <p className="text-sm text-gray-600">
                  Day {cropData.day} · Growth Stage: {cropData.growthStage}
                </p>
              </div>
            </div>
            <button className="w-10 h-10 lg:w-12 lg:h-12 rounded-full bg-gray-100 flex items-center justify-center hover:bg-gray-200 transition-colors">
              <Bell className="w-5 h-5 text-gray-600" />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-4 lg:space-y-6">
        
        <AI />
        
        {/* Hero Card with Image */}
        <Card className="relative overflow-hidden bg-gradient-to-br from-green-50 to-green-100 p-0">
          <div className="flex items-center justify-between p-4 lg:p-6">
            <div className="z-10">
              <div className="flex items-center gap-2 mb-1">
                <Sprout className="w-5 h-5 lg:w-6 lg:h-6 text-green-700" />
                <span className="text-lg lg:text-2xl font-bold text-green-900">
                  {cropData.health}
                </span>
              </div>
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="w-4 h-4 lg:w-5 lg:h-5 text-green-700" />
                <span className="text-sm lg:text-base font-medium text-green-800">
                  Day {cropData.day}
                </span>
              </div>
              <p className="text-green-900 font-semibold text-sm lg:text-base">
                Harvest ETA: <span className="text-lg lg:text-2xl">{cropData.daysToHarvest}</span> Days Remaining
              </p>
            </div>
            <div className="w-40 h-32 lg:w-64 lg:h-48 rounded-lg overflow-hidden shadow-lg">
              <ImageWithFallback
                src="https://images.unsplash.com/photo-1693667660431-827eb63f228d?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxjaGluZXNlJTIwY2FiYmFnZSUyMG5hcGElMjB2ZWdldGFibGV8ZW58MXx8fHwxNzc2MjM0NTQwfDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral"
                alt="Chinese cabbage"
                className="w-full h-full object-cover"
              />
            </div>
          </div>
        </Card>

        {/* Environmental Monitoring Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
          {/* Temperature */}
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Thermometer className="w-4 h-4 text-red-500" />
              <span className="text-sm font-medium">Temperature</span>
            </div>
            <p className="text-3xl font-bold mb-1">{cropData.temperature}°C</p>
            <p className="text-xs text-gray-600 mb-2">
              Optimal Range: {cropData.tempMin}–{cropData.tempMax}°C
            </p>
            <Badge className="bg-green-100 text-green-700 border-green-300 w-full justify-center">
              <div className="w-2 h-2 rounded-full bg-green-600 mr-2" />
              Stable
            </Badge>
          </Card>

          {/* Humidity */}
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Droplets className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium">Humidity</span>
            </div>
            <p className="text-3xl font-bold mb-1">{cropData.humidity}%</p>
            <p className="text-xs text-gray-600 mb-2">
              Optimal Range: {cropData.humidityMin}–{cropData.humidityMax}%
            </p>
            <Badge className="bg-green-100 text-green-700 border-green-300 w-full justify-center">
              <div className="w-2 h-2 rounded-full bg-green-600 mr-2" />
              Stable
            </Badge>
          </Card>

          {/* Soil Moisture */}
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Droplet className="w-4 h-4 text-cyan-500" />
              <span className="text-sm font-medium">Soil Moisture</span>
            </div>
            <p className="text-3xl font-bold mb-1">{cropData.soilMoisture}%</p>
            <p className="text-xs text-gray-600 mb-2">
              Optimal Range: {cropData.moistureMin}–{cropData.moistureMax}%
            </p>
            <Badge className="bg-green-100 text-green-700 border-green-300 w-full justify-center">
              <div className="w-2 h-2 rounded-full bg-green-600 mr-2" />
              Stable
            </Badge>
          </Card>

          {/* NPK Level */}
          <Card className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <FlaskConical className="w-4 h-4 text-purple-500" />
              <span className="text-sm font-medium">NPK Level</span>
            </div>
            <p className="text-3xl font-bold mb-1">{cropData.npkStatus}</p>
            <p className="text-xs text-gray-600 mb-2">
              Optimal Level: {cropData.npkLevel}
            </p>
            <Badge className="bg-green-100 text-green-700 border-green-300 w-full justify-center">
              <div className="w-2 h-2 rounded-full bg-green-600 mr-2" />
              Stable
            </Badge>
          </Card>
        </div>

        {/* Growth Insight & Ideal Conditions */}
        <div className="grid grid-cols-3 lg:grid-cols-5 gap-3 lg:gap-4">
          <Card className="col-span-2 lg:col-span-3 p-4 bg-gradient-to-br from-green-600 to-green-700 text-white">
            <div className="flex items-center gap-2 mb-2">
              <Sprout className="w-4 h-4" />
              <span className="text-sm font-semibold">Growth Insight</span>
            </div>
            <p className="text-sm mb-1">Leaf Count: {cropData.leafCount}</p>
            <div className="flex items-center gap-2">
              <span className="text-xs">Growth Score:</span>
              <Badge className="bg-white/20 text-white border-white/30">
                <Gauge className="w-3 h-3 mr-1" />
                ON
              </Badge>
            </div>
          </Card>

          <Card className="col-span-1 lg:col-span-2 p-4 bg-gradient-to-br from-green-50 to-green-100">
            <div className="flex items-center gap-2 mb-2">
              <Leaf className="w-4 h-4 text-green-700" />
              <span className="text-xs font-semibold text-green-900">
                Ideal Conditions
              </span>
            </div>
            <div className="space-y-1 text-xs text-green-800">
              <div className="flex items-center gap-1">
                <Thermometer className="w-3 h-3" />
                <span>25–30°C</span>
              </div>
              <div className="flex items-center gap-1">
                <Droplets className="w-3 h-3" />
                <span>50–70%</span>
              </div>
              <div className="flex items-center gap-1">
                <FlaskConical className="w-3 h-3" />
                <span>NPK Balanced</span>
              </div>
            </div>
          </Card>
        </div>

        {/* Growth Score & Suggestion Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 lg:gap-4">
        {/* Growth Score Display */}
        <Card className="p-4 lg:p-6 bg-gradient-to-br from-gray-100 to-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <Gauge className="w-5 h-5 text-green-600" />
                <span className="font-semibold">Growth Score</span>
              </div>
              <div className="text-6xl font-bold text-green-600">
                {cropData.growthScore}
              </div>
              <p className="text-sm text-gray-600 mt-1">Optimal</p>
            </div>
          </div>
        </Card>

        {/* Suggestion */}
        <Card className="p-3 lg:p-4 bg-green-50 border-green-200">
          <div className="flex items-start gap-2">
            <Sprout className="w-5 h-5 text-green-600 mt-0.5" />
            <div>
              <p className="text-sm lg:text-base">
                <span className="font-semibold text-green-900">Suggestion:</span>{" "}
                <span className="text-green-800">{cropData.suggestion}</span>
              </p>
            </div>
          </div>
        </Card>
        </div>

        {/* Last 24 Hours */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
              <span className="text-xs font-bold text-blue-600">!</span>
            </div>
            <h3 className="font-semibold">Last 24 Hours</h3>
          </div>

          {/* Device Status */}
          <div className="space-y-2 mb-4">
            {devices.map((device) => {
              const Icon = device.icon;
              return (
                <div
                  key={device.name}
                  className="flex items-center justify-between"
                >
                  <div className="flex items-center gap-2">
                    <Icon className="w-4 h-4 text-gray-600" />
                    <span className="text-sm">{device.name}</span>
                  </div>
                  <Badge
                    variant="outline"
                    className="bg-gray-100 text-gray-600 border-gray-300"
                  >
                    <div className="w-2 h-2 rounded-full bg-gray-400 mr-2" />
                    {device.status}
                  </Badge>
                </div>
              );
            })}
          </div>

          <p className="text-xs text-gray-600 mb-3">
            Mode: <span className="font-semibold">AUTO</span> · Irrigation (2 hrs ago)
          </p>

          {/* Chart */}
          <div className="h-32">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={last24HoursData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="time"
                  fontSize={10}
                  stroke="#9ca3af"
                  tickLine={false}
                />
                <YAxis fontSize={10} stroke="#9ca3af" tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "white",
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="soilMoisture"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  dot={false}
                  name="Soil Moisture"
                />
                <Line
                  type="monotone"
                  dataKey="temp"
                  stroke="#10b981"
                  strokeWidth={2}
                  dot={false}
                  name="Temp"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>
    </div>
  );
}
