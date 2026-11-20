/* Профиль по нормативному документу: разбор, решения по пунктам, черновик, отчёт.
   Обычный скрипт без сборки: файлы интерфейса подключаются по порядку и
   разделяют общую область видимости (см. index.html). */

/* ============ Нормативный документ → черновик профиля ============
   Документ разбирается на сервере: выделяются пронумерованные пункты,
   по базе знаний определяется тема каждого требования и подбираются
   проверки из каталога. Результат — ЧЕРНОВИК: он открывается в
   конструкторе и правится обычным образом. */

let pendingDocFile = null;
let pendingDocAnalysis = null;

/* Идентификатор проекта из имени файла. Кириллица транслитерируется:
   «Методический документ от 25 декабря 2022 г.odt» →
   «metodicheskiy_dokument_ot_25_dekabrya_2022_g». Раньше русские буквы
   заменялись подчёркиваниями, и получалось «__25_2022_». */
const TRANSLIT = {а:"a",б:"b",в:"v",г:"g",д:"d",е:"e",ё:"e",ж:"zh",з:"z",и:"i",й:"y",к:"k",л:"l",м:"m",
  н:"n",о:"o",п:"p",р:"r",с:"s",т:"t",у:"u",ф:"f",х:"kh",ц:"ts",ч:"ch",ш:"sh",щ:"shch",ъ:"",ы:"y",ь:"",
  э:"e",ю:"yu",я:"ya"};
function slugFromName(name) {
  const base = (name || "document").replace(/\.[^.]+$/, "").toLowerCase();
  const lat = Array.from(base).map(ch => (ch in TRANSLIT ? TRANSLIT[ch] : ch)).join("");
  let slug = lat.replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  // Идентификатор проекта — до 64 символов, из них 6 занимает префикс «draft_».
  // Обрезаем по границе слова, чтобы не разрывать слова и числа.
  if (slug.length > 56) {
    const cut = slug.slice(0, 56);
    slug = cut.includes("_") ? cut.slice(0, cut.lastIndexOf("_")) : cut;
  }
  return slug || "document";
}

function onDocumentFileChosen(e) {
  const file = e.target.files[0];
  if (!file) return;
  pendingDocFile = file;
  pendingDocAnalysis = null;
  openDocumentSetupModal();
}

