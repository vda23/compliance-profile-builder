"""
Что проверяет правило — человеческим языком.

Описание собирается по цепочке «правило → определение → тест → объект и
состояние», значения переменных подставляются. Проверяющему черновик нужен
смысл: «Параметр ядра kernel.randomize_va_space = 2», а не идентификаторы
OVAL. Для типов без особого описания используются названия полей из
реестра типов — описание есть всегда.
"""
import re

from . import oval_xml, storage, xccdf_xml
from .oval_registry import TEST_TYPES

OPS = {
    "equals": "=", "not equal": "≠", "greater than": ">", "less than": "<",
    "greater than or equal": "≥", "less than or equal": "≤", "case insensitive equals": "=",
}

# Права доступа unix:file_state: boolean-поле → (русское, английское) название
PERMS = {
    "uread": ("чтение владельцем", "owner read"), "uwrite": ("запись владельцем", "owner write"),
    "uexec": ("выполнение владельцем", "owner execute"), "gread": ("чтение группой", "group read"),
    "gwrite": ("запись группой", "group write"), "gexec": ("выполнение группой", "group execute"),
    "oread": ("чтение для прочих", "read for others"), "owrite": ("запись для прочих", "write for others"),
    "oexec": ("выполнение для прочих", "execute for others"),
    "suid": ("бит SUID", "SUID bit"), "sgid": ("бит SGID", "SGID bit"), "sticky": ("sticky-бит", "sticky bit"),
}

# Все фразы описаний: ключ → (русский шаблон, английский шаблон)
TEXT = {
    "pattern": ("соответствует шаблону", "matches pattern"),
    "boot_param": ("Параметр загрузки ядра %s %s", "Kernel boot parameter %s %s"),
    "set": ("задан", "is set"), "not_set": ("не задан", "is not set"),
    "line": ("Файл %s: %s строка с «%s»", "File %s: %s a line with \"%s\""),
    "has": ("есть", "has"), "has_no": ("нет", "has no"),
    "param": ("параметр %s", "parameter %s"),
    "by_pattern": ("строка по шаблону «%s»", "a line matching \"%s\""),
    "must_not_value": ("Файл %s: %s — такого значения не должно быть", "File %s: %s — this value must not be present"),
    "must_not_lines": ("Файл %s: строк по шаблону «%s» не должно быть", "File %s: no lines may match \"%s\""),
    "file_value": ("Файл %s: %s %s", "File %s: %s %s"),
    "file_set": ("Файл %s: %s задан", "File %s: %s is set"),
    "kernel": ("Параметр ядра %s%s", "Kernel parameter %s%s"),
    "file_exists": ("Файл %s существует", "File %s exists"),
    "file_absent": ("Файл %s отсутствует", "File %s is absent"),
    "denied": ("запрещено: %s", "denied: %s"), "allowed": ("разрешено: %s", "allowed: %s"),
    "owner": ("владелец UID %s", "owner UID %s"), "group": ("группа GID %s", "group GID %s"),
    "file_attrs": ("Файл %s: %s", "File %s: %s"),
    "pkg_absent": ("Пакет %s не установлен", "Package %s is not installed"),
    "pkg_present": ("Пакет %s установлен%s", "Package %s is installed%s"),
    "service": ("Служба %s: %s%s", "Service %s: %s%s"),
    "port_closed": ("Порт %s не прослушивается", "Port %s is not listening"),
    "port_open": ("Порт %s прослушивается", "Port %s is listening"),
    "registry": ("Реестр %s%s", "Registry %s%s"),
    "policy_set": ("задана", "is set"),
    "must_not_exist": (" — не должно существовать", " — must not exist"),
    "no_file": ("OVAL-файл %s не найден", "OVAL file %s not found"),
    "no_def": ("Определение не найдено в %s", "Definition not found in %s"),
    "no_tests": ("Тесты определения не найдены", "Definition tests not found"),
}


def _t(lang, key, *args):
    ru, en = TEXT[key]
    text = en if lang == "en" else ru
    return text % args if args else text


