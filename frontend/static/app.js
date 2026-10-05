/* ===================== Состояние ===================== */

const state = {
  projects: [],
  currentProjectId: null,
  currentProject: null,
  tab: "overview",
  ovalSchema: null,
  labels: null,              // подписи для перечислений (заполняется ниже и обновляется с backend)
  labelsEn: null,            // английские подписи перечислений (xml:lang="en")
  uiLabels: null,            // подписи статических полей интерфейса (ru/en)
  currentOvalFile: null,
  currentOvalData: null,
  ovalSubtab: "variables",
  // Режим отображения: "wizard" — пошаговый мастер (по умолчанию для новых
  // пользователей), "constructor" — прежний свободный доступ по вкладкам.
  // Переключатель не ограничивает функциональность: это два разных вида
  // одних и тех же экранов, редактирование сохранённого проекта работает
  // в обоих режимах.
  viewMode: localStorage.getItem("cpb-view-mode") || "wizard",
  wizardStep: 0,
};

const OPERATIONS = [
  "equals", "not equal", "greater than", "greater than or equal",
  "less than", "less than or equal", "pattern match",
];
const DATATYPES = ["string", "int", "boolean", "version", "float", "evr_string"];
const CHECK_VALUES = ["all", "at least one", "none satisfy", "none exist", "only one"];
const CHECK_EXISTENCE_VALUES = ["at_least_one_exists", "all_exist", "any_exist", "none_exist", "only_one_exists"];
const CLASS_VALUES = ["compliance", "inventory", "patch", "vulnerability", "miscellaneous"];
// Допустимые значения affected/@family по схеме OVAL — это закрытое
// перечисление (FamilyEnumeration), в нём НЕТ значений "linux" и
// "independent". Все Linux-дистрибутивы (РЕД ОС, ALT Linux, Astra Linux,
// Debian, Ubuntu) указываются как "unix"; конкретный дистрибутив
// перечисляется отдельно в <platform> (поле "платформы" ниже).
/* Семейство ОС (affected/@family). По схеме OVAL для всех дистрибутивов
   Linux значение — "unix" (значения "linux" в перечислении нет), в
   интерфейсе оно подписано как «Linux (…)». */
const FAMILY_VALUES = ["windows", "unix"];
const STATUS_VALUES = ["draft", "interim", "accepted", "deprecated", "incomplete"];

/* Русские подписи для перечислений выше приходят с backend (see /oval-type-schemas
   -> labels) и складываются в state.labels; тут — запасной вариант на случай,
   если backend недоступен на момент построения формы. */
const FALLBACK_LABELS = {
  status: { draft: "черновик", interim: "промежуточный", accepted: "принят", deprecated: "устарел", incomplete: "неполный" },
  klass: { compliance: "соответствие требованиям", inventory: "инвентаризация", patch: "наличие патча", vulnerability: "уязвимость", miscellaneous: "прочее" },
  family: { windows: "Windows", unix: "Linux (Astra Linux, РЕД ОС, ALT Linux, Ubuntu, Debian)" },
  operation: {
    "equals": "равно", "not equal": "не равно", "greater than": "больше",
    "greater than or equal": "больше или равно", "less than": "меньше",
    "less than or equal": "меньше или равно", "pattern match": "по регулярному выражению",
  },
  datatype: { string: "строка", int: "целое число", boolean: "логическое", version: "версия", float: "дробное число", evr_string: "EVR-строка" },
  check: { all: "все", "at least one": "хотя бы один", "none satisfy": "ни один не соответствует", "none exist": "ни один не существует", "only one": "ровно один" },
  check_existence: {
    at_least_one_exists: "существует хотя бы один", all_exist: "существуют все",
    any_exist: "существует любой", none_exist: "не существует ни одного", only_one_exists: "существует ровно один",
  },
};
state.labels = FALLBACK_LABELS;

/* Английские подписи для тех же перечислений (для дублирования по xml:lang).
   Обновляются с backend вместе с русскими; здесь — запасной вариант. */
const FALLBACK_LABELS_EN = {
  status: { draft: "draft", interim: "interim", accepted: "accepted", deprecated: "deprecated", incomplete: "incomplete" },
  klass: { compliance: "compliance", inventory: "inventory", patch: "patch", vulnerability: "vulnerability", miscellaneous: "miscellaneous" },
  family: { unix: "Linux (Astra Linux, RED OS, ALT Linux, Ubuntu, Debian)", windows: "Windows" },
  operation: {
    "equals": "equals", "not equal": "not equal", "greater than": "greater than",
    "greater than or equal": "greater than or equal", "less than": "less than",
    "less than or equal": "less than or equal", "pattern match": "pattern match",
  },
  datatype: { string: "string", int: "integer", boolean: "boolean", version: "version", float: "float", evr_string: "EVR string" },
  check: { all: "all", "at least one": "at least one", "none satisfy": "none satisfy", "none exist": "none exist", "only one": "only one" },
  check_existence: {
    at_least_one_exists: "at least one exists", all_exist: "all exist",
    any_exist: "any exist", none_exist: "none exist", only_one_exists: "only one exists",
  },
};
state.labelsEn = FALLBACK_LABELS_EN;

/* Двуязычные подписи статических полей форм (id/title/description/…).
   Ключ — техническое имя поля; используется функцией L(key). Совпадает со
   словарём UI_FIELD_LABELS на backend (см. i18n_labels.py) и обновляется
   оттуда же при загрузке схемы, здесь — запасной вариант на случай, если
   backend недоступен. */
const FALLBACK_UI_LABELS = {
  id: { ru: "идентификатор", en: "id" },
  title: { ru: "заголовок", en: "title" },
  description: { ru: "описание", en: "description" },
  version: { ru: "версия", en: "version" },
  status: { ru: "статус", en: "status" },
  class: { ru: "класс", en: "class" },
  family: { ru: "платформа", en: "family" },
  check: { ru: "условие проверки", en: "check" },
  check_existence: { ru: "условие существования", en: "check existence" },
  comment: { ru: "комментарий", en: "comment" },
  criteria: { ru: "критерии", en: "criteria" },
  datatype: { ru: "тип данных", en: "datatype" },
  object_ref: { ru: "объект", en: "object" },
  state_ref: { ru: "состояние", en: "state" },
  reference: { ru: "ссылка на источник", en: "reference" },
  ident: { ru: "идентификатор требования", en: "ident" },
  product_name: { ru: "название продукта", en: "product name" },
  product_version: { ru: "версия продукта", en: "product version" },
  schema_version: { ru: "версия схемы OVAL", en: "schema version" },
  platforms: { ru: "платформы (через запятую)", en: "platforms (comma-separated)" },
  xml_lang: { ru: "язык (xml:lang)", en: "language (xml:lang)" },
  benchmark_id: { ru: "идентификатор бенчмарка", en: "benchmark id" },
  check_content_href: { ru: "OVAL-файл", en: "OVAL file" },
  check_content_name: { ru: "определение OVAL", en: "OVAL definition" },
  test_type: { ru: "тип проверки", en: "check type" },
  value: { ru: "значение", en: "value" },
  file: { ru: "файл", en: "file" },
  project_id_new: { ru: "идентификатор нового проекта", en: "new project id" },
  project_id_folder: { ru: "идентификатор проекта (папка)", en: "project id (folder)" },
  filename: { ru: "имя файла", en: "filename" },
  selected: { ru: "выбрано по умолчанию", en: "selected by default" },
  id_selects: { ru: "правила профиля", en: "profile rule selection" },
  test_ref: { ru: "тест", en: "test" },
};
state.uiLabels = FALLBACK_UI_LABELS;

/* ===================== Утилиты ===================== */

/* Подпись поля по ключу из словаря UI-подписей — на текущем языке
   интерфейса. required=true добавляет красную «*»; tech — необязательная
   техническая приписка (например путь XML-атрибута), выводится моно-шрифтом
   без изменения регистра. Технические приписки не переводятся: это имена
   элементов и атрибутов самого стандарта XCCDF/OVAL. */
function L(key, opts) {
  opts = opts || {};
  const entry = (state.uiLabels && state.uiLabels[key]) || FALLBACK_UI_LABELS[key] || { ru: key, en: key };
  return L2(entry.ru, entry.en, opts);
}

/* То же самое, но для произвольной пары строк ru/en (используется для полей,
   которые приходят с backend как готовый текст — например, подписи OVAL
   entity из реестра типов: f.label / f.label_en). */
function L2(ru, en, opts) {
  opts = opts || {};
  const lang = getLang();
  const text = capFirst(lang === "en" ? (en || ru) : ru);
  const req = opts.required ? '<span class="lbl-req">*</span>' : "";
  const tech = opts.tech ? `<span class="lbl-tech">(${escapeHtml(opts.tech)})</span>` : "";
  return `<span class="lbl"><span class="lbl-ru" lang="${lang}" xml:lang="${lang}">${escapeHtml(text)}</span></span>${req}${tech}`;
}

function escapeHtml(s) {
  if (s === null || s === undefined) return "";
  return String(s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* Быстрый выбор целевых ОС для поля platforms (свободный текст, пишется как
   <platform> внутри OVAL <affected> — в отличие от family, здесь можно
   указывать конкретные дистрибутивы). Список ограничен целевыми системами
   проекта. */
const PLATFORM_PRESETS = [
  "РЕД ОС", "ALT Linux", "Astra Linux", "Debian", "Ubuntu", "Windows",
];
/* Кнопки быстрого выбора платформ зависят от семейства ОС: для Linux —
   дистрибутивы, для Windows — Windows. Пока семейство не выбрано,
   показываются все. */
const PLATFORMS_BY_FAMILY = {
  unix: ["Astra Linux", "РЕД ОС", "ALT Linux", "Ubuntu", "Debian"],
  windows: ["Windows"],
};
function platformsQuickPicksHtml(inputId, family) {
  const list = PLATFORMS_BY_FAMILY[family] || PLATFORMS_BY_FAMILY.unix.concat(PLATFORMS_BY_FAMILY.windows);
  return `<div class="platform-chips" id="${inputId}-chips">${list.map(p =>
    `<button type="button" class="chip" onclick="addPlatformPreset('${inputId}', '${escapeHtml(p).replace(/'/g, "\\'")}')">+ ${escapeHtml(p)}</button>`
  ).join("")}</div>`;
}
function onFamilyChanged() {
  const box = document.getElementById("d-platforms-chips");
  if (box) box.outerHTML = platformsQuickPicksHtml("d-platforms", val("d-family"));
}
function addPlatformPreset(inputId, preset) {
  const el = document.getElementById(inputId);
  const current = el.value.split(",").map(s => s.trim()).filter(Boolean);
  if (!current.includes(preset)) current.push(preset);
  el.value = current.join(", ");
}

/* Первая буква строки — заглавная (остальные не трогаем: в подписях
   встречаются аббревиатуры вроде OVAL, SMBv1, xml:lang). */
function capFirst(s) {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/* opts.hideValue — не показывать техническое значение в скобках (например,
   для семейства ОС, где значение «unix» только запутало бы пользователя). */
function optionsHtml(values, selected, labelsMap, labelsMapEn, opts) {
  const en = getLang() === "en";
  opts = opts || {};
  return values.map(v => {
    let text = v;
    if (labelsMap && labelsMap[v]) {
      const label = capFirst(en && labelsMapEn && labelsMapEn[v] ? labelsMapEn[v] : labelsMap[v]);
      // В скобках остаётся техническое значение — оно попадает в XML и
      // одинаково в обеих языковых версиях.
      text = opts.hideValue ? label : `${label} (${v})`;
    }
    return `<option value="${escapeHtml(v)}" ${v === selected ? "selected" : ""}>${escapeHtml(text)}</option>`;
  }).join("");
}

/* Название типа OVAL-теста на текущем языке интерфейса. */
function typeLabel(cfg, fallback) {
  if (!cfg) return fallback;
  if (getLang() === "en") return cfg.label_en || cfg.label || fallback;
  return cfg.label || fallback;
}

/* Опции со списком типов OVAL-тестов — показываем русское/английское
   название и технический идентификатор (последний обязателен, это
   XML-словарь OVAL). */
function typeBadgeHtml(typeKey) {
  const cfg = state.ovalSchema && state.ovalSchema.types ? state.ovalSchema.types[typeKey] : null;
  return `<span class="badge type" title="${escapeHtml(typeKey)}">${escapeHtml(typeLabel(cfg, typeKey))}</span>`;
}

function testTypeOptionsHtml(types, selected) {
  return types.map(tt => {
    const cfg = state.ovalSchema.types[tt];
    const label = typeLabel(cfg, tt);
    return `<option value="${escapeHtml(tt)}" ${tt === selected ? "selected" : ""}>${escapeHtml(label)} — ${escapeHtml(tt)}</option>`;
  }).join("");
}

function toast(message, type = "ok") {
  const root = document.getElementById("toast-root");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = message;
  root.appendChild(el);
  setTimeout(() => el.remove(), 4500);
}

function openModal(title, bodyHtml, wide) {
  // wide — для окон с широкими таблицами (разбор документа)
  document.getElementById("modal-root").innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <div class="modal${wide ? " modal-wide" : ""}">
        <button type="button" class="modal-close" id="modal-close-btn" title="${t("Закрыть")}" aria-label="${t("Закрыть")}">✕</button>
        <h2>${escapeHtml(title)}</h2>
        ${bodyHtml}
      </div>
    </div>`;
  // Клик вне окна больше не закрывает его (не user-friendly при случайном
  // клике мимо во время заполнения формы) — закрытие только по кнопке ✕
  // или по клавише Escape.
  document.getElementById("modal-close-btn").addEventListener("click", closeModal);
  document.addEventListener("keydown", modalEscHandler);
}
function modalEscHandler(e) {
  if (e.key === "Escape") closeModal();
}
function closeModal() {
  document.getElementById("modal-root").innerHTML = "";
  document.removeEventListener("keydown", modalEscHandler);
}

