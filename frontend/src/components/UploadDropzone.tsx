"use client";

import { useRef, useState } from "react";
import { ApiError, uploadDocument } from "@/lib/api";

interface UploadDropzoneProps {
  onUploaded: () => void;
}

export function UploadDropzone({ onUploaded }: UploadDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  async function uploadFiles(files: FileList | File[]) {
    setIsUploading(true);
    const failures: string[] = [];

    for (const file of Array.from(files)) {
      try {
        await uploadDocument(file);
      } catch (err) {
        const message = err instanceof ApiError ? err.message : "Upload failed";
        failures.push(`${file.name}: ${message}`);
      }
    }

    setErrors(failures);
    setIsUploading(false);
    onUploaded();
  }

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragActive(true);
        }}
        onDragLeave={() => setIsDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragActive(false);
          if (e.dataTransfer.files.length) {
            void uploadFiles(e.dataTransfer.files);
          }
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-12 text-center transition-colors ${
          isDragActive
            ? "border-blue-500 bg-blue-50 dark:bg-blue-950/30"
            : "border-zinc-300 hover:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-600"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.csv,.xlsx,.txt,.docx"
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) {
              void uploadFiles(e.target.files);
            }
            e.target.value = "";
          }}
        />
        <p className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
          {isUploading ? "Uploading…" : "Drag and drop files here, or click to browse"}
        </p>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-500">
          PDF and CSV/XLSX go through structured extraction. TXT and DOCX are stored but not yet parsed.
        </p>
      </div>
      {errors.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm text-red-600 dark:text-red-400">
          {errors.map((message) => (
            <li key={message}>{message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
