export default function Logo({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="docupilot-grad" x1="0" y1="0" x2="24" y2="24">
          <stop offset="0%" stopColor="#6366f1" />
          <stop offset="100%" stopColor="#a855f7" />
        </linearGradient>
      </defs>
      <rect x="2" y="3" width="20" height="16" rx="4" fill="url(#docupilot-grad)" />
      <path
        d="M7 21l3-2.5h4L17 21"
        stroke="url(#docupilot-grad)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="8" cy="11" r="1.4" fill="white" />
      <circle cx="12" cy="11" r="1.4" fill="white" />
      <circle cx="16" cy="11" r="1.4" fill="white" />
    </svg>
  );
}
