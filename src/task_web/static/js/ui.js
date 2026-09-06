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

export function TaskRow({ task, project, onOpen }) {
  return html`
    <li onClick=${() => onOpen(project, task.id)}>
      <span class="task-id">#${task.id}</span>
      <${Badge} kind="status" value=${task.status} />
      <${Badge} kind="priority" value=${task.priority} />
      <span class="task-title">${task.title}</span>
      ${task.due_date && html`<span class="meta">期限 ${task.due_date}</span>`}
      ${task.total_worked_seconds > 0 &&
      html`<span class="meta">${formatDuration(task.total_worked_seconds)}</span>`}
    </li>
  `;
}

export function TaskList({ tasks, project, onOpen }) {
  if (!tasks.length) return html`<p class="empty">タスクはありません</p>`;
  return html`
    <ul class="tasks">
      ${tasks.map(
        (task) => html`<${TaskRow} key=${task.id} task=${task} project=${project} onOpen=${onOpen} />`
      )}
    </ul>
  `;
}

// `grouped_tasks()` の形（inbox + projects）をそのまま描く。
export function GroupedTasks({ groups, onOpen, emptyMessage }) {
  const sections = [];
  if (groups.inbox && groups.inbox.length) {
    sections.push(html`
      <section class="group" key="inbox">
        <h2>Inbox</h2>
        <${TaskList} tasks=${groups.inbox} project=${null} onOpen=${onOpen} />
      </section>
    `);
  }
  Object.entries(groups.projects || {}).forEach(([name, tasks]) => {
    if (!tasks.length) return;
    sections.push(html`
      <section class="group" key=${`p:${name}`}>
        <h2>${name}</h2>
        <${TaskList} tasks=${tasks} project=${name} onOpen=${onOpen} />
      </section>
    `);
  });
  if (!sections.length) return html`<p class="empty">${emptyMessage}</p>`;
  return html`<div>${sections}</div>`;
}

export function TaskDetail({ project, task, onBack }) {
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
    </div>
  `;
}

export function Overview({ data, onOpen }) {
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
      <${GroupedTasks} groups=${data.tasks} onOpen=${onOpen} emptyMessage="未着手のタスクはありません" />
    </div>
  `;
}

export function ErrorBox({ error }) {
  return html`
    <div class="error">
      <div>${error.message}</div>
      ${error.cause_ && html`<div class="cause">原因: ${error.cause_}</div>`}
      ${error.remedy && html`<div class="remedy">対処: ${error.remedy}</div>`}
    </div>
  `;
}
