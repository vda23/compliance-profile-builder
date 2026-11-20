# -*- coding: utf-8 -*-
"""
Обработчики REST API сервиса — без веб-фреймворка (раньше — FastAPI).

Каждый обработчик — обычная функция, принимающая параметры пути и (для
POST/PUT) разобранное тело запроса. Таблица ROUTES сопоставляет метод и
шаблон пути с обработчиком; сам HTTP-сервер — в server.py.

Контракт API не изменился: те же пути, те же JSON-ответы, ошибки
возвращаются как {"detail": "..."} с кодом 400, поэтому фронтенд работает
без правок.

Совместимость: Python 3.5+.
"""
import os
import re

from . import catalog, coverage, describe, i18n_en, docimport, knowledge, storage, xccdf_xml, oval_xml, validation, export_zip
from .oval_registry import TEST_TYPES, allowed_test_types
from .i18n_labels import all_labels, all_labels_en, ui_field_labels
from . import schemas as S


class ApiError(Exception):
    def __init__(self, status, detail):
        Exception.__init__(self, detail)
        self.status = status
        self.detail = detail


class BinaryResponse(object):
    """Ответ с произвольными байтами (используется для выгрузки ZIP)."""

    def __init__(self, data, content_type, filename=None):
        self.data = data
        self.content_type = content_type
        self.filename = filename


def _run(fn, *args, **kwargs):
    """Любая ошибка бизнес-логики превращается в ответ 400 с текстом."""
    try:
        return fn(*args, **kwargs)
    except ApiError:
        raise
    except Exception as e:  # noqa: BLE001 — сознательно ловим всё
        raise ApiError(400, str(e))


# ---------------------------------------------------------------- справочники

def get_version():
    """Версия сервера. Интерфейс сравнивает её со своей: расхождение означает,
    что файлы обновлены, а сервер не перезапущен."""
    from .server import VERSION
    return {"version": VERSION}


def get_oval_type_schemas():
    return {
        "types": TEST_TYPES,
        "allowed": allowed_test_types(),
        "labels": all_labels(),
        "labels_en": all_labels_en(),
        "ui_labels": ui_field_labels(),
    }


# -------------------------------------------------------------------- проекты

def list_projects():
    return storage.list_projects()


def create_project(body):
    b = S.parse("ProjectCreate", body)
    try:
        storage.create_project(b.project_id)
        xccdf_xml.create_benchmark(b.project_id, b.benchmark_id, b.xml_lang,
                                   b.status, b.title, b.description, b.version)
    except Exception as e:
        try:
            if storage.project_exists(b.project_id):
                storage.delete_project(b.project_id)
        except Exception:
            pass
        raise ApiError(400, str(e))
    return get_project(b.project_id)


def get_project(project_id):
    bench = _run(xccdf_xml.get_benchmark_dict, project_id)
    files = _run(storage.list_oval_files, project_id)
    return {"benchmark": bench, "oval_files": files,
            "has_coverage": coverage.load(project_id) is not None}


def delete_project(project_id):
    _run(storage.delete_project, project_id)
    return {"ok": True}


def update_benchmark(project_id, body):
    b = S.parse("BenchmarkUpdate", body)
    return _run(xccdf_xml.update_benchmark_meta, project_id, status=b.status,
                title=b.title, description=b.description, version=b.version)


# ------------------------------------------------------------------- профили

def add_profile(project_id, body):
    b = S.parse("ProfileCreate", body)
    return _run(xccdf_xml.add_profile, project_id, b.id, b.title, b.description, b.reference)


def update_profile(project_id, profile_id, body):
    b = S.parse("ProfileUpdate", body)
    return _run(xccdf_xml.update_profile, project_id, profile_id,
                title=b.title, description=b.description, reference=b.reference)


def delete_profile(project_id, profile_id):
    return _run(xccdf_xml.delete_profile, project_id, profile_id)


