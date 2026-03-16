import { useState } from "react";

interface Props { onSearch: (term: string) => void; placeholder?: string; }

export default function SearchBar({ onSearch, placeholder = "Search nodes…" }: Props) {
  const [value, setValue] = useState("");
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
    onSearch(e.target.value);
  };
  return (
    <div className="relative">
      <span className="absolute inset-y-0 left-3 flex items-center text-gray-600 text-xs select-none">⌕</span>
      <input type="text" value={value} onChange={handleChange} placeholder={placeholder}
        className="w-full bg-surface border border-surface-border rounded pl-7 pr-3 py-1.5 text-sm text-gray-200 placeholder-gray-600 focus:outline-none focus:border-accent-blue transition-colors" />
    </div>
  );
}