function formActions(saveLabel = t("Сохранить")) {
  return `
    <div class="modal-actions">
      <button type="button" class="btn" onclick="closeModal()">${t("Отмена")}</button>
      <button type="submit" class="btn btn-primary">${escapeHtml(saveLabel)}</button>
    </div>`;
}

function bindForm(handler, addAnother, keepOpen) {
  // keepOpen — для многошаговых форм (загрузка документа): обработчик сам
  // открывает следующее окно, и закрывать его после возврата нельзя.
  document.getElementById("mf").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await handler();
      if (!keepOpen) closeModal();
      if (addAnother && localStorage.getItem("cpb-no-add-another") !== "1") confirmAddAnother(addAnother);
    } catch (err) {
      toast(err.message, "error");
    }
  });
}

/* Пункт требований: там, где можно добавить несколько однотипных
   параметров (профили, правила, OVAL-файлы, definitions/tests/objects/
   states/variables), после успешного сохранения спрашиваем пользователя,
   не хочет ли он сразу добавить ещё один такой же элемент, вместо того
   чтобы заставлять его самостоятельно искать кнопку «+» ещё раз. */
function confirmAddAnother(opts) {
  const what = getLang() === "en" ? opts.en : opts.ru;
  const question = getLang() === "en"
    ? `Add another ${escapeHtml(what)}?`
    : `Добавить ещё ${escapeHtml(what)}?`;
  openModal(t("Добавить ещё?"), `
    <div class="confirm-more-body">
      <p>${question}</p>
    </div>
    <label class="row-check" style="margin-top:4px;">
      <input type="checkbox" id="no-add-another"> ${t("Больше не спрашивать")}
    </label>
    <div class="modal-actions">
      <button type="button" class="btn" onclick="rememberAddAnother(); closeModal()">${t("Нет")}</button>
      <button type="button" class="btn btn-primary" id="confirm-more-yes">${t("Да, добавить ещё")}</button>
    </div>`);
  document.getElementById("confirm-more-yes").addEventListener("click", () => {
    rememberAddAnother();
    closeModal();
    opts.reopen();
  });
}
function rememberAddAnother() {
  if (checked("no-add-another")) localStorage.setItem("cpb-no-add-another", "1");
}

function val(id) { const el = document.getElementById(id); return el ? el.value.trim() : ""; }
function checked(id) { const el = document.getElementById(id); return el ? el.checked : false; }

/* ===================== Инициализация ===================== */

async function init() {
  initTheme();
  document.getElementById("btn-new-project").addEventListener("click", openNewProjectModal);
  document.getElementById("import-file").addEventListener("change", onImportFileChosen);
  document.getElementById("doc-file").addEventListener("change", onDocumentFileChosen);
  document.getElementById("btn-help").addEventListener("click", openOnboarding);
  document.getElementById("btn-theme-toggle").addEventListener("click", toggleTheme);
  document.getElementById("btn-lang-toggle").addEventListener("click", toggleLang);
  applyLang(getLang());
  try {
    state.ovalSchema = await api.get("/oval-type-schemas");
    if (state.ovalSchema.labels) state.labels = state.ovalSchema.labels;
    if (state.ovalSchema.labels_en) state.labelsEn = state.ovalSchema.labels_en;
    if (state.ovalSchema.ui_labels) state.uiLabels = state.ovalSchema.ui_labels;
  } catch (e) {
    toast(t("Не удалось загрузить схему OVAL-типов: ") + e.message, "error");
  }
  await loadProjects();
  renderView();
  // Экран быстрого старта — только при первом запуске
  if (!localStorage.getItem("cpb-onboarded")) openOnboarding();
}

/* ===================== Тема (светлая/тёмная) ===================== */

const THEME_KEY = "cpb-theme";

function initTheme() {
  // По умолчанию — светлая тема.
  const saved = localStorage.getItem(THEME_KEY) || "light";
  applyTheme(saved);
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem(THEME_KEY, theme);
  const btn = document.getElementById("btn-theme-toggle");
  if (btn) btn.textContent = theme === "dark" ? "☀" : "☾";
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || "light";
  applyTheme(current === "dark" ? "light" : "dark");
}

/* ===================== Язык интерфейса (ru/en) ===================== */

/* Применяет язык: обновляет статические подписи в index.html (те, что не
   перерисовываются из JS), надпись на кнопке-переключателе и атрибут
   lang у документа. Динамическая часть интерфейса перерисовывается
   вызовом renderSidebar()/renderView() в toggleLang(). */
function applyLang(lang) {
  setLang(lang);
  const btn = document.getElementById("btn-lang-toggle");
  // На кнопке показываем язык, на который переключимся следующим нажатием.
  if (btn) btn.textContent = lang === "en" ? "RU" : "EN";

  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n-src") || el.textContent.trim();
    // Исходный русский текст сохраняем при первом проходе, чтобы перевод
    // всегда шёл от него, а не от уже переведённой строки.
    if (!el.getAttribute("data-i18n-src")) el.setAttribute("data-i18n-src", key);
    el.textContent = t(el.getAttribute("data-i18n-src"));
  });

  const title = document.querySelector("title");
  if (title) {
    title.textContent = lang === "en"
      ? "Compliance Profile Builder (XCCDF/OVAL)"
      : "Конструктор профилей соответствия (XCCDF/OVAL)";
  }
  const importLabel = document.querySelector(".import-label");
  if (importLabel) importLabel.textContent = t("Импорт ZIP…");
  const docLabel = document.querySelector('label[for="doc-file"]');
  if (docLabel) docLabel.textContent = t("Загрузить документ…");
  const helpBtn = document.getElementById("btn-help");
  if (helpBtn) helpBtn.textContent = t("Справка и настройки");
  const newProjBtn = document.getElementById("btn-new-project");
  if (newProjBtn) newProjBtn.title = t("Новый проект");
}

function toggleLang() {
  applyLang(getLang() === "en" ? "ru" : "en");
  closeModal();
  renderSidebar();
  renderView();
}

async function loadProjects() {
  state.projects = await api.get("/projects");
  renderSidebar();
}

function renderSidebar() {
  const list = document.getElementById("project-list");
  if (!state.projects.length) {
    list.innerHTML = `<div class="sidebar-hint" style="padding:8px 6px;color:var(--text-faint);font-size:12px;">${t("Проектов пока нет")}</div>`;
    return;
  }
  list.innerHTML = state.projects.map(p => `
    <div class="project-item ${p === state.currentProjectId ? "active" : ""}" onclick="selectProject('${escapeHtml(p)}')">
      <span>${escapeHtml(p)}</span>
      <span class="del" onclick="event.stopPropagation(); deleteProject('${escapeHtml(p)}')" title="${t("Удалить проект")}">✕</span>
    </div>
  `).join("");
}

async function selectProject(id) {
  state.currentProjectId = id;
  state.tab = "overview";
  state.wizardStep = 0;
  state.currentOvalFile = null;
  state.currentOvalData = null;
  state.defsByFile = null;
  await refreshCurrentProject();
  renderSidebar();
  renderView();
  if (state.viewMode === "wizard") maybeShowStepHintModal();
}

async function refreshCurrentProject() {
  if (!state.currentProjectId) return;
  state.currentProject = await api.get(`/projects/${encodeURIComponent(state.currentProjectId)}`);
}

async function deleteProject(id) {
  if (!confirm(`${t("Удалить проект")} '${id}'? ${t("Действие необратимо.")}`)) return;
  try {
    await api.del(`/projects/${encodeURIComponent(id)}`);
    if (state.currentProjectId === id) {
      state.currentProjectId = null;
      state.currentProject = null;
    }
    await loadProjects();
    renderView();
    toast(t("Проект удалён"), "ok");
  } catch (e) { toast(e.message, "error"); }
}


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
    hintRu: "Заполните основные сведения о бенчмарке: заголовок, описание, версию и статус. Это заголовок будущего XCCDF-файла.",
    hintEn: "Fill in the benchmark metadata: title, description, version and status. This becomes the XCCDF file header." },
  { key: "ovalfile", tab: "oval", ovalSub: null,
    ruTitle: "OVAL-файл", enTitle: "OVAL file",
    hintRu: "Создайте OVAL-файл — в нём будет храниться техническая логика проверок. Для одного профиля обычно достаточно одного файла checks-oval.xml.",
    hintEn: "Create an OVAL file to hold the technical check logic. One file, checks-oval.xml, is usually enough for a profile." },
  { key: "variables", tab: "oval", ovalSub: "variables",
    ruTitle: "Переменные", enTitle: "Variables",
    hintRu: "Необязательный шаг. Переменная хранит эталонное значение (например, «24» для длины истории паролей), которое затем подставляется в состояние. Если эталонные значения удобнее вводить прямо в состоянии — шаг можно пропустить.",
    hintEn: "Optional. A variable holds a reference value (e.g. 24 for password history length) that a state then refers to. Skip this step if you prefer to enter values directly in states." },
  { key: "objects", tab: "oval", ovalSub: "objects",
    ruTitle: "Объекты", enTitle: "Objects",
    hintRu: "Объект описывает, ЧТО проверяется на узле: файл, параметр ядра, ключ реестра, пакет, политику паролей. Сначала выберите тип проверки — от него зависит набор полей.",
    hintEn: "An object describes WHAT is checked on the host: a file, kernel parameter, registry key, package, or password policy. Choose the check type first — the fields depend on it." },
  { key: "states", tab: "oval", ovalSub: "states",
    ruTitle: "Состояния", enTitle: "States",
    hintRu: "Состояние задаёт ожидаемое значение объекта: чему должно равняться, больше или меньше чего быть. Если проверяется только наличие объекта (например, установленный пакет), состояние не нужно.",
    hintEn: "A state defines the expected value of an object: what it must equal, exceed or stay below. If you only check that an object exists (e.g. an installed package), no state is needed." },
  { key: "tests", tab: "oval", ovalSub: "tests",
    ruTitle: "Тесты", enTitle: "Tests",
    hintRu: "Тест связывает объект с состоянием: «взять этот объект и сравнить с этим состоянием». Списки объектов и состояний автоматически отфильтрованы по выбранному типу проверки.",
    hintEn: "A test links an object to a state: \"take this object and compare it with this state\". Object and state lists are filtered by the selected check type automatically." },
  { key: "definitions", tab: "oval", ovalSub: "definitions",
    ruTitle: "Определения", enTitle: "Definitions",
    hintRu: "Определение — это законченная проверка с названием и описанием. Оно объединяет один или несколько тестов через критерии. Именно на определение будет ссылаться правило.",
    hintEn: "A definition is a complete check with a title and description. It combines one or more tests through criteria. Rules refer to definitions." },
  { key: "rules", tab: "rules",
    ruTitle: "Правила", enTitle: "Rules",
    hintRu: "Правило — требование безопасности в терминах документа (XCCDF). Каждое правило ссылается на определение из OVAL-файла и содержит идентификатор требования (ident).",
    hintEn: "A rule is a security requirement in document terms (XCCDF). Each rule refers to an OVAL definition and carries a requirement identifier (ident)." },
  { key: "profiles", tab: "profiles",
    ruTitle: "Профили", enTitle: "Profiles",
    hintRu: "Профиль — именованный набор правил, который запускается как одна проверка (например, «Базовый» или «Усиленный»). Отметьте правила, которые должны войти в профиль.",
    hintEn: "A profile is a named set of rules run as a single check (e.g. \"Baseline\" or \"Hardened\"). Tick the rules the profile should include." },
  { key: "validate", tab: "validate",
    ruTitle: "Проверка и экспорт", enTitle: "Validation & export",
    hintRu: "Проверьте проект на корректность и выгрузите готовый ZIP-архив для импорта в Kaspersky Vulnerability Management.",
    hintEn: "Validate the project and export the ready-to-import ZIP archive for Kaspersky Vulnerability Management." },
];

/* Порядок вкладок конструктора и подразделов OVAL — тот же, что у мастера. */
const OVAL_SUBTABS = ["variables", "objects", "states", "tests", "definitions"];