def set_select(project_id, profile_id, body):
    b = S.parse("SelectSet", body)
    return _run(xccdf_xml.set_select, project_id, profile_id, b.idref, b.selected)


def delete_select(project_id, profile_id, idref):
    return _run(xccdf_xml.delete_select, project_id, profile_id, idref)


# ------------------------------------------------------------------- правила

def _idents(raw):
    if raw is None:
        return None
    out = []
    for i in raw:
        if not isinstance(i, dict) or "system" not in i or "value" not in i:
            raise ApiError(400, "Каждый ident должен содержать поля system и value.")
        out.append({"system": str(i["system"]), "value": str(i["value"])})
    return out


def add_rule(project_id, body):
    b = S.parse("RuleCreate", body)
    return _run(xccdf_xml.add_rule, project_id, b.id, b.selected, b.title,
                b.description, _idents(b.idents), b.check_href, b.check_name)


def update_rule(project_id, rule_id, body):
    b = S.parse("RuleUpdate", body)
    return _run(xccdf_xml.update_rule, project_id, rule_id, selected=b.selected,
                title=b.title, description=b.description, idents=_idents(b.idents),
                check_href=b.check_href, check_name=b.check_name)


def delete_rule(project_id, rule_id):
    return _run(xccdf_xml.delete_rule, project_id, rule_id)


# ---------------------------------------------------------------- OVAL-файлы

def list_oval_files(project_id):
    names = _run(storage.list_oval_files, project_id)
    return [_run(oval_xml.get_oval_dict, project_id, n) for n in names]


def create_oval_file(project_id, body):
    b = S.parse("OvalFileCreate", body)
    return _run(oval_xml.create_oval_file, project_id, b.filename,
                b.product_name, b.product_version, b.schema_version)


def get_oval_file(project_id, filename):
    return _run(oval_xml.get_oval_dict, project_id, filename)


def delete_oval_file(project_id, filename):
    _run(storage.delete_oval_file, project_id, filename)
    return {"ok": True}


def _criteria(raw):
    if raw is None:
        return None
    out = []
    for c in raw:
        if not isinstance(c, dict) or not c.get("test_ref"):
            raise ApiError(400, "Каждый критерий должен ссылаться на тест (test_ref).")
        out.append({"test_ref": str(c["test_ref"]), "comment": c.get("comment")})
    return out


def add_definition(project_id, filename, body):
    b = S.parse("DefinitionCreate", body)
    return _run(oval_xml.add_definition, project_id, filename, b.id, b.version,
                b.klass, b.title, b.description, b.family,
                [str(p) for p in b.platforms], _criteria(b.criteria))


def update_definition(project_id, filename, def_id, body):
    b = S.parse("DefinitionUpdate", body)
    platforms = [str(p) for p in b.platforms] if b.platforms is not None else None
    return _run(oval_xml.update_definition, project_id, filename, def_id,
                version=b.version, klass=b.klass, title=b.title,
                description=b.description, family=b.family,
                platforms=platforms, criteria=_criteria(b.criteria))


def delete_definition(project_id, filename, def_id):
    return _run(oval_xml.delete_definition, project_id, filename, def_id)


def add_test(project_id, filename, body):
    b = S.parse("TestCreate", body)
    return _run(oval_xml.add_test, project_id, filename, b.test_type, b.id, b.version,
                b.object_ref, b.state_ref, b.check, b.check_existence, b.comment)


def update_test(project_id, filename, test_id, body):
    b = S.parse("TestCreate", body)
    return _run(oval_xml.update_test, project_id, filename, test_id, b.test_type,
                b.version, b.object_ref, b.state_ref, b.check, b.check_existence, b.comment)


def delete_test(project_id, filename, test_id):
    return _run(oval_xml.delete_test, project_id, filename, test_id)


def add_object(project_id, filename, body):
    b = S.parse("ObjectCreate", body)
    return _run(oval_xml.add_object, project_id, filename, b.test_type, b.id,
                b.version, b.fields, b.comment)


