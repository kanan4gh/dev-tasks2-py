// 画面の状態遷移とデータ取得。
//
// サーバが状態を持たないのに合わせて、ここもキャッシュを持たない。SSE で
// リビジョンの変化を受けたら、いま表示しているものをそのまま取り直す。

import { api, subscribe } from "./api.js";
import { ErrorBox, GroupedTasks, Overview, TaskDetail, TaskList, html } from "./ui.js";

const { useCallback, useEffect, useRef, useState } = window.React;
const { createRoot } = window.ReactDOM;

const STATUSES = ["open", "in_progress", "completed", "archived"];
const SORTS = [
  ["id", "ID順"],
  ["priority", "優先度順"],
  ["due_date", "期限順"],
  ["created_at", "作成順"],
];

function Filters({ filters, onChange }) {
  return html`
    <div class="filters">
      <label>ステータス</label>
      <select
        value=${filters.status[0] || ""}
        onChange=${(e) => onChange({ ...filters, status: e.target.value ? [e.target.value] : [] })}
      >
        <option value="">すべて</option>
        ${STATUSES.map((s) => html`<option key=${s} value=${s}>${s}</option>`)}
      </select>
      <label>優先度</label>
      <select
        value=${filters.priority || ""}
        onChange=${(e) => onChange({ ...filters, priority: e.target.value || null })}
      >
        <option value="">すべて</option>
        ${["high", "medium", "low"].map((p) => html`<option key=${p} value=${p}>${p}</option>`)}
      </select>
      <label>並び</label>
      <select value=${filters.sort} onChange=${(e) => onChange({ ...filters, sort: e.target.value })}>
        ${SORTS.map(([v, label]) => html`<option key=${v} value=${v}>${label}</option>`)}
      </select>
    </div>
  `;
}

