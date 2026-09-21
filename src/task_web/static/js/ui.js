// 表示部品。vendor は UMD なのでグローバルから取る。
const { createElement } = window.React;
export const html = window.htm.bind(createElement);

const STATUS_LABEL = {
  open: "open",
  in_progress: "in progress",
  completed: "completed",
  archived: "archived",
};

export function formatDuration(seconds) {
  if (!seconds) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h) return `${h}h ${m}m`;
  if (m) return `${m}m ${s}s`;
  return `${s}s`;
}

export function formatDateTime(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString("ja-JP", { dateStyle: "medium", timeStyle: "short" });
}

export function Badge({ kind, value }) {
  const label = kind === "status" ? STATUS_LABEL[value] || value : value;
  return html`<span class=${`badge ${kind}-${value}`}>${label}</span>`;
}

// 行から直接できる状態変更。can_transition_to と同じ規則を画面側にも置くと
// 二重管理になるので、**押せるかどうかだけ**を現在のステータスから決め、
// 可否の最終判断はサーバに任せる（できなければエラーが返る）。
const ROW_ACTIONS = {
  open: [
    { action: "start", label: "開始" },
    { action: "archive", label: "保留" },
  ],
  in_progress: [{ action: "done", label: "完了" }],
  completed: [{ action: "archive", label: "片付ける" }],
  archived: [],
};

export function TaskRow({ task, project, onOpen, onAction }) {
  const actions = ROW_ACTIONS[task.status] || [];
  return html`
    <li>
      <span class="task-id" onClick=${() => onOpen(project, task.id)}>#${task.id}</span>
      <${Badge} kind="status" value=${task.status} />
      <${Badge} kind="priority" value=${task.priority} />
      <span class="task-title" onClick=${() => onOpen(project, task.id)}>${task.title}</span>
      ${task.due_date && html`<span class="meta">期限 ${task.due_date}</span>`}
      ${task.total_worked_seconds > 0 &&
      html`<span class="meta">${formatDuration(task.total_worked_seconds)}</span>`}
      ${onAction &&
      html`<span class="row-actions">
        ${actions.map(
          ({ action, label }) => html`
            <button
              key=${action}
              type="button"
              onClick=${(e) => {
                e.stopPropagation();
                onAction(project, task, action);
              }}
            >
              ${label}
            </button>
          `
        )}
      </span>`}
    </li>
  `;
}

export function TaskList({ tasks, project, onOpen, onAction }) {
  if (!tasks.length) return html`<p class="empty">タスクはありません</p>`;
  return html`
    <ul class="tasks">
      ${tasks.map(
        (task) => html`<${TaskRow}
          key=${task.id}
          task=${task}
          project=${project}
          onOpen=${onOpen}
          onAction=${onAction}
        />`
      )}
    </ul>
  `;
}

// `grouped_tasks()` の形（inbox + projects）をそのまま描く。
export function GroupedTasks({ groups, onOpen, onAction, emptyMessage }) {
  const sections = [];
  if (groups.inbox && groups.inbox.length) {
    sections.push(html`
      <section class="group" key="inbox">
        <h2>Inbox</h2>
        <${TaskList} tasks=${groups.inbox} project=${null} onOpen=${onOpen} onAction=${onAction} />
      </section>
    `);
  }
  Object.entries(groups.projects || {}).forEach(([name, tasks]) => {
    if (!tasks.length) return;
    sections.push(html`
      <section class="group" key=${`p:${name}`}>
        <h2>${name}</h2>
        <${TaskList} tasks=${tasks} project=${name} onOpen=${onOpen} onAction=${onAction} />
      </section>
    `);
  });
  if (!sections.length) return html`<p class="empty">${emptyMessage}</p>`;
  return html`<div>${sections}</div>`;
}

export function TaskDetail({ project, task, onBack, onEdit, onMove, onDelete }) {
  return html`
    <div class="detail">
      <button class="back" onClick=${onBack}>← 戻る</button>
      <h2>${task.title}</h2>
      <div>
        <${Badge} kind="status" value=${task.status} />
        <${Badge} kind="priority" value=${task.priority} />
        <span class="meta"> ${project === null ? "Inbox" : project} #${task.id}</span>
      </div>
      <dl>
        <dt>期限</dt><dd>${task.due_date || "—"}</dd>
        <dt>解禁日</dt><dd>${task.scheduled_date || "—"}</dd>
        <dt>作成</dt><dd>${formatDateTime(task.created_at)}</dd>
        <dt>更新</dt><dd>${formatDateTime(task.updated_at)}</dd>
        <dt>完了</dt><dd>${formatDateTime(task.completed_at)}</dd>
        <dt>作業時間</dt>
        <dd>
          ${formatDuration(task.total_worked_seconds)}
          ${task.work_sessions.length > 0 &&
          html`
            <ul class="sessions">
              ${task.work_sessions.map(
                (s, i) => html`
                  <li key=${i}>
                    ${formatDateTime(s.started_at)} — ${formatDuration(s.seconds)}
                    ${s.source === "manual" ? "（手動）" : ""}
                  </li>
                `
              )}
            </ul>
          `}
        </dd>
        ${task.branch && html`<dt>ブランチ</dt><dd>${task.branch}</dd>`}
      </dl>
      ${task.description && html`<div class="description">${task.description}</div>`}
      ${onEdit &&
      html`<div class="detail-actions">
        <button type="button" onClick=${onEdit}>編集</button>
        <button type="button" onClick=${onMove}>移動</button>
        <button type="button" class="danger" onClick=${onDelete}>削除</button>
      </div>`}
    </div>
  `;
}