def update_object(project_id, filename, obj_id, body):
    b = S.parse("ObjectCreate", body)
    return _run(oval_xml.update_object, project_id, filename, obj_id, b.test_type,
                b.version, b.fields, b.comment)


def delete_object(project_id, filename, obj_id):
    return _run(oval_xml.delete_object, project_id, filename, obj_id)


def add_state(project_id, filename, body):
    b = S.parse("StateCreate", body)
    return _run(oval_xml.add_state, project_id, filename, b.test_type, b.id,
                b.version, b.fields, b.comment)


def update_state(project_id, filename, ste_id, body):
    b = S.parse("StateCreate", body)
    return _run(oval_xml.update_state, project_id, filename, ste_id, b.test_type,
                b.version, b.fields, b.comment)


def delete_state(project_id, filename, ste_id):
    return _run(oval_xml.delete_state, project_id, filename, ste_id)


def add_variable(project_id, filename, body):
    b = S.parse("VariableCreate", body)
    return _run(oval_xml.add_variable, project_id, filename, b.id, b.version,
                b.datatype, b.value, b.comment)


def update_variable(project_id, filename, var_id, body):
    b = S.parse("VariableCreate", body)
    return _run(oval_xml.update_variable, project_id, filename, var_id, b.version,
                b.datatype, b.value, b.comment)


def delete_variable(project_id, filename, var_id):
    return _run(oval_xml.delete_variable, project_id, filename, var_id)


# --------------------------------------------------- валидация, экспорт, импорт

def validate_project(project_id, query=None):
    issues = _run(validation.validate_project, project_id)
    if _lang(query) == "en":
        issues = [dict(i, message=validation.message_en(i.get("message", ""))) for i in issues]
    return {"valid": validation.is_valid(issues), "issues": issues}


def export_project(project_id):
    data = _run(export_zip.export_project_zip, project_id)
    return BinaryResponse(data, "application/zip", "%s.zip" % project_id)


def import_project(query, raw_body):
    """Тело запроса — сам ZIP-архив (application/zip), идентификатор
    проекта передаётся в строке запроса: ?project_id=..."""
    project_id = (query.get("project_id") or [""])[0]
    if not project_id:
        raise ApiError(400, "Не указан идентификатор проекта (project_id).")
    if not raw_body:
        raise ApiError(400, "Архив не передан.")
    return _run(export_zip.import_zip, project_id, raw_body)


def draft_from_analysis(body):
    """Черновик из уже выполненного разбора с решениями пользователя по пунктам.
    Документ повторно не загружается и не разбирается."""
    body = body or {}
    project_id = str(body.get("project_id", "")).strip()
    if not project_id:
        raise ApiError(400, "Не указан идентификатор проекта (project_id).")
    if storage.project_exists(project_id):
        raise ApiError(400, "Проект '%s' уже существует. Укажите другой идентификатор." % project_id)
    matches = body.get("matches")
    if not isinstance(matches, list) or not matches:
        raise ApiError(400, "Нет пунктов для черновика: сначала выполните разбор документа.")
    clean = []
    for m in matches:
        if not isinstance(m, dict) or not m.get("number"):
            raise ApiError(400, "Повреждены данные разбора.")
        decision = m.get("decision") or "auto"
        if decision not in ("auto", "exclude", "manual"):
            try:
                catalog.get_entry(str(decision))
            except catalog.CatalogError:
                raise ApiError(400, "Пункт %s: в каталоге нет проверки '%s'." % (m["number"], decision))
        cands = [c for c in (m.get("candidates") or []) if isinstance(c, dict) and c.get("entry_id")]
        for c in cands:
            try:
                catalog.get_entry(c["entry_id"])
            except catalog.CatalogError:
                raise ApiError(400, "Пункт %s: в каталоге нет проверки '%s'." % (m["number"], c["entry_id"]))
        clean.append({"number": str(m["number"])[:40], "text": str(m.get("text", ""))[:2000],
                      "section": str(m.get("section", ""))[:200], "confidence": str(m.get("confidence", "нет")),
                      "candidates": cands, "decision": decision,
                      "lang": "en" if m.get("lang") == "en" else "ru"})
    try:
        storage.validate_slug(project_id)
    except Exception as e:  # noqa: BLE001
        raise ApiError(400, str(e))
    title = str(body.get("title") or "Загруженный документ")[:200]
    lang = body.get("lang") if body.get("lang") in ("ru", "en") else None
    return _run(docimport.build_draft, project_id, clean, title,
                os_name=body.get("os") or None, min_confidence=body.get("min_confidence") or "средняя",
                lang=lang)


