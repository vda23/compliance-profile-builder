/* Проверка из каталога: выбор и добавление в проект.
   Обычный скрипт без сборки: файлы интерфейса подключаются по порядку и
   разделяют общую область видимости (см. index.html). */

/* ============ Проверка из каталога ============
   Готовая проверка разворачивается в проект целиком: переменная, объект,
   состояние, тест, определение и правило. Пользователю не нужно проходить
   пять шагов OVAL — достаточно выбрать проверку и при желании поправить
   эталонное значение. */

const CATALOG_OS = TARGET_OS;   // общий список целевых ОС — см. core.js
let catPick = null;   // {os, entries, query, category, selected, added:Set}

async function openCatalogPicker() {
  const os = localStorage.getItem("cpb-catalog-os") || "Astra Linux";
  catPick = { os, entries: [], query: "", category: "", selected: null, added: new Set() };
  await catalogPickerLoad();
}

async function catalogPickerLoad() {
  try {
    const r = await api.get(`/catalog?os=${encodeURIComponent(catPick.os)}`);
    // организационные меры в проект не добавляются — в списке их нет
    catPick.entries = r.entries.filter(e => !e.manual);
    catPick.categoriesEn = r.categories_en || {};
  } catch (e) { toast(e.message, "error"); return; }
  renderCatalogPicker();
}

function renderCatalogPicker() {
  const q = catPick.query.toLowerCase();
  const cats = [...new Set(catPick.entries.map(e => e.category || ""))].sort();
  // Поиск идёт по текстам на обоих языках: «password» находит и русские записи.
  const list = catPick.entries.filter(e =>
    (!catPick.category || e.category === catPick.category) &&
    (!q || [e.title, e.description, e.category, e.title_en, e.description_en, e.category_en]
      .join(" ").toLowerCase().includes(q)));
  const sel = catPick.entries.find(e => e.id === catPick.selected);

  const rows = list.map(e => `
    <button type="button" class="cat-item ${e.id === catPick.selected ? "active" : ""}" data-id="${escapeHtml(e.id)}">
      <span class="cat-title">${escapeHtml(loc(e, "title"))}${catPick.added.has(e.id) ? ` <span class="cat-added">✓ ${t("добавлено")}</span>` : ""}</span>
      <span class="cat-meta">${escapeHtml(loc(e, "category"))}${catalogSourceLabel(e) ? ` · ${escapeHtml(catalogSourceLabel(e))}` : ""}</span>
    </button>`).join("") || `<p class="muted" style="padding:10px;">${t("Ничего не найдено.")}</p>`;

  const detail = sel ? `
    <h3 class="cat-d-title">${escapeHtml(loc(sel, "title"))}</h3>
    <p>${escapeHtml(loc(sel, "description"))}</p>
    ${sel.remediation ? `<p class="muted"><b>${t("Как исправить")}:</b> ${escapeHtml(loc(sel, "remediation"))}</p>` : ""}
    <p class="hint">${t("Тексты правила создаются на языке бенчмарка проекта.")}</p>
    ${(sel.params || []).map(p => `
      <div class="field"><label>${escapeHtml(loc(p, "title") || p.name)}</label>
        <input class="mono-input" id="catp-${escapeHtml(p.name)}" value="${escapeHtml(p.default == null ? "" : String(p.default))}">
      </div>`).join("")}
    <details class="cat-ident">
      <summary>${t("Пункт требования (необязательно)")}</summary>
      <div class="grid">
        <div class="field"><label>${t("Документ")}</label><input id="catp-ident-system" placeholder="${t("Например: Регламент ИБ")}"></div>
        <div class="field"><label>${t("Пункт")}</label><input id="catp-ident-value" placeholder="4.2"></div>
      </div>
      <span class="hint">${t("Если не указать, используется ссылка из каталога, если она есть.")}</span>
    </details>
    <label class="row-check"><input type="checkbox" id="catp-profiles" checked> ${t("Включить во все профили проекта")}</label>
    <div class="modal-actions" style="margin-top:12px;">
      <button type="button" class="btn btn-primary" id="catp-add">${t("Добавить в проект")}</button>
    </div>`
    : `<p class="muted">${t("Выберите проверку слева. Она будет добавлена в проект целиком: от переменной до правила — проходить шаги OVAL вручную не нужно.")}</p>`;

  openModal(t("Проверка из каталога"), `
    <div class="cat-head">
      <div class="field"><label>${t("Операционная система")}</label>
        <select id="catp-os">${CATALOG_OS.map(o => `<option ${o === catPick.os ? "selected" : ""}>${escapeHtml(o)}</option>`).join("")}</select></div>
      <div class="field" style="flex:2;"><label>${t("Поиск")}</label>
        <input id="catp-q" value="${escapeHtml(catPick.query)}" placeholder="${t("Например: пароль, ssh, аудит")}"></div>
      <div class="field"><label>${t("Раздел")}</label>
        <select id="catp-cat"><option value="">${t("Все разделы")}</option>${cats.map(c => `<option value="${escapeHtml(c)}" ${c === catPick.category ? "selected" : ""}>${escapeHtml(locMap(catPick.categoriesEn, c))}</option>`).join("")}</select></div>
    </div>
    <div class="cat-body">
      <div class="cat-list">${rows}</div>
      <div class="cat-detail">${detail}</div>
    </div>
    <div class="modal-actions">
      <span class="muted" style="margin-right:auto;">${t("Проверок")}: ${list.length}${catPick.added.size ? ` · ${t("добавлено")}: ${catPick.added.size}` : ""}</span>
      <button type="button" class="btn" id="catp-close">${t("Готово")}</button>
    </div>`, true);

  document.getElementById("catp-os").addEventListener("change", async ev => {
    catPick.os = ev.target.value; localStorage.setItem("cpb-catalog-os", catPick.os);
    catPick.selected = null; await catalogPickerLoad();
  });
  const qi = document.getElementById("catp-q");
  qi.addEventListener("input", () => {
    const pos = qi.selectionStart; catPick.query = qi.value; renderCatalogPicker();
    const n = document.getElementById("catp-q"); n.focus(); n.setSelectionRange(pos, pos);
  });
  document.getElementById("catp-cat").addEventListener("change", ev => { catPick.category = ev.target.value; renderCatalogPicker(); });
  document.querySelectorAll(".cat-item").forEach(b => b.addEventListener("click", () => {
    catPick.selected = b.getAttribute("data-id"); renderCatalogPicker();
  }));
  document.getElementById("catp-close").addEventListener("click", catalogPickerClose);
  const add = document.getElementById("catp-add");
  if (add) add.addEventListener("click", catalogPickerAdd);
}

