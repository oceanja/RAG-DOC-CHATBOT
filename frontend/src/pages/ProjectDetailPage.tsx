import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getProject, ingestMarkdown, ingestUrl } from "../api/projects";
import RecentQuestions from "../components/RecentQuestions";
import StatusBadge from "../components/StatusBadge";
import TryItWidget from "../components/TryItWidget";
import type { ProjectDetail } from "../types";

const POLL_MS = 2000;
// `pending` = never ingested (button should be enabled). Worker-driven states
// are the only "busy" ones.
const BUSY = new Set(["crawling", "embedding"]);

type Tab = "setup" | "questions";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("setup");
  const [toast, setToast] = useState<string | null>(null);

  const [mode, setMode] = useState<"markdown" | "url">("markdown");
  const [markdown, setMarkdown] = useState("");
  const [url, setUrl] = useState("");
  const [maxPages, setMaxPages] = useState(50);
  const [submitting, setSubmitting] = useState(false);
  const [copied, setCopied] = useState(false);

  const pollRef = useRef<number | null>(null);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2500);
  }

  const load = useCallback(async () => {
    if (!id) return;
    try {
      setProject(await getProject(id));
      setError(null);
    } catch {
      setError("Failed to load project.");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!project) return;
    if (BUSY.has(project.status)) {
      pollRef.current = window.setInterval(load, POLL_MS);
      return () => {
        if (pollRef.current) window.clearInterval(pollRef.current);
      };
    }
  }, [project, load]);

  async function handleIngest(e: React.FormEvent) {
    e.preventDefault();
    if (!id) return;
    setSubmitting(true);
    try {
      if (mode === "markdown") {
        if (!markdown.trim()) return;
        await ingestMarkdown(id, markdown);
      } else {
        if (!url.trim()) return;
        await ingestUrl(id, url.trim(), maxPages);
      }
      showToast("Ingestion started");
      await load();
    } catch {
      setError("Failed to start ingestion.");
    } finally {
      setSubmitting(false);
    }
  }

  async function copySnippet() {
    if (!project) return;
    await navigator.clipboard.writeText(project.embed_snippet);
    setCopied(true);
    showToast("Snippet copied to clipboard");
    setTimeout(() => setCopied(false), 1500);
  }

  if (error && !project) {
    return (
      <div>
        <Link to="/" className="text-sm text-blue-600 hover:underline">
          ← Back
        </Link>
        <div className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="space-y-3">
        <div className="h-8 w-48 animate-pulse rounded bg-gray-200" />
        <div className="h-40 animate-pulse rounded-xl bg-gray-100" />
      </div>
    );
  }

  const isReady = project.status === "ready";
  const isBusy = BUSY.has(project.status);

  return (
    <div>
      {toast && (
        <div className="fixed right-6 top-6 z-50 rounded-lg bg-gray-900 px-4 py-2 text-sm text-white shadow-lg">
          {toast}
        </div>
      )}

      <Link to="/" className="text-sm text-blue-600 hover:underline">
        ← All projects
      </Link>

      <div className="mt-3 mb-5 flex items-center justify-between">
        <h1 className="text-2xl font-bold">{project.name}</h1>
        <StatusBadge status={project.status} />
      </div>

      {project.status === "failed" && project.error_message && (
        <div className="mb-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
          <strong>Ingestion failed:</strong> {project.error_message}
        </div>
      )}

      <div className="mb-6 flex gap-1 border-b border-gray-200">
        {(["setup", "questions"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
              tab === t
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "setup" ? "Setup" : "Recent Questions"}
          </button>
        ))}
      </div>

      {tab === "questions" ? (
        <RecentQuestions projectId={project.id} />
      ) : (
        <>
          <div className="grid gap-6 lg:grid-cols-2">
            <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold">Ingest docs</h2>

              <div className="mb-4 inline-flex rounded-lg border border-gray-200 p-0.5 text-sm">
                <button
                  onClick={() => setMode("markdown")}
                  className={`rounded-md px-3 py-1.5 ${
                    mode === "markdown" ? "bg-blue-600 text-white" : "text-gray-600"
                  }`}
                >
                  Markdown
                </button>
                <button
                  onClick={() => setMode("url")}
                  className={`rounded-md px-3 py-1.5 ${
                    mode === "url" ? "bg-blue-600 text-white" : "text-gray-600"
                  }`}
                >
                  URL crawl
                </button>
              </div>

              <form onSubmit={handleIngest}>
                {mode === "markdown" ? (
                  <textarea
                    value={markdown}
                    onChange={(e) => setMarkdown(e.target.value)}
                    placeholder="# Getting Started&#10;&#10;Paste your markdown docs here…"
                    rows={8}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-xs focus:border-blue-500 focus:outline-none"
                  />
                ) : (
                  <div className="space-y-3">
                    <input
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      placeholder="https://docs.example.com"
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                    />
                    <label className="block text-sm text-gray-600">
                      Max pages
                      <input
                        type="number"
                        min={1}
                        max={1000}
                        value={maxPages}
                        onChange={(e) => setMaxPages(Number(e.target.value))}
                        className="ml-2 w-24 rounded-lg border border-gray-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
                      />
                    </label>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={submitting || isBusy}
                  className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-gray-400"
                >
                  {isBusy ? "Ingesting…" : submitting ? "Starting…" : "Ingest"}
                </button>
                {isBusy && (
                  <span className="ml-3 text-xs text-gray-500">
                    Status updates automatically.
                  </span>
                )}
                {isReady && project.last_ingested_at && (
                  <span className="ml-3 text-xs text-gray-500">
                    Re-ingesting replaces existing docs.
                  </span>
                )}
              </form>
            </section>

            <section className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold">Embed snippet</h2>
              <p className="mb-3 text-sm text-gray-500">
                Paste this into your docs site, just before{" "}
                <code>&lt;/body&gt;</code>.
              </p>
              <pre className="overflow-x-auto rounded-lg bg-gray-900 p-3 text-xs text-gray-100">
                {project.embed_snippet}
              </pre>
              <button
                onClick={copySnippet}
                className="mt-3 rounded-lg border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
              >
                {copied ? "Copied!" : "Copy snippet"}
              </button>
            </section>
          </div>

          <section className="mt-6 rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">Try it</h2>
            {isReady ? (
              <TryItWidget projectId={project.id} />
            ) : (
              <p className="text-sm text-gray-500">
                Ingest some docs and wait for status <strong>ready</strong> to
                test the widget here.
              </p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
