/* База знаний: просмотр, отбор, редактор тем и синонимов, проверка формулировки, правки.
   Обычный скрипт без сборки: файлы интерфейса подключаются по порядку и
   разделяют общую область видимости (см. index.html). */

/* ===================== Редактор базы знаний =====================
   Правки хранятся на сервере отдельным слоем поверх поставляемой базы
   (data/knowledge/user-knowledge.json): обновление сервиса их не стирает,
   а любую тему можно вернуть к исходному виду. */

let kbCatalog = null;
async function kbLoadCatalog() {
  if (!kbCatalog) kbCatalog = (await api.get("/catalog")).entries;
  return kbCatalog;
}
async function kbReload() {
  kbData = await api.get("/knowledge");
}

/* ---------- окно правки темы ---------- */
let kbEd = null;   // редактируемое состояние: {id, title, ru, en, hints, checks, base}

async function openConceptEditor(conceptId) {
  try {
    await kbLoadCatalog();
  } catch (e) { toast(`${t("Не удалось загрузить каталог проверок")}: ${e.message}`, "error"); return; }
  const c = conceptId ? kbData.concepts.find(x => x.id === conceptId) : null;
  kbEd = c ? {
    id: c.id, title: c.title, titleEn: c.title_en || "", ru: [...(c.ru || [])], en: [...(c.en || [])],
    hints: (c.doc_hints || []).map(h => ({ family: h.family, ref: h.ref, user: !!h.user })),
    checks: [...(c.checks || []), ...(c.measures || [])],
    userRu: new Set(c.user_ru || []), userEn: new Set(c.user_en || []),
    hiddenRu: [...(c.hidden_ru || [])], hiddenEn: [...(c.hidden_en || [])],
    created: !!c.user_created, modified: !!c.user_modified,
  } : { id: null, title: "", titleEn: "", ru: [], en: [], hints: [], checks: [], userRu: new Set(), userEn: new Set(),
        hiddenRu: [], hiddenEn: [], created: true, modified: false };
  renderConceptEditor();
}

function kbChipsHtml(list, lang, userSet) {
  return list.map((p, i) => `
    <span class="kb-chip ${userSet.has(p) ? "own" : ""}" title="${userSet.has(p) ? escapeHtml(t("Добавлено вами")) : escapeHtml(t("Поставляемая формулировка"))}">
      ${escapeHtml(p)}<button type="button" class="kb-chip-x" ${on("click", "kbRemovePhrase", (lang), (i))} aria-label="${t("Удалить")}">×</button>
    </span>`).join("") || `<span class="muted">${t("нет")}</span>`;
}

/* Язык формулировок, которые показываются и правятся: язык интерфейса.
   Формулировки другого языка в окне не видны, но сохраняются как были. */
function kbLang() { return getLang() === "en" ? "en" : "ru"; }

/* Название документа: в английском интерфейсе — английское, а в базе
   хранится русское (оно же — ключ отбора). */
function kbFamilyLabel(f) { return locMap(kbData.families_en, f); }
function kbFamilyKey(label) {
  const v = (label || "").trim();
  const back = Object.entries(kbData.families_en || {}).find(([ru, en]) => en === v);
  return back ? back[0] : v;
}

