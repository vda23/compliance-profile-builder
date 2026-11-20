/* Ядро интерфейса: состояние, утилиты, диспетчер событий, инициализация, тема и язык.
   Обычный скрипт без сборки: файлы интерфейса подключаются по порядку и
   разделяют общую область видимости (см. index.html). */

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
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

/* ===================== Обработчики событий =====================
   Разметка не содержит встроенного JavaScript (onclick="…"): это позволяет
   включить строгую политику безопасности контента без 'unsafe-inline'.
   Вместо него — атрибуты data-click / data-change / data-input с именем
   функции и аргументами в JSON. Один обработчик на документ вызывает
   функцию по имени.

   Аргументы сериализуются в JSON и экранируются, а не подставляются в код:
   раньше значение с одинарной кавычкой внутри onclick="fn('…')" ломало бы
   разметку и могло исполниться как JavaScript.

   Особые аргументы: "$el" — элемент, "$event" — событие,
   "$checked" и "$value" — состояние элемента управления. */
const UI_EVENTS = ["click", "change", "input"];

function on(type, fn, ...args) {
  return ` data-${type}="${escapeHtml(fn)}"` +
    (args.length ? ` data-${type}-args="${escapeHtml(JSON.stringify(args))}"` : "");
}

function dispatchUiEvent(type, ev) {
  const el = ev.target.closest && ev.target.closest(`[data-${type}]`);
  if (!el) return;
  const name = el.getAttribute(`data-${type}`);
  const fn = window[name];
  if (typeof fn !== "function") { console.error("Нет обработчика: " + name); return; }
  const raw = el.getAttribute(`data-${type}-args`);
  // Таблица без прототипа и проверка на «$»: иначе строковый аргумент
  // "constructor" совпадал с Object.prototype.constructor и подменялся
  // объектом (нашёл сквозной тест переключения в конструктор).
  const special = Object.assign(Object.create(null), {
    "$el": () => el, "$event": () => ev, "$checked": () => el.checked, "$value": () => el.value,
  });
  const resolve = a => (typeof a === "string" && a.charAt(0) === "$" && special[a] ? special[a]() : a);
  const args = raw ? JSON.parse(raw).map(resolve) : [];
  fn.apply(el, args);
}
UI_EVENTS.forEach(type => document.addEventListener(type, ev => dispatchUiEvent(type, ev)));

