import { useState } from "react";
import { Card } from "./ui/card";
import { Button } from "./ui/button";
import { Switch } from "./ui/switch";
import { Slider } from "./ui/slider";
import { Badge } from "./ui/badge";
import {
  Settings,
  Droplet,
  Fan,
  Droplets,
  Zap,
  Clock,
  Power,
} from "lucide-react";

export function Control() {
  const [autoMode, setAutoMode] = useState(true);
  const [irrigationPump, setIrrigationPump] = useState(false);
  const [exhaustFan, setExhaustFan] = useState(false);
  const [humidifier, setHumidifier] = useState(false);
  const [irrigationDuration, setIrrigationDuration] = useState([120]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-br from-green-600 to-green-700 text-white">
        <div className="max-w-7xl mx-auto p-4 lg:p-6">
          <div className="flex items-center gap-3 mb-2">
            <Settings className="w-7 h-7 lg:w-8 lg:h-8" />
            <div>
              <h1 className="text-2xl lg:text-3xl font-bold">Control Panel</h1>
              <p className="text-green-100 text-sm lg:text-base">Manage your devices</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-4 lg:space-y-6">
        {/* Auto Mode */}
        <Card className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                <Zap className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <h3 className="font-semibold">Auto Mode</h3>
                <p className="text-xs text-gray-600">
                  AI-controlled environment management
                </p>
              </div>
            </div>
            <Switch checked={autoMode} onCheckedChange={setAutoMode} />
          </div>
          {autoMode && (
            <div className="mt-3 p-3 bg-green-50 rounded-lg">
              <p className="text-sm text-green-900">
                Devices will automatically adjust based on optimal conditions
              </p>
            </div>
          )}
        </Card>

        {/* Device Controls */}
        <div className="space-y-3 lg:space-y-4">
          <h2 className="font-bold text-lg lg:text-xl">Device Controls</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 lg:gap-4">

          {/* Irrigation Pump */}
          <Card className="p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <Droplet className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Irrigation Pump</h3>
                  <p className="text-xs text-gray-600">Control water supply</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge
                  variant="outline"
                  className={
                    irrigationPump
                      ? "bg-green-100 text-green-700 border-green-300"
                      : "bg-gray-100 text-gray-600 border-gray-300"
                  }
                >
                  <Power className="w-3 h-3 mr-1" />
                  {irrigationPump ? "ON" : "OFF"}
                </Badge>
                <Switch
                  checked={irrigationPump}
                  onCheckedChange={setIrrigationPump}
                  disabled={autoMode}
                />
              </div>
            </div>

            {irrigationPump && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">Duration</span>
                  <span className="font-semibold">{irrigationDuration[0]} minutes</span>
                </div>
                <Slider
                  value={irrigationDuration}
                  onValueChange={setIrrigationDuration}
                  min={30}
                  max={240}
                  step={30}
                  disabled={autoMode}
                />
              </div>
            )}

            <div className="mt-3 pt-3 border-t flex items-center justify-between text-xs text-gray-600">
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>Last run: 2 hours ago</span>
              </div>
              <span>Total today: 3.5 hrs</span>
            </div>
          </Card>

          {/* Exhaust Fan */}
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                  <Fan className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Exhaust Fan</h3>
                  <p className="text-xs text-gray-600">Temperature control</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge
                  variant="outline"
                  className={
                    exhaustFan
                      ? "bg-green-100 text-green-700 border-green-300"
                      : "bg-gray-100 text-gray-600 border-gray-300"
                  }
                >
                  <Power className="w-3 h-3 mr-1" />
                  {exhaustFan ? "ON" : "OFF"}
                </Badge>
                <Switch
                  checked={exhaustFan}
                  onCheckedChange={setExhaustFan}
                  disabled={autoMode}
                />
              </div>
            </div>

            <div className="mt-3 pt-3 border-t flex items-center justify-between text-xs text-gray-600">
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>Last run: 5 hours ago</span>
              </div>
              <span>Total today: 1.2 hrs</span>
            </div>
          </Card>

          {/* Humidifier */}
          <Card className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-cyan-100 rounded-full flex items-center justify-center">
                  <Droplets className="w-5 h-5 text-cyan-600" />
                </div>
                <div>
                  <h3 className="font-semibold">Humidifier</h3>
                  <p className="text-xs text-gray-600">Humidity control</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Badge
                  variant="outline"
                  className={
                    humidifier
                      ? "bg-green-100 text-green-700 border-green-300"
                      : "bg-gray-100 text-gray-600 border-gray-300"
                  }
                >
                  <Power className="w-3 h-3 mr-1" />
                  {humidifier ? "ON" : "OFF"}
                </Badge>
                <Switch
                  checked={humidifier}
                  onCheckedChange={setHumidifier}
                  disabled={autoMode}
                />
              </div>
            </div>

            <div className="mt-3 pt-3 border-t flex items-center justify-between text-xs text-gray-600">
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span>Last run: Never</span>
              </div>
              <span>Total today: 0 hrs</span>
            </div>
          </Card>
          </div>
        </div>

        {/* Quick Actions */}
        <Card className="p-4">
          <h3 className="font-semibold mb-3">Quick Actions</h3>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4">
            <Button
              variant="outline"
              className="w-full"
              disabled={autoMode}
            >
              <Droplet className="w-4 h-4 mr-2" />
              Water Now
            </Button>
            <Button
              variant="outline"
              className="w-full"
              disabled={autoMode}
            >
              <Fan className="w-4 h-4 mr-2" />
              Ventilate
            </Button>
          </div>
        </Card>

        {autoMode && (
          <Card className="p-4 bg-blue-50 border-blue-200">
            <p className="text-sm text-blue-900">
              <span className="font-semibold">Auto Mode Active:</span> Manual
              controls are disabled. The system will automatically manage all
              devices based on optimal conditions for Chinese cabbage growth.
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
