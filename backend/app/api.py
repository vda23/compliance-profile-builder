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
import re

from . import catalog, docimport, knowledge, storage, xccdf_xml, oval_xml, validation, export_zip
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
    return {"benchmark": bench, "oval_files": files}


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

def validate_project(project_id):
    issues = _run(validation.validate_project, project_id)
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


# ------------------------------------------- каталог проверок и база знаний

def get_catalog(query=None, raw_body=None):
    """Записи каталога типовых проверок; ?os=... сужает список до
    применимых к конкретной системе."""
    os_name = (query or {}).get("os", [None])[0]
    entries = catalog.entries_for_os(os_name) if os_name else catalog.load_catalog()
    return {
        "categories": catalog.categories(),
        "entries": [{
            "id": e.get("id"), "title": e.get("title"), "category": e.get("category"),
            "description": e.get("description"), "manual": bool(e.get("manual")),
            "pack": e.get("pack"), "params": e.get("params", []),
            "refs": e.get("refs", []), "remediation": e.get("remediation"),
        } for e in entries],
    }


def get_knowledge(query=None, raw_body=None):
    """Состав базы знаний: темы требований и семейства документов."""
    return {
        "families": knowledge.document_families(),
        "concepts": [{"id": c["id"], "title": c.get("title"),
                      "themes": c.get("themes", []),
                      "ru": c.get("ru", []), "en": c.get("en", []),
                      "doc_hints": c.get("doc_hints", []),
                      "checks": [eid for eid, cids in knowledge.catalog_links().items() if c["id"] in cids]}
                     for c in knowledge.load_concepts()],
        "synonyms": knowledge.synonym_pairs(),
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
    matches = docimport.match_items(items, os_name=os_name, pack=pack)
    return {
        "disclaimer": docimport.DISCLAIMER,
        "filename": filename,
        "items_total": len(items),
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
    matches = docimport.match_items(items, os_name=os_name, pack=pack)
    return _run(docimport.build_draft, project_id, matches, title,
                os_name=os_name, min_confidence=min_conf)


# ------------------------------------------------------------ таблица маршрутов

_SEG = r"([^/]+)"


def _route(method, pattern, handler, kind="json"):
    """kind: 'none' — без тела, 'json' — тело JSON, 'raw' — сырое тело + query."""
    regex = "^/api" + re.sub(r"\{[a-z_]+\}", _SEG, pattern) + "$"
    return (method, re.compile(regex), handler, kind)


ROUTES = [
    _route("GET", "/oval-type-schemas", get_oval_type_schemas, "none"),
    _route("GET", "/catalog", get_catalog, "raw"),
    _route("GET", "/knowledge", get_knowledge, "raw"),
    _route("POST", "/documents/analyze", analyze_document, "raw"),
    _route("POST", "/documents/draft", draft_from_document, "raw"),
    _route("GET", "/projects", list_projects, "none"),
    _route("POST", "/projects/import", import_project, "raw"),
    _route("POST", "/projects", create_project),
    _route("GET", "/projects/{p}", get_project, "none"),
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
    _route("GET", "/projects/{p}/validate", validate_project, "none"),
    _route("GET", "/projects/{p}/export", export_project, "none"),
]
