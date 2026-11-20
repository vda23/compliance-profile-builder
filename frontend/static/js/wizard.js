/* Мастер: шаги, основной рендер, бенчмарк.
   Обычный скрипт без сборки: файлы интерфейса подключаются по порядку и
   разделяют общую область видимости (см. index.html). */

/* ===================== Мастер (пошаговое создание) ===================== */

/* Шаги выстроены в порядке ЗАВИСИМОСТЕЙ элементов профиля — «снизу вверх»:
   каждый следующий элемент ссылается только на уже созданные. Благодаря
   этому пользователь никогда не упирается в пустой выпадающий список:

     Переменная ← Состояние ← Тест → Объект
                                ↑
                          Определение ← Правило ← Профиль

   Шаги 3–7 — это отдельные разделы OVAL-файла (поле ovalSub). Режим
   «Конструктор» показывает те же экраны вкладками, в том же порядке. */
const WIZARD_STEPS = [
  { key: "overview", tab: "overview",
    ruTitle: "Бенчмарк", enTitle: "Benchmark",
    hintRu: "Заполните основные сведения о бенчмарке: заголовок, описание, версию и статус.\nЭто заголовок будущего XCCDF-файла.",
    hintEn: "Fill in the benchmark metadata: title, description, version and status.\nThis becomes the XCCDF file header." },
  { key: "ovalfile", tab: "oval", ovalSub: null,
    ruTitle: "OVAL-файл", enTitle: "OVAL file",
    hintRu: "Создайте OVAL-файл — в нём будет храниться техническая логика проверок.\nДля одного профиля обычно достаточно одного файла checks-oval.xml.",
    hintEn: "Create an OVAL file to hold the technical check logic.\nOne file, checks-oval.xml, is usually enough for a profile." },
  { key: "variables", tab: "oval", ovalSub: "variables",
    ruTitle: "Переменные", enTitle: "Variables",
    hintRu: "Необязательный шаг. Переменная хранит эталонное значение (например, «24» для длины истории паролей), которое затем подставляется в состояние.\nЕсли эталонные значения удобнее вводить прямо в состоянии — шаг можно пропустить.",
    hintEn: "Optional. A variable holds a reference value (e.g. 24 for password history length) that a state then refers to.\nSkip this step if you prefer to enter values directly in states." },
  { key: "objects", tab: "oval", ovalSub: "objects",
    ruTitle: "Объекты", enTitle: "Objects",
    hintRu: "Объект описывает, что проверяется на узле: файл, параметр ядра, ключ реестра, пакет, политику паролей.\nСначала выберите тип проверки — от него зависит набор полей.",
    hintEn: "An object describes what is checked on the host: a file, kernel parameter, registry key, package, or password policy.\nChoose the check type first — the fields depend on it." },
  { key: "states", tab: "oval", ovalSub: "states",
    ruTitle: "Состояния", enTitle: "States",
    hintRu: "Состояние задаёт ожидаемое значение объекта: чему должно равняться, больше или меньше чего быть.\nЕсли проверяется только наличие объекта (например, установленный пакет), состояние не нужно.",
    hintEn: "A state defines the expected value of an object: what it must equal, exceed or stay below.\nIf you only check that an object exists (e.g. an installed package), no state is needed." },
  { key: "tests", tab: "oval", ovalSub: "tests",
    ruTitle: "Тесты", enTitle: "Tests",
    hintRu: "Тест связывает объект с состоянием: «взять этот объект и сравнить с этим состоянием».\nСписки объектов и состояний автоматически отфильтрованы по выбранному типу проверки.",
    hintEn: "A test links an object to a state: \"take this object and compare it with this state\".\nObject and state lists are filtered by the selected check type automatically." },
  { key: "definitions", tab: "oval", ovalSub: "definitions",
    ruTitle: "Определения", enTitle: "Definitions",
    hintRu: "Определение — это законченная проверка с названием и описанием.\nОно объединяет один или несколько тестов через критерии. Именно на определение будет ссылаться правило.",
    hintEn: "A definition is a complete check with a title and description.\nIt combines one or more tests through criteria. Rules refer to definitions." },
  { key: "rules", tab: "rules",
    ruTitle: "Правила", enTitle: "Rules",
    hintRu: "Правило — требование безопасности в терминах документа (XCCDF).\nКаждое правило ссылается на определение из OVAL-файла и содержит идентификатор требования (ident).",
    hintEn: "A rule is a security requirement in document terms (XCCDF).\nEach rule refers to an OVAL definition and carries a requirement identifier (ident)." },
  { key: "profiles", tab: "profiles",
    ruTitle: "Профили", enTitle: "Profiles",
    hintRu: "Профиль — именованный набор правил, который запускается как одна проверка (например, «Базовый» или «Усиленный»).\nОтметьте правила, которые должны войти в профиль.",
    hintEn: "A profile is a named set of rules run as a single check (e.g. \"Baseline\" or \"Hardened\").\nTick the rules the profile should include." },
  { key: "validate", tab: "validate",
    ruTitle: "Проверка и экспорт", enTitle: "Validation & export",
    hintRu: "Проверьте проект на корректность и выгрузите готовый ZIP-архив для импорта в Kaspersky Vulnerability Management.",
    hintEn: "Validate the project and export the ready-to-import ZIP archive for Kaspersky Vulnerability Management." },
];

