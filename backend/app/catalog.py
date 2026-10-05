"""
Каталог типовых проверок и развёртывание записей каталога в элементы профиля.

ЗАЧЕМ
    Нормативный документ говорит «длина пароля не менее 8 символов», но не
    говорит, что в Debian-подобных системах это параметр minlen в файле
    /etc/security/pwquality.conf. Это знание хранится здесь — в каталоге.

    Запись каталога описывает проверку ПАРАМЕТРИЧЕСКИ: где искать, что
    сравнивать и какие значения можно подставить. Одна запись разворачивается
    в цепочку переменная → объект → состояние → тест → определение → правило.

ФОРМАТ ЗАПИСИ
    Файлы каталога — JSON (без внешних библиотек), лежат в backend/catalog/.
    Ключевые поля записи:

    id            строковый ключ, например "ssh.permit_root_login"
    title         краткое название проверки (пойдёт в заголовок определения)
    description   что проверяется — в описание определения
    rationale     зачем это нужно — в описание правила
    category      раздел для группировки ("Удалённый доступ")
    keywords      слова для сопоставления с пунктами документа
    platforms     {"family": "unix", "os": [...]} — где применимо
    params        параметры записи: {name, title, default, datatype}
    check         техническая часть (см. ниже)
    remediation   как исправить нарушение — текстом, для отчёта
    manual        true, если требование технически не проверяется

    Блок check:
      type              тип OVAL-теста либо псевдотип "pkg"
      object            поля объекта; значения могут содержать {{param}}
      state             поля состояния: {значение, operation, datatype}
      check             условие проверки (по умолчанию "all")
      check_existence   условие существования

    Псевдотип "pkg" разворачивается в linux:dpkginfo_test для DEB-систем и
    linux:rpminfo_test для RPM-систем; имя пакета задаётся как
    {"deb": "auditd", "rpm": "audit"}.

    Запись с manual=true не порождает проверку: она попадает только в отчёт
    о покрытии как «требуется организационная мера». Это сознательно —
    честная пометка полезнее, чем натянутая техническая проверка.
"""
import json
import os
import re

from . import oval_xml, xccdf_xml

CATALOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "catalog")

# Какой пакетный менеджер у какой системы — для псевдотипа "pkg".
RPM_SYSTEMS = ("ред ос", "red os", "redos", "alt", "альт", "sberlinux", "slo")

_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


class CatalogError(Exception):
    pass


# ---------------------------------------------------------------- загрузка

