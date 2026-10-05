"""
Проверка проекта на соответствие "Требованиям к формату пользовательских
профилей и бенчмарков". Каждая проверка добавляет Issue с уровнем error/warning.
Наличие хотя бы одного error означает, что архив не пройдёт импорт.
"""
import re
from . import storage, xccdf_xml, oval_xml
from .oval_registry import TEST_TYPES, get_type_config

OVAL_ID_RE = re.compile(r"^oval:[A-Za-z0-9_.\-]+:(def|tst|obj|ste|var):\d+$")


def issue(level, message, path=""):
    return {"level": level, "message": message, "path": path}


def validate_project(project_id):
    issues = []

    if not storage.benchmark_file(project_id).exists():
        issues.append(issue("error", "Отсутствует benchmark-xccdf.xml.", "archive"))
        return issues

    oval_filenames = storage.list_oval_files(project_id)
    if not oval_filenames:
        issues.append(issue("error", "В проекте нет ни одного OVAL-файла (нужен хотя бы один).", "archive"))

    bench = xccdf_xml.get_benchmark_dict(project_id)

    for field in ("id", "xml_lang", "status", "title", "description", "version"):
        if not bench.get(field):
            issues.append(issue("error", "Benchmark: не заполнено обязательное поле '{}'.".format(field), "benchmark"))

    if not bench["profiles"]:
        issues.append(issue("warning", "В бенчмарке не описано ни одного профиля.", "benchmark"))
    if not bench["rules"]:
        issues.append(issue("warning", "В бенчмарке не описано ни одного правила.", "benchmark"))

    rule_ids = {r["id"] for r in bench["rules"]}
    profile_ids = set()

    for prof in bench["profiles"]:
        path = "profile:{}".format(prof['id'])
        if prof["id"] in profile_ids:
            issues.append(issue("error", "Дублирующийся идентификатор профиля '{}'.".format(prof['id']), path))
        profile_ids.add(prof["id"])

        if not prof.get("title"):
            issues.append(issue("error", "Profile: не заполнено название.", path))
        if not prof.get("description"):
            issues.append(issue("error", "Profile: не заполнено описание.", path))
        if not prof["selects"]:
            issues.append(issue("warning", "Профиль '{}' не содержит ни одного select.".format(prof['id']), path))

        for sel in prof["selects"]:
            if sel["idref"] not in rule_ids:
                issues.append(issue(
                    "error",
                    "Profile/select ссылается на несуществующее правило '{}'.".format(sel['idref']),
                    path,
                ))

    seen_rule_ids = set()
    for rule in bench["rules"]:
        path = "rule:{}".format(rule['id'])
        if rule["id"] in seen_rule_ids:
            issues.append(issue("error", "Дублирующийся идентификатор правила '{}'.".format(rule['id']), path))
        seen_rule_ids.add(rule["id"])

        if not rule.get("title"):
            issues.append(issue("error", "Rule: не заполнено название.", path))
        if not rule.get("description"):
            issues.append(issue("error", "Rule: не заполнено описание.", path))
        if not rule["idents"]:
            issues.append(issue("warning", "Правило '{}' не содержит ident.".format(rule['id']), path))

        href = rule.get("check_href")
        name = rule.get("check_name")
        if not href or not name:
            issues.append(issue("error", "Правило '{}': не задана ссылка check-content-ref.".format(rule['id']), path))
            continue
        if href not in oval_filenames:
            issues.append(issue(
                "error",
                "Правило '{}' ссылается на OVAL-файл '{}', которого нет в проекте.".format(rule['id'], href),
                path,
            ))
            continue
        oval_data = oval_xml.get_oval_dict(project_id, href)
        def_ids = {d["id"] for d in oval_data["definitions"]}
        if name not in def_ids:
            issues.append(issue(
                "error",
                "Правило '{}' ссылается на definition '{}', "
                "которого нет в файле '{}'.".format(rule['id'], name, href),
                path,
            ))

    all_ids = {}
    per_file_data = {}
    for fname in oval_filenames:
        data = oval_xml.get_oval_dict(project_id, fname)
        per_file_data[fname] = data
        for kind, items in (
            ("definition", data["definitions"]),
            ("test", data["tests"]),
            ("object", data["objects"]),
            ("state", data["states"]),
            ("variable", data["variables"]),
        ):
            for item in items:
                _id = item["id"]
                if not _id:
                    issues.append(issue("error", "{} без идентификатора в файле '{}'.".format(kind, fname), fname))
                    continue
                if not OVAL_ID_RE.match(_id):
                    issues.append(issue(
                        "error",
                        "Идентификатор '{}' не соответствует формату oval:<namespace>:<type>:<number>.".format(_id),
                        fname,
                    ))
                all_ids.setdefault(_id, []).append((fname, kind))

    for _id, locations in all_ids.items():
        if len(locations) > 1:
            files = ", ".join("{} ({})".format(f, k) for f, k in locations)
            issues.append(issue(
                "error",
                "Идентификатор '{}' не уникален в рамках комплекта файлов: {}.".format(_id, files),
                "oval",
            ))

    for fname, data in per_file_data.items():
        test_ids = {t["id"] for t in data["tests"]}
        for d in data["definitions"]:
            path = "{}#definition:{}".format(fname, d['id'])
            if not d.get("title"):
                issues.append(issue("error", "Definition: не заполнено metadata/title.", path))
            if not d.get("description"):
                issues.append(issue("error", "Definition: не заполнено metadata/description.", path))
            if not d.get("family"):
                issues.append(issue("warning", "Definition: не указано metadata/affected/@family.", path))
            if not d["criteria"]:
                issues.append(issue("error", "Definition: не содержит ни одного criterion.", path))
            for c in d["criteria"]:
                if c["test_ref"] not in test_ids:
                    issues.append(issue(
                        "error",
                        "criterion ссылается на несуществующий тест '{}' в файле '{}'.".format(c['test_ref'], fname),
                        path,
                    ))

        obj_by_id = {o["id"]: o for o in data["objects"]}
        ste_by_id = {s["id"]: s for s in data["states"]}
        var_ids = {v["id"] for v in data["variables"]}

        for t in data["tests"]:
            path = "{}#test:{}".format(fname, t['id'])
            ttype = t.get("type")
            if ttype not in TEST_TYPES:
                issues.append(issue(
                    "error",
                    "Тест '{}' использует недопустимый или нераспознанный тип '{}'.".format(t['id'], ttype),
                    path,
                ))
                continue

            cfg = get_type_config(ttype)
            obj_ref = t.get("object_ref")
            if not obj_ref or obj_ref not in obj_by_id:
                issues.append(issue("error", "Тест '{}': object_ref не найден в objects.".format(t['id']), path))
            else:
                if obj_by_id[obj_ref].get("type") != ttype:
                    issues.append(issue(
                        "error",
                        "Тест '{}' ({}) ссылается на object '{}' несовместимого типа "
                        "'{}'.".format(t['id'], ttype, obj_ref, obj_by_id[obj_ref].get('type')),
                        path,
                    ))

            if cfg["state_fields"]:
                ste_ref = t.get("state_ref")
                if ste_ref:
                    if ste_ref not in ste_by_id:
                        issues.append(issue("error", "Тест '{}': state_ref не найден в states.".format(t['id']), path))
                    elif ste_by_id[ste_ref].get("type") != ttype:
                        issues.append(issue(
                            "error",
                            "Тест '{}' ({}) ссылается на state '{}' несовместимого типа "
                            "'{}'.".format(t['id'], ttype, ste_ref, ste_by_id[ste_ref].get('type')),
                            path,
                        ))

        for s in data["states"]:
            for fname_, value in (s.get("fields") or {}).items():
                if isinstance(value, dict) and value.get("var_ref"):
                    if value["var_ref"] not in var_ids:
                        issues.append(issue(
                            "error",
                            "State '{}': var_ref '{}' не найден среди variables.".format(s['id'], value['var_ref']),
                            "{}#state:{}".format(fname, s['id']),
                        ))

    return issues


def is_valid(issues):
    return not any(i["level"] == "error" for i in issues)
