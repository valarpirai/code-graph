import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { uploadProjectZip } from "../../api/client";
import { projectKeys } from "../../hooks/useProject";

const MAX_BYTES = 200 * 1024 * 1024;

export default function ZipUpload() {
  const [dragging, setDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: uploadProjectZip,
    onSuccess: (project) => {
      qc.invalidateQueries({ queryKey: projectKeys.all });
      navigate(`/projects/${project.id}`);
    },
  });

  const handleFile = useCallback(
    (file: File) => {
      setFileError(null);
      if (!file.name.endsWith(".zip")) {
        setFileError("Only .zip files are supported.");
        return;
      }
      if (file.size > MAX_BYTES) {
        setFileError("File exceeds 200 MB limit.");
        return;
      }
      mutation.mutate(file);
    },
    [mutation]
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={`flex flex-col items-center justify-center gap-3 border-2 border-dashed
                  rounded-lg p-8 cursor-pointer transition-colors
                  ${dragging
                    ? "border-accent-blue bg-accent-blue/5"
                    : "border-surface-border hover:border-gray-500"}`}
    >
      <input
        id="zip-file"
        type="file"
        accept=".zip"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />
      <label htmlFor="zip-file" className="cursor-pointer text-center">
        <p className="text-gray-300 text-sm">
          {mutation.isPending
            ? "Uploading…"
            : "Drop a .zip here, or click to browse"}
        </p>
        <p className="text-gray-600 text-xs mt-1">Max 200 MB</p>
      </label>
      {(fileError ?? mutation.isError) && (
        <p className="text-accent-red text-sm">
          {fileError ?? (mutation.error as Error).message}
        </p>
      )}
    </div>
  );
}