/* Порядок вкладок конструктора и подразделов OVAL — тот же, что у мастера. */
const OVAL_SUBTABS = ["variables", "objects", "states", "tests", "definitions"];

function stepTitle(step) { return getLang() === "en" ? step.enTitle : step.ruTitle; }
/* Подсказка с переносами строк: каждая мысль — с новой строки. */
function stepHintHtml(step) { return escapeHtml(stepHint(step)).replace(/\n/g, "<br>"); }
function stepHint(step) { return getLang() === "en" ? step.hintEn : step.hintRu; }

function currentStep() { return WIZARD_STEPS[state.wizardStep]; }

/* Если в проекте есть OVAL-файл, а активный не выбран — выбираем первый.
   Избавляет от лишнего клика на шагах 3–7 и во вкладке «OVAL-проверки». */
async function ensureOvalFileSelected() {
  const files = state.currentProject ? state.currentProject.oval_files : [];
  if (!files.length) { state.currentOvalFile = null; state.currentOvalData = null; return; }
  if (!state.currentOvalFile || !files.includes(state.currentOvalFile)) {
    state.currentOvalFile = files[0];
  }
  if (!state.currentOvalData || state.currentOvalData.filename !== state.currentOvalFile) {
    await loadOvalFileData();
  }
}

async function applyStepToState(step) {
  state.tab = step.tab;
  if (step.tab === "oval") {
    if (step.ovalSub) state.ovalSubtab = step.ovalSub;
    await ensureOvalFileSelected();
  }
  if (step.tab === "rules") await loadAllDefinitions();
}

async function setViewMode(mode) {
  state.viewMode = mode;
  localStorage.setItem("cpb-view-mode", mode);
  if (mode === "wizard") {
    let idx = WIZARD_STEPS.findIndex(s => s.tab === state.tab && (s.tab !== "oval" || s.ovalSub === state.ovalSubtab));
    if (idx < 0) idx = WIZARD_STEPS.findIndex(s => s.tab === state.tab);
    state.wizardStep = idx >= 0 ? idx : 0;
    await applyStepToState(currentStep());
  }
  renderView();
}

async function setWizardStep(i) {
  state.wizardStep = i;
  await applyStepToState(currentStep());
  renderView();
  maybeShowStepHintModal();
}

function wizardNext() { if (state.wizardStep < WIZARD_STEPS.length - 1) setWizardStep(state.wizardStep + 1); }
function wizardBack() { if (state.wizardStep > 0) setWizardStep(state.wizardStep - 1); }

/* Переход на шаг мастера по ключу (или на вкладку конструктора). Используется
   кнопками в подсказках о недостающих элементах. */
async function gotoStepKey(key) {
  const idx = WIZARD_STEPS.findIndex(s => s.key === key);
  if (idx < 0) return;
  if (state.viewMode === "wizard") return setWizardStep(idx);
  await applyStepToState(WIZARD_STEPS[idx]);
  renderView();
}

/* Плашка «сначала создайте …» — показывается вместо пустого списка, когда
   для создания элемента не хватает элемента предыдущего шага. */
function depWarningHtml(textRu, textEn, stepKey) {
  const step = WIZARD_STEPS.find(s => s.key === stepKey);
  return `
    <div class="dep-warning">
      <span class="icon">↩</span>
      <div>${escapeHtml(getLang() === "en" ? textEn : textRu)}</div>
      ${step ? `<button class="btn btn-sm" ${on("click", "gotoStepKey", (stepKey))}>${escapeHtml(t("Перейти к шагу"))} «${escapeHtml(stepTitle(step))}»</button>` : ""}
    </div>`;
}

/* Признак «подсказка просмотрена» общий для всех проектов. Раньше он
   хранился отдельно для каждого проекта, и в новом проекте все подсказки
   всплывали заново — пользователи воспринимали это как навязчивость. */
