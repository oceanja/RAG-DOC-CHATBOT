import type { ProjectStatus } from "../types";

const STYLES: Record<ProjectStatus, string> = {
  pending: "bg-gray-100 text-gray-700",
  crawling: "bg-blue-100 text-blue-700",
  embedding: "bg-amber-100 text-amber-700",
  ready: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

export default function StatusBadge({ status }: { status: ProjectStatus }) {
  const busy = status === "crawling" || status === "embedding";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}
    >
      {busy && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
      )}
      {status}
    </span>
  );
}