# ------------------------------------------------- отчёт о покрытии

def projects_overview():
    """Список проектов для боковой панели: название, черновик или нет,
    число правил, есть ли отчёт о покрытии. Повреждённый проект попадает в
    список с пометкой, а не роняет его целиком."""
    out = []
    for pid in storage.list_projects():
        item = {"id": pid, "title": pid, "draft": False, "rules": 0, "has_coverage": False, "error": None}
        try:
            b = xccdf_xml.get_benchmark_dict(pid)
            item.update({"title": b.get("title") or pid, "draft": b.get("status") == "draft",
                         "rules": len(b.get("rules", []))})
        except Exception as e:  # noqa: BLE001
            item["error"] = "Не удалось прочитать бенчмарк: %s" % e
        try:
            item["has_coverage"] = coverage.load(pid) is not None
        except Exception:  # noqa: BLE001
            pass
        out.append(item)
    return out


def copy_project(project_id, body):
    new_id = str((body or {}).get("new_id", "")).strip()
    _run(storage.copy_project, project_id, new_id)
    try:
        b = xccdf_xml.get_benchmark_dict(new_id)
        xccdf_xml.update_benchmark_meta(new_id, title="%s (копия)" % (b.get("title") or project_id))
    except Exception:  # noqa: BLE001 — копия без бенчмарка остаётся копией
        pass
    return {"id": new_id}


def rename_project(project_id, body):
    new_id = str((body or {}).get("new_id", "")).strip()
    _run(storage.rename_project, project_id, new_id)
    return {"id": new_id}


def _lang(query):
    """Язык интерфейса из ?lang=: "en" или "ru"."""
    return "en" if ((query or {}).get("lang") or ["ru"])[0] == "en" else "ru"


def get_rules_summary(project_id, query=None):
    """Что проверяет каждое правило — человеческим языком (?lang=en — по-английски)."""
    if not storage.project_exists(project_id):
        raise ApiError(404, "Проект '%s' не найден." % project_id)
    return _run(describe.describe_rules, project_id, _lang(query))


def get_coverage(project_id):
    if not storage.project_exists(project_id):
        raise ApiError(404, "Проект '%s' не найден." % project_id)
    rep = coverage.load(project_id)
    if rep is None:
        raise ApiError(404, "У проекта нет отчёта о покрытии: он создаётся при сборке черновика по документу.")
    return rep


def get_coverage_report(project_id, query=None):
    rep = get_coverage(project_id)
    lang = _lang(query) if (query or {}).get("lang") else rep.get("lang", "ru")
    return BinaryResponse(coverage.render_html(project_id, rep, lang), "text/html; charset=utf-8",
                          "coverage-%s.html" % project_id)


# ------------------------------------------- каталог проверок и база знаний