_NOISE = {"space", "alnum", "alpha", "digit", "upper", "lower", "punct", "blank"}


def _param_name(pattern):
    """Имя параметра из шаблона: «^[[:space:]]*PermitRootLogin[[:space:]]+(…)» → PermitRootLogin."""
    for lit in re.findall(r"[A-Za-z_][A-Za-z0-9_.]{2,}", pattern or ""):
        if lit.lower() not in _NOISE:
            return lit.replace("\\", "")
    return None


def _literal_group(pattern):
    """Текст в захватывающей группе, если это конкретный текст, а не шаблон:
    «…(pam_wheel\\.so)» → pam_wheel.so, «(init_on_alloc=1)» → init_on_alloc=1.
    Для «([a-zA-Z-]+)» и подобных возвращает None."""
    m = re.search(r"\(([^()]*)\)", pattern or "")
    if not m:
        return None
    body = m.group(1)
    if re.search(r"(?<!\\)[\[\]*+?{}|^$]", body):     # есть метасимволы — это шаблон
        return None
    if re.search(r"(?<!\\)\.", body):                    # неэкранированная точка — тоже шаблон
        return None
    return body.replace("\\", "")


def _value_text(op, value, lang="ru"):
    """«соответствует шаблону ^no$» → «= no»: точный шаблон показывается как значение."""
    m = re.match(r"^\^([A-Za-z0-9_./:-]+)\$$", str(value))
    if op == "pattern match" and m:
        return "= %s" % m.group(1)
    sym = _t(lang, "pattern") if op == "pattern match" else OPS.get(op, op)
    return "%s %s" % (sym, value)


def _state_fields(state, variables):
    """Поля состояния с подставленными значениями переменных."""
    out = []
    for name, f in (state or {}).get("fields", {}).items():
        if isinstance(f, dict):
            value = f.get("value")
            if f.get("var_ref"):
                value = variables.get(f["var_ref"], f["var_ref"])
            out.append((name, f.get("operation", "equals"), value))
        else:
            out.append((name, "equals", f))
    return out


def _label(ttype, name, lang="ru"):
    for f in TEST_TYPES.get(ttype, {}).get("state_fields", []) + TEST_TYPES.get(ttype, {}).get("object_fields", []):
        if f["name"] == name:
            return f.get("label_en" if lang == "en" else "label", name)
    return name


def _type_label(ttype, lang):
    cfg = TEST_TYPES.get(ttype, {})
    return cfg.get("label_en" if lang == "en" else "label", ttype)


