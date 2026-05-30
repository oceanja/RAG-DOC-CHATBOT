import { useEffect, useState } from "react";
import { listQuestions } from "../api/projects";
import type { Question } from "../types";

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const secs = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return new Date(iso).toLocaleDateString();
}

export default function RecentQuestions({ projectId }: { projectId: string }) {
  const [questions, setQuestions] = useState<Question[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    listQuestions(projectId, 100)
      .then(setQuestions)
      .catch(() => setError("Failed to load questions."));
  }, [projectId]);

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (questions === null) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-12 animate-pulse rounded-lg bg-gray-100" />
        ))}
      </div>
    );
  }

  if (questions.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center text-gray-500">
        No questions yet. Ask one in the widget — it'll show up here.
      </div>
    );
  }

  return (
    <div className="divide-y divide-gray-100 overflow-hidden rounded-xl border border-gray-200 bg-white">
      {questions.map((q) => {
        const open = openId === q.id;
        return (
          <div key={q.id}>
            <button
              onClick={() => setOpenId(open ? null : q.id)}
              className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50"
            >
              <span className="truncate text-sm font-medium">
                {q.question_text}
              </span>
              <span className="shrink-0 text-xs text-gray-400">
                {timeAgo(q.created_at)}
              </span>
            </button>
            {open && (
              <div className="bg-gray-50 px-4 py-3 text-sm">
                <p className="whitespace-pre-wrap text-gray-700">
                  {q.answer_text}
                </p>
                {q.citations.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {q.citations.map((c, i) =>
                      c.url ? (
                        <a
                          key={c.chunk_id + i}
                          href={c.url}
                          target="_blank"
                          rel="noopener"
                          className="rounded-full border border-gray-300 bg-white px-2.5 py-0.5 text-xs text-gray-600 hover:bg-gray-100"
                        >
                          <span className="font-semibold text-blue-600">
                            [{i + 1}]
                          </span>{" "}
                          {c.title ?? "source"}
                        </a>
                      ) : (
                        <span
                          key={c.chunk_id + i}
                          className="rounded-full border border-gray-300 bg-white px-2.5 py-0.5 text-xs text-gray-600"
                        >
                          <span className="font-semibold text-blue-600">
                            [{i + 1}]
                          </span>{" "}
                          {c.title ?? "source"}
                        </span>
                      ),
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