function stepTitle(step) { return getLang() === "en" ? step.enTitle : step.ruTitle; }
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
      ${step ? `<button class="btn btn-sm" onclick="gotoStepKey('${stepKey}')">${escapeHtml(t("Перейти к шагу"))} «${escapeHtml(stepTitle(step))}»</button>` : ""}
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
      <p>${escapeHtml(stepHint(step))}</p>
    </div>
    <label class="row-check" style="margin-top:6px;">
      <input type="checkbox" id="hint-dont-show" checked> ${t("Больше не показывать эту подсказку")}
    </label>
    <div class="modal-actions">
      <button type="button" class="btn btn-primary" onclick="dismissStepHint('${step.key}')">${t("Понятно")}</button>
    </div>`);
}
function dismissStepHint(stepKey) {
  if (checked("hint-dont-show")) localStorage.setItem(hintSeenKey(stepKey), "1");
  closeModal();
}

function modeSwitchHtml() {
  return `
    <div class="mode-switch">
      <button class="${state.viewMode === "wizard" ? "active" : ""}" onclick="setViewMode('wizard')">${t("Мастер")}</button>
      <button class="${state.viewMode === "constructor" ? "active" : ""}" onclick="setViewMode('constructor')">${t("Конструктор")}</button>
    </div>`;
}

function wizardStepsHtml() {
  return `<div class="wizard-steps">` + WIZARD_STEPS.map((s, i) => `
    <div class="wizard-step ${i === state.wizardStep ? "active" : ""} ${i < state.wizardStep ? "done" : ""}" onclick="setWizardStep(${i})">
      <span class="num">${i + 1}</span><span>${escapeHtml(stepTitle(s))}</span>
    </div>`).join("") + `</div>`;
}

function wizardHintBannerHtml(step) {
  return `
    <div class="wizard-hint-banner">
      <span class="icon">💡</span>
      <div><div>${escapeHtml(stepHint(step))}</div></div>
      <button class="btn btn-sm hint-reopen" onclick="maybeForceShowHint()" title="${t("Показать подсказку")}"><span class="hint-reopen-icon">?</span> ${t("Подсказка")}</button>
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
      <button type="button" class="hintbtn" onclick="toggleHintPopover(event, '${id}')">?</button>
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
    <div class="page-sub">${t("Проект")}: <span class="mono-input" style="all:unset;font-family:var(--mono);">${escapeHtml(state.currentProjectId)}</span></div>
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
      <button class="btn" ${state.wizardStep === 0 ? "disabled" : ""} onclick="wizardBack()">${t("← Назад")}</button>
      <button class="btn btn-primary" ${state.wizardStep === WIZARD_STEPS.length - 1 ? "disabled" : ""} onclick="wizardNext()">${t("Далее →")}</button>
    </div>` : ""}
  `;
  const content = document.getElementById("tab-content");
  if (state.tab === "overview") content.innerHTML = renderOverview(b);
  else if (state.tab === "profiles") content.innerHTML = renderProfiles(b);
  else if (state.tab === "rules") content.innerHTML = renderRules(b);
  else if (state.tab === "oval") renderOval(content);
  else if (state.tab === "validate") renderValidate(content);

  if (state.tab === "overview") bindOverviewForm();
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
  return `<div class="tab ${state.tab === key ? "active" : ""}" onclick="setTab('${key}')">${escapeHtml(label)}</div>`;
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

/* ===================== Правила ===================== */

/* Определения всех OVAL-файлов проекта: {файл: [определения]}. Нужны форме
   правила, чтобы предлагать выбор определения из списка, а не вводить
   идентификатор вручную. */
async function loadAllDefinitions() {
  const out = {};
  for (const f of state.currentProject.oval_files) {
    try {
      const d = (state.currentOvalData && state.currentOvalData.filename === f)
        ? state.currentOvalData
        : await api.get(`/projects/${encodeURIComponent(state.currentProjectId)}/oval-files/${encodeURIComponent(f)}`);
      out[f] = d.definitions || [];
    } catch (e) { out[f] = []; }
  }
  state.defsByFile = out;
  return out;
}
function totalDefinitions() {
  return Object.values(state.defsByFile || {}).reduce((n, l) => n + l.length, 0);
}

/* Следующий свободный идентификатор XCCDF-элемента: <prefix><N+1>. */
function nextXccdfId(list, prefix) {
  let max = 0;
  (list || []).forEach(x => {
    const m = new RegExp("^" + prefix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "(\\d+)$").exec(x.id || "");
    if (m) max = Math.max(max, parseInt(m[1], 10));
  });
  return prefix + (max + 1);
}

function renderRules(b) {
  if (state.defsByFile && totalDefinitions() === 0) {
    return `<div class="panel">${depWarningHtml(
      "Правило ссылается на определение из OVAL-файла, поэтому сначала нужно создать хотя бы одно определение.",
      "A rule refers to a definition in an OVAL file, so create at least one definition first.", "definitions")}</div>`;
  }
  const rows = b.rules.map(r => `
    <tr>
      <td class="id-cell">${escapeHtml(r.id)}</td>
      <td>${escapeHtml(r.title)}</td>
      <td class="id-cell">${escapeHtml((r.idents || []).map(i => i.value).join(", ") || "—")}</td>
      <td class="muted">${escapeHtml(r.check_href || "—")}<br><span class="id-cell">${escapeHtml(r.check_name || "")}</span></td>
      <td class="actions-cell">
        <button class="btn btn-sm" onclick="openEditRuleModal('${escapeHtml(r.id)}')">${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" onclick="deleteRule('${escapeHtml(r.id)}')">${t("Удалить")}</button>
      </td>
    </tr>`).join("");
  return `
    <div class="panel">
      <div class="toolbar">
        <button class="btn btn-primary" onclick="openAddRuleModal()">${t("+ Правило")}</button>
      </div>
      ${b.rules.length ? `
        <table>
          <thead><tr><th>${t("Идентификатор")}</th><th>${t("Название")}</th><th>${t("Требование (ident)")}</th><th>${t("Определение")}</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table>` : emptyListHtml("Правила ещё не добавлены.", "No rules yet.")}
    </div>
  `;
}

function identRowHtml(i) {
  i = i || { system: "", value: "" };
  return `
    <div class="row" data-ident-row style="margin-bottom:6px;">
      <input class="mono-input" placeholder="${t("Система (system)")}" value="${escapeHtml(i.system)}" data-ident-system style="flex:1;">
      <input class="mono-input" placeholder="${t("Значение (value)")}" value="${escapeHtml(i.value)}" data-ident-value style="flex:1;">
      <button type="button" class="btn-icon" onclick="this.closest('[data-ident-row]').remove()">✕</button>
    </div>`;
}
function identsEditorHtml(idents) {
  const list = idents && idents.length ? idents : [null];
  return `<div id="idents-container">${list.map(identRowHtml).join("")}</div>
    <button type="button" class="btn btn-sm" onclick="addIdentRow()">${t("+ Идентификатор требования")}</button>`;
}
function addIdentRow() {
  document.getElementById("idents-container").insertAdjacentHTML("beforeend", identRowHtml(null));
}
function collectIdents() {
  return Array.from(document.querySelectorAll("[data-ident-row]")).map(row => ({
    system: row.querySelector("[data-ident-system]").value.trim(),
    value: row.querySelector("[data-ident-value]").value.trim(),
  })).filter(i => i.system && i.value);
}

function ovalFileOptions(selected) {
  return optionsHtml(state.currentProject.oval_files, selected);
}

/* Список определений выбранного OVAL-файла в форме правила. */
function onRuleFileChanged(selectedDef) {
  const file = val("r-href");
  const defs = (state.defsByFile || {})[file] || [];
  const sel = document.getElementById("r-name");
  sel.innerHTML = defs.length
    ? defs.map(d => `<option value="${escapeHtml(d.id)}" ${d.id === selectedDef ? "selected" : ""}>${escapeHtml(d.id)} — ${escapeHtml(d.title)}</option>`).join("")
    : `<option value="">${t("В этом файле нет определений")}</option>`;
}
/* При выборе определения название и описание правила подставляются из
   него, если пользователь ещё не заполнил их сам. */
function onRuleDefChanged() {
  const defs = (state.defsByFile || {})[val("r-href")] || [];
  const d = defs.find(x => x.id === val("r-name"));
  if (!d) return;
  const title = document.getElementById("r-title");
  const desc = document.getElementById("r-description");
  if (title && !title.value) title.value = d.title || "";
  if (desc && !desc.value) desc.value = d.description || "";
}

function ruleFormHtml(r, isNew) {
  r = r || {};
  const rules = state.currentProject.benchmark.rules;
  // Система требований по умолчанию — та же, что у последнего правила.
  const lastSystem = (rules.slice().reverse().find(x => (x.idents || []).length) || {}).idents;
  const defaultIdents = isNew
    ? [{ system: (lastSystem && lastSystem[0].system) || "custom_requirements", value: `REQ.${rules.length + 1}` }]
    : r.idents;
  return `
    <form id="mf">
      <div class="grid">
        <div class="field"><label>${L('check_content_href', {required:true})}</label>
          <select id="r-href" required onchange="onRuleFileChanged()">${ovalFileOptions(r.check_href)}</select>
        </div>
        <div class="field"><label>${L('check_content_name', {required:true})} ${hintIcon(
          "Определение из OVAL-файла, которое реализует это правило технически. При выборе название и описание правила подставляются автоматически.",
          "The OVAL definition that implements this rule. Selecting it pre-fills the rule title and description."
        )}</label>
          <select class="mono-input" id="r-name" required onchange="onRuleDefChanged()"></select>
        </div>
      </div>
      ${isNew ? `<div class="field"><label>${L('id', {required:true})}</label><input class="mono-input" id="r-id" required value="${escapeHtml(nextXccdfId(rules, "xccdf_custom_rule_"))}"></div>` : ""}
      <div class="field"><label>${L('title', {required:true})}</label><input id="r-title" required value="${escapeHtml(r.title || "")}"></div>
      <div class="field"><label>${L('description', {required:true})}</label><textarea id="r-description" required>${escapeHtml(r.description || "")}</textarea></div>
      <div class="field"><label>${L('ident', {required:true})} ${hintIcon(
        "Идентификатор требования, которому соответствует правило: система (каталог требований) и номер пункта. Обязателен — без него правило не будет распознано при импорте.",
        "The requirement this rule maps to: a system (requirements catalogue) and an item number. Required — without it the rule is not recognised on import."
      )}</label>${identsEditorHtml(defaultIdents)}</div>
      <label class="row-check" style="margin-top:4px;"><input type="checkbox" id="r-selected" ${r.selected ? "checked" : ""}> ${L("selected")}</label>
      ${formActions(isNew ? t("Создать") : t("Сохранить"))}
    </form>`;
}

async function openAddRuleModal() {
  await loadAllDefinitions();
  if (!totalDefinitions()) { renderView(); return; }
  // Первым предлагается файл, в котором есть определения.
  const firstWithDefs = state.currentProject.oval_files.find(f => (state.defsByFile[f] || []).length);
  openModal(t("Новое правило"), ruleFormHtml({ check_href: firstWithDefs }, true));
  onRuleFileChanged();
  onRuleDefChanged();
  bindForm(async () => {
    await api.post(`/projects/${encodeURIComponent(state.currentProjectId)}/rules`, {
      id: val("r-id"), selected: checked("r-selected"), title: val("r-title"),
      description: val("r-description"), idents: collectIdents(),
      check_href: val("r-href"), check_name: val("r-name"),
    });
    await refreshCurrentProject(); renderView(); toast(t("Правило создано"), "ok");
  }, { ru: "правило", en: "rule", reopen: openAddRuleModal });
}

async function openEditRuleModal(id) {
  await loadAllDefinitions();
  const r = state.currentProject.benchmark.rules.find(x => x.id === id);
  openModal(`${t("Правило")}: ${id}`, ruleFormHtml(r, false));
  onRuleFileChanged(r.check_name);
  bindForm(async () => {
    await api.put(`/projects/${encodeURIComponent(state.currentProjectId)}/rules/${encodeURIComponent(id)}`, {
      selected: checked("r-selected"), title: val("r-title"), description: val("r-description"),
      idents: collectIdents(), check_href: val("r-href"), check_name: val("r-name"),
    });
    await refreshCurrentProject(); renderView(); toast(t("Сохранено"), "ok");
  });
}

async function deleteRule(id) {
  if (!confirm(`${t("Удалить правило")} '${id}'?`)) return;
  try {
    await api.del(`/projects/${encodeURIComponent(state.currentProjectId)}/rules/${encodeURIComponent(id)}`);
    await refreshCurrentProject(); renderView(); toast(t("Правило удалено"), "ok");
  } catch (e) { toast(e.message, "error"); }
}

/* ===================== Профили ===================== */