def get_catalog(query=None, raw_body=None):
    """Записи каталога типовых проверок; ?os=... сужает список до
    применимых к конкретной системе."""
    os_name = (query or {}).get("os", [None])[0]
    entries = catalog.entries_for_os(os_name) if os_name else catalog.load_catalog()
    out = []
    for raw in entries:
        e = catalog.with_en(raw)
        item = {
            "id": e.get("id"), "title": e.get("title"), "category": e.get("category"),
            "description": e.get("description"), "manual": bool(e.get("manual")),
            "pack": e.get("pack"), "params": e.get("params", []),
            "family": e.get("platforms", {}).get("family", "unix"),
            "refs": [dict(r, value_en=i18n_en.translate(r.get("value")) or r.get("value"),
                          system_en=i18n_en.translate(r.get("system")) or r.get("system"))
                     for r in e.get("refs", [])],
            "remediation": e.get("remediation"),
        }
        # Английские версии текстов: интерфейс на английском показывает их,
        # а при отсутствии перевода — русский текст.
        for f in ("title", "category", "description", "remediation"):
            if e.get(f + "_en"):
                item[f + "_en"] = e[f + "_en"]
        out.append(item)
    return {
        "categories": catalog.categories(),
        "categories_en": {c: i18n_en.translate(c) or c for c in catalog.categories()},
        "entries": out,
    }


def get_knowledge(query=None, raw_body=None):
    """Состав базы знаний: темы требований и семейства документов."""
    links = knowledge.catalog_links()
    entries = {e["id"]: e for e in catalog.load_catalog()}
    families = knowledge.document_families()
    themes = sorted({t for c in knowledge.load_concepts() for t in c.get("themes", [])})
    return {
        "families": families,
        # Названия документов и разделов на английском: ключи фильтров
        # остаются русскими, интерфейс подставляет только подпись.
        "families_en": {f: i18n_en.translate(f) or f for f in families},
        "themes_en": {t: i18n_en.translate(t) or t for t in themes},
        "concepts": [{"id": c["id"], "title": c.get("title"),
                      "title_en": c.get("title_en") or i18n_en.translate(c.get("title")),
                      "themes": c.get("themes", []),
                      "ru": c.get("ru", []), "en": c.get("en", []),
                      "user_created": c.get("user_created", False),
                      "user_modified": c.get("user_modified", False),
                      "user_ru": c.get("user_ru", []), "user_en": c.get("user_en", []),
                      "hidden_ru": c.get("hidden_ru", []), "hidden_en": c.get("hidden_en", []),
                      "doc_hints": [dict(h, family_en=i18n_en.translate(h.get("family")) or h.get("family"),
                                         ref_en=i18n_en.translate(h.get("ref")) or h.get("ref"))
                                    for h in c.get("doc_hints", [])],
                      # Технические проверки и организационные меры считаются
                      # отдельно: раньше мера шла в общий счёт «проверок».
                      "checks": [eid for eid, cids in links.items()
                                 if c["id"] in cids and eid in entries and not entries[eid].get("manual")],
                      "measures": [eid for eid, cids in links.items()
                                   if c["id"] in cids and eid in entries and entries[eid].get("manual")]}
                     for c in knowledge.load_concepts()],
        "synonyms": knowledge.synonym_entries(),
    }


# ------------------------------------------ загрузка нормативного документа

def analyze_document(query, raw_body):
    """Разбор документа без создания проекта: пункты, темы требований и
    кандидаты проверок. Позволяет посмотреть, что получится, до сборки."""
    filename = (query.get("filename") or [""])[0]
    os_name = (query.get("os") or [None])[0]
    pack = (query.get("pack") or [None])[0]
    if not raw_body:
        raise ApiError(400, "Документ не передан.")
    try:
        paragraphs = docimport.read_document_bytes(raw_body, filename)
    except docimport.ImportError_ as e:
        raise ApiError(400, str(e))
    items = docimport.extract_items(paragraphs)
    if not items:
        raise ApiError(400, "В документе не найдено пронумерованных пунктов. "
                            "Проверьте, что требования оформлены нумерованным списком (1.1, 1.2 и так далее).")
    # Документ, по которому в каталоге есть пакет (например, Рекомендации
    # ФСТЭК по Linux), узнаётся по заголовку: тогда номера его пунктов
    # сопоставляются с пунктами пакета.
    ref_pack = catalog.detect_pack(" ".join(paragraphs[:40]))
    matches = docimport.match_items(items, os_name=os_name, pack=pack, ref_pack=ref_pack)
    return {
        "disclaimer": docimport.DISCLAIMER,
        "disclaimer_en": docimport.DISCLAIMER_EN,
        "lang": docimport.document_lang(items),
        "filename": filename,
        "items_total": len(items),
        "detected_pack": ref_pack,
        "matches": matches,
    }