const PRIORITIES = ["high", "medium", "low"];

// 編集フォーム。**入力中の値はこのコンポーネントが持つ**。SSE でリビジョンが
// 変わっても呼び出し側はこれを作り直さないので、打ちかけの内容が消えない。
// 食い違いは保存時に 409 で分かる。
export function TaskForm({ task, title, submitLabel, onSubmit, onCancel, busy }) {
  const { useState } = window.React;
  const [fields, setFields] = useState({
    title: (task && task.title) || "",
    description: (task && task.description) || "",
    priority: (task && task.priority) || "medium",
    due_date: (task && task.due_date) || "",
    scheduled_date: (task && task.scheduled_date) || "",
  });

  const set = (key) => (e) => setFields({ ...fields, [key]: e.target.value });

  return html`
    <form
      class="task-form"
      onSubmit=${(e) => {
        e.preventDefault();
        onSubmit(fields);
      }}
    >
      <h2>${title}</h2>
      <label>
        タイトル
        <input value=${fields.title} onInput=${set("title")} required maxLength="200" />
      </label>
      <label>
        説明
        <textarea rows="4" value=${fields.description} onInput=${set("description")}></textarea>
      </label>
      <div class="form-row">
        <label>
          優先度
          <select value=${fields.priority} onChange=${set("priority")}>
            ${PRIORITIES.map((p) => html`<option key=${p} value=${p}>${p}</option>`)}
          </select>
        </label>
        <label>
          期限
          <input type="date" value=${fields.due_date} onInput=${set("due_date")} />
        </label>
        <label>
          解禁日
          <input type="date" value=${fields.scheduled_date} onInput=${set("scheduled_date")} />
        </label>
      </div>
      <div class="form-actions">
        <button type="submit" disabled=${busy}>${submitLabel}</button>
        <button type="button" onClick=${onCancel} disabled=${busy}>やめる</button>
      </div>
    </form>
  `;
}

export function MoveForm({ task, project, projects, onSubmit, onCancel, busy }) {
  const { useState } = window.React;
  const [target, setTarget] = useState(project === null ? "" : project);

  return html`
    <form
      class="task-form"
      onSubmit=${(e) => {
        e.preventDefault();
        onSubmit(target === "" ? null : target);
      }}
    >
      <h2>「${task.title}」を移動</h2>
      <label>
        移動先
        <select value=${target} onChange=${(e) => setTarget(e.target.value)}>
          <option value="">Inbox</option>
          ${projects.map((p) => html`<option key=${p.name} value=${p.name}>${p.name}</option>`)}
        </select>
      </label>
      <div class="form-actions">
        <button type="submit" disabled=${busy}>移動する</button>
        <button type="button" onClick=${onCancel} disabled=${busy}>やめる</button>
      </div>
    </form>
  `;
}

export function ConfirmDelete({ task, onConfirm, onCancel, busy }) {
  return html`
    <div class="task-form">
      <h2>削除の確認</h2>
      <p>「${task.title}」を削除します。元に戻せません。</p>
      <div class="form-actions">
        <button type="button" class="danger" onClick=${onConfirm} disabled=${busy}>
          削除する
        </button>
        <button type="button" onClick=${onCancel} disabled=${busy}>やめる</button>
      </div>
    </div>
  `;
}

export function Overview({ data, onOpen, onAction }) {
  const pending = (data.routines || []).filter((r) => !r.paused);
  return html`
    <div>
      ${data.timer &&
      html`
        <section class="group">
          <h2>実行中のタイマー</h2>
          <p>
            ${data.timer.task_title
              ? `#${data.timer.task_id} ${data.timer.task_title}`
              : "タスクに紐づいていません"}
            <span class="meta"> 開始 ${formatDateTime(data.timer.started_at)}</span>
          </p>
        </section>
      `}
      ${pending.length > 0 &&
      html`
        <section class="group">
          <h2>今日の毎日やること</h2>
          <ul class="routines">
            ${pending.map(
              (r) => html`<li key=${r.id} class=${r.status === "done" ? "done" : ""}>
                ${r.status === "done" ? "✓" : "○"} ${r.title}
              </li>`
            )}
          </ul>
        </section>
      `}
      <${GroupedTasks}
        groups=${data.tasks}
        onOpen=${onOpen}
        onAction=${onAction}
        emptyMessage="未着手のタスクはありません"
      />
    </div>
  `;
}

export function ErrorBox({ error, onReload, onDismiss }) {
  // 競合はほかのエラーと同じ赤い箱に流し込まない。混ぜると「自分の入力が
  // 悪かった」と誤解される。原因は利用者の入力ではなく、別の場所での変更である。
  if (error.isConflict) {
    return html`
      <div class="conflict">
        <div class="conflict-title">${error.message}</div>
        ${error.current &&
        html`<div class="conflict-current">
          現在の内容: <strong>${error.current.title}</strong>
          <span class="meta">（${error.current.status}・${error.current.priority}）</span>
        </div>`}
        <div class="remedy">${error.remedy}</div>
        <div class="conflict-actions">
          ${onReload &&
          html`<button type="button" onClick=${onReload}>最新の内容に合わせて続ける</button>`}
          ${onDismiss &&
          html`<button type="button" onClick=${onDismiss}>入力を捨てて閉じる</button>`}
        </div>
      </div>
    `;
  }
  return html`
    <div class="error">
      <div>${error.message}</div>
      ${error.cause_ && html`<div class="cause">原因: ${error.cause_}</div>`}
      ${error.remedy && html`<div class="remedy">対処: ${error.remedy}</div>`}
    </div>
  `;
}