function renderConceptEditor() {
  const e = kbEd;
  const lang = kbLang();
  const families = Object.keys(kbData.families).map(kbFamilyLabel).sort();
  const groups = [
    [t("Linux"), kbCatalog.filter(x => !x.manual && x.family !== "windows")],
    [t("Windows"), kbCatalog.filter(x => !x.manual && x.family === "windows")],
    [t("Организационные меры"), kbCatalog.filter(x => x.manual)],
  ];
  const opts = groups.map(([g, list]) => `<optgroup label="${escapeHtml(g)}">${
    list.filter(x => !e.checks.includes(x.id)).sort((a, b) => loc(a, "title").localeCompare(loc(b, "title")))
        .map(x => `<option value="${escapeHtml(x.id)}">${escapeHtml(loc(x, "title"))}</option>`).join("")}</optgroup>`).join("");
  const hidden = (lang, arr) => arr.length ? `
    <div class="kb-hidden">${t("Скрытые поставляемые формулировки")}:
      ${arr.map((p, i) => `<button type="button" class="kb-restore" ${on("click", "kbRestorePhrase", (lang), (i))} title="${escapeHtml(t("Вернуть"))}">↺ ${escapeHtml(p)}</button>`).join("")}
    </div>` : "";

  const titleShown = lang === "en" ? (e.titleEn || e.title) : e.title;
  const phrases = lang === "en"
    ? `<div class="field"><label>${t("Формулировки на английском")}</label>
        <div class="kb-chips" id="kb-en">${kbChipsHtml(e.en, "en", e.userEn)}</div>
        <div class="kb-add">
          <input id="kb-add-en" placeholder="${t("New phrasing")}" maxlength="120">
          <button type="button" class="btn btn-sm" ${on("click", "kbAddPhrase", "en")}>${t("Добавить")}</button>
        </div>
        ${hidden("en", e.hiddenEn)}
        <span class="hint">${t("Оборот ищется в тексте с учётом словоформ: «регистрация событий» найдёт и «регистрацию событий». Лучше всего работают 2–4 слова, характерные именно для этой темы.")}</span>
      </div>`
    : `<div class="field"><label>${t("Формулировки на русском")}</label>
        <div class="kb-chips" id="kb-ru">${kbChipsHtml(e.ru, "ru", e.userRu)}</div>
        <div class="kb-add">
          <input id="kb-add-ru" placeholder="${t("Новая формулировка — короткий характерный оборот")}" maxlength="120">
          <button type="button" class="btn btn-sm" ${on("click", "kbAddPhrase", "ru")}>${t("Добавить")}</button>
        </div>
        ${hidden("ru", e.hiddenRu)}
        <span class="hint">${t("Оборот ищется в тексте с учётом словоформ: «регистрация событий» найдёт и «регистрацию событий». Лучше всего работают 2–4 слова, характерные именно для этой темы.")}</span>
      </div>`;

  openModal(e.id ? `${t("Тема")}: ${titleShown}` : t("Новая тема"), `
    <form id="mf" class="kb-editor">
      <div class="field"><label>${t("Название темы")} <span class="req">*</span></label>
        <input id="kb-title" value="${escapeHtml(titleShown)}" maxlength="200" required></div>

      ${phrases}
      <p class="hint" style="margin-top:-6px;">${t("Формулировки на другом языке видны при переключении языка интерфейса.")}</p>

      <div class="field"><label>${t("Где встречается")}</label>
        <div id="kb-hints">${e.hints.map((h, i) => `
          <div class="kb-hint-row">
            <input list="kb-fam-list" value="${escapeHtml(kbFamilyLabel(h.family))}" ${on("input", "kbSetHint", (i), "family", "$value")} placeholder="${t("Документ")}">
            <input value="${escapeHtml(h.ref)}" ${on("input", "kbSetHint", (i), "ref", "$value")} placeholder="${t("Пункт")}" class="kb-ref">
            <button type="button" class="btn btn-sm btn-danger" ${on("click", "kbRemoveHint", (i))} aria-label="${t("Удалить")}">×</button>
          </div>`).join("")}</div>
        <datalist id="kb-fam-list">${families.map(f => `<option value="${escapeHtml(f)}">`).join("")}</datalist>
        <button type="button" class="btn btn-sm" ${on("click", "kbAddHint")}>+ ${t("Ссылка на документ")}</button>
      </div>

      <div class="field"><label>${t("Чем закрывается")}</label>
        <div class="kb-chips">${e.checks.map((id, i) => {
          const x = kbCatalog.find(c => c.id === id) || { title: id };
          return `<span class="kb-chip ${x.manual ? "manual" : "check"}">${escapeHtml(loc(x, "title"))}${x.manual ? ` <em>· ${t("орг. мера")}</em>` : ""}
            <button type="button" class="kb-chip-x" ${on("click", "kbRemoveCheck", (i))} aria-label="${t("Удалить")}">×</button></span>`;
        }).join("") || `<span class="muted">${t("Тема распознаётся, но в профиль ничего не попадёт")}</span>`}</div>
        <div class="kb-add">
          <select id="kb-add-check"><option value="">— ${t("выберите проверку или меру")} —</option>${opts}</select>
          <button type="button" class="btn btn-sm" ${on("click", "kbAddCheck")}>${t("Добавить")}</button>
        </div>
      </div>

      <div class="modal-actions kb-actions">
        ${e.id && e.created ? `<button type="button" class="btn btn-danger" ${on("click", "kbResetConcept", true)} style="margin-right:auto;">${t("Удалить тему")}</button>` : ""}
        ${e.id && !e.created && e.modified ? `<button type="button" class="btn" ${on("click", "kbResetConcept", false)} style="margin-right:auto;">${t("Вернуть исходный вид")}</button>` : ""}
        <button type="button" class="btn" ${on("click", "renderKnowledgeBase")}>${t("Отмена")}</button>
        <button type="submit" class="btn btn-primary">${t("Сохранить")}</button>
      </div>
    </form>`, true);

  document.getElementById(`kb-add-${lang}`).addEventListener("keydown", ev => {
    if (ev.key === "Enter") { ev.preventDefault(); kbAddPhrase(lang); }
  });
  document.getElementById("mf").addEventListener("submit", async ev => {
    ev.preventDefault();
    kbSyncFields();
    const body = { title: kbEd.title, title_en: kbEd.titleEn, ru: kbEd.ru, en: kbEd.en,
                   hints: kbEd.hints.filter(h => h.family.trim())
                                    .map(h => Object.assign({}, h, { family: kbFamilyKey(h.family) })),
                   checks: kbEd.checks };
    try {
      if (kbEd.id) await api.put(`/knowledge/concepts/${encodeURIComponent(kbEd.id)}`, body);
      else await api.post("/knowledge/concepts", body);
      await kbReload();
      toast(t("Тема сохранена"), "ok");
      renderKnowledgeBase();
    } catch (e) { toast(e.message, "error"); }
  });
}

