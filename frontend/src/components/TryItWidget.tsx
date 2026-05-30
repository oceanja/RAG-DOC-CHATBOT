import { useEffect } from "react";
import { API_BASE } from "../api/client";

/**
 * Injects the live embed widget for a project, exactly as a real docs site
 * would. Cleans up the injected <script> and the widget's shadow-host on
 * unmount so navigating away doesn't leave stray bubbles behind.
 */
export default function TryItWidget({ projectId }: { projectId: string }) {
  useEffect(() => {
    const script = document.createElement("script");
    script.src = `${API_BASE}/widget.js?v=${Date.now()}`;
    script.dataset.projectId = projectId;
    script.dataset.apiBase = API_BASE;
    document.body.appendChild(script);

    return () => {
      script.remove();
      document.getElementById("docupilot-host")?.remove();
    };
  }, [projectId]);

  return (
    <p className="text-sm text-gray-500">
      The live widget is loaded on this page — look for the chat bubble in the
      bottom-right corner.
    </p>
  );
}
