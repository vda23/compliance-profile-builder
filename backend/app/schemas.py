# -*- coding: utf-8 -*-
"""
Проверка тел запросов API без внешних библиотек (раньше — pydantic).

Каждая модель описана списком полей: (имя, тип, обязательно, по умолчанию).
Функция parse() проверяет тело запроса и возвращает объект с доступом к
полям через точку — так код обработчиков не отличается от прежнего.

Совместимость: Python 3.5+.
"""
import types

REQ = object()   # маркер «поле обязательно»

_STR, _BOOL, _LIST, _DICT = "str", "bool", "list", "dict"

MODELS = {
    "ProjectCreate": [
        ("project_id", _STR, REQ), ("benchmark_id", _STR, REQ),
        ("xml_lang", _STR, "ru-RU"), ("status", _STR, "accepted"),
        ("title", _STR, REQ), ("description", _STR, REQ), ("version", _STR, "1.0"),
    ],
    "BenchmarkUpdate": [
        ("status", _STR, None), ("title", _STR, None),
        ("description", _STR, None), ("version", _STR, None),
    ],
    "ProfileCreate": [
        ("id", _STR, REQ), ("title", _STR, REQ), ("description", _STR, REQ),
        ("reference", _STR, None),
    ],
    "ProfileUpdate": [
        ("title", _STR, None), ("description", _STR, None), ("reference", _STR, None),
    ],
    "SelectSet": [("idref", _STR, REQ), ("selected", _BOOL, True)],
    "RuleCreate": [
        ("id", _STR, REQ), ("selected", _BOOL, False),
        ("title", _STR, REQ), ("description", _STR, REQ),
        ("idents", _LIST, []), ("check_href", _STR, REQ), ("check_name", _STR, REQ),
    ],
    "RuleUpdate": [
        ("selected", _BOOL, None), ("title", _STR, None), ("description", _STR, None),
        ("idents", _LIST, None), ("check_href", _STR, None), ("check_name", _STR, None),
    ],
    "OvalFileCreate": [
        ("filename", _STR, REQ), ("product_name", _STR, "Custom"),
        ("product_version", _STR, "1.0"), ("schema_version", _STR, "5.11.2"),
    ],
    "DefinitionCreate": [
        ("id", _STR, REQ), ("version", _STR, "1"), ("class", _STR, "compliance"),
        ("title", _STR, REQ), ("description", _STR, REQ),
        ("family", _STR, None), ("platforms", _LIST, []), ("criteria", _LIST, []),
    ],
    "DefinitionUpdate": [
        ("version", _STR, None), ("class", _STR, None), ("title", _STR, None),
        ("description", _STR, None), ("family", _STR, None),
        ("platforms", _LIST, None), ("criteria", _LIST, None),
    ],
    "TestCreate": [
        ("test_type", _STR, REQ), ("id", _STR, REQ), ("version", _STR, "1"),
        ("object_ref", _STR, REQ), ("state_ref", _STR, None),
        ("check", _STR, "all"), ("check_existence", _STR, "at_least_one_exists"),
        ("comment", _STR, None),
    ],
    "ObjectCreate": [
        ("test_type", _STR, REQ), ("id", _STR, REQ), ("version", _STR, "1"),
        ("fields", _DICT, {}), ("comment", _STR, None),
    ],
    "StateCreate": [
        ("test_type", _STR, REQ), ("id", _STR, REQ), ("version", _STR, "1"),
        ("fields", _DICT, {}), ("comment", _STR, None),
    ],
    "VariableCreate": [
        ("id", _STR, REQ), ("version", _STR, "1"), ("datatype", _STR, "int"),
        ("value", _STR, REQ), ("comment", _STR, None),
    ],
}


class ValidationError(Exception):
    pass


def _coerce(name, kind, value):
    if value is None:
        return None
    if kind == _STR:
        if isinstance(value, bool) or isinstance(value, (dict, list)):
            raise ValidationError("Поле '%s' должно быть строкой." % name)
        return str(value)
    if kind == _BOOL:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in ("true", "false"):
            return value.lower() == "true"
        raise ValidationError("Поле '%s' должно быть true/false." % name)
    if kind == _LIST:
        if not isinstance(value, list):
            raise ValidationError("Поле '%s' должно быть списком." % name)
        return value
    if kind == _DICT:
        if not isinstance(value, dict):
            raise ValidationError("Поле '%s' должно быть объектом." % name)
        return value
    return value


def parse(model, body):
    """Проверяет тело запроса по описанию модели и возвращает объект.
    Поле 'class' (зарезервированное слово Python) доступно как .klass."""
    if not isinstance(body, dict):
        raise ValidationError("Тело запроса должно быть JSON-объектом.")
    result = {}
    for name, kind, default in MODELS[model]:
        if name in body and body[name] is not None:
            value = _coerce(name, kind, body[name])
        elif default is REQ:
            raise ValidationError("Не заполнено обязательное поле '%s'." % name)
        else:
            value = list(default) if isinstance(default, list) else (
                dict(default) if isinstance(default, dict) else default)
        result["klass" if name == "class" else name] = value
    return types.SimpleNamespace(**result)
