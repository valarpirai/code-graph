import type { Project } from "../../api/types";
export default function ProjectHeader({ project }: { project: Project }) {
  return <div className="px-4 py-2 border-b border-surface-border text-sm text-gray-300">{project.name}</div>;
}