def draft_from_document(query, raw_body):
    """Разбор документа и сборка чернового профиля."""
    filename = (query.get("filename") or [""])[0]
    project_id = (query.get("project_id") or [""])[0]
    os_name = (query.get("os") or [None])[0]
    pack = (query.get("pack") or [None])[0]
    title = (query.get("title") or [filename or "Загруженный документ"])[0]
    min_conf = (query.get("min_confidence") or ["средняя"])[0]
    if not project_id:
        raise ApiError(400, "Не указан идентификатор проекта (project_id).")
    if storage.project_exists(project_id):
        raise ApiError(400, "Проект '%s' уже существует. Укажите другой идентификатор." % project_id)
    if not raw_body:
        raise ApiError(400, "Документ не передан.")
    try:
        paragraphs = docimport.read_document_bytes(raw_body, filename)
    except docimport.ImportError_ as e:
        raise ApiError(400, str(e))
    items = docimport.extract_items(paragraphs)
    if not items:
        raise ApiError(400, "В документе не найдено пронумерованных пунктов.")
    ref_pack = catalog.detect_pack(" ".join(paragraphs[:40]))
    matches = docimport.match_items(items, os_name=os_name, pack=pack, ref_pack=ref_pack)
    return _run(docimport.build_draft, project_id, matches, title,
                os_name=os_name, min_confidence=min_conf)


# ------------------------------------------------ редактор базы знаний

def _check_ids():
    return {e["id"] for e in catalog.load_catalog()}


def _kb(fn, *args):
    try:
        return fn(*args)
    except knowledge.KnowledgeError as e:
        raise ApiError(400, str(e))


def update_concept(concept_id, body):
    """Сохранить тему: название, формулировки, ссылки на документы, проверки."""
    return _kb(knowledge.set_concept, concept_id, body or {}, _check_ids())


def create_concept(body):
    return _kb(knowledge.create_concept, body or {}, _check_ids())


def reset_concept(concept_id):
    """Поставляемая тема — к исходному виду; своя тема — удалить."""
    return _kb(knowledge.reset_concept, concept_id)


def update_synonyms(body):
    return {"synonyms": _kb(knowledge.set_synonyms, (body or {}).get("pairs", []))}


def test_phrase(body):
    """Проверка формулировки: какую тему и проверку сервис найдёт для этого
    текста. Нужна, чтобы сразу увидеть, сработала ли добавленная формулировка."""
    text = str((body or {}).get("text", "")).strip()
    if not text:
        raise ApiError(400, "Введите текст требования.")
    if len(text) > 2000:
        raise ApiError(400, "Слишком длинный текст: проверяйте по одному пункту.")
    item = {"number": "—", "text": text, "lang": "ru", "tokens": docimport._tokens(text), "section": ""}
    m = docimport.match_items([item])[0]
    return {"concepts": m["concepts"][:5], "candidates": m["candidates"][:3], "confidence": m["confidence"],
            # Если текст слишком короткий для распознавания пункта (одно-два
            # слова), полезно хотя бы показать темы, где эти слова встречаются.
            "search": knowledge.search_concepts(text) if not m["concepts"] else []}


def export_user_knowledge():
    """Правки базы знаний одним файлом — для переноса на другой сервер."""
    return knowledge.user_layer()


def import_user_knowledge(body):
    body = body or {}
    mode = body.get("mode", "merge")
    if mode not in ("merge", "replace"):
        raise ApiError(400, "Режим импорта: merge или replace.")
    return _kb(knowledge.import_layer, body.get("data"), _check_ids(), mode)


# ------------------------------------- проверки из каталога