/* поля ввода переносятся в состояние перед любой перерисовкой окна */
function kbSyncFields() {
  const ti = document.getElementById("kb-title");
  if (ti) { if (kbLang() === "en") kbEd.titleEn = ti.value; else kbEd.title = ti.value; }
}
/* Действия редактора темы и синонимов (раньше — выражения прямо в разметке). */
function kbSetHint(i, field, value) { kbEd.hints[i][field] = value; }
function kbRemoveHint(i) { kbSyncFields(); kbEd.hints.splice(i, 1); renderConceptEditor(); }
function kbAddHint() { kbSyncFields(); kbEd.hints.push({ family: "", ref: "", user: true }); renderConceptEditor(); }
function kbRemoveCheck(i) { kbSyncFields(); kbEd.checks.splice(i, 1); renderConceptEditor(); }
function kbSetSynonym(i, field, value) { kbSyn[i][field] = value; }
function kbAddSynonym() { kbSyn.push({ variant: "", canonical: "", user: true }); renderSynonymsEditor(); }
function kbRemoveSynonym(i) { kbSyn.splice(i, 1); renderSynonymsEditor(); }
function addAnotherNo() { rememberAddAnother(); closeModal(); }

function kbAddPhrase(lang) {
  kbSyncFields();
  const inp = document.getElementById(`kb-add-${lang}`);
  const v = (inp.value || "").replace(/\s+/g, " ").trim();
  if (!v) return;
  if (v.length > 120) { toast(t("Формулировка длиннее 120 символов — сократите до характерного оборота."), "error"); return; }
  const list = kbEd[lang];
  if (!list.some(x => x.toLowerCase() === v.toLowerCase())) {
    list.push(v);
    (lang === "ru" ? kbEd.userRu : kbEd.userEn).add(v);
  }
  renderConceptEditor();
  document.getElementById(`kb-add-${lang}`).focus();
}
function kbRemovePhrase(lang, i) {
  kbSyncFields();
  const p = kbEd[lang][i];
  kbEd[lang].splice(i, 1);
  const own = lang === "ru" ? kbEd.userRu : kbEd.userEn;
  if (!own.has(p)) (lang === "ru" ? kbEd.hiddenRu : kbEd.hiddenEn).push(p);   // поставляемая — можно вернуть
  own.delete(p);
  renderConceptEditor();
}
function kbRestorePhrase(lang, i) {
  kbSyncFields();
  const arr = lang === "ru" ? kbEd.hiddenRu : kbEd.hiddenEn;
  const p = arr.splice(i, 1)[0];
  kbEd[lang].push(p);
  renderConceptEditor();
}
function kbAddCheck() {
  kbSyncFields();
  const v = document.getElementById("kb-add-check").value;
  if (v && !kbEd.checks.includes(v)) kbEd.checks.push(v);
  renderConceptEditor();
}
async function kbResetConcept(isDelete) {
  const q = isDelete ? t("Удалить эту тему? Её формулировки и связи будут удалены.")
                     : t("Вернуть тему к поставляемому виду? Ваши правки этой темы будут удалены.");
  if (!confirm(q)) return;
  try {
    await api.del(`/knowledge/concepts/${encodeURIComponent(kbEd.id)}`);
    await kbReload();
    toast(isDelete ? t("Тема удалена") : t("Тема возвращена к исходному виду"), "ok");
    renderKnowledgeBase();
  } catch (e) { toast(e.message, "error"); }
}

