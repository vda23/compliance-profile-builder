const API_BASE = "/api";

async function apiRequest(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(API_BASE + path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch (e) { /* ignore */ }
    throw new Error(detail);
  }
  const ctype = res.headers.get("content-type") || "";
  if (ctype.includes("application/json")) return res.json();
  return res;
}

const api = {
  get: (path) => apiRequest("GET", path),
  post: (path, body) => apiRequest("POST", path, body),
  put: (path, body) => apiRequest("PUT", path, body),
  del: (path) => apiRequest("DELETE", path),

  async uploadDocument(path, file, params) {
    // Документ отправляется «как есть», параметры — в строке запроса.
    // Кириллица в параметрах обязательно кодируется: стандартный
    // HTTP-сервер отклоняет запросы с не-ASCII в строке запроса.
    const qs = Object.entries(params || {})
      .filter(([, v]) => v != null && v !== "")
      .map(([k, v]) => encodeURIComponent(k) + "=" + encodeURIComponent(v))
      .join("&");
    const res = await fetch(API_BASE + path + (qs ? "?" + qs : ""), {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: file,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { const data = await res.json(); detail = data.detail || detail; } catch (e) {}
      throw new Error(detail);
    }
    return res.json();
  },

  async importZip(projectId, file) {
    // Архив отправляется «как есть» (application/zip), идентификатор
    // проекта — в строке запроса. Серверу не нужен разбор multipart,
    // поэтому он обходится стандартной библиотекой Python.
    const url = API_BASE + "/projects/import?project_id=" + encodeURIComponent(projectId);
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/zip" },
      body: file,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try { const data = await res.json(); detail = data.detail || detail; } catch (e) {}
      throw new Error(detail);
    }
    return res.json();
  },

  exportUrl(projectId) {
    return API_BASE + `/projects/${encodeURIComponent(projectId)}/export`;
  },
};
