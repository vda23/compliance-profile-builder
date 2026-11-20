/* Правила и профили.
   Обычный скрипт без сборки: файлы интерфейса подключаются по порядку и
   разделяют общую область видимости (см. index.html). */

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
  if (state.defsByFile && totalDefinitions() === 0 && !b.rules.length) {
    return `<div class="panel">
      <div class="catalog-cta">
        <div><b>${t("Быстрый путь — готовая проверка из каталога")}</b>
          <span class="muted">${t("Она создаст всё сама: переменную, объект, состояние, тест, определение и правило.")}</span></div>
        <button class="btn btn-primary" ${on("click", "openCatalogPicker")}>${t("+ Проверка из каталога")}</button>
      </div>
      ${depWarningHtml(
      "Правило ссылается на определение из OVAL-файла, поэтому сначала нужно создать хотя бы одно определение.",
      "A rule refers to a definition in an OVAL file, so create at least one definition first.", "definitions")}</div>`;
  }
  const rows = b.rules.map(r => `
    <tr>
      <td class="id-cell">${escapeHtml(r.id)}</td>
      <td>${escapeHtml(r.title)}</td>
      <td class="id-cell">${escapeHtml((r.idents || []).map(i => i.value).join(", ") || "—")}</td>
      <td>${escapeHtml((state.rulesSummary || {})[r.id] || "—")}
        <div class="rule-ref">${escapeHtml(r.check_href || "—")} · ${escapeHtml(r.check_name || "")}</div></td>
      <td class="actions-cell">
        <button class="btn btn-sm" ${on("click", "openEditRuleModal", (r.id))}>${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" ${on("click", "deleteRule", (r.id))}>${t("Удалить")}</button>
      </td>
    </tr>`).join("");
  return `
    <div class="panel">
      <div class="toolbar">
        <button class="btn btn-primary" ${on("click", "openCatalogPicker")}>${t("+ Проверка из каталога")}</button>
        <button class="btn" ${on("click", "openAddRuleModal")}>${t("+ Правило")}</button>
      </div>
      ${b.rules.length ? `
        <table>
          <thead><tr><th>${t("Идентификатор")}</th><th>${t("Название")}</th><th>${t("Требование (ident)")}</th><th>${t("Что проверяется")}</th><th></th></tr></thead>
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
      <button type="button" class="btn-icon" ${on("click", "removeClosest", "$el", "[data-ident-row]")}>✕</button>
    </div>`;
}
function identsEditorHtml(idents) {
  const list = idents && idents.length ? idents : [null];
  return `<div id="idents-container">${list.map(identRowHtml).join("")}</div>
    <button type="button" class="btn btn-sm" ${on("click", "addIdentRow")}>${t("+ Идентификатор требования")}</button>`;
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
          <select id="r-href" required ${on("change", "onRuleFileChanged")}>${ovalFileOptions(r.check_href)}</select>
        </div>
        <div class="field"><label>${L('check_content_name', {required:true})} ${hintIcon(
          "Определение из OVAL-файла, которое реализует это правило технически. При выборе название и описание правила подставляются автоматически.",
          "The OVAL definition that implements this rule. Selecting it pre-fills the rule title and description."
        )}</label>
          <select class="mono-input" id="r-name" required ${on("change", "onRuleDefChanged")}></select>
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
  if (!b.rules.length && !b.profiles.length) {
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
        <button class="btn btn-sm" ${on("click", "openManageSelectsModal", (p.id))}>${t("Состав")}</button>
        <button class="btn btn-sm" ${on("click", "openEditProfileModal", (p.id))}>${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" ${on("click", "deleteProfile", (p.id))}>${t("Удалить")}</button>
      </td>
    </tr>`).join("");
  return `
    <div class="panel">
      <div class="toolbar">
        <button class="btn btn-primary" ${on("click", "openAddProfileModal")}>${t("+ Профиль")}</button>
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
      <label class="row-check checklist-all"><input type="checkbox" id="rules-all" ${on("change", "toggleAllRules", "$checked")} ${rules.every(r => selectedIds.has(r.id)) ? "checked" : ""}> <b>${t("Выбрать все")}</b></label>
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
