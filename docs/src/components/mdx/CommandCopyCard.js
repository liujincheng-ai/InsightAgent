import React, { useCallback, useState } from "react";

export default function CommandCopyCard({ command }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch (error) {
      setCopied(false);
    }
  }, [command]);

  return (
    <div className="quickstart-command-card quickstart-command-card--interactive">
      <button
        type="button"
        className="quickstart-copy-button"
        onClick={handleCopy}
        aria-label={copied ? "Copied command" : "Copy command"}
      >
        {copied ? (
          <span className="quickstart-copy-button-label">Copied</span>
        ) : (
          <svg viewBox="0 0 24 24" aria-hidden="true" className="quickstart-copy-icon">
            <path
              d="M9 9a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2z"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <path
              d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </button>
      <pre>
        <code>{command}</code>
      </pre>
    </div>
  );
}
