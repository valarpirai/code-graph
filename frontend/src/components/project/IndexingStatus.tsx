interface Props { message: string; progress: number; }
export default function IndexingStatus({ message, progress }: Props) {
  return (
    <div className="h-1 bg-surface-border">
      <div className="h-1 bg-accent-blue transition-all" style={{ width: `${progress}%` }} />
    </div>
  );
}
