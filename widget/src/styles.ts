export const CSS = `
:host, * { box-sizing: border-box; }

.bubble {
  position: fixed;
  bottom: 24px;
  right: 24px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: #111827;
  color: #fff;
  border: none;
  cursor: pointer;
  box-shadow: 0 8px 20px rgba(0,0,0,0.18);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  z-index: 2147483646;
  transition: transform .15s ease;
}
.bubble:hover { transform: scale(1.05); }

.panel {
  position: fixed;
  bottom: 96px;
  right: 24px;
  width: 380px;
  max-width: calc(100vw - 32px);
  height: 520px;
  max-height: calc(100vh - 120px);
  background: #fff;
  color: #111827;
  border-radius: 14px;
  box-shadow: 0 12px 32px rgba(0,0,0,0.18);
  display: none;
  flex-direction: column;
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 14px;
  line-height: 1.45;
  z-index: 2147483647;
}
.panel.open { display: flex; }

.header {
  padding: 12px 16px;
  background: #111827;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-title { font-weight: 600; font-size: 14px; }
.header-close {
  background: transparent;
  border: none;
  color: #fff;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
  padding: 0 4px;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  background: #f9fafb;
}
.msg { margin-bottom: 14px; max-width: 90%; word-wrap: break-word; }
.msg-user { margin-left: auto; }
.msg-user .bubble-body {
  background: #4f46e5;
  color: #fff;
  padding: 8px 12px;
  border-radius: 12px 12px 2px 12px;
  display: inline-block;
}
.msg-bot .bubble-body {
  background: #fff;
  color: #111827;
  padding: 8px 12px;
  border-radius: 12px 12px 12px 2px;
  border: 1px solid #e5e7eb;
  display: inline-block;
}
.msg-bot .bubble-body p { margin: 0 0 8px 0; }
.msg-bot .bubble-body p:last-child { margin-bottom: 0; }
.msg-bot .bubble-body code {
  background: #f3f4f6;
  padding: 1px 5px;
  border-radius: 4px;
  font-family: ui-monospace, Menlo, Consolas, monospace;
  font-size: 12.5px;
}
.msg-bot .bubble-body a { color: #4f46e5; }

.typing {
  display: inline-flex;
  gap: 4px;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px 12px 12px 2px;
}
.typing span {
  width: 6px; height: 6px; border-radius: 50%;
  background: #9ca3af;
  animation: blink 1.2s infinite ease-in-out;
}
.typing span:nth-child(2) { animation-delay: .2s; }
.typing span:nth-child(3) { animation-delay: .4s; }
@keyframes blink {
  0%, 60%, 100% { opacity: .3; }
  30% { opacity: 1; }
}

.citations {
  margin-top: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.citation {
  font-size: 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 3px 10px;
  color: #374151;
  text-decoration: none;
  cursor: pointer;
}
.citation:hover { background: #f3f4f6; }
.citation-num {
  display: inline-block;
  font-weight: 600;
  color: #4f46e5;
  margin-right: 4px;
}

.input-row {
  display: flex;
  border-top: 1px solid #e5e7eb;
  background: #fff;
  padding: 8px;
  gap: 6px;
}
.input {
  flex: 1;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 14px;
  font-family: inherit;
  resize: none;
  outline: none;
}
.input:focus { border-color: #4f46e5; }
.send {
  background: #4f46e5;
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 0 14px;
  cursor: pointer;
  font-weight: 600;
}
.send:disabled { background: #9ca3af; cursor: not-allowed; }

.error { color: #b91c1c; font-size: 12px; padding: 6px 12px; }

.powered {
  text-align: center;
  font-size: 11px;
  color: #9ca3af;
  padding: 4px 0 6px;
  background: #fff;
}
`;