function renderProfiles(b) {
  if (!b.rules.length) {
    return `<div class="panel">${depWarningHtml(
      "Профиль — это набор правил, поэтому сначала нужно создать хотя бы одно правило.",
      "A profile is a set of rules, so create at least one rule first.", "rules")}</div>`;
  }
  const rows = b.profiles.map(p => `
    <tr>
      <td class="id-cell">${escapeHtml(p.id)}</td>
      <td>${escapeHtml(p.title)}</td>
      <td>${p.selects.filter(s => s.selected).length} / ${b.rules.length}</td>
      <td class="actions-cell">
        <button class="btn btn-sm" onclick="openManageSelectsModal('${escapeHtml(p.id)}')">${t("Состав")}</button>
        <button class="btn btn-sm" onclick="openEditProfileModal('${escapeHtml(p.id)}')">${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" onclick="deleteProfile('${escapeHtml(p.id)}')">${t("Удалить")}</button>
      </td>
    </tr>`).join("");
  return `
    <div class="panel">
      <div class="toolbar">
        <button class="btn btn-primary" onclick="openAddProfileModal()">${t("+ Профиль")}</button>
      </div>
      ${b.profiles.length ? `
        <table>
          <thead><tr><th>${t("Идентификатор")}</th><th>${t("Название")}</th><th>${t("Правил в составе")}</th><th></th></tr></thead>
          <tbody>${rows}</tbody>
        </table>` : emptyListHtml("Профили ещё не добавлены.", "No profiles yet.")}
    </div>
  `;
}

/* Список правил с галочками — используется и при создании профиля, и при
   изменении его состава. */
function rulesChecklistHtml(selectedIds) {
  const rules = state.currentProject.benchmark.rules;
  return `
    <div class="rules-checklist">
      <label class="row-check checklist-all"><input type="checkbox" id="rules-all" onchange="toggleAllRules(this.checked)" ${rules.every(r => selectedIds.has(r.id)) ? "checked" : ""}> <b>${t("Выбрать все")}</b></label>
      ${rules.map(r => `
        <label class="row-check" style="padding:4px 0;">
          <input type="checkbox" class="rule-check" value="${escapeHtml(r.id)}" ${selectedIds.has(r.id) ? "checked" : ""}>
          <span class="id-cell">${escapeHtml(r.id)}</span>
          <span class="muted">— ${escapeHtml(r.title || "")}</span>
        </label>`).join("")}
    </div>`;
}
function toggleAllRules(on) {
  document.querySelectorAll(".rule-check").forEach(b => { b.checked = on; });
}
function checkedRuleIds() {
  return Array.from(document.querySelectorAll(".rule-check")).filter(b => b.checked).map(b => b.value);
}

function openAddProfileModal() {
  const b = state.currentProject.benchmark;
  const all = new Set(b.rules.map(r => r.id));   // по умолчанию — все правила
  openModal(t("Новый профиль"), `
    <form id="mf">
      <div class="field"><label>${L('id', {required:true})}</label><input class="mono-input" id="p-id" required value="${escapeHtml(nextXccdfId(b.profiles, "xccdf_custom_profile_"))}"></div>
      <div class="field"><label>${L('title', {required:true})}</label><input id="p-title" required></div>
      <div class="field"><label>${L('description', {required:true})}</label><textarea id="p-description" required></textarea></div>
      <div class="field"><label>${L('reference')}</label><input id="p-reference" placeholder="https://..."></div>
      <div class="field"><label>${L('id_selects')} ${hintIcon(
        "Правила, которые войдут в профиль. По умолчанию отмечены все; состав можно изменить позже кнопкой «Состав».",
        "Rules included in the profile. All are ticked by default; you can change this later with the \"Contents\" button."
      )}</label>${rulesChecklistHtml(all)}</div>
      ${formActions(t("Создать"))}
    </form>`);
  bindForm(async () => {
    const pid = val("p-id");
    const chosen = checkedRuleIds();
    await api.post(`/projects/${encodeURIComponent(state.currentProjectId)}/profiles`, {
      id: pid, title: val("p-title"), description: val("p-description"),
      reference: val("p-reference") || null,
    });
    for (const ruleId of chosen) {
      await api.put(`/projects/${encodeURIComponent(state.currentProjectId)}/profiles/${encodeURIComponent(pid)}/select`, { idref: ruleId, selected: true });
    }
    await refreshCurrentProject(); renderView(); toast(t("Профиль создан"), "ok");
  }, { ru: "профиль", en: "profile", reopen: openAddProfileModal });
}

function openEditProfileModal(id) {
  const p = state.currentProject.benchmark.profiles.find(x => x.id === id);
  openModal(`${t("Профиль")}: ${id}`, `
    <form id="mf">
      <div class="field"><label>${L('title', {required:true})}</label><input id="p-title" required value="${escapeHtml(p.title)}"></div>
      <div class="field"><label>${L('description', {required:true})}</label><textarea id="p-description" required>${escapeHtml(p.description)}</textarea></div>
      <div class="field"><label>${L('reference')}</label><input id="p-reference" value="${escapeHtml(p.reference || "")}"></div>
      ${formActions()}
    </form>`);
  bindForm(async () => {
    await api.put(`/projects/${encodeURIComponent(state.currentProjectId)}/profiles/${encodeURIComponent(id)}`, {
      title: val("p-title"), description: val("p-description"), reference: val("p-reference") || null,
    });
    await refreshCurrentProject(); renderView(); toast(t("Сохранено"), "ok");
  });
}

async function deleteProfile(id) {
  if (!confirm(`${t("Удалить профиль")} '${id}'?`)) return;
  try {
    await api.del(`/projects/${encodeURIComponent(state.currentProjectId)}/profiles/${encodeURIComponent(id)}`);
    await refreshCurrentProject(); renderView(); toast(t("Профиль удалён"), "ok");
  } catch (e) { toast(e.message, "error"); }
}

function openManageSelectsModal(profileId) {
  const b = state.currentProject.benchmark;
  const profile = b.profiles.find(x => x.id === profileId);
  const selectedIds = new Set(profile.selects.filter(s => s.selected).map(s => s.idref));
  openModal(`${t("Состав профиля")}: ${profileId}`, `
    <form id="mf">
      <div class="field">${rulesChecklistHtml(selectedIds)}</div>
      ${formActions(t("Сохранить состав"))}
    </form>`);
  bindForm(async () => {
    const nowChecked = new Set(checkedRuleIds());
    const base = `/projects/${encodeURIComponent(state.currentProjectId)}/profiles/${encodeURIComponent(profileId)}`;
    for (const ruleId of nowChecked) {
      const s = profile.selects.find(x => x.idref === ruleId);
      if (!s || !s.selected) await api.put(`${base}/select`, { idref: ruleId, selected: true });
    }
    for (const s of profile.selects) {
      if (!nowChecked.has(s.idref)) await api.del(`${base}/select/${encodeURIComponent(s.idref)}`);
    }
    await refreshCurrentProject(); renderView(); toast(t("Состав профиля сохранён"), "ok");
  });
}

/* ===================== Вкладка: OVAL-файлы ===================== */

function renderOval(container) {
  const files = state.currentProject.oval_files;
  const isWizard = state.viewMode === "wizard";
  const step = isWizard ? currentStep() : null;
  // Шаг мастера «OVAL-файл» — только управление файлами.
  // Шаги 3–7 — только раздел своей сущности, без переключателя подразделов.
  const fileStep = isWizard && step.key === "ovalfile";
  const entityStep = isWizard && !!step.ovalSub;

  if (entityStep && !files.length) {
    container.innerHTML = `<div class="panel">${depWarningHtml(
      "Сначала создайте OVAL-файл — в нём будут храниться все элементы проверок.",
      "Create an OVAL file first — it will hold all check elements.", "ovalfile")}</div>`;
    return;
  }

  const showFileToolbar = !entityStep;          // добавление файлов
  const showChips = !entityStep || files.length > 1;  // выбор файла, если их несколько
  container.innerHTML = `
    <div class="panel">
      ${showFileToolbar ? `
      <div class="toolbar">
        <button class="btn btn-primary" onclick="openAddOvalFileModal()">${t("+ OVAL-файл")}</button>
      </div>` : ""}
      ${showChips ? `
      <div class="oval-file-list" id="oval-file-list">
        ${files.map(f => `
          <div class="oval-file-chip ${f === state.currentOvalFile ? "active" : ""}" onclick="selectOvalFile('${escapeHtml(f)}')">
            ${escapeHtml(f)}
          </div>`).join("") || `<span class="muted">${t("OVAL-файлы ещё не добавлены.")}</span>`}
      </div>` : ""}
      ${fileStep && files.length ? `<div class="muted" style="margin-top:6px;">${t("Файл создан. Нажмите «Далее», чтобы перейти к наполнению проверок.")}</div>` : ""}
      <div id="oval-file-detail"></div>
    </div>
  `;
  if (!fileStep && state.currentOvalFile && files.includes(state.currentOvalFile)) {
    renderOvalFileDetail(document.getElementById("oval-file-detail"), entityStep);
  }
}

/* Имя OVAL-файла по требованию формата архива оканчивается на -oval.xml.
   Пользователю не нужно помнить это правило: «checks», «checks.xml» и
   «checks-oval.xml» дают одно и то же имя. */
function normalizeOvalName(name) {
  let n = (name || "").trim().replace(/\s+/g, "-");
  if (!n) return "checks-oval.xml";
  n = n.replace(/\.xml$/i, "").replace(/-oval$/i, "");
  return n + "-oval.xml";
}
function previewOvalName() {
  const el = document.getElementById("of-final");
  if (el) el.textContent = normalizeOvalName(val("of-filename"));
}

function openAddOvalFileModal() {
  openModal(t("Новый OVAL-файл"), `
    <form id="mf">
      <div class="field"><label>${L('filename', {required:true})}</label><input class="mono-input" id="of-filename" required value="checks" oninput="previewOvalName()">
        <span class="hint">${t("Итоговое имя файла")}: <code id="of-final">checks-oval.xml</code> — ${t("окончание -oval.xml добавляется автоматически.")}</span></div>
      <div class="grid">
        <div class="field"><label>${L('product_name')}</label><input id="of-product" value="Custom"></div>
        <div class="field"><label>${L('product_version')}</label><input id="of-version" value="1.0"></div>
        <div class="field full"><label>${L('schema_version')}</label><input class="mono-input" id="of-schema" value="5.11.2"></div>
      </div>
      ${formActions(t("Создать"))}
    </form>`);
  bindForm(async () => {
    const fname = normalizeOvalName(val("of-filename"));
    await api.post(`/projects/${encodeURIComponent(state.currentProjectId)}/oval-files`, {
      filename: fname, product_name: val("of-product"), product_version: val("of-version"), schema_version: val("of-schema"),
    });
    await refreshCurrentProject();
    state.currentOvalFile = fname;
    await loadOvalFileData();
    renderView();
    toast(t("OVAL-файл создан"), "ok");
  }, { ru: "OVAL-файл", en: "OVAL file", reopen: openAddOvalFileModal });
}

async function deleteOvalFile(filename) {
  if (!confirm(`${t("Удалить OVAL-файл")} '${filename}'? ${t("Ссылающиеся на него правила перестанут быть валидны.")}`)) return;
  try {
    await api.del(`/projects/${encodeURIComponent(state.currentProjectId)}/oval-files/${encodeURIComponent(filename)}`);
    if (state.currentOvalFile === filename) { state.currentOvalFile = null; state.currentOvalData = null; }
    await refreshCurrentProject(); renderView(); toast(t("Файл удалён"), "ok");
  } catch (e) { toast(e.message, "error"); }
}

async function selectOvalFile(filename) {
  state.currentOvalFile = filename;
  if (state.viewMode !== "wizard") state.ovalSubtab = state.ovalSubtab || "variables";
  await loadOvalFileData();
  renderView();
}

async function loadOvalFileData() {
  if (!state.currentOvalFile) return;
  state.currentOvalData = await api.get(
    `/projects/${encodeURIComponent(state.currentProjectId)}/oval-files/${encodeURIComponent(state.currentOvalFile)}`
  );
}

function setOvalSubtab(tab) { state.ovalSubtab = tab; renderView(); }

function renderOvalFileDetail(container, entityStep) {
  const d = state.currentOvalData;
  if (!d) { container.innerHTML = ""; return; }
  if (!OVAL_SUBTABS.includes(state.ovalSubtab)) state.ovalSubtab = "variables";
  const counts = {
    variables: d.variables.length, objects: d.objects.length, states: d.states.length,
    tests: d.tests.length, definitions: d.definitions.length,
  };
  const names = {
    variables: t("Переменные"), objects: t("Объекты"), states: t("Состояния"),
    tests: t("Тесты"), definitions: t("Определения"),
  };
  container.innerHTML = `
    ${entityStep ? "" : `
    <div class="section-divider"></div>
    <div class="row" style="justify-content:space-between;margin-bottom:12px;">
      <div class="muted">${t("Генератор")}: ${escapeHtml(d.generator.product_name)} ${escapeHtml(d.generator.product_version)}, ${t("схема OVAL")} ${escapeHtml(d.generator.schema_version)}</div>
      <button class="btn btn-sm btn-danger" onclick="deleteOvalFile('${escapeHtml(state.currentOvalFile)}')">${t("Удалить файл")}</button>
    </div>
    <div class="subtabs subtabs-flow">
      ${OVAL_SUBTABS.map((k, i) => `${i ? '<span class="flow-arrow">→</span>' : ""}${subtabHtml(k, `${i + 1}. ${names[k]} (${counts[k]})`)}`).join("")}
    </div>`}
    <div id="oval-subtab-content"></div>
  `;
  const c = document.getElementById("oval-subtab-content");
  if (state.ovalSubtab === "definitions") renderDefinitions(c, d);
  else if (state.ovalSubtab === "tests") renderTests(c, d);
  else if (state.ovalSubtab === "objects") renderObjects(c, d);
  else if (state.ovalSubtab === "states") renderStates(c, d);
  else if (state.ovalSubtab === "variables") renderVariables(c, d);
}