/* ---------- синонимы ---------- */
let kbSyn = null;
function openSynonymsEditor() {
  kbSyn = kbData.synonyms.map(s => ({ ...s }));
  renderSynonymsEditor();
}
function renderSynonymsEditor() {
  openModal(t("Синонимы"), `
    <p class="muted">${t("Перед поиском тем оборот слева заменяется оборотом справа. Так «секретный код доступа» распознаётся как «пароль». Замена ищется как есть — укажите оборот в той форме, в какой он встречается в документах.")}</p>
    <div class="doc-review"><table>
      <thead><tr><th>${t("Как написано в документе")}</th><th>${t("Как понимать")}</th><th></th><th></th></tr></thead>
      <tbody>${kbSyn.map((s, i) => `<tr>
        <td><input value="${escapeHtml(s.variant)}" ${on("input", "kbSetSynonym", (i), "variant", "$value")}></td>
        <td><input value="${escapeHtml(s.canonical)}" ${on("input", "kbSetSynonym", (i), "canonical", "$value")}></td>
        <td>${s.user ? `<span class="kb-cov kb-cov-auto">${t("ваш")}</span>` : `<span class="muted">${t("поставляемый")}</span>`}</td>
        <td><button type="button" class="btn btn-sm btn-danger" ${on("click", "kbRemoveSynonym", (i))} aria-label="${t("Удалить")}">×</button></td>
      </tr>`).join("")}</tbody></table></div>
    <div class="modal-actions">
      <button type="button" class="btn" ${on("click", "kbAddSynonym")} style="margin-right:auto;">+ ${t("Синоним")}</button>
      <button type="button" class="btn" ${on("click", "renderKnowledgeBase")}>${t("Отмена")}</button>
      <button type="button" class="btn btn-primary" ${on("click", "kbSaveSynonyms")}>${t("Сохранить")}</button>
    </div>`, true);
}
async function kbSaveSynonyms() {
  try {
    await api.put("/knowledge/synonyms", { pairs: kbSyn.filter(s => s.variant.trim() && s.canonical.trim()) });
    await kbReload();
    toast(t("Синонимы сохранены"), "ok");
    renderKnowledgeBase();
  } catch (e) { toast(e.message, "error"); }
}