function openDocumentSetupModal() {
  const file = pendingDocFile;
  const guess = slugFromName(file.name);
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
            ${TARGET_OS.map(o => `<option value="${escapeHtml(o)}">`).join("")}
          </datalist>
        </div>
        <div class="field"><label>${L('project_id_new', {required:true})}</label>
          <input class="mono-input" id="doc-project-id" required value="${escapeHtml("draft_" + guess)}">
        </div>
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
/* Экран разбора документа: у каждого пункта — решение пользователя.
   Оставить предложенную проверку, выбрать другую из кандидатов, отнести к
   организационным мерам или исключить. Черновик собирается из этого разбора
   без повторной загрузки документа. */
const CONF_ORDER = { "высокая": 3, "средняя": 2, "низкая": 1, "нет": 0 };

function docDecisionOptions(m, minconf) {
  const best = m.candidates && m.candidates[0];
  const passes = best && (CONF_ORDER[m.confidence] || 0) >= (CONF_ORDER[minconf] || 2);
  const autoLabel = !best ? t("Авто: нет проверки — не войдёт")
    : passes ? `${t("Авто")}: ${loc(best, "title")}${best.manual ? ` (${t("орг. мера")})` : ""}`
             : `${t("Авто: не войдёт — уверенность ниже порога")}`;
  const cur = m.decision || "auto";
  const opt = (v, label) => `<option value="${escapeHtml(v)}" ${cur === v ? "selected" : ""}>${escapeHtml(label)}</option>`;
  const cands = (m.candidates || []).map(c => opt(c.entry_id, `${loc(c, "title")}${c.manual ? ` (${t("орг. мера")})` : ""}`)).join("");
  return opt("auto", autoLabel)
    + (cands ? `<optgroup label="${escapeHtml(t("Выбрать проверку"))}">${cands}</optgroup>` : "")
    + `<optgroup label="${escapeHtml(t("Другое"))}">${opt("manual", t("Организационная мера"))}${opt("exclude", t("Исключить пункт"))}</optgroup>`;
}

function openDocumentReviewModal() {
  const a = pendingDocAnalysis;
  a.minconf = a.minconf || "средняя";
  const rows = a.matches.map((m, i) => {
    const concept = m.concepts && m.concepts[0];
    const cls = m.confidence === "высокая" ? "ok" : m.confidence === "средняя" ? "mid" : "low";
    const dec = m.decision || "auto";
    return `
      <tr class="${dec === "exclude" ? "doc-excluded" : ""}">
        <td class="id-cell">${escapeHtml(m.number)}</td>
        <td>${escapeHtml((m.text || "").slice(0, 110))}${(m.text || "").length > 110 ? "…" : ""}</td>
        <td>${concept ? escapeHtml(loc(concept, "title")) : `<span class="muted">—</span>`}</td>
        <td><select class="doc-decision" data-i="${i}">${docDecisionOptions(m, a.minconf)}</select></td>
        <td><span class="conf conf-${cls}">${escapeHtml(t(m.confidence))}</span></td>
      </tr>`;
  }).join("");

  const counts = a.matches.reduce((acc, m) => { acc[m.confidence] = (acc[m.confidence] || 0) + 1; return acc; }, {});
  const changed = a.matches.filter(m => m.decision && m.decision !== "auto").length;

  openModal(`${t("Разбор документа")}: ${a.filename}`, `
    <form id="mf">
      <p class="muted" style="margin-bottom:10px;">
        ${t("Пунктов найдено")}: <b>${a.items_total}</b> ·
        ${t("высокая")}: ${counts["высокая"] || 0} ·
        ${t("средняя")}: ${counts["средняя"] || 0} ·
        ${t("низкая")}: ${counts["низкая"] || 0} ·
        ${t("нет")}: ${counts["нет"] || 0}
        ${changed ? ` · <b>${t("изменено вручную")}: ${changed}</b>` : ""}
      </p>
      <div class="doc-review">
        <table>
          <thead><tr>
            <th>${t("Пункт")}</th><th>${t("Текст")}</th>
            <th>${t("Тема требования")}</th><th>${t("Решение")}</th>
            <th>${t("Уверенность")}</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
      <div class="field" style="margin-top:12px;">
        <label>${t("Для пунктов с решением «Авто» включать уверенность")}</label>
        <select id="doc-minconf">
          <option value="высокая" ${a.minconf === "высокая" ? "selected" : ""}>${t("только высокая")}</option>
          <option value="средняя" ${a.minconf === "средняя" ? "selected" : ""}>${t("высокая и средняя")}</option>
          <option value="низкая" ${a.minconf === "низкая" ? "selected" : ""}>${t("любая, включая низкую")}</option>
        </select>
        <span class="hint">${t("Выбранная вручную проверка войдёт в черновик при любой уверенности.")}</span>
      </div>
      <div class="dep-warning" style="margin-top:4px;">
        <span class="icon">!</span>
        <div>${escapeHtml(getLang() === "en" ? (a.disclaimer_en || a.disclaimer) : a.disclaimer)}</div>
      </div>
      ${formActions(t("Создать черновик профиля"))}
    </form>`, true);

  document.querySelectorAll(".doc-decision").forEach(sel => sel.addEventListener("change", () => {
    a.matches[+sel.getAttribute("data-i")].decision = sel.value;
    const scroll = document.querySelector(".doc-review").scrollTop;
    openDocumentReviewModal();
    document.querySelector(".doc-review").scrollTop = scroll;   // не терять место в длинном документе
  }));
  document.getElementById("doc-minconf").addEventListener("change", ev => {
    a.minconf = ev.target.value;
    const scroll = document.querySelector(".doc-review").scrollTop;
    openDocumentReviewModal();
    document.querySelector(".doc-review").scrollTop = scroll;
  });
  bindForm(async () => {
    const report = await api.post("/documents/draft-from-analysis", {
      project_id: a.projectId, title: a.title, os: a.osName,
      min_confidence: a.minconf, matches: a.matches,
    });
    document.getElementById("doc-file").value = "";
    await loadProjects();
    await selectProject(a.projectId);
    openDocumentReportModal(report);
  }, null, true);
}

/* Сохранённый отчёт о покрытии: открывается из шапки проекта. */
async function openSavedCoverage() {
  try {
    const rep = await api.get(`/projects/${encodeURIComponent(state.currentProjectId)}/coverage`);
    openDocumentReportModal(rep);
  } catch (e) { toast(e.message, "error"); }
}

/* Итог сборки: что создано, что требует организационных мер, что осталось
   без сопоставления. Отчёт полезен и сам по себе — как оценка покрытия. */
function openDocumentReportModal(rep) {
  const s = rep.summary;
  const list = (arr, empty, fmt) => arr.length
    ? `<ul class="report-list">${arr.map(fmt).join("")}</ul>`
    : `<p class="muted">${escapeHtml(empty)}</p>`;
  openModal(rep.created ? `${t("Отчёт о покрытии")}: ${rep.document}` : t("Черновик профиля создан"), `
    ${rep.created ? `<p class="muted" style="margin-top:0;">${t("Сформирован при сборке черновика")} ${escapeHtml(new Date(rep.created).toLocaleString())}${rep.os ? ` · ${escapeHtml(rep.os)}` : ""}</p>` : ""}
    <div class="report-grid">
      <div><b>${s.items_total}</b><span>${t("пунктов в документе")}</span></div>
      <div><b>${s.rules_created}</b><span>${t("создано правил")}</span></div>
      <div><b>${s.items_manual}</b><span>${t("организационных мер")}</span></div>
      <div><b>${s.items_unmatched}</b><span>${t("без сопоставления")}</span></div>
      ${s.items_excluded ? `<div><b>${s.items_excluded}</b><span>${t("исключено")}</span></div>` : ""}
    </div>
    ${s.items_covered > s.rules_created ? `<p class="muted" style="margin-top:8px;">${t("Пунктов, закрытых проверками")}: ${s.items_covered}. ${t("Часть пунктов закрывается одним правилом — у такого правила несколько идентификаторов требований.")}</p>` : ""}
    <div class="dep-warning" style="margin-top:12px;">
      <span class="icon">!</span><div>${escapeHtml(loc(rep, "disclaimer"))}</div>
    </div>
    <h3 style="margin-top:14px;">${t("Требуют организационных мер")}</h3>
    ${list(rep.manual, t("Таких пунктов нет."), m =>
      `<li><span class="id-cell">${escapeHtml(m.number)}</span> ${escapeHtml(loc(m, "title"))}
       <div class="muted">${escapeHtml(loc(m, "reason"))}</div></li>`)}
    ${(rep.excluded || []).length ? `<h3 style="margin-top:14px;">${t("Исключены при разборе")}</h3>
    ${list(rep.excluded, "", m => `<li><span class="id-cell">${escapeHtml(m.number)}</span>
       <span class="muted">${escapeHtml((m.text || "").slice(0, 120))}</span></li>`)}` : ""}
    <h3 style="margin-top:14px;">${t("Без сопоставления")}</h3>
    ${list(rep.skipped, t("Все пункты сопоставлены."), m =>
      `<li><span class="id-cell">${escapeHtml(m.number)}</span>
       <span class="muted">${escapeHtml((m.text || "").slice(0, 120))}</span></li>`)}
    <div class="modal-actions">
      ${rep.project_id ? `<a class="btn" style="margin-right:auto;" href="/api/projects/${encodeURIComponent(rep.project_id)}/coverage/report?lang=${getLang()}" download>${t("Скачать отчёт (HTML)")}</a>` : ""}
      <button type="button" class="btn btn-primary" ${on("click", "closeModal")}>${rep.created ? t("Закрыть") : t("Перейти к правке")}</button>
    </div>`, true);
}