function subtabHtml(key, label) {
  return `<div class="subtab ${state.ovalSubtab === key ? "active" : ""}" onclick="setOvalSubtab('${key}')">${escapeHtml(label)}</div>`;
}

/* ===================== Элементы OVAL-файла =====================
   Разделы расположены в порядке зависимостей: переменные → объекты →
   состояния → тесты → определения. Формы подсказывают следующий свободный
   идентификатор и предлагают только те элементы, на которые реально можно
   сослаться, — пользователю не нужно помнить идентификаторы и типы. */

function ovalBase() {
  return `/projects/${encodeURIComponent(state.currentProjectId)}/oval-files/${encodeURIComponent(state.currentOvalFile)}`;
}

/* Следующий свободный идентификатор вида oval:<ns>:<kind>:<N>.
   Пространство имён берётся из уже существующих элементов файла
   (по умолчанию "custom"), номер — максимальный + 1. */
function nextOvalId(kind) {
  const d = state.currentOvalData || {};
  const all = [].concat(d.definitions || [], d.tests || [], d.objects || [], d.states || [], d.variables || []);
  let ns = "custom";
  const anyId = all.map(x => x.id).find(id => /^oval:[^:]+:[a-z]+:\d+$/.test(id || ""));
  if (anyId) ns = anyId.split(":")[1];
  const pool = { def: d.definitions, tst: d.tests, obj: d.objects, ste: d.states, var: d.variables }[kind] || [];
  let max = 0;
  pool.forEach(x => {
    const m = /^oval:[^:]+:[a-z]+:(\d+)$/.exec(x.id || "");
    if (m) max = Math.max(max, parseInt(m[1], 10));
  });
  return `oval:${ns}:${kind}:${max + 1}`;
}

/* Подпись элемента в выпадающем списке: идентификатор и комментарий. */
function refLabel(item) {
  return item.comment ? `${item.id} — ${item.comment}` : item.id;
}
function refOptionsHtml(items, selected) {
  return items.map(x =>
    `<option value="${escapeHtml(x.id)}" ${x.id === selected ? "selected" : ""}>${escapeHtml(refLabel(x))}</option>`
  ).join("");
}

/* Поля объекта/состояния в таблице — «имя = значение», читаемо, без JSON. */
function fieldsSummary(fields) {
  const parts = Object.entries(fields || {}).map(([k, v]) => {
    if (v && typeof v === "object") {
      const val_ = v.var_ref ? `→ ${v.var_ref}` : (v.value != null ? v.value : "");
      const op = v.operation ? ` (${v.operation})` : "";
      return `${k} = ${val_}${op}`;
    }
    return `${k} = ${v}`;
  });
  return parts.length ? parts.map(escapeHtml).join("<br>") : `<span class="muted">—</span>`;
}

/* Семейство ОС для определения по типу теста: windows:* → windows,
   всё остальное (ind:, unix:, linux:) → unix. */
function familyForTestType(type) {
  return (type || "").startsWith("windows:") ? "windows" : "unix";
}

function emptyListHtml(ru, en) {
  return `<div class="muted">${escapeHtml(getLang() === "en" ? en : ru)}</div>`;
}

/* ---------- Переменные ---------- */

