import type { ProjectStatus } from "../../api/types";

const STATUS_STYLES: Record<ProjectStatus, string> = {
  pending: "bg-gray-700 text-gray-300",
  cloning: "bg-yellow-900/50 text-accent-yellow",
  indexing: "bg-blue-900/50 text-accent-blue animate-pulse",
  ready: "bg-green-900/50 text-accent-green",
  error: "bg-red-900/50 text-accent-red",
};

interface Props {
  status: ProjectStatus;
}

export default function StatusBadge({ status }: Props) {
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_STYLES[status]}`}
    >
      {status}
    </span>
  );
}
