/* Проверка и выгрузка, новый проект, импорт архива.
   Обычный скрипт без сборки: файлы интерфейса подключаются по порядку и
   разделяют общую область видимости (см. index.html). */

/* ===================== Вкладка: Валидация и экспорт ===================== */

/* Переход от ошибки валидатора к элементу.
   Адрес ошибки: «benchmark», «rule:<id>», «profile:<id>» или
   «<файл>#<вид>:<id>» — формат закреплён тестом на стороне сервера. */
const ISSUE_STEP = { definition: "definitions", test: "tests", state: "states", object: "objects",
                     variable: "variables", rule: "rules", profile: "profiles", benchmark: "overview" };

function issueTarget(path) {
  if (!path || path === "archive") return null;
  if (path === "benchmark") return { step: "overview", id: null, file: null };
  let m = path.match(/^(rule|profile):(.+)$/);
  if (m) return { step: ISSUE_STEP[m[1]], id: m[2], file: null };
  m = path.match(/^(.+\.xml)#([a-z]+):(.+)$/);
  if (m && ISSUE_STEP[m[2]]) return { step: ISSUE_STEP[m[2]], id: m[3], file: m[1] };
  return null;
}

async function gotoIssue(path) {
  const target = issueTarget(path);
  if (!target) return;
  if (target.file && (state.currentProject.oval_files || []).includes(target.file)) {
    state.currentOvalFile = target.file;          // ошибка может быть не в текущем OVAL-файле
    await loadOvalFileData();
  }
  await gotoStepKey(target.step);
  if (target.id) highlightElement(target.id);
}

function highlightElement(id) {
  const root = document.getElementById("tab-content") || document;
  const cell = [...root.querySelectorAll(".id-cell, code, td")].find(el => el.textContent.trim() === id);
  const row = cell && (cell.closest("tr") || cell.closest(".card") || cell);
  if (!row) { toast(`${t("Элемент не найден на этом шаге")}: ${id}`, "error"); return; }
  row.classList.add("row-flash");
  row.scrollIntoView({ block: "center", behavior: "smooth" });
  setTimeout(() => row.classList.remove("row-flash"), 2600);
}

function renderValidate(container) {
  container.innerHTML = `
    <div class="panel">
      <div class="toolbar">
        <button class="btn btn-primary" id="btn-run-validate">${t("Проверить проект")}</button>
        <a class="btn" href="${api.exportUrl(state.currentProjectId)}" id="btn-export">${t("Экспортировать ZIP")}</a>
      </div>
      <div id="validate-result" class="muted">${t("Нажмите «Проверить проект», чтобы увидеть результат.")}</div>
    </div>
  `;
  document.getElementById("btn-run-validate").addEventListener("click", runValidate);
  document.getElementById("validate-result").addEventListener("click", ev => {
    const b = ev.target.closest(".issue-go");
    if (b) gotoIssue(b.getAttribute("data-path"));
  });
}

async function runValidate() {
  const box = document.getElementById("validate-result");
  box.innerHTML = t("Проверка…");
  try {
    const res = await api.get(`/projects/${encodeURIComponent(state.currentProjectId)}/validate?lang=${getLang()}`);
    if (res.valid && !res.issues.length) {
      box.innerHTML = `<div class="valid-ok">${t("✓ Проект соответствует требованиям, ошибок и замечаний не найдено.")}</div>`;
      return;
    }
    box.innerHTML = `
      ${res.valid ? `<div class="valid-ok" style="margin-bottom:10px;">${t("✓ Критичных ошибок нет (есть замечания ниже)")}</div>` :
                     `<div style="color:var(--red);margin-bottom:10px;">${t("✕ Найдены ошибки — архив не пройдёт импорт, пока они не исправлены.")}</div>`}
      <div class="issues">
        ${res.issues.map(i => `
          <div class="issue ${i.level}">
            <span class="lvl">${escapeHtml(i.level === "error" ? t("Ошибка") : i.level === "warning" ? t("Замечание") : i.level)}</span>
            <div>
              <div>${escapeHtml(i.message)}</div>
              ${i.path ? `<div class="path">${escapeHtml(i.path)}${issueTarget(i.path) ? ` <button type="button" class="btn btn-sm issue-go" data-path="${escapeHtml(i.path)}">${t("Перейти")} →</button>` : ""}</div>` : ""}
            </div>
          </div>`).join("")}
      </div>`;
  } catch (e) {
    box.innerHTML = `<div style="color:var(--red);">${escapeHtml(e.message)}</div>`;
  }
}

/* ===================== Новый проект / импорт ===================== */

function openNewProjectModal() {
  openModal(t("Новый проект"), `
    <form id="mf">
      <div class="field"><label>${L('project_id_folder', {required:true})}</label>
        <input class="mono-input" id="np-project-id" required placeholder="win_hardening_2026">
        <span class="hint">${t("Латиница, цифры, - и _")}</span>
      </div>
      <div class="field"><label>${L('benchmark_id', {required:true, tech:'Benchmark/@id'})}</label><input class="mono-input" id="np-benchmark-id" required placeholder="xccdf_custom_benchmark_windows"></div>
      <div class="grid">
        <div class="field"><label>${L('xml_lang')}</label><input id="np-lang" value="ru-RU"></div>
        <div class="field"><label>${L('status')}</label><select id="np-status">${optionsHtml(STATUS_VALUES, "accepted", state.labels.status, state.labelsEn.status)}</select></div>
      </div>
      <div class="field"><label>${L('title', {required:true})}</label><input id="np-title" required></div>
      <div class="field"><label>${L('description', {required:true})}</label><textarea id="np-description" required></textarea></div>
      <div class="field"><label>${L('version')}</label><input id="np-version" value="1.0"></div>
      ${formActions(t("Создать проект"))}
    </form>`);
  bindForm(async () => {
    const id = val("np-project-id");
    await api.post("/projects", {
      project_id: id, benchmark_id: val("np-benchmark-id"), xml_lang: val("np-lang"),
      status: val("np-status"), title: val("np-title"), description: val("np-description"),
      version: val("np-version"),
    });
    await loadProjects();
    await selectProject(id);
    toast(t("Проект создан"), "ok");
  });
}

let pendingImportFile = null;
function onImportFileChosen(e) {
  const file = e.target.files[0];
  if (!file) return;
  pendingImportFile = file;
  openModal(t("Импорт ZIP-архива"), `
    <form id="mf">
      <div class="field"><label>${L('file')}</label><input value="${escapeHtml(file.name)}" disabled></div>
      <div class="field"><label>${L('project_id_new', {required:true})}</label>
        <input class="mono-input" id="imp-project-id" required placeholder="imported_profile">
      </div>
      ${formActions(t("Импортировать"))}
    </form>`);
  bindForm(async () => {
    const id = val("imp-project-id");
    await api.importZip(id, pendingImportFile);
    document.getElementById("import-file").value = "";
    await loadProjects();
    await selectProject(id);
    toast(t("Архив импортирован"), "ok");
  });
}