function renderVariables(container, d) {
  const rows = d.variables.map(v => `
    <tr>
      <td class="id-cell">${escapeHtml(v.id)}</td>
      <td>${escapeHtml(v.datatype)}</td>
      <td class="id-cell">${escapeHtml(v.value)}</td>
      <td>${escapeHtml(v.comment || "")}</td>
      <td class="actions-cell"><button class="btn btn-sm" onclick="openEditVariableModal('${escapeHtml(v.id)}')">${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" onclick="deleteVariable('${escapeHtml(v.id)}')">${t("Удалить")}</button></td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" onclick="openAddVariableModal()">${t("+ Переменная")}</button></div>
    ${d.variables.length
      ? `<table><thead><tr><th>${t("Идентификатор")}</th><th>${t("Тип данных")}</th><th>${t("Значение")}</th><th>${t("Комментарий")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
      : emptyListHtml("Переменные ещё не добавлены. Это необязательный шаг — его можно пропустить.",
                      "No variables yet. This step is optional and can be skipped.")}
  `;
}

function openAddVariableModal() {
  openModal(t("Новая переменная"), `
    <form id="mf">
      <div class="grid">
        <div class="field"><label>${L('id', {required:true})}</label><input class="mono-input" id="v-id" required value="${escapeHtml(nextOvalId("var"))}"></div>
        <div class="field"><label>${L('version')}</label><input id="v-version" value="1"></div>
        <div class="field"><label>${L('datatype')}</label><select id="v-datatype">${optionsHtml(DATATYPES, "int", state.labels.datatype, state.labelsEn.datatype)}</select></div>
        <div class="field"><label>${L('value', {required:true})}</label><input class="mono-input" id="v-value" required></div>
        <div class="field full"><label>${L('comment')}</label><input id="v-comment"></div>
      </div>
      ${formActions(t("Создать"))}
    </form>`);
  bindForm(async () => {
    await api.post(`${ovalBase()}/variables`, {
      id: val("v-id"), version: val("v-version") || "1", datatype: val("v-datatype"),
      value: val("v-value"), comment: val("v-comment") || null,
    });
    await loadOvalFileData(); renderView(); toast(t("Переменная создана"), "ok");
  }, { ru: "переменную", en: "variable", reopen: openAddVariableModal });
}

async function deleteVariable(id) {
  if (!confirm(`${t("Удалить переменную")} '${id}'?`)) return;
  try {
    await api.del(`${ovalBase()}/variables/${encodeURIComponent(id)}`);
    await loadOvalFileData(); renderView(); toast(t("Переменная удалена"), "ok");
  } catch (e) { toast(e.message, "error"); }
}

/* ---------- Объекты / состояния: генерируемые по схеме формы ---------- */

function fieldPlainInputHtml(f, prefix, value) {
  value = value == null ? "" : String(value);
  if (f.options && f.options.length) {
    return `<select id="${prefix}_${f.name}"><option value="">—</option>${optionsHtml(f.options, value)}</select>`;
  }
  return `<input class="mono-input" id="${prefix}_${f.name}" placeholder="${escapeHtml(f.name)}" value="${escapeHtml(value)}">`;
}

function objectFieldsEditorHtml(fields_config, values) {
  // values — текущие значения полей при изменении существующего объекта
  values = values || {};
  return fields_config.map(f => `
    <div class="field">
      <label>${L2(f.label, f.label_en, {required: f.required, tech: f.name})}</label>
      ${fieldPlainInputHtml(f, "objf", values[f.name])}
    </div>`).join("") || `<div class="muted">${t("У этого типа проверки нет полей объекта — объект описывает всю политику целиком.")}</div>`;
}
function collectObjectFields(fields_config) {
  const out = {};
  fields_config.forEach(f => {
    const v = val(`objf_${f.name}`);
    if (v) out[f.name] = v;
  });
  return out;
}

function stateFieldsEditorHtml(fields_config, variables, values) {
  // values — текущие значения полей при изменении существующего состояния:
  // либо {value, operation, datatype}, либо {var_ref, operation, datatype}
  values = values || {};
  return fields_config.map(f => {
    const cur = values[f.name] || {};
    const isVar = !!cur.var_ref;
    const curVal = cur.value == null ? "" : String(cur.value);
    const varOptions = variables.map(v =>
      `<option value="${escapeHtml(v.id)}" ${v.id === cur.var_ref ? "selected" : ""}>${escapeHtml(v.id)} (= ${escapeHtml(v.value)})</option>`).join("");
    return `
    <div class="panel" style="padding:12px;margin-bottom:10px;">
      <div class="row" style="justify-content:space-between;margin-bottom:8px;">
        <label style="font-weight:600;">${L2(f.label, f.label_en, {tech: f.name})}</label>
        ${f.allow_var_ref && variables.length ? `<label class="row-check"><input type="checkbox" id="stemode_${f.name}" ${isVar ? "checked" : ""} onchange="toggleVarRefMode('${f.name}')"> ${t("Из переменной")}</label>` : ""}
      </div>
      <div class="field-value-row">
        <span id="stevalwrap_${f.name}" style="flex:1;display:${isVar ? "none" : "flex"};">
          <input class="mono-input" id="stef_${f.name}_value" placeholder="${t("Значение")}" style="flex:1;" value="${escapeHtml(curVal)}">
        </span>
        ${f.allow_var_ref ? `
        <span id="stevarwrap_${f.name}" class="var-ref-mode" style="flex:1;display:${isVar ? "flex" : "none"};">
          <select id="stef_${f.name}_varref" style="flex:1;"><option value="">${t("— Переменная —")}</option>${varOptions}</select>
        </span>` : ""}
        <!-- Операция и тип данных доступны и при выборе переменной: в
             эталонном комплекте сущность с var_ref содержит все три
             атрибута (datatype, operation, var_ref). -->
        <select id="stef_${f.name}_operation" title="${t("Операция сравнения")}">${optionsHtml(OPERATIONS, cur.operation || f.default_operation, state.labels.operation, state.labelsEn.operation)}</select>
        <select id="stef_${f.name}_datatype" title="${t("Тип данных")}">${optionsHtml(DATATYPES, cur.datatype || f.datatype, state.labels.datatype, state.labelsEn.datatype)}</select>
      </div>
    </div>`;
  }).join("") || `<div class="muted">${t("У этого типа проверки нет полей состояния.")}</div>`;
}
function toggleVarRefMode(name) {
  // Переключается только источник значения (поле ввода ↔ список переменных);
  // операция и тип данных остаются видимыми в обоих режимах.
  const on = document.getElementById(`stemode_${name}`).checked;
  document.getElementById(`stevalwrap_${name}`).style.display = on ? "none" : "flex";
  document.getElementById(`stevarwrap_${name}`).style.display = on ? "flex" : "none";
}
function collectStateFields(fields_config) {
  const out = {};
  fields_config.forEach(f => {
    if (f.allow_var_ref && checked(`stemode_${f.name}`)) {
      const ref = val(`stef_${f.name}_varref`);
      if (ref) {
        out[f.name] = {
          var_ref: ref,
          operation: val(`stef_${f.name}_operation`),
          datatype: val(`stef_${f.name}_datatype`),
        };
      }
      return;
    }
    const v = val(`stef_${f.name}_value`);
    if (v) {
      out[f.name] = {
        value: v,
        operation: val(`stef_${f.name}_operation`),
        datatype: val(`stef_${f.name}_datatype`),
      };
    }
  });
  return out;
}

/* ---------- Объекты ---------- */

function renderObjects(container, d) {
  const rows = d.objects.map(o => `
    <tr>
      <td class="id-cell">${escapeHtml(o.id)}</td>
      <td>${typeBadgeHtml(o.type)}</td>
      <td class="id-cell">${fieldsSummary(o.fields)}</td>
      <td>${escapeHtml(o.comment || "")}</td>
      <td class="actions-cell"><button class="btn btn-sm" onclick="openEditObjectModal('${escapeHtml(o.id)}')">${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" onclick="deleteObject('${escapeHtml(o.id)}')">${t("Удалить")}</button></td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" onclick="openAddObjectModal()">${t("+ Объект")}</button></div>
    ${d.objects.length
      ? `<table><thead><tr><th>${t("Идентификатор")}</th><th>${t("Тип проверки")}</th><th>${t("Поля")}</th><th>${t("Комментарий")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
      : emptyListHtml("Объекты ещё не добавлены.", "No objects yet.")}
  `;
}

function openAddObjectModal() {
  const typeOptions = testTypeOptionsHtml(state.ovalSchema.allowed);
  openModal(t("Новый объект"), `
    <form id="mf">
      <div class="field"><label>${L('test_type', {required:true})} ${hintIcon(
        "Тип проверки определяет, что именно проверяется на узле, и какие поля нужно заполнить ниже.",
        "The check type defines what is checked on the host and which fields need to be filled below."
      )}</label><select id="o-type" required onchange="onObjectTypeChanged()">${typeOptions}</select></div>
      <div class="grid">
        <div class="field"><label>${L('id', {required:true})}</label><input class="mono-input" id="o-id" required value="${escapeHtml(nextOvalId("obj"))}"></div>
        <div class="field"><label>${L('version')}</label><input id="o-version" value="1"></div>
        <div class="field full"><label>${L('comment')}</label><input id="o-comment"></div>
      </div>
      <div id="o-fields"></div>
      ${formActions(t("Создать"))}
    </form>`);
  onObjectTypeChanged();
  bindForm(async () => {
    const type = val("o-type");
    const cfg = state.ovalSchema.types[type];
    await api.post(`${ovalBase()}/objects`, {
      test_type: type, id: val("o-id"), version: val("o-version") || "1",
      fields: collectObjectFields(cfg.object_fields), comment: val("o-comment") || null,
    });
    await loadOvalFileData(); renderView(); toast(t("Объект создан"), "ok");
  }, { ru: "объект", en: "object", reopen: openAddObjectModal });
}
function onObjectTypeChanged() {
  const cfg = state.ovalSchema.types[val("o-type")];
  document.getElementById("o-fields").innerHTML = objectFieldsEditorHtml(cfg.object_fields);
}

async function deleteObject(id) {
  if (!confirm(`${t("Удалить объект")} '${id}'?`)) return;
  try {
    await api.del(`${ovalBase()}/objects/${encodeURIComponent(id)}`);
    await loadOvalFileData(); renderView(); toast(t("Объект удалён"), "ok");
  } catch (e) { toast(e.message, "error"); }
}

/* ---------- Состояния ---------- */

function renderStates(container, d) {
  const rows = d.states.map(s => `
    <tr>
      <td class="id-cell">${escapeHtml(s.id)}</td>
      <td>${typeBadgeHtml(s.type)}</td>
      <td class="id-cell">${fieldsSummary(s.fields)}</td>
      <td>${escapeHtml(s.comment || "")}</td>
      <td class="actions-cell"><button class="btn btn-sm" onclick="openEditStateModal('${escapeHtml(s.id)}')">${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" onclick="deleteState('${escapeHtml(s.id)}')">${t("Удалить")}</button></td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" onclick="openAddStateModal()">${t("+ Состояние")}</button></div>
    ${d.states.length
      ? `<table><thead><tr><th>${t("Идентификатор")}</th><th>${t("Тип проверки")}</th><th>${t("Ожидаемые значения")}</th><th>${t("Комментарий")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
      : emptyListHtml("Состояния ещё не добавлены. Если проверяется только наличие объекта (например, пакета), состояние не требуется.",
                      "No states yet. If you only check that an object exists (e.g. a package), no state is needed.")}
  `;
}

function openAddStateModal() {
  const d = state.currentOvalData;
  // Первыми в списке — типы, для которых уже созданы объекты: состояние
  // почти всегда создаётся «в пару» к существующему объекту.
  const withState = state.ovalSchema.allowed.filter(tt => state.ovalSchema.types[tt].state_fields.length);
  const used = new Set(d.objects.map(o => o.type));
  const ordered = withState.filter(tt => used.has(tt)).concat(withState.filter(tt => !used.has(tt)));
  if (!ordered.length) { toast(t("Нет типов проверок с полями состояния"), "error"); return; }
  openModal(t("Новое состояние"), `
    <form id="mf">
      <div class="field"><label>${L('test_type', {required:true})}</label><select id="s-type" required onchange="onStateTypeChanged()">${testTypeOptionsHtml(ordered)}</select></div>
      <div class="grid">
        <div class="field"><label>${L('id', {required:true})}</label><input class="mono-input" id="s-id" required value="${escapeHtml(nextOvalId("ste"))}"></div>
        <div class="field"><label>${L('version')}</label><input id="s-version" value="1"></div>
        <div class="field full"><label>${L('comment')}</label><input id="s-comment"></div>
      </div>
      <div id="s-fields"></div>
      ${formActions(t("Создать"))}
    </form>`);
  onStateTypeChanged();
  bindForm(async () => {
    const type = val("s-type");
    const cfg = state.ovalSchema.types[type];
    await api.post(`${ovalBase()}/states`, {
      test_type: type, id: val("s-id"), version: val("s-version") || "1",
      fields: collectStateFields(cfg.state_fields), comment: val("s-comment") || null,
    });
    await loadOvalFileData(); renderView(); toast(t("Состояние создано"), "ok");
  }, { ru: "состояние", en: "state", reopen: openAddStateModal });
}
function onStateTypeChanged() {
  const cfg = state.ovalSchema.types[val("s-type")];
  document.getElementById("s-fields").innerHTML = stateFieldsEditorHtml(cfg.state_fields, state.currentOvalData.variables);
}

async function deleteState(id) {
  if (!confirm(`${t("Удалить состояние")} '${id}'?`)) return;
  try {
    await api.del(`${ovalBase()}/states/${encodeURIComponent(id)}`);
    await loadOvalFileData(); renderView(); toast(t("Состояние удалено"), "ok");
  } catch (e) { toast(e.message, "error"); }
}

/* ---------- Тесты ---------- */

function renderTests(container, d) {
  if (!d.objects.length) {
    container.innerHTML = depWarningHtml(
      "Тест связывает объект с состоянием, поэтому сначала нужно создать хотя бы один объект.",
      "A test links an object to a state, so create at least one object first.", "objects");
    return;
  }
  const byId = {};
  d.objects.concat(d.states).forEach(x => { byId[x.id] = x; });
  const rows = d.tests.map(tt => `
    <tr>
      <td class="id-cell">${escapeHtml(tt.id)}</td>
      <td>${typeBadgeHtml(tt.type)}</td>
      <td class="id-cell">${escapeHtml(tt.object_ref ? refLabel(byId[tt.object_ref] || { id: tt.object_ref }) : "—")}</td>
      <td class="id-cell">${escapeHtml(tt.state_ref ? refLabel(byId[tt.state_ref] || { id: tt.state_ref }) : "—")}</td>
      <td class="actions-cell"><button class="btn btn-sm" onclick="openEditTestModal('${escapeHtml(tt.id)}')">${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" onclick="deleteTest('${escapeHtml(tt.id)}')">${t("Удалить")}</button></td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" onclick="openAddTestModal()">${t("+ Тест")}</button></div>
    ${d.tests.length
      ? `<table><thead><tr><th>${t("Идентификатор")}</th><th>${t("Тип проверки")}</th><th>${t("Объект")}</th><th>${t("Состояние")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
      : emptyListHtml("Тесты ещё не добавлены.", "No tests yet.")}
  `;
}

function openAddTestModal() {
  const d = state.currentOvalData;
  // Предлагаются только типы проверок, для которых уже есть объект:
  // тест без объекта создать нельзя.
  const types = state.ovalSchema.allowed.filter(tt => d.objects.some(o => o.type === tt));
  openModal(t("Новый тест"), `
    <form id="mf">
      <div class="field"><label>${L('test_type', {required:true})}</label>
        <select id="t-type" required onchange="onTestTypeChanged()">${testTypeOptionsHtml(types)}</select>
      </div>
      <div class="grid">
        <div class="field"><label>${L('id', {required:true})}</label><input class="mono-input" id="t-id" required value="${escapeHtml(nextOvalId("tst"))}"></div>
        <div class="field"><label>${L('version')}</label><input id="t-version" value="1"></div>
        <div class="field full"><label>${L('object_ref', {required:true})} ${hintIcon(
          "Объект, значение которого проверяется. В списке — только объекты выбранного типа проверки.",
          "The object whose value is checked. Only objects of the selected check type are listed."
        )}</label><select id="t-objref" required></select></div>
        <div class="field full" id="t-steref-wrap"><label>${L('state_ref')} ${hintIcon(
          "Ожидаемое значение. Оставьте пустым, если достаточно проверить, что объект существует.",
          "The expected value. Leave empty if it is enough to check that the object exists."
        )}</label><select id="t-steref"><option value="">—</option></select></div>
        <div class="field"><label>${L('check')} ${hintIcon(
          "Сколько из найденных объектов должны соответствовать состоянию, чтобы тест считался пройденным.",
          "How many of the matched objects must satisfy the state for the test to pass."
        )}</label><select id="t-check">${optionsHtml(CHECK_VALUES, "all", state.labels.check, state.labelsEn.check)}</select></div>
        <div class="field"><label>${L('check_existence')}</label><select id="t-checkexist">${optionsHtml(CHECK_EXISTENCE_VALUES, "at_least_one_exists", state.labels.check_existence, state.labelsEn.check_existence)}</select></div>
      </div>
      <div class="field"><label>${L('comment')}</label><input id="t-comment"></div>
      ${formActions(t("Создать"))}
    </form>`);
  onTestTypeChanged();
  bindForm(async () => {
    await api.post(`${ovalBase()}/tests`, {
      test_type: val("t-type"), id: val("t-id"), version: val("t-version") || "1",
      object_ref: val("t-objref"), state_ref: val("t-steref") || null,
      check: val("t-check"), check_existence: val("t-checkexist"), comment: val("t-comment") || null,
    });
    await loadOvalFileData(); renderView(); toast(t("Тест создан"), "ok");
  }, { ru: "тест", en: "test", reopen: openAddTestModal });
}

function onTestTypeChanged() {
  const type = val("t-type");
  const cfg = state.ovalSchema.types[type];
  const d = state.currentOvalData;
  const objs = d.objects.filter(o => o.type === type);
  const stes = d.states.filter(s => s.type === type);
  document.getElementById("t-objref").innerHTML = refOptionsHtml(objs);
  const steWrap = document.getElementById("t-steref-wrap");
  if (cfg && cfg.state_fields.length) {
    steWrap.style.display = "";
    document.getElementById("t-steref").innerHTML = `<option value="">— ${t("Без состояния")} —</option>` + refOptionsHtml(stes);
  } else {
    steWrap.style.display = "none";
  }
}

async function deleteTest(id) {
  if (!confirm(`${t("Удалить тест")} '${id}'?`)) return;
  try {
    await api.del(`${ovalBase()}/tests/${encodeURIComponent(id)}`);
    await loadOvalFileData(); renderView(); toast(t("Тест удалён"), "ok");
  } catch (e) { toast(e.message, "error"); }
}

/* ---------- Определения ---------- */

function renderDefinitions(container, d) {
  if (!d.tests.length) {
    container.innerHTML = depWarningHtml(
      "Определение объединяет один или несколько тестов, поэтому сначала нужно создать хотя бы один тест.",
      "A definition combines one or more tests, so create at least one test first.", "tests");
    return;
  }
  const famLabel = f => {
    if (!f) return "—";
    const map = getLang() === "en" ? state.labelsEn.family : state.labels.family;
    return (map && map[f]) || f;
  };
  const rows = d.definitions.map(def => `
    <tr>
      <td class="id-cell">${escapeHtml(def.id)}</td>
      <td>${escapeHtml(def.title)}</td>
      <td>${escapeHtml(famLabel(def.family))}</td>
      <td>${escapeHtml((def.platforms || []).join(", ") || "—")}</td>
      <td>${def.criteria.length}</td>
      <td class="actions-cell">
        <button class="btn btn-sm" onclick="openEditDefinitionModal('${escapeHtml(def.id)}')">${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" onclick="deleteDefinition('${escapeHtml(def.id)}')">${t("Удалить")}</button>
      </td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" onclick="openAddDefinitionModal()">${t("+ Определение")}</button></div>
    ${d.definitions.length
      ? `<table><thead><tr><th>${t("Идентификатор")}</th><th>${t("Название")}</th><th>${t("Семейство ОС")}</th><th>${t("Платформы")}</th><th>${t("Критериев")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
      : emptyListHtml("Определения ещё не добавлены.", "No definitions yet.")}
  `;
}

function criteriaRowHtml(tests, c) {
  c = c || { test_ref: "", comment: "" };
  return `
    <div class="row" data-crit-row style="margin-bottom:6px;">
      <select class="mono-input" data-crit-testref style="flex:2;" onchange="onCriterionChanged(this)">
        <option value="">${t("— Тест —")}</option>${refOptionsHtml(tests, c.test_ref)}
      </select>
      <input placeholder="${t("Комментарий")}" value="${escapeHtml(c.comment || "")}" data-crit-comment style="flex:1;">
      <button type="button" class="btn-icon" onclick="this.closest('[data-crit-row]').remove()">✕</button>
    </div>`;
}
function criteriaEditorHtml(criteria, tests) {
  const list = criteria && criteria.length ? criteria : [null];
  return `<div id="criteria-container">${list.map(c => criteriaRowHtml(tests, c)).join("")}</div>
    <button type="button" class="btn btn-sm" onclick="addCriterionRow()">${t("+ Критерий")}</button>`;
}
function addCriterionRow() {
  const c = document.getElementById("criteria-container");
  c.insertAdjacentHTML("beforeend", criteriaRowHtml(state.currentOvalData.tests, null));
}
/* При выборе теста: комментарий критерия берётся из комментария теста, а
   семейство ОС определения выставляется по типу теста (если не выбрано). */
function onCriterionChanged(sel) {
  const tst = state.currentOvalData.tests.find(x => x.id === sel.value);
  if (!tst) return;
  const row = sel.closest("[data-crit-row]");
  const com = row.querySelector("[data-crit-comment]");
  if (com && !com.value && tst.comment) com.value = tst.comment;
  const fam = document.getElementById("d-family");
  if (fam && !fam.value) { fam.value = familyForTestType(tst.type); onFamilyChanged(); }
}
function collectCriteria() {
  return Array.from(document.querySelectorAll("[data-crit-row]")).map(row => ({
    test_ref: row.querySelector("[data-crit-testref]").value,
    comment: row.querySelector("[data-crit-comment]").value.trim(),
  })).filter(c => c.test_ref);
}

function definitionFormHtml(def, isNew) {
  const tests = state.currentOvalData.tests;
  def = def || {};
  return `
    <form id="mf">
      <div class="grid">
        ${isNew ? `<div class="field"><label>${L('id', {required:true})}</label><input class="mono-input" id="d-id" required value="${escapeHtml(nextOvalId("def"))}"></div>` : ""}
        <div class="field"><label>${L('version')}</label><input id="d-version" value="${escapeHtml(def.version || "1")}"></div>
        <div class="field"><label>${L('class')}</label><select id="d-class">${optionsHtml(CLASS_VALUES, def.class || "compliance", state.labels.klass, state.labelsEn.klass)}</select></div>
        <div class="field ${isNew ? "" : "full"}"><label>${L('family')} ${hintIcon(
          "Семейство ОС по схеме OVAL: Windows или Linux. Для всех дистрибутивов Linux (Astra Linux, РЕД ОС, ALT Linux, Ubuntu, Debian) выбирается «Linux». Выставляется автоматически по типу выбранного теста.",
          "OS family per the OVAL schema: Windows or Linux. All Linux distributions (Astra Linux, RED OS, ALT Linux, Ubuntu, Debian) use \"Linux\". Set automatically from the selected test type."
        )}</label><select id="d-family" onchange="onFamilyChanged()"><option value="">—</option>${optionsHtml(FAMILY_VALUES, def.family || null, state.labels.family, state.labelsEn.family, {hideValue: true})}</select></div>
      </div>
      <div class="field"><label>${L('title', {required:true})}</label><input id="d-title" required value="${escapeHtml(def.title || "")}"></div>
      <div class="field"><label>${L('description', {required:true})}</label><textarea id="d-description" required>${escapeHtml(def.description || "")}</textarea></div>
      <div class="field"><label>${L('platforms')}</label><input id="d-platforms" value="${escapeHtml((def.platforms || []).join(", "))}" placeholder="${t("Например: Astra Linux")}">${platformsQuickPicksHtml('d-platforms', def.family)}</div>
      <div class="field"><label>${L('criteria')} ${hintIcon(
        "Тесты, из которых складывается проверка. Определение считается выполненным, если выполнены все выбранные тесты.",
        "The tests that make up the check. The definition passes when all selected tests pass."
      )}</label>${criteriaEditorHtml(def.criteria, tests)}</div>
      ${formActions(isNew ? t("Создать") : t("Сохранить"))}
    </form>`;
}

function openAddDefinitionModal() {
  openModal(t("Новое определение"), definitionFormHtml(null, true));
  bindForm(async () => {
    const platforms = val("d-platforms").split(",").map(s => s.trim()).filter(Boolean);
    await api.post(`${ovalBase()}/definitions`, {
      id: val("d-id"), version: val("d-version") || "1", "class": val("d-class"),
      title: val("d-title"), description: val("d-description"),
      family: val("d-family") || null, platforms, criteria: collectCriteria(),
    });
    await loadOvalFileData(); renderView(); toast(t("Определение создано"), "ok");
  }, { ru: "определение", en: "definition", reopen: openAddDefinitionModal });
}

function openEditDefinitionModal(id) {
  const def = state.currentOvalData.definitions.find(x => x.id === id);
  openModal(`${t("Определение")}: ${id}`, definitionFormHtml(def, false));
  bindForm(async () => {
    const platforms = val("d-platforms").split(",").map(s => s.trim()).filter(Boolean);
    await api.put(`${ovalBase()}/definitions/${encodeURIComponent(id)}`, {
      version: val("d-version"), "class": val("d-class"), title: val("d-title"),
      description: val("d-description"), family: val("d-family") || null,
      platforms, criteria: collectCriteria(),
    });
    await loadOvalFileData(); renderView(); toast(t("Сохранено"), "ok");
  });
}

async function deleteDefinition(id) {
  if (!confirm(`${t("Удалить определение")} '${id}'?`)) return;
  try {
    await api.del(`${ovalBase()}/definitions/${encodeURIComponent(id)}`);
    await loadOvalFileData(); renderView(); toast(t("Определение удалено"), "ok");
  } catch (e) { toast(e.message, "error"); }
}

/* ===================== Вкладка: Валидация и экспорт ===================== */

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
}

async function runValidate() {
  const box = document.getElementById("validate-result");
  box.innerHTML = t("Проверка…");
  try {
    const res = await api.get(`/projects/${encodeURIComponent(state.currentProjectId)}/validate`);
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
              ${i.path ? `<div class="path">${escapeHtml(i.path)}</div>` : ""}
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



/* ============ Нормативный документ → черновик профиля ============
   Документ разбирается на сервере: выделяются пронумерованные пункты,
   по базе знаний определяется тема каждого требования и подбираются
   проверки из каталога. Результат — ЧЕРНОВИК: он открывается в
   конструкторе и правится обычным образом. */

let pendingDocFile = null;
let pendingDocAnalysis = null;

function onDocumentFileChosen(e) {
  const file = e.target.files[0];
  if (!file) return;
  pendingDocFile = file;
  pendingDocAnalysis = null;
  openDocumentSetupModal();
}

function openDocumentSetupModal() {
  const file = pendingDocFile;
  const guess = (file.name || "document").replace(/\.[^.]+$/, "")
    .replace(/[^A-Za-z0-9_-]+/g, "_").toLowerCase().slice(0, 40) || "document";
  openModal(t("Загрузка нормативного документа"), `
    <form id="mf">
      <div class="field"><label>${L('file')}</label><input value="${escapeHtml(file.name)}" disabled></div>
      <div class="field"><label>${t("Название документа")}</label>
        <input id="doc-title" value="${escapeHtml(file.name.replace(/\.[^.]+$/, ""))}">
        <span class="hint">${t("Попадёт в идентификатор требования каждого правила вместе с номером пункта.")}</span>
      </div>
      <div class="grid">
        <div class="field"><label>${t("Операционная система")}</label>
          <input id="doc-os" list="doc-os-list" placeholder="Astra Linux">
          <datalist id="doc-os-list">
            ${["Astra Linux", "РЕД ОС", "ALT Linux", "Debian", "Ubuntu", "SberLinux"]
              .map(o => `<option value="${o}">`).join("")}
          </datalist>
        </div>
        <div class="field"><label>${L('project_id_new', {required:true})}</label>
          <input class="mono-input" id="doc-project-id" required value="${escapeHtml("draft_" + guess)}">
        </div>
      </div>
      <div class="dep-warning" style="margin-top:4px;">
        <span class="icon">i</span>
        <div>${t("Поддерживаются DOCX, ODT и TXT. PDF не используется: в нём текст хранится как набор глифов, и кириллица часто извлекается искажённой.")}</div>
      </div>
      ${formActions(t("Разобрать документ"))}
    </form>`);
  bindForm(async () => {
    const params = {
      filename: pendingDocFile.name,
      os: val("doc-os") || null,
    };
    pendingDocAnalysis = await api.uploadDocument("/documents/analyze", pendingDocFile, params);
    pendingDocAnalysis.title = val("doc-title") || pendingDocFile.name;
    pendingDocAnalysis.projectId = val("doc-project-id");
    pendingDocAnalysis.osName = val("doc-os") || null;
    openDocumentReviewModal();
  }, null, true);
}

/* Разбор показывается ДО создания проекта: видно, какие пункты распознаны,
   какая тема определена и какая проверка предложена. */
function openDocumentReviewModal() {
  const a = pendingDocAnalysis;
  const rows = a.matches.map(m => {
    const best = m.candidates && m.candidates[0];
    const concept = m.concepts && m.concepts[0];
    const cls = m.confidence === "высокая" ? "ok" : m.confidence === "средняя" ? "mid" : "low";
    return `
      <tr>
        <td class="id-cell">${escapeHtml(m.number)}</td>
        <td>${escapeHtml((m.text || "").slice(0, 110))}…</td>
        <td>${concept ? escapeHtml(concept.title) : `<span class="muted">—</span>`}</td>
        <td>${best ? escapeHtml(best.title || best.entry_id) : `<span class="muted">${t("нет проверки")}</span>`}</td>
        <td><span class="conf conf-${cls}">${escapeHtml(m.confidence)}</span></td>
      </tr>`;
  }).join("");

  const counts = a.matches.reduce((acc, m) => {
    acc[m.confidence] = (acc[m.confidence] || 0) + 1; return acc;
  }, {});

  openModal(`${t("Разбор документа")}: ${a.filename}`, `
    <form id="mf">
      <p class="muted" style="margin-bottom:10px;">
        ${t("Пунктов найдено")}: <b>${a.items_total}</b> ·
        ${t("высокая")}: ${counts["высокая"] || 0} ·
        ${t("средняя")}: ${counts["средняя"] || 0} ·
        ${t("низкая")}: ${counts["низкая"] || 0} ·
        ${t("нет")}: ${counts["нет"] || 0}
      </p>
      <div class="doc-review">
        <table>
          <thead><tr>
            <th>${t("Пункт")}</th><th>${t("Текст")}</th>
            <th>${t("Тема требования")}</th><th>${t("Предложенная проверка")}</th>
            <th>${t("Уверенность")}</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="field" style="margin-top:12px;">
        <label>${t("Включать в черновик пункты с уверенностью")}</label>
        <select id="doc-minconf">
          <option value="высокая">${t("только высокая")}</option>
          <option value="средняя" selected>${t("высокая и средняя")}</option>
          <option value="низкая">${t("любая, включая низкую")}</option>
        </select>
        <span class="hint">${t("Пункты ниже выбранного уровня в черновик не попадут — их видно в отчёте как несопоставленные.")}</span>
      </div>
      <div class="dep-warning" style="margin-top:4px;">
        <span class="icon">!</span>
        <div>${escapeHtml(a.disclaimer)}</div>
      </div>
      ${formActions(t("Создать черновик профиля"))}
    </form>`, true);
  bindForm(async () => {
    const report = await api.uploadDocument("/documents/draft", pendingDocFile, {
      project_id: a.projectId,
      filename: a.filename,
      os: a.osName,
      title: a.title,
      min_confidence: val("doc-minconf"),
    });
    document.getElementById("doc-file").value = "";
    await loadProjects();
    await selectProject(a.projectId);
    openDocumentReportModal(report);
  }, null, true);
}

/* Итог сборки: что создано, что требует организационных мер, что осталось
   без сопоставления. Отчёт полезен и сам по себе — как оценка покрытия. */
function openDocumentReportModal(rep) {
  const s = rep.summary;
  const list = (arr, empty, fmt) => arr.length
    ? `<ul class="report-list">${arr.map(fmt).join("")}</ul>`
    : `<p class="muted">${escapeHtml(empty)}</p>`;
  openModal(t("Черновик профиля создан"), `
    <div class="report-grid">
      <div><b>${s.items_total}</b><span>${t("пунктов в документе")}</span></div>
      <div><b>${s.rules_created}</b><span>${t("создано правил")}</span></div>
      <div><b>${s.items_manual}</b><span>${t("организационных мер")}</span></div>
      <div><b>${s.items_unmatched}</b><span>${t("без сопоставления")}</span></div>
    </div>
    <div class="dep-warning" style="margin-top:12px;">
      <span class="icon">!</span><div>${escapeHtml(rep.disclaimer)}</div>
    </div>
    <h3 style="margin-top:14px;">${t("Требуют организационных мер")}</h3>
    ${list(rep.manual, t("Таких пунктов нет."), m =>
      `<li><span class="id-cell">${escapeHtml(m.number)}</span> ${escapeHtml(m.title || "")}
       <div class="muted">${escapeHtml(m.reason || "")}</div></li>`)}
    <h3 style="margin-top:14px;">${t("Без сопоставления")}</h3>
    ${list(rep.skipped, t("Все пункты сопоставлены."), m =>
      `<li><span class="id-cell">${escapeHtml(m.number)}</span>
       <span class="muted">${escapeHtml((m.text || "").slice(0, 120))}</span></li>`)}
    <div class="modal-actions">
      <button type="button" class="btn btn-primary" onclick="closeModal()">${t("Перейти к правке")}</button>
    </div>`, true);
}



/* ===================== Быстрый старт =====================
   Открывается при первом запуске и по ссылке «Справка» в боковой панели.
   Отвечает на вопросы, которые чаще всего возникали у первых
   пользователей: с чего начать, чем мастер отличается от конструктора и
   как отключить всплывающие подсказки. */

function openOnboarding() {
  const hintsOn = !hintsDisabled();
  const askMore = localStorage.getItem("cpb-no-add-another") !== "1";
  openModal(t("Быстрый старт"), `
    <div class="onboarding">
      <p>${t("Сервис собирает профиль соответствия — пару файлов XCCDF и OVAL — и выгружает его ZIP-архивом для импорта в Kaspersky Vulnerability Management.")}</p>

      <h3>${t("С чего начать")}</h3>
      <ol>
        <li>${t("Откройте пример — он покажет, как выглядит готовый профиль.")}</li>
        <li>${t("Создайте проект кнопкой «+» или загрузите нормативный документ — сервис соберёт черновик.")}</li>
        <li>${t("Пройдите шаги мастера и на последнем шаге выгрузите архив.")}</li>
      </ol>

      <h3>${t("Мастер или конструктор")}</h3>
      <div class="mode-compare">
        <div><b>${t("Мастер")}</b><span>${t("Ведёт по шагам в нужном порядке и подсказывает на каждом. Для первого профиля и для тех, кто не помнит устройство XCCDF и OVAL.")}</span></div>
        <div><b>${t("Конструктор")}</b><span>${t("Все разделы сразу, в любом порядке. Для правки готового или импортированного профиля.")}</span></div>
      </div>
      <p class="muted">${t("Данные у режимов общие: переключаться можно в любой момент, ничего не теряется.")}</p>

      <h3>${t("Настройки")}</h3>
      <label class="row-check"><input type="checkbox" id="ob-hints" ${hintsOn ? "checked" : ""}> ${t("Показывать подсказку при первом открытии каждого шага")}</label>
      <label class="row-check"><input type="checkbox" id="ob-more" ${askMore ? "checked" : ""}> ${t("Предлагать добавить ещё один элемент после создания")}</label>
    </div>
    <div class="modal-actions">
      <button type="button" class="btn" onclick="openKnowledgeBase()" style="margin-right:auto;">${t("База знаний")}</button>
      <button type="button" class="btn" onclick="finishOnboarding(false)">${t("Начать")}</button>
      <button type="button" class="btn btn-primary" onclick="finishOnboarding(true)">${t("Открыть пример")}</button>
    </div>`, true);
}

async function finishOnboarding(openExample) {
  if (checked("ob-hints")) localStorage.removeItem("cpb-hints-off");
  else localStorage.setItem("cpb-hints-off", "1");
  if (checked("ob-more")) localStorage.removeItem("cpb-no-add-another");
  else localStorage.setItem("cpb-no-add-another", "1");
  localStorage.setItem("cpb-onboarded", "1");
  closeModal();
  if (openExample) {
    const ex = (state.projects || []).find(p => p.startsWith("example_astra")) ||
               (state.projects || []).find(p => p.startsWith("example_"));
    if (ex) await selectProject(ex);
  }
}



/* ===================== База знаний =====================
   Показывает, на чём строится черновик профиля по документу: какие темы
   требований сервис узнаёт, по каким формулировкам, в каких документах эти
   темы встречаются и какие проверки их закрывают. Только просмотр —
   пополнение базы выполняется правкой файлов backend/knowledge/*.json. */

let kbData = null;

async function openKnowledgeBase() {
  if (!kbData) kbData = await api.get("/knowledge");
  renderKnowledgeBase("");
}

function renderKnowledgeBase(filter) {
  const f = (filter || "").toLowerCase();
  const concepts = kbData.concepts.filter(c => !f ||
    c.title.toLowerCase().includes(f) ||
    (c.ru || []).concat(c.en || []).some(x => x.toLowerCase().includes(f)) ||
    (c.themes || []).some(x => x.toLowerCase().includes(f)));
  const fam = Object.entries(kbData.families)
    .map(([k, v]) => `<span class="kb-fam">${escapeHtml(k)} <b>${v}</b></span>`).join("");
  const rows = concepts.map(c => `
    <tr>
      <td><b>${escapeHtml(c.title)}</b><div class="muted">${escapeHtml((c.themes || []).join(", "))}</div></td>
      <td class="kb-phr">${(c.ru || []).map(x => `<span>${escapeHtml(x)}</span>`).join("")}</td>
      <td class="kb-phr">${(c.en || []).map(x => `<span>${escapeHtml(x)}</span>`).join("")}</td>
      <td>${(c.doc_hints || []).map(h =>
        `<div>${escapeHtml(h.family)}: <span class="id-cell">${escapeHtml(h.ref)}</span>${h.verify ? ` <span class="muted" title="${t("Номер требует сверки с вашей редакцией документа")}">*</span>` : ""}</div>`).join("")}</td>
      <td>${c.checks.length ? c.checks.length : `<span class="muted">${t("нет")}</span>`}</td>
    </tr>`).join("");
  openModal(t("База знаний"), `
    <p class="muted">${t("Темы требований, по которым сервис распознаёт пункты нормативных документов, и формулировки, по которым он их узнаёт.")}</p>
    <div class="kb-summary">
      <div><b>${kbData.concepts.length}</b><span>${t("тем требований")}</span></div>
      <div><b>${kbData.concepts.reduce((n, c) => n + (c.ru || []).length + (c.en || []).length, 0)}</b><span>${t("формулировок RU и EN")}</span></div>
      <div><b>${kbData.synonyms.length}</b><span>${t("пар синонимов")}</span></div>
    </div>
    <div class="kb-fams">${fam}</div>
    <input id="kb-filter" placeholder="${t("Поиск по темам и формулировкам")}" value="${escapeHtml(filter || "")}" style="width:100%;margin:10px 0;">
    <div class="doc-review">
      <table>
        <thead><tr><th>${t("Тема")}</th><th>${t("Формулировки RU")}</th><th>${t("Формулировки EN")}</th><th>${t("Где встречается")}</th><th>${t("Проверок")}</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="5" class="muted">${t("Ничего не найдено.")}</td></tr>`}</tbody>
      </table>
    </div>
    <p class="muted" style="margin-top:8px;">* ${t("Номер пункта зарубежного стандарта — ориентир: нумерация меняется между редакциями, сверьте со своей копией документа.")}</p>
    <div class="modal-actions">
      <button type="button" class="btn" onclick="openOnboarding()">${t("Назад")}</button>
      <button type="button" class="btn btn-primary" onclick="closeModal()">${t("Закрыть")}</button>
    </div>`, true);
  const inp = document.getElementById("kb-filter");
  inp.addEventListener("input", () => {
    const v = inp.value, pos = inp.selectionStart;
    renderKnowledgeBase(v);
    const ni = document.getElementById("kb-filter");
    ni.focus(); ni.setSelectionRange(pos, pos);
  });
}

/* ===================== Старт ===================== */

init();


/* ===================== Изменение элементов OVAL-файла =====================
   Формы повторяют формы создания, но открываются заполненными и
   отправляют PUT. Идентификатор и тип проверки менять нельзя: на них
   держатся ссылки из тестов и определений — чтобы сменить тип, элемент
   создаётся заново. */

function openEditVariableModal(id) {
  const v = state.currentOvalData.variables.find(x => x.id === id);
  if (!v) return;
  openModal(`${t("Переменная")}: ${id}`, `
    <form id="mf">
      <div class="grid">
        <div class="field"><label>${L('version')}</label><input id="v-version" value="${escapeHtml(v.version || "1")}"></div>
        <div class="field"><label>${L('datatype')}</label><select id="v-datatype">${optionsHtml(DATATYPES, v.datatype, state.labels.datatype, state.labelsEn.datatype)}</select></div>
        <div class="field full"><label>${L('value', {required:true})}</label><input class="mono-input" id="v-value" required value="${escapeHtml(v.value || "")}"></div>
        <div class="field full"><label>${L('comment')}</label><input id="v-comment" value="${escapeHtml(v.comment || "")}"></div>
      </div>
      ${formActions(t("Сохранить"))}
    </form>`);
  bindForm(async () => {
    await api.put(`${ovalBase()}/variables/${encodeURIComponent(id)}`, {
      id: id, version: val("v-version") || "1", datatype: val("v-datatype"),
      value: val("v-value"), comment: val("v-comment") || null,
    });
    await loadOvalFileData(); renderView(); toast(t("Сохранено"), "ok");
  });
}

function openEditObjectModal(id) {
  const o = state.currentOvalData.objects.find(x => x.id === id);
  if (!o) return;
  const cfg = state.ovalSchema.types[o.type];
  openModal(`${t("Объект")}: ${id}`, `
    <form id="mf">
      <div class="field"><label>${L('test_type')}</label>
        <input class="mono-input" value="${escapeHtml(typeLabel(cfg, o.type))}" disabled>
        <span class="hint">${t("Тип проверки не меняется: на объект ссылаются тесты. Чтобы сменить тип, создайте объект заново.")}</span>
      </div>
      <div class="grid">
        <div class="field"><label>${L('version')}</label><input id="o-version" value="${escapeHtml(o.version || "1")}"></div>
        <div class="field"><label>${L('comment')}</label><input id="o-comment" value="${escapeHtml(o.comment || "")}"></div>
      </div>
      <div id="o-fields">${objectFieldsEditorHtml(cfg.object_fields, o.fields)}</div>
      ${formActions(t("Сохранить"))}
    </form>`);
  bindForm(async () => {
    await api.put(`${ovalBase()}/objects/${encodeURIComponent(id)}`, {
      test_type: o.type, id: id, version: val("o-version") || "1",
      fields: collectObjectFields(cfg.object_fields), comment: val("o-comment") || null,
    });
    await loadOvalFileData(); renderView(); toast(t("Сохранено"), "ok");
  });
}

function openEditStateModal(id) {
  const st = state.currentOvalData.states.find(x => x.id === id);
  if (!st) return;
  const cfg = state.ovalSchema.types[st.type];
  openModal(`${t("Состояние")}: ${id}`, `
    <form id="mf">
      <div class="field"><label>${L('test_type')}</label>
        <input class="mono-input" value="${escapeHtml(typeLabel(cfg, st.type))}" disabled>
        <span class="hint">${t("Тип проверки не меняется: на состояние ссылаются тесты.")}</span>
      </div>
      <div class="grid">
        <div class="field"><label>${L('version')}</label><input id="s-version" value="${escapeHtml(st.version || "1")}"></div>
        <div class="field"><label>${L('comment')}</label><input id="s-comment" value="${escapeHtml(st.comment || "")}"></div>
      </div>
      <div id="s-fields">${stateFieldsEditorHtml(cfg.state_fields, state.currentOvalData.variables, st.fields)}</div>
      ${formActions(t("Сохранить"))}
    </form>`);
  bindForm(async () => {
    await api.put(`${ovalBase()}/states/${encodeURIComponent(id)}`, {
      test_type: st.type, id: id, version: val("s-version") || "1",
      fields: collectStateFields(cfg.state_fields), comment: val("s-comment") || null,
    });
    await loadOvalFileData(); renderView(); toast(t("Сохранено"), "ok");
  });
}

function openEditTestModal(id) {
  const d = state.currentOvalData;
  const tst = d.tests.find(x => x.id === id);
  if (!tst) return;
  const cfg = state.ovalSchema.types[tst.type];
  const objs = d.objects.filter(o => o.type === tst.type);
  const stes = d.states.filter(x => x.type === tst.type);
  openModal(`${t("Тест")}: ${id}`, `
    <form id="mf">
      <div class="field"><label>${L('test_type')}</label>
        <input class="mono-input" value="${escapeHtml(typeLabel(cfg, tst.type))}" disabled>
        <span class="hint">${t("Тип проверки не меняется: на тест ссылаются определения.")}</span>
      </div>
      <div class="grid">
        <div class="field"><label>${L('version')}</label><input id="t-version" value="${escapeHtml(tst.version || "1")}"></div>
        <div class="field"><label>${L('comment')}</label><input id="t-comment" value="${escapeHtml(tst.comment || "")}"></div>
        <div class="field full"><label>${L('object_ref', {required:true})}</label>
          <select id="t-objref" required>${refOptionsHtml(objs, tst.object_ref)}</select></div>
        ${cfg && cfg.state_fields.length ? `
        <div class="field full"><label>${L('state_ref')}</label>
          <select id="t-steref"><option value="">— ${t("Без состояния")} —</option>${refOptionsHtml(stes, tst.state_ref)}</select></div>` : ""}
        <div class="field"><label>${L('check')}</label><select id="t-check">${optionsHtml(CHECK_VALUES, tst.check || "all", state.labels.check, state.labelsEn.check)}</select></div>
        <div class="field"><label>${L('check_existence')}</label><select id="t-checkexist">${optionsHtml(CHECK_EXISTENCE_VALUES, tst.check_existence || "at_least_one_exists", state.labels.check_existence, state.labelsEn.check_existence)}</select></div>
      </div>
      ${formActions(t("Сохранить"))}
    </form>`);
  bindForm(async () => {
    await api.put(`${ovalBase()}/tests/${encodeURIComponent(id)}`, {
      test_type: tst.type, id: id, version: val("t-version") || "1",
      object_ref: val("t-objref"), state_ref: val("t-steref") || null,
      check: val("t-check"), check_existence: val("t-checkexist"),
      comment: val("t-comment") || null,
    });
    await loadOvalFileData(); renderView(); toast(t("Сохранено"), "ok");
  });
}