function App() {
  const [state, setState] = useState(null);
  const [view, setView] = useState({ kind: "overview" });
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ status: [], priority: null, sort: "id" });
  const [revision, setRevision] = useState(null);
  const [connected, setConnected] = useState(false);
  // 取得済みのリビジョン。SSE が最初に送ってくる値はたいてい今持っているものと
  // 同じなので、これと比べて同じなら読み直さない（比べないと、ページを開くたびに
  // 全 API を2回叩くことになる）。
  const [reloadToken, setReloadToken] = useState(0);
  const loadedRevision = useRef(null);
  // 初回の取得が終わる前に SSE が新しいリビジョンを送ってきた場合、それを
  // 捨ててはいけない（捨てると、取得結果のほうが古いのに「最新」として
  // 居座り、次に誰かが書き込むまで古い画面のままになる）。
  const pendingRevision = useRef(null);
  // 取得の世代番号。プロジェクトを続けて切り替えたとき、遅れて返ってきた
  // 古い応答が新しい表示を上書きしないようにする。
  const requestSeq = useRef(0);

  // 取得したデータには「どのビューのものか」を必ず添える。view だけを先に
  // 切り替えて payload を古いまま描くと、形の違うデータを読んで落ちる
  // （実際に、要約から詳細へ移った最初の1フレームで payload.task が
  //  undefined になり画面が真っ白になった）。
  const load = useCallback(async () => {
    const seq = ++requestSeq.current;
    const stale = () => seq !== requestSeq.current;
    try {
      const nextState = await api.state();
      if (stale()) return;
      loadedRevision.current = nextState.revision;
      setState(nextState);
      let data;
      if (view.kind === "overview") data = await api.overview();
      else if (view.kind === "all") data = await api.allTasks(filters);
      else if (view.kind === "project") data = await api.tasks(view.project, filters);
      else if (view.kind === "task") data = await api.task(view.project, view.id);
      else if (view.kind === "search") data = await api.search(view.query);
      if (stale()) return;
      setPayload({ view, data });
      setError(null);
    } catch (e) {
      if (stale()) return;
      setPayload(null);
      setError(e);
    } finally {
      // 取得中に届いていたリビジョンがあれば、ここで反映する。
      if (!stale() && pendingRevision.current !== null) {
        const pending = pendingRevision.current;
        pendingRevision.current = null;
        if (pending !== loadedRevision.current) {
          loadedRevision.current = pending;
          setReloadToken((n) => n + 1);
        }
      }
    }
  }, [view, filters]);

  useEffect(() => {
    load();
  }, [load, reloadToken]);

  useEffect(() => {
    const stop = subscribe((rev) => {
      setConnected(true);
      setRevision(rev);
      if (loadedRevision.current === null) {
        // 初回の取得がまだ終わっていない。捨てずに預けておく。
        pendingRevision.current = rev;
        return;
      }
      if (rev !== loadedRevision.current) {
        loadedRevision.current = rev;
        setReloadToken((n) => n + 1);
      }
    });
    return stop;
  }, []);

  const openTask = useCallback((project, id) => setView({ kind: "task", project, id }), []);
  const back = useCallback(() => setView({ kind: "all" }), []);

  const projects = (state && state.projects) || [];
  // payload が「いまのビューのもの」であるときだけ描画に使う。
  const ready = !error && payload !== null && payload.view === view;
  const data = ready ? payload.data : null;

  return html`
    <div>
      <header class="top">
        <h1>task-py</h1>
        ${state &&
        html`<span class="active"
          >アクティブ: ${state.active_project || "Inbox"}</span
        >`}
        <nav class="tabs">
          <button
            aria-current=${String(view.kind === "overview")}
            onClick=${() => setView({ kind: "overview" })}
          >
            要約
          </button>
          <button aria-current=${String(view.kind === "all")} onClick=${() => setView({ kind: "all" })}>
            すべて
          </button>
          <button
            aria-current=${String(view.kind === "project" && view.project === null)}
            onClick=${() => setView({ kind: "project", project: null })}
          >
            Inbox
          </button>
          ${projects.map(
            (p) => html`
              <button
                key=${p.name}
                aria-current=${String(view.kind === "project" && view.project === p.name)}
                onClick=${() => setView({ kind: "project", project: p.name })}
              >
                ${p.name}
              </button>
            `
          )}
        </nav>
        <span class="spacer"></span>
        <input
          type="search"
          placeholder="検索"
          onKeyDown=${(e) => {
            if (e.key !== "Enter") return;
            const q = e.target.value.trim();
            setView(q ? { kind: "search", query: q } : { kind: "all" });
          }}
        />
      </header>

      <main>
        ${error && html`<${ErrorBox} error=${error} />`}
        ${!error && !ready && html`<p class="empty">読み込み中…</p>`}
        ${ready && view.kind === "overview" && html`<${Overview} data=${data} onOpen=${openTask} />`}
        ${ready &&
        view.kind === "all" &&
        html`
          <div>
            <${Filters} filters=${filters} onChange=${setFilters} />
            <${GroupedTasks} groups=${data} onOpen=${openTask} emptyMessage="タスクはありません" />
          </div>
        `}
        ${ready &&
        view.kind === "project" &&
        html`
          <div>
            <${Filters} filters=${filters} onChange=${setFilters} />
            <section class="group">
              <h2>${view.project === null ? "Inbox" : view.project}</h2>
              <${TaskList} tasks=${data.tasks} project=${view.project} onOpen=${openTask} />
            </section>
          </div>
        `}
        ${ready &&
        view.kind === "search" &&
        html`
          <div>
            <p class="meta">「${data.query}」の検索結果</p>
            <${GroupedTasks} groups=${data} onOpen=${openTask} emptyMessage="見つかりませんでした" />
          </div>
        `}
        ${ready &&
        view.kind === "task" &&
        html`<${TaskDetail} project=${data.project} task=${data.task} onBack=${back} />`}
      </main>

      <footer class="status">
        ${connected ? "変更を監視中" : "接続待ち"}
        ${revision && html`<span> · rev ${revision}</span>`}
        <span> · 読み取り専用（編集は task-py コマンドから）</span>
      </footer>
    </div>
  `;
}

createRoot(document.getElementById("root")).render(html`<${App} />`);
