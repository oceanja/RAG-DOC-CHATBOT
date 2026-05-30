import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  createProject,
  deleteProject,
  listProjects,
} from "../api/projects";
import StatusBadge from "../components/StatusBadge";
import type { Project } from "../types";

export default function ProjectListPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [docsUrl, setDocsUrl] = useState("");
  const [creating, setCreating] = useState(false);

  async function refresh() {
    try {
      setProjects(await listProjects());
      setError(null);
    } catch {
      setError("Failed to load projects. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    try {
      await createProject(name.trim(), docsUrl.trim() || undefined);
      setName("");
      setDocsUrl("");
      setShowCreate(false);
      await refresh();
    } catch {
      setError("Failed to create project.");
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string, projName: string) {
    if (!confirm(`Delete project "${projName}"? This removes all its docs and chunks.`))
      return;
    await deleteProject(id);
    await refresh();
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Projects</h1>
        <button
          onClick={() => setShowCreate((v) => !v)}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          {showCreate ? "Cancel" : "New project"}
        </button>
      </div>

      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="mb-6 rounded-xl border border-gray-200 bg-white p-4 shadow-sm"
        >
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">Name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="ReactKit Docs"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                autoFocus
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                Docs URL <span className="text-gray-400">(optional)</span>
              </label>
              <input
                value={docsUrl}
                onChange={(e) => setDocsUrl(e.target.value)}
                placeholder="https://docs.example.com"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={creating || !name.trim()}
            className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-gray-400"
          >
            {creating ? "Creating…" : "Create"}
          </button>
        </form>
      )}

      {error && (
        <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="text-sm text-gray-500">Loading…</div>
      ) : projects.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center text-gray-500">
          No projects yet. Create one to get started.
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3 font-medium">Name</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Source</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {projects.map((p) => (
                <tr key={p.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/projects/${p.id}`}
                      className="font-medium text-blue-600 hover:underline"
                    >
                      {p.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {p.docs_url ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleDelete(p.id, p.name)}
                      className="text-xs text-red-600 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
