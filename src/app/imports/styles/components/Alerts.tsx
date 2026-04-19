import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import {
  Bell,
  AlertTriangle,
  Info,
  CheckCircle2,
  Clock,
  Droplet,
  Thermometer,
  Droplets,
} from "lucide-react";

export function Alerts() {
  const alerts = [
    {
      id: 1,
      type: "warning",
      title: "Soil Moisture Low",
      message: "Soil moisture has dropped to 42%. Consider irrigation.",
      time: "2 hours ago",
      icon: Droplet,
      read: false,
    },
    {
      id: 2,
      type: "info",
      title: "Growth Milestone",
      message: "Your Chinese cabbage has reached 12 leaves!",
      time: "5 hours ago",
      icon: CheckCircle2,
      read: false,
    },
    {
      id: 3,
      type: "warning",
      title: "Temperature Rising",
      message: "Temperature increased to 29°C. Monitor closely.",
      time: "1 day ago",
      icon: Thermometer,
      read: true,
    },
    {
      id: 4,
      type: "info",
      title: "Auto Irrigation Completed",
      message: "Irrigation pump ran for 2 hours as scheduled.",
      time: "2 hours ago",
      icon: Droplet,
      read: true,
    },
    {
      id: 5,
      type: "success",
      title: "Optimal Conditions Achieved",
      message: "All environmental parameters are within ideal ranges.",
      time: "1 day ago",
      icon: CheckCircle2,
      read: true,
    },
    {
      id: 6,
      type: "info",
      title: "Humidity Suggestion",
      message: "Consider increasing humidity slightly for optimal growth.",
      time: "2 days ago",
      icon: Droplets,
      read: true,
    },
  ];

  const getAlertStyle = (type: string) => {
    switch (type) {
      case "warning":
        return {
          bg: "bg-orange-50",
          border: "border-orange-200",
          icon: "text-orange-600",
          badge: "bg-orange-100 text-orange-700 border-orange-300",
        };
      case "success":
        return {
          bg: "bg-green-50",
          border: "border-green-200",
          icon: "text-green-600",
          badge: "bg-green-100 text-green-700 border-green-300",
        };
      default:
        return {
          bg: "bg-blue-50",
          border: "border-blue-200",
          icon: "text-blue-600",
          badge: "bg-blue-100 text-blue-700 border-blue-300",
        };
    }
  };

  const unreadCount = alerts.filter((a) => !a.read).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-br from-green-600 to-green-700 text-white">
        <div className="max-w-7xl mx-auto p-4 lg:p-6">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <Bell className="w-7 h-7 lg:w-8 lg:h-8" />
              <div>
                <h1 className="text-2xl lg:text-3xl font-bold">Alerts</h1>
                <p className="text-green-100 text-sm lg:text-base">
                  {unreadCount} unread notification{unreadCount !== 1 ? "s" : ""}
                </p>
              </div>
            </div>
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                className="text-white hover:bg-white/20"
              >
                Mark all read
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4 lg:p-6 space-y-3 lg:space-y-4">
        {/* Alert Categories */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          <Badge className="bg-white text-gray-900 border-gray-300 whitespace-nowrap">
            All ({alerts.length})
          </Badge>
          <Badge
            variant="outline"
            className="bg-orange-100 text-orange-700 border-orange-300 whitespace-nowrap"
          >
            <AlertTriangle className="w-3 h-3 mr-1" />
            Warnings (2)
          </Badge>
          <Badge
            variant="outline"
            className="bg-blue-100 text-blue-700 border-blue-300 whitespace-nowrap"
          >
            <Info className="w-3 h-3 mr-1" />
            Info (3)
          </Badge>
          <Badge
            variant="outline"
            className="bg-green-100 text-green-700 border-green-300 whitespace-nowrap"
          >
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Success (1)
          </Badge>
        </div>

        {/* Alerts List */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 lg:gap-4">
          {alerts.map((alert) => {
            const Icon = alert.icon;
            const styles = getAlertStyle(alert.type);

            return (
              <Card
                key={alert.id}
                className={`p-4 ${styles.bg} ${styles.border} ${
                  !alert.read ? "border-l-4" : ""
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`w-10 h-10 rounded-full ${
                      alert.type === "warning"
                        ? "bg-orange-100"
                        : alert.type === "success"
                        ? "bg-green-100"
                        : "bg-blue-100"
                    } flex items-center justify-center flex-shrink-0`}
                  >
                    <Icon className={`w-5 h-5 ${styles.icon}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <h3 className="font-semibold text-gray-900">
                        {alert.title}
                      </h3>
                      {!alert.read && (
                        <div className="w-2 h-2 bg-green-600 rounded-full flex-shrink-0 mt-1.5" />
                      )}
                    </div>
                    <p className="text-sm text-gray-700 mb-2">{alert.message}</p>
                    <div className="flex items-center gap-1 text-xs text-gray-600">
                      <Clock className="w-3 h-3" />
                      <span>{alert.time}</span>
                    </div>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>

        {/* Alert Settings */}
        <Card className="p-4 lg:p-6 mt-3 lg:mt-4">
          <h3 className="font-semibold mb-3">Notification Settings</h3>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span>Critical alerts</span>
              <Badge className="bg-green-100 text-green-700 border-green-300">
                Enabled
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Growth milestones</span>
              <Badge className="bg-green-100 text-green-700 border-green-300">
                Enabled
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Daily summaries</span>
              <Badge className="bg-green-100 text-green-700 border-green-300">
                Enabled
              </Badge>
            </div>
            <div className="flex items-center justify-between">
              <span>Device status changes</span>
              <Badge className="bg-gray-100 text-gray-600 border-gray-300">
                Disabled
              </Badge>
            </div>
          </div>
          <Button variant="outline" className="w-full mt-4">
            Manage Preferences
          </Button>
        </Card>
      </div>
    </div>
  );
}
