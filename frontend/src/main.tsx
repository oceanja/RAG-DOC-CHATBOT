import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import App from "./App";
import RequireAuth from "./components/RequireAuth";
import LoginPage from "./pages/LoginPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";
import ProjectListPage from "./pages/ProjectListPage";
import "./index.css";

const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  {
    path: "/",
    element: (
      <RequireAuth>
        <App />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <ProjectListPage /> },
      { path: "projects/:id", element: <ProjectDetailPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