function hintSeenKey(stepKey) {
  return `cpb-hint-seen-${stepKey}`;
}
/* Глобальный выключатель всплывающих подсказок (выбирается на экране
   первого запуска и в «Справке»). Баннер с подсказкой на шаге остаётся
   всегда — он не мешает работе. */
function hintsDisabled() { return localStorage.getItem("cpb-hints-off") === "1"; }

/* Всплывающая подсказка при первом посещении шага. Показывается один раз
   на проект и шаг (галочкой можно отключить); дальше подсказка остаётся
   доступна баннером и кнопкой «?» на самой странице. */
function maybeShowStepHintModal() {
  const step = currentStep();
  if (hintsDisabled() || localStorage.getItem(hintSeenKey(step.key))) return;
  openModal(`${state.wizardStep + 1}. ${stepTitle(step)}`, `
    <div class="modal-hint-body">
      <p>${stepHintHtml(step)}</p>
    </div>
    <label class="row-check" style="margin-top:6px;">
      <input type="checkbox" id="hint-dont-show" checked> ${t("Больше не показывать эту подсказку")}
    </label>
    <div class="modal-actions">
      <button type="button" class="btn btn-primary" ${on("click", "dismissStepHint", (step.key))}>${t("Понятно")}</button>
    </div>`);
}
function dismissStepHint(stepKey) {
  if (checked("hint-dont-show")) localStorage.setItem(hintSeenKey(stepKey), "1");
  closeModal();
}

function modeSwitchHtml() {
  return `
    <div class="mode-switch">
      <button class="${state.viewMode === "wizard" ? "active" : ""}" ${on("click", "setViewMode", "wizard")}>${t("Мастер")}</button>
      <button class="${state.viewMode === "constructor" ? "active" : ""}" ${on("click", "setViewMode", "constructor")}>${t("Конструктор")}</button>
    </div>`;
}

function wizardStepsHtml() {
  return `<div class="wizard-steps">` + WIZARD_STEPS.map((s, i) => `
    <div class="wizard-step ${i === state.wizardStep ? "active" : ""} ${i < state.wizardStep ? "done" : ""}" ${on("click", "setWizardStep", (i))}>
      <span class="num">${i + 1}</span><span>${escapeHtml(stepTitle(s))}</span>
    </div>`).join("") + `</div>`;
}

function wizardHintBannerHtml(step) {
  return `
    <div class="wizard-hint-banner">
      <span class="icon">💡</span>
      <div><div>${stepHintHtml(step)}</div></div>
      <button class="btn btn-sm hint-reopen" ${on("click", "maybeForceShowHint")} title="${t("Показать подсказку")}"><span class="hint-reopen-icon">?</span> ${t("Подсказка")}</button>
    </div>`;
}
function maybeForceShowHint() {
  localStorage.removeItem(hintSeenKey(currentStep().key));
  const off = hintsDisabled();
  if (off) localStorage.removeItem("cpb-hints-off");
  maybeShowStepHintModal();
  if (off) localStorage.setItem("cpb-hints-off", "1");
}

/* Небольшая иконка-подсказка (всплывающий popover) рядом со сложными полями. */
function hintIcon(ru, en) {
  const id = "hint" + Math.random().toString(36).slice(2, 9);
  return `
    <span class="hint-popover-wrap">
      <button type="button" class="hintbtn" ${on("click", "toggleHintPopover", "$event", (id))}>?</button>
      <span class="hint-popover" id="${id}" style="display:none;">
        <div>${escapeHtml(getLang() === "en" ? (en || ru) : ru)}</div>
      </span>
    </span>`;
}
function toggleHintPopover(e, id) {
  e.stopPropagation();
  document.querySelectorAll(".hint-popover").forEach(el => { if (el.id !== id) el.style.display = "none"; });
  const el = document.getElementById(id);
  el.style.display = el.style.display === "none" ? "block" : "none";
}
document.addEventListener("click", () => document.querySelectorAll(".hint-popover").forEach(el => el.style.display = "none"));

/* ===================== Основной рендер ===================== */