/* ---------- проверка формулировки ---------- */
function openPhraseTester() {
  openModal(t("Проверить формулировку"), `
    <p class="muted">${t("Вставьте текст пункта требования — сервис покажет, какую тему и какую проверку он найдёт. Удобно, чтобы убедиться, что добавленная формулировка срабатывает.")}</p>
    <textarea id="kb-test-text" rows="4" style="width:100%;" placeholder="${t("Например: Учётные записи, не использовавшиеся более 45 дней, блокируются.")}"></textarea>
    <div id="kb-test-result" style="margin-top:10px;"></div>
    <div class="modal-actions">
      <button type="button" class="btn" ${on("click", "renderKnowledgeBase")}>${t("Назад")}</button>
      <button type="button" class="btn btn-primary" id="kb-test-run">${t("Проверить")}</button>
    </div>`, true);
  const run = async () => {
    const text = document.getElementById("kb-test-text").value;
    const out = document.getElementById("kb-test-result");
    try {
      const r = await api.post("/knowledge/test", { text });
      const link = (id, title) => `<button type="button" class="kb-title-link" data-edit="${escapeHtml(id)}" title="${t("Открыть тему")}">${escapeHtml(title)}</button>`;
      if (r.concepts.length) {
        out.innerHTML = `
        <table><thead><tr><th>${t("Тема")}</th><th>${t("Почему")}</th></tr></thead><tbody>${
          r.concepts.slice(0, 3).map((c, i) => `<tr${i === 0 ? ' class="kb-best"' : ""}>
            <td>${link(c.concept_id, loc(c, "title"))}</td>
            <td class="muted">${c.hits && c.hits.length ? `${t("формулировки")}: ${escapeHtml(c.hits.join(", "))}`
                                                       : `${t("частичное сходство")}: ${escapeHtml((c.similar || []).join(", "))}`}</td>
          </tr>`).join("")}</tbody></table>
        <p style="margin-top:8px;">${t("Предложенная проверка")}: <b>${r.candidates.length ? escapeHtml(loc(r.candidates[0], "title")) : t("нет")}</b>
          · ${t("уверенность")}: ${escapeHtml(t(r.confidence))}</p>`;
      } else if (r.search && r.search.length) {
        // Одного-двух слов мало для уверенного распознавания пункта —
        // показываем темы, где эти слова встречаются.
        out.innerHTML = `
        <div class="kb-search-note">${t("Как пункт требования этот текст не распознан: для уверенного сопоставления нужен текст пункта целиком или характерный оборот. Ниже — темы, где встречаются эти слова.")}</div>
        <table><thead><tr><th>${t("Тема")}</th><th>${t("Совпало")}</th></tr></thead><tbody>${
          r.search.map(c => `<tr><td>${link(c.concept_id, loc(c, "title"))}</td>
            <td class="muted">${escapeHtml(c.matched.join(", "))}${c.in_title ? ` · ${t("в названии")}` : ""}</td></tr>`).join("")}</tbody></table>`;
      } else {
        out.innerHTML = `<p class="muted">${t("Тема не найдена. Добавьте характерный оборот из этого текста в формулировки нужной темы.")}</p>`;
      }
      out.querySelectorAll("[data-edit]").forEach(b => b.addEventListener("click", () => openConceptEditor(b.getAttribute("data-edit"))));
    } catch (e) { out.innerHTML = `<p class="muted">${escapeHtml(e.message)}</p>`; }
  };
  document.getElementById("kb-test-run").addEventListener("click", run);
}