class _ProjectSnapshot:
    """Снимок файлов проекта для отката.

    Запись каталога разворачивается в несколько шагов: переменные, объект,
    состояние, тест, определение, правило. Если шаг посередине сорвался,
    в проекте остались бы осиротевшие элементы — поэтому при ошибке все
    файлы проекта возвращаются к прежнему виду."""

    def __init__(self, project_id):
        self.root = storage.project_path(project_id)
        self.files = {}
        for name in os.listdir(str(self.root)):
            full = os.path.join(str(self.root), name)
            if os.path.isfile(full):
                with open(full, "rb") as f:
                    self.files[name] = f.read()

    def restore(self):
        for name in os.listdir(str(self.root)):
            full = os.path.join(str(self.root), name)
            if os.path.isfile(full) and name not in self.files:
                os.remove(full)               # файлы, созданные по ходу (новый OVAL-файл)
        for name, data in self.files.items():
            with open(os.path.join(str(self.root), name), "wb") as f:
                f.write(data)


def add_catalog_check(project_id, body):
    """Добавить в проект проверку из каталога: вся цепочка элементов OVAL
    и правило XCCDF одним действием."""
    body = body or {}
    if not storage.project_exists(project_id):
        raise ApiError(404, "Проект '%s' не найден." % project_id)
    try:
        entry = catalog.get_entry(str(body.get("entry_id", "")))
    except catalog.CatalogError:
        entry = None
    if entry is None:
        raise ApiError(400, "В каталоге нет проверки '%s'." % body.get("entry_id"))
    if entry.get("manual"):
        raise ApiError(400, "«%s» — организационная мера: техническими средствами она не проверяется, "
                            "и правило для неё не создаётся." % entry.get("title"))
    if not storage.benchmark_file(project_id).exists():
        raise ApiError(400, "Сначала создайте бенчмарк — шаг 1 мастера.")

    snap = _ProjectSnapshot(project_id)
    try:
        files = storage.list_oval_files(project_id)
        filename = body.get("filename") or (files[0] if files else None)
        if not filename:
            filename = "checks-oval.xml"
            oval_xml.create_oval_file(project_id, filename, "Custom", "1.0", "5.11.2")
        params = body.get("params") or None
        result = catalog.apply_entry(
            project_id, filename, entry, params=params, os_name=body.get("os") or None,
            ident_system=(body.get("ident_system") or None), ident_value=(body.get("ident_value") or None))
        if body.get("add_to_profiles", True):
            rid = result["created"]["rules"][0]
            for prof in xccdf_xml.get_benchmark_dict(project_id)["profiles"]:
                xccdf_xml.set_select(project_id, prof["id"], rid, True)
    except ApiError:
        snap.restore()
        raise
    except Exception as e:  # noqa: BLE001
        snap.restore()
        raise ApiError(400, "Проверка не добавлена, проект возвращён к прежнему виду: %s" % e)
    result["filename"] = filename
    return result


# ------------------------------------------------------------ таблица маршрутов

_SEG = r"([^/]+)"


def _route(method, pattern, handler, kind="json"):
    """kind: 'none' — без тела, 'query' — без тела, с параметрами строки запроса,
    'json' — тело JSON, 'raw' — сырое тело + query."""
    regex = "^/api" + re.sub(r"\{[a-z_]+\}", _SEG, pattern) + "$"
    return (method, re.compile(regex), handler, kind)


