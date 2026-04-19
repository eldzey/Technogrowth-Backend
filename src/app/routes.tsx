import { createBrowserRouter } from "react-router";
import { Layout } from "./components/Layout";
import { Dashboard } from "./components/Dashboard";
import { Analytics } from "./components/Analytics";
import { Control } from "./components/Control";
import { Alerts } from "./components/Alerts";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: Dashboard },
      { path: "analytics", Component: Analytics },
      { path: "control", Component: Control },
      { path: "alerts", Component: Alerts },
    ],
  },
]);
