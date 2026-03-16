interface Props {
  message: string;
  progress: number; // 0–100
}

export default function IndexingStatus({ message, progress }: Props) {
  return (
    <div className="shrink-0 border-b border-surface-border">
      {/* Progress bar */}
      <div className="h-0.5 bg-surface-border">
        <div
          className="h-0.5 bg-accent-blue transition-all duration-300"
          style={{ width: `${Math.min(progress, 100)}%` }}
        />
      </div>
      {/* Message */}
      {message && (
        <p className="px-4 py-1.5 text-xs text-gray-500 bg-surface-elevated">
          {message}
        </p>
      )}
    </div>
  );
}
