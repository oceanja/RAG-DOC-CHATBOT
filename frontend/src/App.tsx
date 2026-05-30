import { Link, Outlet, useNavigate } from "react-router-dom";
import { clearToken } from "./auth";

export default function App() {
  const navigate = useNavigate();

  function handleLogout() {
    clearToken();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen">
      <header className="bg-gray-900 text-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link to="/" className="text-lg font-semibold">
            DocuPilot
          </Link>
          <div className="flex items-center gap-4">
            <span className="text-xs text-gray-400">Admin dashboard</span>
            <button
              onClick={handleLogout}
              className="rounded-md border border-gray-700 px-3 py-1 text-xs text-gray-200 hover:bg-gray-800"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
