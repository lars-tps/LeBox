import { getToken } from "./auth";

const API_BASE = "/api";

export type FolderOut = { id: number; name: string; parent_id: number | null; created_at: string };
export type FileOut = {
  id: number; name: string; folder_id: number | null;
  size_bytes: number; mime_type: string | null; status: string; created_at: string;
};
export type FolderListing = { folder: FolderOut | null; folders: FolderOut[]; files: FileOut[] };
export type UserOut = { id: string; email: string; display_name: string | null };

type UploadInitResponse = {
  file_id: number;
  type: "single" | "multipart";
  url?: string;
  upload_id?: string;
  parts?: { part_number: number; url: string }[];
  part_size_bytes?: number;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const resp = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`${resp.status}: ${text}`);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  devLogin: (email: string, displayName?: string) =>
    request<{ access_token: string }>("/auth/dev-login", {
      method: "POST",
      body: JSON.stringify({ email, display_name: displayName }),
    }),
  me: () => request<UserOut>("/auth/me"),

  listRoot: () => request<FolderListing>("/folders"),
  listFolder: (id: number) => request<FolderListing>(`/folders/${id}`),
  createFolder: (name: string, parentId: number | null) =>
    request<FolderOut>("/folders", { method: "POST", body: JSON.stringify({ name, parent_id: parentId }) }),
  deleteFolder: (id: number) => request<void>(`/folders/${id}`, { method: "DELETE" }),

  uploadInit: (name: string, sizeBytes: number, mimeType: string | null, folderId: number | null) =>
    request<UploadInitResponse>("/files/upload-init", {
      method: "POST",
      body: JSON.stringify({ name, size_bytes: sizeBytes, mime_type: mimeType, folder_id: folderId }),
    }),
  uploadComplete: (fileId: number, parts: { part_number: number; etag: string }[]) =>
    request<FileOut>(`/files/${fileId}/upload-complete`, {
      method: "POST",
      body: JSON.stringify({ parts }),
    }),
  download: (fileId: number) => request<{ url: string; expires_in_seconds: number }>(`/files/${fileId}/download`),
  deleteFile: (id: number) => request<void>(`/files/${id}`, { method: "DELETE" }),
};

/**
 * Upload a file using whichever flow the backend chose.
 * For multipart, uploads parts sequentially (could be parallelized later).
 */
export async function uploadFile(
  file: File,
  folderId: number | null,
  onProgress?: (pct: number) => void,
): Promise<FileOut> {
  const init = await api.uploadInit(file.name, file.size, file.type || null, folderId);

  if (init.type === "single" && init.url) {
    const resp = await fetch(init.url, { method: "PUT", body: file });
    if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
    onProgress?.(100);
    return api.uploadComplete(init.file_id, []);
  }

  // multipart
  const partSize = init.part_size_bytes!;
  const partsResult: { part_number: number; etag: string }[] = [];
  for (const p of init.parts!) {
    const start = (p.part_number - 1) * partSize;
    const end = Math.min(start + partSize, file.size);
    const blob = file.slice(start, end);
    const resp = await fetch(p.url, { method: "PUT", body: blob });
    if (!resp.ok) throw new Error(`Part ${p.part_number} failed: ${resp.status}`);
    const etag = resp.headers.get("ETag");
    if (!etag) throw new Error(`Part ${p.part_number} missing ETag header (CORS ExposeHeaders not configured?)`);
    partsResult.push({ part_number: p.part_number, etag: etag.replace(/"/g, "") });
    onProgress?.(Math.round((p.part_number / init.parts!.length) * 100));
  }
  return api.uploadComplete(init.file_id, partsResult);
}