ROUTES = [
    _route("GET", "/version", get_version, "none"),
    _route("GET", "/oval-type-schemas", get_oval_type_schemas, "none"),
    _route("GET", "/catalog", get_catalog, "raw"),
    _route("POST", "/projects/{p}/catalog-checks", add_catalog_check),
    _route("POST", "/projects/{p}/copy", copy_project),
    _route("POST", "/projects/{p}/rename", rename_project),
    _route("GET", "/knowledge", get_knowledge, "raw"),
    _route("POST", "/knowledge/test", test_phrase),
    _route("GET", "/knowledge/user", export_user_knowledge, "none"),
    _route("POST", "/knowledge/user", import_user_knowledge),
    _route("PUT", "/knowledge/synonyms", update_synonyms),
    _route("POST", "/knowledge/concepts", create_concept),
    _route("PUT", "/knowledge/concepts/{x}", update_concept),
    _route("DELETE", "/knowledge/concepts/{x}", reset_concept, "none"),
    _route("POST", "/documents/analyze", analyze_document, "raw"),
    _route("POST", "/documents/draft", draft_from_document, "raw"),
    _route("POST", "/documents/draft-from-analysis", draft_from_analysis),
    _route("GET", "/projects", list_projects, "none"),
    _route("GET", "/projects/overview", projects_overview, "none"),
    _route("POST", "/projects/import", import_project, "raw"),
    _route("POST", "/projects", create_project),
    _route("GET", "/projects/{p}", get_project, "none"),
    _route("GET", "/projects/{p}/coverage", get_coverage, "none"),
    _route("GET", "/projects/{p}/rules/summary", get_rules_summary, "query"),
    _route("GET", "/projects/{p}/coverage/report", get_coverage_report, "query"),
    _route("DELETE", "/projects/{p}", delete_project, "none"),
    _route("PUT", "/projects/{p}/benchmark", update_benchmark),
    _route("POST", "/projects/{p}/profiles", add_profile),
    _route("PUT", "/projects/{p}/profiles/{x}/select", set_select),
    _route("DELETE", "/projects/{p}/profiles/{x}/select/{y}", delete_select, "none"),
    _route("PUT", "/projects/{p}/profiles/{x}", update_profile),
    _route("DELETE", "/projects/{p}/profiles/{x}", delete_profile, "none"),
    _route("POST", "/projects/{p}/rules", add_rule),
    _route("PUT", "/projects/{p}/rules/{x}", update_rule),
    _route("DELETE", "/projects/{p}/rules/{x}", delete_rule, "none"),
    _route("GET", "/projects/{p}/oval-files", list_oval_files, "none"),
    _route("POST", "/projects/{p}/oval-files", create_oval_file),
    _route("POST", "/projects/{p}/oval-files/{f}/definitions", add_definition),
    _route("PUT", "/projects/{p}/oval-files/{f}/definitions/{x}", update_definition),
    _route("DELETE", "/projects/{p}/oval-files/{f}/definitions/{x}", delete_definition, "none"),
    _route("POST", "/projects/{p}/oval-files/{f}/tests", add_test),
    _route("PUT", "/projects/{p}/oval-files/{f}/tests/{x}", update_test),
    _route("DELETE", "/projects/{p}/oval-files/{f}/tests/{x}", delete_test, "none"),
    _route("POST", "/projects/{p}/oval-files/{f}/objects", add_object),
    _route("PUT", "/projects/{p}/oval-files/{f}/objects/{x}", update_object),
    _route("DELETE", "/projects/{p}/oval-files/{f}/objects/{x}", delete_object, "none"),
    _route("POST", "/projects/{p}/oval-files/{f}/states", add_state),
    _route("PUT", "/projects/{p}/oval-files/{f}/states/{x}", update_state),
    _route("DELETE", "/projects/{p}/oval-files/{f}/states/{x}", delete_state, "none"),
    _route("POST", "/projects/{p}/oval-files/{f}/variables", add_variable),
    _route("PUT", "/projects/{p}/oval-files/{f}/variables/{x}", update_variable),
    _route("DELETE", "/projects/{p}/oval-files/{f}/variables/{x}", delete_variable, "none"),
    _route("GET", "/projects/{p}/oval-files/{f}", get_oval_file, "none"),
    _route("DELETE", "/projects/{p}/oval-files/{f}", delete_oval_file, "none"),
    _route("GET", "/projects/{p}/validate", validate_project, "query"),
    _route("GET", "/projects/{p}/export", export_project, "none"),
]