def load_catalog():
    """Все записи каталога из backend/catalog/*.json, отсортированные по id."""
    entries = []
    if not os.path.isdir(CATALOG_DIR):
        return entries
    for name in sorted(os.listdir(CATALOG_DIR)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(CATALOG_DIR, name)
        with open(path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except ValueError as e:
                raise CatalogError("Файл каталога %s повреждён: %s" % (name, e))
        pack = data.get("pack", name[:-5])
        for item in data.get("checks", []):
            item.setdefault("pack", pack)
            entries.append(item)
    entries.sort(key=lambda e: e.get("id", ""))
    return entries


def get_entry(entry_id):
    for e in load_catalog():
        if e.get("id") == entry_id:
            return e
    raise CatalogError("Запись каталога '%s' не найдена." % entry_id)


def categories():
    """Категории с числом записей — для группировки в интерфейсе."""
    out = {}
    for e in load_catalog():
        c = e.get("category", "Прочее")
        out[c] = out.get(c, 0) + 1
    return out


def entries_for_os(os_name):
    """Записи, применимые к указанной ОС (по списку platforms.os)."""
    if not os_name:
        return load_catalog()
    low = os_name.lower()
    out = []
    for e in load_catalog():
        oslist = [s.lower() for s in e.get("platforms", {}).get("os", [])]
        if not oslist or any(low in s or s in low for s in oslist):
            out.append(e)
    return out


# ------------------------------------------------------- подстановка значений

def resolve_params(entry, overrides=None):
    """Итоговые значения параметров записи: значения по умолчанию,
    переопределённые тем, что передал пользователь."""
    values = {}
    for p in entry.get("params", []):
        values[p["name"]] = p.get("default", "")
    for k, v in (overrides or {}).items():
        if v not in (None, ""):
            values[k] = v
    return values


def _subst(value, params):
    """Подставляет {{param}} в строку. Нестроковые значения возвращает как есть."""
    if not isinstance(value, str):
        return value
    def repl(m):
        key = m.group(1)
        if key not in params:
            raise CatalogError("В записи каталога использован неизвестный параметр '%s'." % key)
        return str(params[key])
    return _PLACEHOLDER.sub(repl, value)


def _is_rpm(os_name):
    low = (os_name or "").lower()
    return any(s in low for s in RPM_SYSTEMS)


def resolve_check(entry, params, os_name):
    """Разворачивает блок check: подставляет параметры и раскрывает
    псевдотип "pkg" в конкретный тип теста для целевой ОС."""
    check = json.loads(json.dumps(entry.get("check", {})))  # глубокая копия
    ttype = check.get("type")

    if ttype == "pkg":
        rpm = _is_rpm(os_name)
        check["type"] = "linux:rpminfo_test" if rpm else "linux:dpkginfo_test"
        name = check.get("object", {}).get("name")
        if isinstance(name, dict):
            check["object"]["name"] = name.get("rpm" if rpm else "deb", "")

    obj = {}
    for k, v in (check.get("object") or {}).items():
        if isinstance(v, dict):
            raise CatalogError("Поле объекта '%s' осталось словарём — уточните запись каталога." % k)
        obj[k] = _subst(v, params)
    check["object"] = obj

    state = {}
    for k, spec in (check.get("state") or {}).items():
        if isinstance(spec, dict):
            state[k] = {
                "value": _subst(spec.get("value", ""), params),
                "operation": spec.get("operation", "equals"),
                "datatype": spec.get("datatype", "string"),
            }
        else:
            state[k] = {"value": _subst(spec, params), "operation": "equals", "datatype": "string"}
    check["state"] = state
    return check


# ----------------------------------------------------- выделение идентификаторов

def _next_num(items, kind):
    mx = 0
    pat = re.compile(r"^oval:[^:]+:%s:(\d+)$" % kind)
    for it in items:
        m = pat.match(it.get("id", "") or "")
        if m:
            mx = max(mx, int(m.group(1)))
    return mx + 1


def _namespace(data):
    for group in ("definitions", "tests", "objects", "states", "variables"):
        for it in data.get(group, []):
            m = re.match(r"^oval:([^:]+):[a-z]+:\d+$", it.get("id", "") or "")
            if m:
                return m.group(1)
    return "custom"


def _next_rule_id(benchmark, prefix="xccdf_custom_rule_"):
    mx = 0
    pat = re.compile(r"^%s(\d+)$" % re.escape(prefix))
    for r in benchmark.get("rules", []):
        m = pat.match(r.get("id", "") or "")
        if m:
            mx = max(mx, int(m.group(1)))
    return "%s%d" % (prefix, mx + 1)


# ------------------------------------------------------------- развёртывание

def apply_entry(project_id, filename, entry, params=None, os_name=None,
                ident_system=None, ident_value=None, rule_id=None):
    """Разворачивает запись каталога в проект: создаёт переменные, объект,
    состояние, тест, определение и правило. Возвращает сводку созданного.

    Запись с manual=true ничего не создаёт — она возвращается как
    требующая организационной меры."""
    if entry.get("manual"):
        return {"manual": True, "entry_id": entry.get("id"), "created": {}}

    values = resolve_params(entry, params)
    check = resolve_check(entry, values, os_name)
    ttype = check["type"]

    data = oval_xml.get_oval_dict(project_id, filename)
    ns = _namespace(data)
    n_var = _next_num(data.get("variables", []), "var")
    n_obj = _next_num(data.get("objects", []), "obj")
    n_ste = _next_num(data.get("states", []), "ste")
    n_tst = _next_num(data.get("tests", []), "tst")
    n_def = _next_num(data.get("definitions", []), "def")

    def oid(kind, num):
        return "oval:%s:%s:%d" % (ns, kind, num)

    created = {"variables": [], "objects": [], "states": [], "tests": [], "definitions": [], "rules": []}
    title = entry.get("title", entry.get("id", ""))

    # --- объект ---
    obj_id = oid("obj", n_obj)
    oval_xml.add_object(project_id, filename, ttype, obj_id, "1",
                        check["object"], comment=title)
    created["objects"].append(obj_id)

    # --- переменные и состояние ---
    state_fields = {}
    for fname, spec in check.get("state", {}).items():
        # Эталонное значение выносится в переменную — так его проще
        # поменять централизованно, и это совпадает с эталонным комплектом.
        var_id = oid("var", n_var)
        oval_xml.add_variable(project_id, filename, var_id, "1",
                              spec["datatype"], spec["value"],
                              comment="Ожидаемое значение: %s" % title)
        created["variables"].append(var_id)
        n_var += 1
        state_fields[fname] = {
            "var_ref": var_id,
            "operation": spec["operation"],
            "datatype": spec["datatype"],
        }

    state_id = None
    if state_fields:
        state_id = oid("ste", n_ste)
        oval_xml.add_state(project_id, filename, ttype, state_id, "1",
                           state_fields, comment="Ожидаемое значение: %s" % title)
        created["states"].append(state_id)

    # --- тест ---
    test_id = oid("tst", n_tst)
    oval_xml.add_test(project_id, filename, ttype, test_id, "1",
                      object_ref=obj_id, state_ref=state_id,
                      check=check.get("check", "all"),
                      check_existence=check.get("check_existence", "at_least_one_exists"),
                      comment="Проверка: %s" % title)
    created["tests"].append(test_id)

    # --- определение ---
    def_id = oid("def", n_def)
    platforms = [os_name] if os_name else entry.get("platforms", {}).get("os", [])
    oval_xml.add_definition(
        project_id, filename, def_id, "1", "compliance",
        title=title,
        description=entry.get("description", title),
        family=entry.get("platforms", {}).get("family", "unix"),
        platforms=platforms,
        criteria=[{"test_ref": test_id, "comment": "Проверка: %s" % title}],
    )
    created["definitions"].append(def_id)

    # --- правило ---
    benchmark = xccdf_xml.get_benchmark_dict(project_id)
    rid = rule_id or _next_rule_id(benchmark)
    # Идентификатор требования: явно переданный, иначе — ссылка на пункт
    # документа из самой записи каталога (поле refs).
    idents = []
    if ident_system and ident_value:
        idents = [{"system": ident_system, "value": ident_value}]
    else:
        for r in entry.get("refs", []):
            if r.get("system") and r.get("value"):
                idents.append({"system": r["system"], "value": r["value"]})
    xccdf_xml.add_rule(
        project_id, rid, False, title,
        entry.get("rationale") or entry.get("description", title),
        idents, filename, def_id,
    )
    created["rules"].append(rid)

    return {"manual": False, "entry_id": entry.get("id"), "created": created}


# ------------------------------------------------------------ отчёт о покрытии

def coverage_report(pack=None, os_name=None):
    """Сводка по пакету каталога: какие пункты документа закрываются
    автоматической проверкой, а какие требуют ручной работы.

    Отчёт полезен сам по себе, до всякой генерации профиля: он показывает,
    какую долю требований вообще возможно проверить техническими средствами."""
    entries = load_catalog()
    if pack:
        entries = [e for e in entries if e.get("pack") == pack]
    if os_name:
        ids = {e["id"] for e in entries_for_os(os_name)}
        entries = [e for e in entries if e["id"] in ids]

    auto, manual = [], []
    for e in entries:
        row = {
            "entry_id": e.get("id"),
            "title": e.get("title"),
            "category": e.get("category", "Прочее"),
            "refs": [r.get("value") for r in e.get("refs", [])],
            "reason": e.get("notes") or "",
        }
        (manual if e.get("manual") else auto).append(row)

    items_auto = {v for r in auto for v in r["refs"]}
    items_manual = {v for r in manual for v in r["refs"]}
    return {
        "pack": pack,
        "total_entries": len(entries),
        "automatic": auto,
        "manual": manual,
        "items_covered": sorted(items_auto),
        "items_manual_only": sorted(items_manual - items_auto),
        "summary": {
            "entries_automatic": len(auto),
            "entries_manual": len(manual),
            "document_items_total": len(items_auto | items_manual),
            "document_items_automatic": len(items_auto),
        },
    }
