// サーバの JSON API を叩くための薄いラッパ。
//
// サーバは状態を持たないので、ここも持たない。SSE で「変わった」と言われたら
// 単純に取り直す。書き込みも楽観的更新をせず、応答で置き換えるか取り直す。

class ApiError extends Error {
  constructor(payload, status, body) {
    super((payload && payload.message) || `HTTP ${status}`);
    this.cause_ = (payload && payload.cause) || "";
    this.remedy = (payload && payload.remedy) || "";
    this.status = status;
    // 409 のときサーバが添えてくる「いま保存されている内容」。
    // 画面が最新を出し直すのに使う。
    this.current = (body && body.current) || null;
  }

  get isConflict() {
    return this.status === 409;
  }
}

async function request(path, { method = "GET", body, ifMatch } = {}) {
  const headers = { Accept: "application/json" };
  const init = { method, headers };
  if (method !== "GET") {
    // JSON を必須にしているのはサーバ側の CSRF 対策の一部（クロスオリジンでは
    // プリフライトが必要になり、サーバは OPTIONS を返さない）。
    headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body || {});
  }
  if (ifMatch) headers["If-Match"] = ifMatch;

  const response = await fetch(path, init);
  let payload = null;
  try {
    payload = await response.json();
  } catch (e) {
    payload = null;
  }
  if (!response.ok) {
    throw new ApiError(payload && payload.error, response.status, payload);
  }
  return payload;
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
  // --- 読み取り ---
  state: () => request("/api/state"),
  overview: () => request("/api/overview"),
  allTasks: (filters = {}) => request(`/api/tasks${query(filters)}`),
  tasks: (project, filters = {}) => request(`${tasksPath(project)}${query(filters)}`),
  task: (project, id) => request(`${tasksPath(project)}/${id}`),
  search: (q) => request(`/api/search?q=${encodeURIComponent(q)}`),

  // --- 書き込み ---
  // 既存タスクを変える操作はすべて version（いま画面が見ている updated_at）を
  // 要求する。省略すると 428 で拒否される。
  create: (project, fields) =>
    request(tasksPath(project), { method: "POST", body: fields }),
  edit: (project, id, fields, version) =>
    request(`${tasksPath(project)}/${id}`, { method: "PATCH", body: fields, ifMatch: version }),
  transition: (project, id, action, version) =>
    request(`${tasksPath(project)}/${id}/${action}`, { method: "POST", ifMatch: version }),
  remove: (project, id, version) =>
    request(`${tasksPath(project)}/${id}`, { method: "DELETE", ifMatch: version }),
  move: (project, id, target, version) =>
    request(`${tasksPath(project)}/${id}/move`, {
      method: "POST",
      body: { project: target },
      ifMatch: version,
    }),
};

// リビジョンが変わったら onChange を呼ぶ。EventSource はネットワークが切れると
// 自動で再接続し、サーバは接続直後に現在値を1度送るので取りこぼさない。
export function subscribe(onChange) {
  const source = new EventSource("/api/events");
  source.addEventListener("revision", (event) => onChange(event.data));
  return () => source.close();
}

export { ApiError };