/* ---------- перенос правок между серверами ---------- */
async function kbExport() {
  if (!kbData.concepts.some(c => c.user_modified) && !kbData.synonyms.some(x => x.user)) {
    toast(t("Правок пока нет — экспортировать нечего. Измените тему или добавьте свою, и она попадёт в файл."), "error");
    return;
  }
  try {
    const layer = await api.get("/knowledge/user");
    const blob = new Blob([JSON.stringify(layer, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `knowledge-edits-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  } catch (e) { toast(e.message, "error"); }
}
function kbImportPick() {
  const inp = document.createElement("input");
  inp.type = "file"; inp.accept = ".json,application/json";
  inp.addEventListener("change", async () => {
    const f = inp.files[0]; if (!f) return;
    let data;
    try { data = JSON.parse(await f.text()); }
    catch (e) { toast(t("Файл не является корректным JSON."), "error"); return; }
    const n = Object.keys((data && data.concepts) || {}).length;
    if (!confirm(`${t("Импортировать правок тем")}: ${n}. ${t("Правки тех же тем на этом сервере будут заменены, остальные сохранятся.")}`)) return;
    try {
      await api.post("/knowledge/user", { data, mode: "merge" });
      await kbReload();
      toast(t("Правки импортированы"), "ok");
      renderKnowledgeBase();
    } catch (e) { toast(e.message, "error"); }
  });
  inp.click();
}
/* ===================== База знаний =====================
   Показывает, на чём строится черновик профиля по документу: какие темы
   требований сервис узнаёт, по каким формулировкам, в каких документах эти
   темы встречаются и какие проверки их закрывают. Только просмотр —
   пополнение базы выполняется правкой файлов backend/knowledge/*.json. */

let kbData = null;

async function openKnowledgeBase() {
  // Раньше ошибка запроса здесь проглатывалась, и кнопка выглядела
  // «неактивной». Теперь причина видна пользователю.
  try {
    if (!kbData) kbData = await api.get("/knowledge");
    kbFilter.mode = "any";
    renderKnowledgeBase("", null);
  } catch (e) {
    toast(`${t("Не удалось открыть базу знаний")}: ${e.message}`, "error");
  }
}

/* Фильтры окна базы знаний: текст поиска и выбранное семейство документов.
   Поиск идёт по названию темы, формулировкам, разделам и по столбцу
   «Где встречается»; плашка документа отбирает темы, которые в нём есть. */
/* Фильтры окна базы знаний: text — строка поиска; families — выбранные
   документы; mode — «any» (тема хотя бы в одном из выбранных) или «all»
   (во всех сразу — так видно, что общего у документов); theme — раздел. */
let kbFilter = { text: "", families: [], mode: "any", theme: null };

/* Чем закрывается тема: технические проверки и организационные меры —
   отдельно. Раньше мера считалась «проверкой», и у организационных тем
   стояла цифра, хотя на узле они не проверяются. */
function kbCoverageHtml(c) {
  const n = (c.checks || []).length, m = (c.measures || []).length;
  const parts = [];
  if (n) parts.push(`<span class="kb-cov kb-cov-auto">${n} ${plural(n, t("проверка"), t("проверки"), t("проверок"))}</span>`);
  if (m) parts.push(`<span class="kb-cov kb-cov-manual" title="${escapeHtml(t("Проверяется анализом документов и процессов, а не настройками узла"))}">${t("орг. мера")}</span>`);
  return parts.join("") || `<span class="muted">${t("нет")}</span>`;
}
function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

function kbFamilyOf(h) { return (h.family || "").trim(); }

function renderKnowledgeBase(text, families) {
  if (text !== undefined) kbFilter.text = text;
  if (families !== undefined) { kbFilter.families = families || []; if (!families) kbFilter.theme = null; }
  const f = (kbFilter.text || "").toLowerCase();
  const fams = kbFilter.families;
  const theme = kbFilter.theme;

  const concepts = kbData.concepts.filter(c => {
    if (fams.length) {
      const has = new Set((c.doc_hints || []).map(kbFamilyOf));
      const ok = kbFilter.mode === "all" ? fams.every(x => has.has(x)) : fams.some(x => has.has(x));
      if (!ok) return false;
    }
    if (theme && !(c.themes || []).includes(theme)) return false;
    if (!f) return true;
    const hay = [c.title, c.title_en || ""]
      .concat(c.ru || [], c.en || [], c.themes || [], (c.themes || []).map(th => locMap(kbData.themes_en, th)))
      .concat((c.doc_hints || []).map(h => `${h.family} ${h.family_en || ""} ${h.ref}`))
      .join(" ").toLowerCase();
    return hay.includes(f);
  });

  const chips = Object.entries(kbData.families).sort((x, y) => y[1] - x[1]).map(([k, v]) => `
    <button type="button" class="kb-fam ${fams.includes(k) ? "active" : ""}" data-fam="${escapeHtml(k)}"
            aria-pressed="${fams.includes(k)}"
            title="${escapeHtml(fams.includes(k) ? t("Убрать документ из отбора") : t("Добавить документ в отбор"))}">
      ${escapeHtml(kbFamilyLabel(k))} <b>${v}</b>
    </button>`).join("");
  const modeBar = fams.length > 1 ? `
    <div class="kb-mode">
      <span class="muted">${t("Показать темы, которые есть")}:</span>
      <button type="button" class="kb-mode-btn ${kbFilter.mode === "any" ? "active" : ""}" data-mode="any">${t("хотя бы в одном из выбранных")}</button>
      <button type="button" class="kb-mode-btn ${kbFilter.mode === "all" ? "active" : ""}" data-mode="all">${t("во всех выбранных сразу")}</button>
    </div>` : "";

  const lang = kbLang();
  const userKey = lang === "en" ? "user_en" : "user_ru";
  const rows = concepts.map(c => `
    <tr>
      <td><button type="button" class="kb-title-link" data-edit="${escapeHtml(c.id)}" title="${t("Открыть тему")}">${escapeHtml(loc(c, "title"))}</button>
        ${c.user_created ? `<span class="kb-badge own">${t("своя тема")}</span>` : c.user_modified ? `<span class="kb-badge">${t("изменено")}</span>` : ""}
        <div class="kb-themes">${(c.themes || []).map(th => `<button type="button" class="kb-theme ${th === theme ? "active" : ""}" data-theme="${escapeHtml(th)}" title="${t("Показать темы этого раздела")}">${escapeHtml(locMap(kbData.themes_en, th))}</button>`).join("")}</div>
        <button type="button" class="btn btn-sm kb-edit" data-edit="${escapeHtml(c.id)}">${t("Изменить")}</button></td>
      <td class="kb-phr">${(c[lang] || []).map(x => `<span class="${(c[userKey] || []).includes(x) ? "own" : ""}">${escapeHtml(x)}</span>`).join("") || `<span class="muted">—</span>`}</td>
      <td>${(c.doc_hints || []).map(h => `
        <div class="kb-hint ${fams.includes(kbFamilyOf(h)) ? "hl" : ""}">${escapeHtml(loc(h, "family"))}: <span class="id-cell">${escapeHtml(loc(h, "ref"))}</span>${h.verify ? ` <span class="muted" title="${t("Номер требует сверки с вашей редакцией документа")}">*</span>` : ""}</div>`).join("")}</td>
      <td>${kbCoverageHtml(c)}</td>
    </tr>`).join("");

  const filtered = fams.length || f || theme;
  const shown = filtered
    ? `<p class="muted kb-shown">${t("Найдено тем")}: <b>${concepts.length}</b> ${t("из")} ${kbData.concepts.length}
         ${theme ? ` · ${t("раздел")}: <b>${escapeHtml(locMap(kbData.themes_en, theme))}</b>` : ""}
         · <a href="#" id="kb-reset">${t("сбросить фильтры")}</a></p>`
    : "";
  const edits = kbData.concepts.filter(c => c.user_modified).length;

  openModal(t("База знаний"), `
    <p class="muted">${t("Темы требований, по которым сервис распознаёт пункты нормативных документов, и формулировки, по которым он их узнаёт.")}</p>
    <div class="kb-summary">
      <div><b>${kbData.concepts.length}</b><span>${t("тем требований")}</span></div>
      <div><b>${kbData.concepts.reduce((n, c) => n + (c[lang] || []).length, 0)}</b><span>${lang === "en" ? t("формулировок EN") : t("формулировок RU")}</span></div>
      <div><b>${Object.keys(kbData.families).length}</b><span>${t("семейств документов")}</span></div>
      <div><b>${kbData.synonyms.length}</b><span>${t("пар синонимов")}</span></div>
    </div>
    <div class="kb-toolbar">
      <button type="button" class="btn btn-primary btn-sm" ${on("click", "openConceptEditor", null)}>+ ${t("Новая тема")}</button>
      <button type="button" class="btn btn-sm" ${on("click", "openPhraseTester")}>${t("Проверить формулировку")}</button>
      <button type="button" class="btn btn-sm" ${on("click", "openSynonymsEditor")}>${t("Синонимы")}</button>
      <span class="kb-toolbar-sep"></span>
      <span class="muted kb-edits">${t("Ваших правок")}: <b>${edits}</b></span>
      <button type="button" class="btn btn-sm" ${on("click", "kbExport")}>${t("Экспорт правок")}</button>
      <button type="button" class="btn btn-sm" ${on("click", "kbImportPick")}>${t("Импорт правок")}</button>
      <button type="button" class="btn btn-sm kb-help" ${on("click", "openEditsHelp")} title="${t("Что такое экспорт и импорт правок")}">?</button>
    </div>
    <div class="kb-fams">${chips}</div>
    ${modeBar}
    <input id="kb-filter" placeholder="${t("Поиск по темам, формулировкам и документам")}" value="${escapeHtml(kbFilter.text || "")}" style="width:100%;margin:10px 0 4px;">
    ${shown}
    <div class="doc-review">
      <table>
        <thead><tr><th>${t("Тема")}</th><th>${lang === "en" ? t("Формулировки EN") : t("Формулировки RU")}</th><th>${t("Где встречается")}</th><th>${t("Чем закрывается")}</th></tr></thead>
        <tbody>${rows || `<tr><td colspan="4" class="muted">${t("Ничего не найдено.")}</td></tr>`}</tbody>
      </table>
    </div>
    <p class="muted" style="margin-top:8px;">* ${t("Номер пункта — ориентир: нумерация меняется между редакциями, сверьте со своей копией документа.")}</p>
    <div class="modal-actions">
      <button type="button" class="btn btn-primary" ${on("click", "closeModal")}>${t("Закрыть")}</button>
    </div>`, true);

  const root = document.getElementById("modal-root");
  root.querySelectorAll(".kb-fam").forEach(btn => btn.addEventListener("click", () => {
    const k = btn.getAttribute("data-fam");
    const next = fams.includes(k) ? fams.filter(x => x !== k) : fams.concat([k]);
    renderKnowledgeBase(undefined, next);
  }));
  root.querySelectorAll(".kb-mode-btn").forEach(btn => btn.addEventListener("click", () => {
    kbFilter.mode = btn.getAttribute("data-mode"); renderKnowledgeBase();
  }));
  root.querySelectorAll("[data-edit]").forEach(btn => btn.addEventListener("click", () =>
    openConceptEditor(btn.getAttribute("data-edit"))));
  root.querySelectorAll(".kb-theme").forEach(btn => btn.addEventListener("click", () => {
    const th = btn.getAttribute("data-theme");
    kbFilter.theme = kbFilter.theme === th ? null : th; renderKnowledgeBase();
  }));
  const reset = document.getElementById("kb-reset");
  if (reset) reset.addEventListener("click", e => { e.preventDefault(); kbFilter.theme = null; renderKnowledgeBase("", null); });
  const inp = document.getElementById("kb-filter");
  inp.addEventListener("input", () => {
    const v = inp.value, pos = inp.selectionStart;
    renderKnowledgeBase(v);
    const ni = document.getElementById("kb-filter");
    ni.focus(); ni.setSelectionRange(pos, pos);
  });
}

/* Что такое экспорт и импорт правок — объяснение для пользователя. */
function openEditsHelp() {
  openModal(t("Экспорт и импорт правок базы знаний"), `
    <div class="onboarding">
      <p>${t("Правки — это всё, что вы изменили в базе знаний: добавленные и скрытые формулировки, ссылки на документы, связи с проверками, свои темы и синонимы. Поставляемая база в файл не входит — только ваши изменения поверх неё.")}</p>
      <h3>${t("Для чего это нужно")}</h3>
      <ul>
        <li>${t("Перенести наработки на другой сервер — например, с тестового стенда на рабочий или к заказчику.")}</li>
        <li>${t("Поделиться с коллегами: один специалист пополняет базу по документам организации, остальные импортируют файл.")}</li>
        <li>${t("Сохранить резервную копию перед экспериментами — и вернуться к ней, если что-то пошло не так.")}</li>
        <li>${t("Посмотреть, что именно изменено: файл в формате JSON читается в любом текстовом редакторе.")}</li>
      </ul>
      <h3>${t("Как работает импорт")}</h3>
      <ul>
        <li>${t("Правки тем из файла заменяют правки тех же тем на этом сервере; правки остальных тем сохраняются.")}</li>
        <li>${t("Свои синонимы из файла добавляются к уже имеющимся.")}</li>
        <li>${t("Перед загрузкой файл проверяется: если в нём есть ссылки на проверки, которых нет в каталоге этого сервера, импорт отменяется целиком.")}</li>
      </ul>
      <h3>${t("Важно знать")}</h3>
      <ul>
        <li>${t("Обновление сервиса правки не стирает — они хранятся отдельно, в каталоге данных. Экспорт нужен для переноса, а не для сохранности при обновлении.")}</li>
        <li>${t("Любую тему можно вернуть к поставляемому виду кнопкой «Вернуть исходный вид» в окне темы.")}</li>
      </ul>
    </div>
    <div class="modal-actions">
      <button type="button" class="btn btn-primary" ${on("click", "renderKnowledgeBase")}>${t("Понятно")}</button>
    </div>`, true);
}