function renderView() {
  const root = document.getElementById("view-root");
  if (!state.currentProjectId || !state.currentProject) {
    root.innerHTML = `<div class="empty-state">${t("Выберите проект слева или создайте новый, чтобы начать составление профиля.")}</div>`;
    return;
  }
  const b = state.currentProject.benchmark;
  const isWizard = state.viewMode === "wizard";
  root.innerHTML = `
    <div class="page-head">
      <h1>${escapeHtml(b.title || t("(Без названия)"))}</h1>
      <span class="page-id">${escapeHtml(b.id)}</span>
    </div>
    <div class="page-sub">${t("Проект")}: <span class="mono-input" style="all:unset;font-family:var(--mono);">${escapeHtml(state.currentProjectId)}</span>
      ${state.currentProject.has_coverage ? `<button type="button" class="btn btn-sm coverage-btn" ${on("click", "openSavedCoverage")}>${t("Отчёт о покрытии")}</button>` : ""}</div>
    ${modeSwitchHtml()}
    ${isWizard ? wizardStepsHtml() : `
    <div class="tabs">
      ${tabHtml("overview", t("Бенчмарк"))}
      ${tabHtml("oval", `${t("OVAL-проверки")} (${state.currentProject.oval_files.length})`)}
      ${tabHtml("rules", `${t("Правила")} (${b.rules.length})`)}
      ${tabHtml("profiles", `${t("Профили")} (${b.profiles.length})`)}
      ${tabHtml("validate", t("Проверка и экспорт"))}
    </div>`}
    ${isWizard ? wizardHintBannerHtml(currentStep()) : ""}
    <div id="tab-content"></div>
    ${isWizard ? `
    <div class="wizard-nav">
      <button class="btn" ${state.wizardStep === 0 ? "disabled" : ""} ${on("click", "wizardBack")}>${t("← Назад")}</button>
      <button class="btn btn-primary" ${state.wizardStep === WIZARD_STEPS.length - 1 ? "disabled" : ""} ${on("click", "wizardNext")}>${t("Далее →")}</button>
    </div>` : ""}
  `;
  const content = document.getElementById("tab-content");
  if (state.tab === "overview") content.innerHTML = renderOverview(b);
  else if (state.tab === "profiles") content.innerHTML = renderProfiles(b);
  else if (state.tab === "rules") content.innerHTML = renderRules(b);
  else if (state.tab === "oval") renderOval(content);
  else if (state.tab === "validate") renderValidate(content);

  if (state.tab === "overview") bindOverviewForm();
  // В низком окне шаги мастера идут одной прокручиваемой строкой —
  // текущий шаг должен быть виден.
  const act = document.querySelector(".wizard-step.active");
  if (act && act.parentElement.scrollWidth > act.parentElement.clientWidth) {
    act.scrollIntoView({ inline: "center", block: "nearest" });
  }
  // Подсказка первого визита показывается только при явном переходе на
  // шаг, а не при каждом renderView() — иначе всплывала бы повторно при
  // любом действии внутри шага.
}

async function setTab(tab) {
  state.tab = tab;
  if (tab === "oval") await ensureOvalFileSelected();
  if (tab === "rules") await loadAllDefinitions();
  renderView();
}

function tabHtml(key, label) {
  return `<div class="tab ${state.tab === key ? "active" : ""}" ${on("click", "setTab", (key))}>${escapeHtml(label)}</div>`;
}

/* ===================== Вкладка: Бенчмарк ===================== */

function renderOverview(b) {
  return `
    <div class="panel">
      <h2>${t("Метаданные бенчмарка")}</h2>
      <form id="mf-overview">
        <div class="grid">
          <div class="field"><label>${L('benchmark_id', {tech:'Benchmark/@id'})}</label><input class="mono-input" value="${escapeHtml(b.id)}" disabled></div>
          <div class="field"><label>${L('xml_lang')}</label><input class="mono-input" value="${escapeHtml(b.xml_lang)}" disabled></div>
          <div class="field"><label>${L('status')}</label>
            <select id="ov-status">${optionsHtml(STATUS_VALUES, b.status, state.labels.status, state.labelsEn.status)}</select>
          </div>
          <div class="field"><label>${L('version')}</label><input id="ov-version" value="${escapeHtml(b.version)}"></div>
          <div class="field full"><label>${L('title')}</label><input id="ov-title" value="${escapeHtml(b.title)}"></div>
          <div class="field full"><label>${L('description')}</label><textarea id="ov-description">${escapeHtml(b.description)}</textarea></div>
        </div>
        <div class="row">
          <button type="submit" class="btn btn-primary">${t("Сохранить")}</button>
        </div>
      </form>
    </div>
  `;
}

function bindOverviewForm() {
  const form = document.getElementById("mf-overview");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api.put(`/projects/${encodeURIComponent(state.currentProjectId)}/benchmark`, {
        status: val("ov-status"), version: val("ov-version"),
        title: val("ov-title"), description: val("ov-description"),
      });
      await refreshCurrentProject();
      renderView();
      toast(t("Сохранено"), "ok");
    } catch (err) { toast(err.message, "error"); }
  });
}
