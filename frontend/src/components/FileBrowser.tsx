import { useEffect, useRef, useState } from "react";
import { api, FolderListing, FolderOut, uploadFile } from "../api";

type Crumb = { id: number | null; name: string };

export function FileBrowser() {
  const [listing, setListing] = useState<FolderListing | null>(null);
  const [crumbs, setCrumbs] = useState<Crumb[]>([{ id: null, name: "Home" }]);
  const [error, setError] = useState<string | null>(null);
  const [uploadPct, setUploadPct] = useState<number | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const currentId = crumbs[crumbs.length - 1].id;

  const load = async (id: number | null) => {
    setError(null);
    try {
      const data = id == null ? await api.listRoot() : await api.listFolder(id);
      setListing(data);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => { load(currentId); }, [currentId]);

  const enterFolder = (f: FolderOut) => setCrumbs([...crumbs, { id: f.id, name: f.name }]);
  const goCrumb = (i: number) => setCrumbs(crumbs.slice(0, i + 1));

  const newFolder = async () => {
    const name = prompt("Folder name:");
    if (!name) return;
    try {
      await api.createFolder(name, currentId);
      load(currentId);
    } catch (e: any) { setError(e.message); }
  };

  const deleteFolder = async (id: number) => {
    if (!confirm("Delete folder and everything in it?")) return;
    try {
      await api.deleteFolder(id);
      load(currentId);
    } catch (e: any) { setError(e.message); }
  };

  const deleteFile = async (id: number) => {
    if (!confirm("Delete file?")) return;
    try {
      await api.deleteFile(id);
      load(currentId);
    } catch (e: any) { setError(e.message); }
  };

  const download = async (id: number) => {
    try {
      const { url } = await api.download(id);
      window.location.href = url;
    } catch (e: any) { setError(e.message); }
  };

  const onFilePicked = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadPct(0);
    try {
      await uploadFile(file, currentId, setUploadPct);
      load(currentId);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploadPct(null);
      if (fileInput.current) fileInput.current.value = "";
    }
  };

  return (
    <div className="container">
      <div className="crumbs">
        {crumbs.map((c, i) => (
          <span key={i}>
            {i > 0 && " / "}
            <a onClick={() => goCrumb(i)}>{c.name}</a>
          </span>
        ))}
      </div>

      <div className="toolbar">
        <button className="primary" onClick={() => fileInput.current?.click()}>
          Upload file
        </button>
        <input ref={fileInput} type="file" style={{ display: "none" }} onChange={onFilePicked} />
        <button onClick={newFolder}>New folder</button>
        {uploadPct !== null && <span className="upload-progress">Uploading… {uploadPct}%</span>}
      </div>

      {error && <div className="error">{error}</div>}

      {listing && (
        <div>
          {listing.folders.length === 0 && listing.files.length === 0 && (
            <p style={{ color: "#888" }}>This folder is empty.</p>
          )}
          {listing.folders.map((f) => (
            <div className="row" key={`d${f.id}`}>
              <span className="name" onClick={() => enterFolder(f)}>📁 {f.name}</span>
              <button onClick={() => deleteFolder(f.id)}>Delete</button>
            </div>
          ))}
          {listing.files.map((f) => (
            <div className="row" key={`f${f.id}`}>
              <span className="name" onClick={() => download(f.id)}>📄 {f.name}</span>
              <span className="meta">{formatSize(f.size_bytes)}</span>
              <button onClick={() => download(f.id)}>Download</button>
              <button onClick={() => deleteFile(f.id)}>Delete</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function formatSize(b: number): string {
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0; let n = b;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i === 0 ? 0 : 1)} ${u[i]}`;
}
