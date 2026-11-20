/* OVAL-файлы: список, формы добавления и правки элементов.
   Обычный скрипт без сборки: файлы интерфейса подключаются по порядку и
   разделяют общую область видимости (см. index.html). */

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
        <button class="btn btn-primary" ${on("click", "openAddOvalFileModal")}>${t("+ OVAL-файл")}</button>
      </div>` : ""}
      ${showChips ? `
      <div class="oval-file-list" id="oval-file-list">
        ${files.map(f => `
          <div class="oval-file-chip ${f === state.currentOvalFile ? "active" : ""}" ${on("click", "selectOvalFile", (f))}>
            ${escapeHtml(f)}
          </div>`).join("") || `<span class="muted">${t("OVAL-файлы ещё не добавлены.")}</span>`}
      </div>` : ""}
      ${fileStep && files.length ? `
      <div class="row" style="margin-top:8px;gap:10px;align-items:center;flex-wrap:wrap;">
        <span class="muted">${t("Файл создан. Нажмите «Далее», чтобы перейти к наполнению проверок.")}</span>
        ${state.currentOvalFile && files.includes(state.currentOvalFile) ? `
        <button class="btn btn-sm btn-danger" style="margin-left:auto;" ${on("click", "deleteOvalFile", (state.currentOvalFile))}>${t("Удалить файл")} ${escapeHtml(state.currentOvalFile)}</button>` : ""}
      </div>` : ""}
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
      <div class="field"><label>${L('filename', {required:true})}</label><input class="mono-input" id="of-filename" required value="checks" ${on("input", "previewOvalName")}>
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
      <button class="btn btn-sm btn-danger" ${on("click", "deleteOvalFile", (state.currentOvalFile))}>${t("Удалить файл")}</button>
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
  return `<div class="subtab ${state.ovalSubtab === key ? "active" : ""}" ${on("click", "setOvalSubtab", (key))}>${escapeHtml(label)}</div>`;
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
      <td class="actions-cell"><button class="btn btn-sm" ${on("click", "openEditVariableModal", (v.id))}>${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" ${on("click", "deleteVariable", (v.id))}>${t("Удалить")}</button></td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" ${on("click", "openAddVariableModal")}>${t("+ Переменная")}</button></div>
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
        ${f.allow_var_ref && variables.length ? `<label class="row-check"><input type="checkbox" id="stemode_${f.name}" ${isVar ? "checked" : ""} ${on("change", "toggleVarRefMode", (f.name))}> ${t("Из переменной")}</label>` : ""}
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
      <td class="actions-cell"><button class="btn btn-sm" ${on("click", "openEditObjectModal", (o.id))}>${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" ${on("click", "deleteObject", (o.id))}>${t("Удалить")}</button></td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" ${on("click", "openAddObjectModal")}>${t("+ Объект")}</button></div>
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
      )}</label><select id="o-type" required ${on("change", "onObjectTypeChanged")}>${typeOptions}</select></div>
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
      <td class="actions-cell"><button class="btn btn-sm" ${on("click", "openEditStateModal", (s.id))}>${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" ${on("click", "deleteState", (s.id))}>${t("Удалить")}</button></td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" ${on("click", "openAddStateModal")}>${t("+ Состояние")}</button></div>
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
      <div class="field"><label>${L('test_type', {required:true})}</label><select id="s-type" required ${on("change", "onStateTypeChanged")}>${testTypeOptionsHtml(ordered)}</select></div>
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
  if (!d.objects.length && !d.tests.length) {
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
      <td class="actions-cell"><button class="btn btn-sm" ${on("click", "openEditTestModal", (tt.id))}>${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" ${on("click", "deleteTest", (tt.id))}>${t("Удалить")}</button></td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" ${on("click", "openAddTestModal")}>${t("+ Тест")}</button></div>
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
        <select id="t-type" required ${on("change", "onTestTypeChanged")}>${testTypeOptionsHtml(types)}</select>
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
  if (!d.tests.length && !d.definitions.length) {
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
        <button class="btn btn-sm" ${on("click", "openEditDefinitionModal", (def.id))}>${t("Изменить")}</button>
        <button class="btn btn-sm btn-danger" ${on("click", "deleteDefinition", (def.id))}>${t("Удалить")}</button>
      </td>
    </tr>`).join("");
  container.innerHTML = `
    <div class="toolbar"><button class="btn btn-primary" ${on("click", "openAddDefinitionModal")}>${t("+ Определение")}</button></div>
    ${d.definitions.length
      ? `<table><thead><tr><th>${t("Идентификатор")}</th><th>${t("Название")}</th><th>${t("Семейство ОС")}</th><th>${t("Платформы")}</th><th>${t("Критериев")}</th><th></th></tr></thead><tbody>${rows}</tbody></table>`
      : emptyListHtml("Определения ещё не добавлены.", "No definitions yet.")}
  `;
}

function criteriaRowHtml(tests, c) {
  c = c || { test_ref: "", comment: "" };
  return `
    <div class="row" data-crit-row style="margin-bottom:6px;">
      <select class="mono-input" data-crit-testref style="flex:2;" ${on("change", "onCriterionChanged", "$el")}>
        <option value="">${t("— Тест —")}</option>${refOptionsHtml(tests, c.test_ref)}
      </select>
      <input placeholder="${t("Комментарий")}" value="${escapeHtml(c.comment || "")}" data-crit-comment style="flex:1;">
      <button type="button" class="btn-icon" ${on("click", "removeClosest", "$el", "[data-crit-row]")}>✕</button>
    </div>`;
}
function criteriaEditorHtml(criteria, tests) {
  const list = criteria && criteria.length ? criteria : [null];
  return `<div id="criteria-container">${list.map(c => criteriaRowHtml(tests, c)).join("")}</div>
    <button type="button" class="btn btn-sm" ${on("click", "addCriterionRow")}>${t("+ Критерий")}</button>`;
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
        )}</label><select id="d-family" ${on("change", "onFamilyChanged")}><option value="">—</option>${optionsHtml(FAMILY_VALUES, def.family || null, state.labels.family, state.labelsEn.family, {hideValue: true})}</select></div>
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
