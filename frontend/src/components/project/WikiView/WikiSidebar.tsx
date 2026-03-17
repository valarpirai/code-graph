import type { WikiFile } from "../../../api/types";

interface Props {
  files: WikiFile[];
  selected: string | null;
  onSelect: (name: string) => void;
}

export default function WikiSidebar({ files, selected, onSelect }: Props) {
  if (files.length === 0) {
    return (
      <div className="p-4 text-gray-600 text-xs">No wiki pages yet.</div>
    );
  }

  return (
    <ul className="flex flex-col gap-0.5 p-2">
      {files.map((f) => (
        <li key={f.path}>
          <button
            onClick={() => onSelect(f.path)}
            className={`w-full text-left text-xs px-3 py-2 rounded transition-colors
                        ${
                          selected === f.path
                            ? "bg-accent-blue/20 text-accent-blue"
                            : "text-gray-400 hover:bg-surface-elevated hover:text-gray-200"
                        }`}
          >
            {f.name}
          </button>
        </li>
      ))}
    </ul>
  );
}