/* Удаление строки формы (критерий, идентификатор требования). */
function removeClosest(el, selector) {
  const row = el.closest(selector);
  if (row) row.remove();
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
    `<button type="button" class="chip" ${on("click", "addPlatformPreset", inputId, p)}>+ ${escapeHtml(p)}</button>`
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
      <button type="button" class="btn" ${on("click", "closeModal")}>${t("Отмена")}</button>
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
      <button type="button" class="btn" ${on("click", "addAnotherNo")}>${t("Нет")}</button>
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

/* Версия интерфейса. Должна совпадать с версией сервера (backend/app/server.py). */
const APP_VERSION = "1.0.0";

/* Сверка версий интерфейса и сервера. Файлы интерфейса сервер читает с диска
   при каждом запросе, а свой код — один раз при запуске. Если после
   обновления сервер не перезапустили, интерфейс уже новый, а сервер старый,
   и новые функции отвечают «Метод API не найден». Такое состояние
   показывается явно, с командой для исправления. */
async function checkServerVersion() {
  let server = null;
  try { server = (await api.get("/version")).version; } catch (e) { server = null; }
  if (server === APP_VERSION) return;
  const bar = document.createElement("div");
  bar.className = "version-warning";
  bar.innerHTML = `
    <b>${t("Сервер работает на старой версии")}</b>
    <span>${escapeHtml(t("Интерфейс"))} ${APP_VERSION}, ${escapeHtml(t("сервер"))} ${escapeHtml(server || t("неизвестна"))}.
    ${t("Часть функций не будет работать, пока сервер не перезапущен")}:</span>
    <code>sudo systemctl restart compliance-profile-builder</code>`;
  document.body.prepend(bar);
}

async function init() {
  initTheme();
  document.getElementById("btn-new-project").addEventListener("click", openNewProjectModal);
  document.getElementById("import-file").addEventListener("change", onImportFileChosen);
  document.getElementById("doc-file").addEventListener("change", onDocumentFileChosen);
  document.getElementById("btn-help").addEventListener("click", openOnboarding);
  document.getElementById("btn-knowledge").addEventListener("click", () => { toggleSidebar(false); openKnowledgeBase(); });
  document.getElementById("btn-sidebar-toggle").addEventListener("click", () => toggleSidebar());
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
  checkServerVersion();
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

/* Целевые ОС профиля: один список для загрузки документа и каталога проверок.
   Раньше при загрузке документа были только системы Linux, и для документа
   по Windows нельзя было выбрать ОС. */
const TARGET_OS = ["Astra Linux", "РЕД ОС", "ALT Linux", "Debian", "Ubuntu", "SberLinux",
                   "Windows 10", "Windows 11", "Windows Server 2016", "Windows Server 2019", "Windows Server 2022"];

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
  // Подписи пунктов меню переводятся общим механизмом data-i18n выше:
  // атрибут стоит на <span> внутри кнопки, поэтому иконки не затираются.
  const newProjBtn = document.getElementById("btn-new-project");
  if (newProjBtn) newProjBtn.title = t("Новый проект");
}

async function toggleLang() {
  applyLang(getLang() === "en" ? "ru" : "en");
  closeModal();
  renderSidebar();
  renderView();
  // Описания «что проверяется» формирует сервер — на новом языке их
  // нужно запросить заново.
  if (state.currentProjectId) {
    try {
      state.rulesSummary = await api.get(`/projects/${encodeURIComponent(state.currentProjectId)}/rules/summary?lang=${getLang()}`);
      renderView();
    } catch (e) { /* описание вспомогательное */ }
  }
}

async function loadProjects() {
  // Сводка: название, черновик, число правил. Идентификаторы
  // по-прежнему в state.projects — на них опирается остальной код.
  state.projectMeta = await api.get("/projects/overview");
  state.projects = state.projectMeta.map(p => p.id);
  renderSidebar();
}

let projectFilter = "";

function renderSidebar() {
  const list = document.getElementById("project-list");
  const meta = state.projectMeta || state.projects.map(id => ({ id, title: id }));
  if (!meta.length) {
    list.innerHTML = `<div class="sidebar-hint" style="padding:8px 6px;color:var(--text-faint);font-size:12px;">${t("Проектов пока нет")}</div>`;
    return;
  }
  const f = projectFilter.toLowerCase();
  const shown = meta.filter(p => !f || p.id.toLowerCase().includes(f) || (p.title || "").toLowerCase().includes(f));
  // Поиск появляется, когда проектов становится много
  const search = meta.length > 6 ? `
    <input id="project-search" class="project-search" placeholder="${t("Поиск проекта")}" value="${escapeHtml(projectFilter)}">` : "";
  list.innerHTML = search + (shown.map(p => `
    <div class="project-item ${p.id === state.currentProjectId ? "active" : ""}" data-id="${escapeHtml(p.id)}"
         title="${escapeHtml(p.title)} — ${escapeHtml(p.id)}${p.error ? "\n" + escapeHtml(p.error) : ""}">
      <span class="pname">
        <span class="ptitle">${escapeHtml(p.title || p.id)}</span>
        <span class="pid">${p.error ? `<b class="perror">${t("ошибка")}</b> · ` : ""}${p.draft ? `<b class="pdraft">${t("черновик")}</b> · ` : ""}${escapeHtml(p.id)}</span>
      </span>
      <span class="pactions">
        <button type="button" class="pact" data-act="rename" title="${t("Переименовать")}" aria-label="${t("Переименовать")}">✎</button>
        <button type="button" class="pact" data-act="copy" title="${t("Копировать")}" aria-label="${t("Копировать")}">⧉</button>
        <button type="button" class="pact del" data-act="delete" title="${t("Удалить проект")}" aria-label="${t("Удалить проект")}">✕</button>
      </span>
    </div>`).join("") || `<div class="muted" style="padding:8px 6px;font-size:12px;">${t("Ничего не найдено.")}</div>`);

  list.querySelectorAll(".project-item").forEach(el => el.addEventListener("click", ev => {
    const id = el.getAttribute("data-id");
    const act = ev.target.closest(".pact");
    if (!act) return selectProject(id);
    ev.stopPropagation();
    const kind = act.getAttribute("data-act");
    if (kind === "delete") deleteProject(id);
    else openProjectIdModal(kind, id);
  }));
  const si = document.getElementById("project-search");
  if (si) si.addEventListener("input", () => {
    const pos = si.selectionStart; projectFilter = si.value; renderSidebar();
    const n = document.getElementById("project-search"); n.focus(); n.setSelectionRange(pos, pos);
  });
}

/* Переименование и копирование проекта */
function openProjectIdModal(kind, id) {
  const isCopy = kind === "copy";
  openModal(isCopy ? t("Копировать проект") : t("Переименовать проект"), `
    <form id="mf">
      <div class="field"><label>${t("Новый идентификатор")} <span class="req">*</span></label>
        <input class="mono-input" id="pid-new" required value="${escapeHtml(isCopy ? id + "_copy" : id)}">
        <span class="hint">${t("Латинские буквы, цифры, «-» и «_», до 64 символов.")}</span></div>
      ${formActions(isCopy ? t("Копировать") : t("Переименовать"))}
    </form>`);
  bindForm(async () => {
    const newId = val("pid-new").trim();
    await api.post(`/projects/${encodeURIComponent(id)}/${isCopy ? "copy" : "rename"}`, { new_id: newId });
    if (!isCopy && state.currentProjectId === id) state.currentProjectId = newId;
    await loadProjects();
    if (state.currentProjectId) await selectProject(isCopy ? newId : state.currentProjectId);
    toast(isCopy ? t("Копия создана") : t("Проект переименован"), "ok");
  });
}

/* На узком экране (половина и четверть окна) панель проектов свёрнута в
   кнопку ☰: развёрнутая сверху, она занимала большую часть высоты и
   вытесняла рабочую область за край экрана. */
function toggleSidebar(force) {
  const sb = document.querySelector(".sidebar");
  const open = force === undefined ? !sb.classList.contains("open") : force;
  sb.classList.toggle("open", open);
  document.getElementById("btn-sidebar-toggle").setAttribute("aria-expanded", open ? "true" : "false");
}

async function selectProject(id) {
  toggleSidebar(false);   // выбрали проект — освобождаем место под работу
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
  const base = `/projects/${encodeURIComponent(state.currentProjectId)}`;
  state.currentProject = await api.get(base);
  // Что проверяет каждое правило — человеческим языком. Описание
  // вспомогательное: если его не удалось получить, таблица правил работает.
  try { state.rulesSummary = await api.get(`${base}/rules/summary?lang=${getLang()}`); }
  catch (e) { state.rulesSummary = {}; }
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