/* Источник записи: одна и та же проверка бывает и в базовом каталоге, и в
   пакете по конкретному документу (с номером пункта). Без подписи две
   одинаковые строки в списке неразличимы. */
function catalogSourceLabel(e) {
  const r = (e.refs || [])[0];
  if (r && r.value) {
    const sys = (loc(r, "system") || "").replace(/^Рекомендации /, "").replace(/ по безопасной настройке ОС Linux/, " по Linux");
    return `${sys.length > 38 ? sys.slice(0, 38) + "…" : sys}, ${t("п.")} ${loc(r, "value")}`;
  }
  return e.pack === "linux-base" ? t("базовый каталог") : "";
}

async function catalogPickerAdd() {
  const e = catPick.entries.find(x => x.id === catPick.selected);
  const params = {};
  (e.params || []).forEach(p => { params[p.name] = val(`catp-${p.name}`); });
  try {
    const r = await api.post(`/projects/${encodeURIComponent(state.currentProjectId)}/catalog-checks`, {
      entry_id: e.id, os: catPick.os, params,
      ident_system: val("catp-ident-system") || null, ident_value: val("catp-ident-value") || null,
      add_to_profiles: checked("catp-profiles"),
    });
    catPick.added.add(e.id);
    toast(`${t("Добавлено правило")} ${r.created.rules[0]}`, "ok");
    renderCatalogPicker();
  } catch (err) { toast(err.message, "error"); }
}

async function catalogPickerClose() {
  closeModal();
  if (catPick && catPick.added.size) {
    await refreshCurrentProject();
    state.defsByFile = null;
    await loadAllDefinitions();
    if (state.currentOvalFile) await loadOvalFileData();
  }
  renderView();
}
