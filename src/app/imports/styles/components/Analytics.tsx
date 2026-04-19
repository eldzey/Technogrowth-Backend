import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./ui/tabs";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import {
  TrendingUp,
  Calendar,
  Leaf,
  Droplets,
  Thermometer,
  FlaskConical,
  Activity,
  Download,
} from "lucide-react";

export function Analytics() {
  const growthData = [
    { day: "Day 1", size: 2, predicted: 2, leafCount: 2 },
    { day: "Day 7", size: 5, predicted: 5.2, leafCount: 4 },
    { day: "Day 14", size: 12, predicted: 11.5, leafCount: 6 },
    { day: "Day 21", size: 22, predicted: 21, leafCount: 9 },
    { day: "Day 27", size: 35, predicted: 34, leafCount: 12 },
    { day: "Day 35", size: null, predicted: 49, leafCount: null },
    { day: "Day 42", size: null, predicted: 65, leafCount: null },
    { day: "Day 49", size: null, predicted: 82, leafCount: null },
  ];

  const environmentalTrends = [
    { day: "Day 1", temp: 26, humidity: 65, moisture: 70 },
    { day: "Day 5", temp: 27, humidity: 62, moisture: 68 },
    { day: "Day 10", temp: 28, humidity: 60, moisture: 65 },
    { day: "Day 15", temp: 29, humidity: 58, moisture: 55 },
    { day: "Day 20", temp: 30, humidity: 56, moisture: 48 },
    { day: "Day 25", temp: 29, humidity: 55, moisture: 42 },
    { day: "Day 27", temp: 29, humidity: 55, moisture: 42 },
  ];

  const npkHistory = [
    { week: "Week 1", N: 200, P: 70, K: 220 },
    { week: "Week 2", N: 190, P: 68, K: 215 },
    { week: "Week 3", N: 185, P: 65, K: 210 },
    { week: "Week 4", N: 180, P: 62, K: 205 },
  ];

  const weeklyStats = [
    { label: "Avg Temperature", value: "28.5°C", change: "+1.2°C", trend: "up" },
    { label: "Avg Humidity", value: "57%", change: "-3%", trend: "down" },
    { label: "Avg Soil Moisture", value: "48%", change: "-8%", trend: "down" },
    { label: "Growth Rate", value: "High", change: "+15%", trend: "up" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-br from-green-600 to-green-700 text-white">
        <div className="max-w-7xl mx-auto p-4 lg:p-6">
          <div className="flex items-center justify-between mb-4 lg:mb-6">
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold">Analytics</h1>
              <p className="text-green-100 text-sm lg:text-base">Growth & Performance Insights</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-white hover:bg-white/20"
            >
              <Download className="w-4 h-4 mr-2" />
              Export
            </Button>
          </div>

          {/* Quick Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
            <Card className="bg-white/95 backdrop-blur p-3 lg:p-4">
              <div className="flex items-center gap-2 mb-1">
                <Calendar className="w-4 h-4 text-green-600" />
                <span className="text-xs text-gray-600">Current Day</span>
              </div>
              <p className="text-2xl lg:text-3xl font-bold">27</p>
            </Card>
            <Card className="bg-white/95 backdrop-blur p-3 lg:p-4">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4 text-green-600" />
                <span className="text-xs text-gray-600">Growth Score</span>
              </div>
              <p className="text-2xl lg:text-3xl font-bold">88</p>
            </Card>
            <Card className="bg-white/95 backdrop-blur p-3 lg:p-4">
              <div className="flex items-center gap-2 mb-1">
                <Leaf className="w-4 h-4 text-green-600" />
                <span className="text-xs text-gray-600">Leaf Count</span>
              </div>
              <p className="text-2xl lg:text-3xl font-bold">12</p>
            </Card>
            <Card className="bg-white/95 backdrop-blur p-3 lg:p-4">
              <div className="flex items-center gap-2 mb-1">
                <Activity className="w-4 h-4 text-green-600" />
                <span className="text-xs text-gray-600">Days Old</span>
              </div>
              <p className="text-2xl lg:text-3xl font-bold">27</p>
            </Card>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-4 lg:space-y-6">
        {/* Weekly Performance */}
        <div>
          <h2 className="font-bold text-lg lg:text-xl mb-3 lg:mb-4">Weekly Performance</h2>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
            {weeklyStats.map((stat, index) => (
              <Card key={index} className="p-3">
                <p className="text-xs text-gray-600 mb-1">{stat.label}</p>
                <p className="text-xl font-bold mb-1">{stat.value}</p>
                <div className="flex items-center gap-1">
                  <Activity
                    className={`w-3 h-3 ${
                      stat.trend === "up" ? "text-green-600" : "text-orange-600"
                    }`}
                  />
                  <span
                    className={`text-xs font-medium ${
                      stat.trend === "up" ? "text-green-600" : "text-orange-600"
                    }`}
                  >
                    {stat.change}
                  </span>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Growth Analytics */}
        <Tabs defaultValue="growth" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="growth">Growth</TabsTrigger>
            <TabsTrigger value="environment">Environment</TabsTrigger>
            <TabsTrigger value="nutrients">Nutrients</TabsTrigger>
          </TabsList>

          <TabsContent value="growth" className="mt-4 space-y-4">
            <Card className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold">Growth Forecast</h3>
                <Badge className="bg-green-100 text-green-700 border-green-300">
                  On Track
                </Badge>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={growthData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" fontSize={11} />
                    <YAxis fontSize={11} label={{ value: 'Size (cm)', angle: -90, position: 'insideLeft', fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="size"
                      stroke="#22c55e"
                      strokeWidth={3}
                      name="Actual Growth"
                      dot={{ r: 4 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="predicted"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      name="Predicted"
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 p-3 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-900">
                  <span className="font-semibold">AI Forecast:</span> Based on current
                  growth patterns, your Chinese cabbage will reach optimal harvest size
                  in 3 days. Growth is 12% faster than predicted.
                </p>
              </div>
            </Card>

            <Card className="p-4">
              <h3 className="font-semibold mb-4">Leaf Development</h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={growthData.filter(d => d.leafCount !== null)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" fontSize={11} />
                    <YAxis fontSize={11} />
                    <Tooltip />
                    <Bar dataKey="leafCount" fill="#10b981" name="Leaf Count" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="environment" className="mt-4 space-y-4">
            <Card className="p-4">
              <div className="flex items-center gap-2 mb-4">
                <Thermometer className="w-5 h-5 text-orange-600" />
                <h3 className="font-semibold">Temperature Trend</h3>
              </div>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={environmentalTrends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" fontSize={11} />
                    <YAxis fontSize={11} />
                    <Tooltip />
                    <Area
                      type="monotone"
                      dataKey="temp"
                      stroke="#f97316"
                      fill="#fed7aa"
                      name="Temperature (°C)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <p className="text-xs text-gray-600 mt-3">
                Average temperature has increased by 3°C over the past 27 days
              </p>
            </Card>

            <Card className="p-4">
              <div className="flex items-center gap-2 mb-4">
                <Droplets className="w-5 h-5 text-blue-600" />
                <h3 className="font-semibold">Humidity & Moisture</h3>
              </div>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={environmentalTrends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="day" fontSize={11} />
                    <YAxis fontSize={11} />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="humidity"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      name="Humidity (%)"
                      dot={{ r: 3 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="moisture"
                      stroke="#06b6d4"
                      strokeWidth={2}
                      name="Soil Moisture (%)"
                      dot={{ r: 3 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="nutrients" className="mt-4 space-y-4">
            <Card className="p-4">
              <div className="flex items-center gap-2 mb-4">
                <FlaskConical className="w-5 h-5 text-purple-600" />
                <h3 className="font-semibold">NPK Level History</h3>
              </div>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={npkHistory}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="week" fontSize={11} />
                    <YAxis fontSize={11} label={{ value: 'PPM', angle: -90, position: 'insideLeft', fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="N" fill="#ef4444" name="Nitrogen (N)" />
                    <Bar dataKey="P" fill="#f59e0b" name="Phosphorus (P)" />
                    <Bar dataKey="K" fill="#8b5cf6" name="Potassium (K)" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-4 grid grid-cols-3 lg:grid-cols-3 gap-3 lg:gap-4">
                <div className="p-3 bg-red-50 rounded-lg">
                  <p className="text-xs text-red-800 mb-1">Nitrogen (N)</p>
                  <p className="text-lg font-bold text-red-900">180 ppm</p>
                  <p className="text-xs text-red-700">Target: 180</p>
                </div>
                <div className="p-3 bg-orange-50 rounded-lg">
                  <p className="text-xs text-orange-800 mb-1">Phosphorus (P)</p>
                  <p className="text-lg font-bold text-orange-900">62 ppm</p>
                  <p className="text-xs text-orange-700">Target: 60</p>
                </div>
                <div className="p-3 bg-purple-50 rounded-lg">
                  <p className="text-xs text-purple-800 mb-1">Potassium (K)</p>
                  <p className="text-lg font-bold text-purple-900">205 ppm</p>
                  <p className="text-xs text-purple-700">Target: 200</p>
                </div>
              </div>
            </Card>

            <Card className="p-4 bg-green-50 border-green-200">
              <div className="flex items-start gap-2">
                <Leaf className="w-5 h-5 text-green-600 mt-0.5" />
                <div>
                  <p className="font-semibold text-green-900 mb-1">
                    Nutrient Analysis
                  </p>
                  <p className="text-sm text-green-800">
                    NPK balance is optimal for current growth stage. Nutrient levels
                    are decreasing as expected due to plant uptake. Consider adding
                    fertilizer in Week 5 to maintain optimal levels through harvest.
                  </p>
                </div>
              </div>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Historical Performance */}
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-3">
            <Activity className="w-5 h-5 text-green-600" />
            <h3 className="font-semibold">Key Metrics</h3>
          </div>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Total Growth Days</span>
              <span className="font-semibold">27 days</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Current Size</span>
              <span className="font-semibold">35 cm</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Growth Rate</span>
              <span className="font-semibold text-green-600">1.3 cm/day</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Leaf Count</span>
              <span className="font-semibold">12 leaves</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Health Score</span>
              <span className="font-semibold text-green-600">Excellent (88/100)</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