def describe_test(test, objects, states, variables, lang="ru"):
    T = lambda key, *a: _t(lang, key, *a)
    V = lambda op, v: _value_text(op, v, lang)
    ttype = test.get("type", "")
    obj = objects.get(test.get("object_ref"), {})
    of = obj.get("fields", {})
    sf = _state_fields(states.get(test.get("state_ref")), variables)
    absent = test.get("check_existence") == "none_exist"

    if ttype == "ind:textfilecontent54_test":
        path = "%s/%s" % (of.get("path", "").rstrip("/"), of.get("filename", ""))
        literal = _literal_group(of.get("pattern"))
        if path == "/proc/cmdline" and literal:
            return T("boot_param", literal, T("not_set") if absent else T("set"))
        if literal:
            # Проверка наличия конкретной строки: «auth required pam_wheel.so».
            # Значение состояния здесь повторяет захваченный текст.
            return T("line", path, T("has_no") if absent else T("has"), literal)
        param = _param_name(of.get("pattern"))
        what = T("param", param) if param else T("by_pattern", of.get("pattern", ""))
        if absent:
            return T("must_not_value", path, what) if param else T("must_not_lines", path, of.get("pattern", ""))
        if sf:
            return T("file_value", path, what, V(sf[0][1], sf[0][2]))
        return T("file_set", path, what)

    if ttype == "unix:sysctl_test":
        val = " %s" % V(sf[0][1], sf[0][2]) if sf else " " + T("set")
        return T("kernel", of.get("name", ""), val)

    if ttype == "unix:file_test":
        path = "%s/%s" % (of.get("path", "").rstrip("/"), of.get("filename", ""))
        if not sf:
            return T("file_absent" if absent else "file_exists", path)
        parts = []
        for name, op, value in sf:
            if name in PERMS:
                label = PERMS[name][1 if lang == "en" else 0]
                parts.append(T("denied" if str(value).lower() in ("false", "0") else "allowed", label))
            elif name == "user_id":
                parts.append(T("owner", value))
            elif name == "group_id":
                parts.append(T("group", value))
            else:
                parts.append("%s %s" % (_label(ttype, name, lang), V(op, value)))
        return T("file_attrs", path, ", ".join(parts))

    if ttype in ("linux:dpkginfo_test", "linux:rpminfo_test"):
        name = of.get("name", "")
        if absent:
            return T("pkg_absent", name)
        extra = "".join(", %s %s" % (_label(ttype, n, lang), V(o, v)) for n, o, v in sf)
        return T("pkg_present", name, extra)

    if ttype == "linux:systemdunitproperty_test":
        val = " %s" % V(sf[0][1], sf[0][2]) if sf else ""
        return T("service", of.get("unit", ""), of.get("property", ""), val)

    if ttype == "linux:inetlisteningservers_test":
        port = "%s/%s" % (of.get("local_port", "?"), of.get("protocol", "tcp"))
        return T("port_closed" if absent else "port_open", port)

    if ttype == "windows:registry_test":
        loc = "%s\\%s\\%s" % (of.get("hive", ""), of.get("key", ""), of.get("name", ""))
        val = " %s" % V(sf[0][1], sf[0][2]) if sf else ""
        return T("registry", loc, val)

    if ttype in ("windows:passwordpolicy_test", "windows:lockoutpolicy_test",
                 "windows:auditeventpolicysubcategories_test"):
        parts = ["%s %s" % (_label(ttype, n, lang), V(o, v)) for n, o, v in sf]
        return "%s: %s" % (_type_label(ttype, lang), ", ".join(parts) or T("policy_set"))

    # Общий случай: название типа и поля из реестра
    ofs = ", ".join("%s: %s" % (_label(ttype, k, lang), v) for k, v in of.items() if v not in (None, ""))
    sfs = ", ".join("%s %s" % (_label(ttype, n, lang), V(o, v)) for n, o, v in sf)
    text = _type_label(ttype, lang) + (" (%s)" % ofs if ofs else "")
    if absent:
        text += T("must_not_exist")
    return text + (": %s" % sfs if sfs else "")


def describe_rules(project_id, lang="ru"):
    """{идентификатор правила: описание} для всех правил проекта."""
    bench = xccdf_xml.get_benchmark_dict(project_id)
    cache = {}

    def oval(fname):
        if fname not in cache:
            try:
                d = oval_xml.get_oval_dict(project_id, fname)
            except Exception:  # noqa: BLE001 — файл, на который ссылается правило, может отсутствовать
                d = None
            if d is not None:
                d = {
                    "defs": {x["id"]: x for x in d.get("definitions", [])},
                    "tests": {x["id"]: x for x in d.get("tests", [])},
                    "objects": {x["id"]: x for x in d.get("objects", [])},
                    "states": {x["id"]: x for x in d.get("states", [])},
                    "vars": {x["id"]: x.get("value") for x in d.get("variables", [])},
                }
            cache[fname] = d
        return cache[fname]

    out = {}
    for r in bench.get("rules", []):
        d = oval(r.get("check_href") or "")
        if d is None:
            out[r["id"]] = _t(lang, "no_file", r.get("check_href") or "—")
            continue
        definition = d["defs"].get(r.get("check_name"))
        if not definition:
            out[r["id"]] = _t(lang, "no_def", r.get("check_href"))
            continue
        parts = []
        for c in definition.get("criteria", []):
            t = d["tests"].get(c.get("test_ref"))
            if t:
                parts.append(describe_test(t, d["objects"], d["states"], d["vars"], lang))
        out[r["id"]] = "; ".join(parts) or _t(lang, "no_tests")
    return out
