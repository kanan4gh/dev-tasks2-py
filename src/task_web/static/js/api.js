// サーバの JSON API を叩くための薄いラッパ。
//
// サーバは状態を持たないので、ここも持たない。SSE で「変わった」と言われたら
// 単純に取り直す。

class ApiError extends Error {
  constructor(payload, status) {
    super((payload && payload.message) || `HTTP ${status}`);
    this.cause_ = (payload && payload.cause) || "";
    this.remedy = (payload && payload.remedy) || "";
    this.status = status;
  }
}

async function get(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  let body = null;
  try {
    body = await response.json();
  } catch (e) {
    body = null;
  }
  if (!response.ok) {
    throw new ApiError(body && body.error, response.status);
  }
  return body;
}

// Inbox と名前付きプロジェクトはパスが分かれている。`inbox` という名前の
// プロジェクトがあっても衝突しない。
function tasksPath(project) {
  return project === null
    ? "/api/inbox/tasks"
    : `/api/projects/${encodeURIComponent(project)}/tasks`;
}

function query(filters) {
  const params = new URLSearchParams();
  (filters.status || []).forEach((s) => params.append("status", s));
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.sort && filters.sort !== "id") params.set("sort", filters.sort);
  const s = params.toString();
  return s ? `?${s}` : "";
}

export const api = {
  state: () => get("/api/state"),
  overview: () => get("/api/overview"),
  allTasks: (filters = {}) => get(`/api/tasks${query(filters)}`),
  tasks: (project, filters = {}) => get(`${tasksPath(project)}${query(filters)}`),
  task: (project, id) => get(`${tasksPath(project)}/${id}`),
  search: (q) => get(`/api/search?q=${encodeURIComponent(q)}`),
};

// リビジョンが変わったら onChange を呼ぶ。EventSource はネットワークが切れると
// 自動で再接続し、サーバは接続直後に現在値を1度送るので取りこぼさない。
export function subscribe(onChange) {
  const source = new EventSource("/api/events");
  source.addEventListener("revision", (event) => onChange(event.data));
  return () => source.close();
}

export { ApiError };
