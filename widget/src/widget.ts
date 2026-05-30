import { CSS } from "./styles";

interface Citation {
  chunk_id: string;
  document_id: string;
  title: string;
  url: string | null;
  snippet: string;
}

const scriptEl = document.currentScript as HTMLScriptElement | null;

function resolveConfig(): { projectId: string; apiBase: string } {
  const projectId = scriptEl?.dataset.projectId || "";
  let apiBase = scriptEl?.dataset.apiBase || "";
  if (!apiBase && scriptEl?.src) {
    try {
      apiBase = new URL(scriptEl.src).origin;
    } catch {
      apiBase = window.location.origin;
    }
  }
  if (!apiBase) apiBase = window.location.origin;
  return { projectId, apiBase };
}

const escapeHtml = (s: string): string =>
  s.replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!,
  );

function renderMarkdown(src: string): string {
  let s = escapeHtml(src);
  s = s.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  s = s.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  s = s.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>',
  );
  const paragraphs = s
    .split(/\n\s*\n/)
    .map((p) => `<p>${p.replace(/\n/g, "<br>")}</p>`);
  return paragraphs.join("");
}

async function* sseEvents(
  response: Response,
): AsyncGenerator<{ raw: string }, void, void> {
  if (!response.body) throw new Error("No response body");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const line = part.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      yield { raw: line.slice(6) };
    }
  }
}

class Widget {
  private shadow: ShadowRoot;
  private panel!: HTMLElement;
  private messages!: HTMLElement;
  private input!: HTMLTextAreaElement;
  private sendBtn!: HTMLButtonElement;
  private busy = false;
  private projectId: string;
  private apiBase: string;

  constructor(projectId: string, apiBase: string) {
    this.projectId = projectId;
    this.apiBase = apiBase;

    const host = document.createElement("div");
    host.id = "docupilot-host";
    document.body.appendChild(host);
    this.shadow = host.attachShadow({ mode: "open" });
    this.shadow.innerHTML = this.html();
    this.bind();
  }

  private html(): string {
    return `
      <style>${CSS}</style>
      <button class="bubble" aria-label="Open chat">💬</button>
      <div class="panel" role="dialog" aria-label="Documentation chat">
        <div class="header">
          <div class="header-title">Ask the docs</div>
          <button class="header-close" aria-label="Close">×</button>
        </div>
        <div class="messages"></div>
        <div class="powered">Powered by DocuPilot</div>
        <div class="input-row">
          <textarea class="input" rows="1" placeholder="Ask a question…"></textarea>
          <button class="send">Send</button>
        </div>
      </div>
    `;
  }

  private bind(): void {
    const $ = <T extends HTMLElement>(sel: string) =>
      this.shadow.querySelector(sel) as T;
    this.panel = $(".panel");
    this.messages = $(".messages");
    this.input = $<HTMLTextAreaElement>(".input");
    this.sendBtn = $<HTMLButtonElement>(".send");

    $(".bubble").addEventListener("click", () => this.panel.classList.add("open"));
    $(".header-close").addEventListener("click", () =>
      this.panel.classList.remove("open"),
    );
    this.sendBtn.addEventListener("click", () => this.submit());
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        this.submit();
      }
    });

    if (!this.projectId) {
      this.renderError("Missing data-project-id on widget script tag.");
    }
  }

  private appendUser(text: string): void {
    const el = document.createElement("div");
    el.className = "msg msg-user";
    el.innerHTML = `<div class="bubble-body">${escapeHtml(text)}</div>`;
    this.messages.appendChild(el);
    this.scroll();
  }

  private appendBotShell(): {
    body: HTMLElement;
    citations: HTMLElement;
    typing: HTMLElement;
  } {
    const el = document.createElement("div");
    el.className = "msg msg-bot";
    el.innerHTML = `
      <div class="bubble-body"><span class="bot-text"></span></div>
      <div class="typing"><span></span><span></span><span></span></div>
      <div class="citations"></div>
    `;
    this.messages.appendChild(el);
    this.scroll();
    return {
      body: el.querySelector(".bot-text") as HTMLElement,
      citations: el.querySelector(".citations") as HTMLElement,
      typing: el.querySelector(".typing") as HTMLElement,
    };
  }

  private renderError(msg: string): void {
    const el = document.createElement("div");
    el.className = "error";
    el.textContent = msg;
    this.messages.appendChild(el);
    this.scroll();
  }

  private scroll(): void {
    this.messages.scrollTop = this.messages.scrollHeight;
  }

  private renderCitations(container: HTMLElement, items: Citation[]): void {
    container.innerHTML = "";
    items.forEach((c, i) => {
      const el = document.createElement(c.url ? "a" : "span");
      el.className = "citation";
      el.setAttribute("title", c.snippet);
      el.innerHTML = `<span class="citation-num">[${i + 1}]</span>${escapeHtml(c.title)}`;
      if (c.url && el instanceof HTMLAnchorElement) {
        el.href = c.url;
        el.target = "_blank";
        el.rel = "noopener";
      }
      container.appendChild(el);
    });
  }

  private async submit(): Promise<void> {
    if (this.busy) return;
    const question = this.input.value.trim();
    if (!question) return;
    if (!this.projectId) {
      this.renderError("Missing data-project-id on widget script tag.");
      return;
    }

    this.busy = true;
    this.sendBtn.disabled = true;
    this.input.value = "";
    this.appendUser(question);
    const { body, citations, typing } = this.appendBotShell();

    let raw = "";
    try {
      const response = await fetch(`${this.apiBase}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: this.projectId, question }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      let firstToken = true;
      for await (const { raw: data } of sseEvents(response)) {
        if (data === "[DONE]") break;
        let parsed: { type: string; text?: string; items?: Citation[]; message?: string };
        try {
          parsed = JSON.parse(data);
        } catch {
          continue;
        }
        if (parsed.type === "token" && parsed.text) {
          if (firstToken) {
            typing.remove();
            firstToken = false;
          }
          raw += parsed.text;
          body.innerHTML = renderMarkdown(raw);
          this.scroll();
        } else if (parsed.type === "citations" && parsed.items) {
          this.renderCitations(citations, parsed.items);
          this.scroll();
        } else if (parsed.type === "error") {
          throw new Error(parsed.message || "Unknown error");
        }
      }
      if (firstToken) typing.remove();
    } catch (err) {
      typing.remove();
      body.innerHTML = `<em>Sorry — something went wrong: ${escapeHtml(
        err instanceof Error ? err.message : String(err),
      )}</em>`;
    } finally {
      this.busy = false;
      this.sendBtn.disabled = false;
    }
  }
}

function init(): void {
  const { projectId, apiBase } = resolveConfig();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => new Widget(projectId, apiBase));
  } else {
    new Widget(projectId, apiBase);
  }
}

init();
