"""
Двуязычные (русский/английский) подписи для служебных перечислений стандарта
XCCDF/OVAL. Сами значения (ключи словарей) остаются английскими — это часть
стандарта и записываются в XML как есть; словари дают только текст для
интерфейса (пункт требований: подписи полей дублируются на русском и
английском языке через xml:lang).
"""

STATUS_LABELS = {
    "draft": "черновик",
    "interim": "промежуточный",
    "accepted": "принят",
    "deprecated": "устарел",
    "incomplete": "неполный",
}
STATUS_LABELS_EN = {
    "draft": "draft",
    "interim": "interim",
    "accepted": "accepted",
    "deprecated": "deprecated",
    "incomplete": "incomplete",
}

CLASS_LABELS = {
    "compliance": "соответствие требованиям",
    "inventory": "инвентаризация",
    "patch": "наличие патча",
    "vulnerability": "уязвимость",
    "miscellaneous": "прочее",
}
CLASS_LABELS_EN = {
    "compliance": "compliance",
    "inventory": "inventory",
    "patch": "patch",
    "vulnerability": "vulnerability",
    "miscellaneous": "miscellaneous",
}

# affected/@family — закрытое перечисление схемы OVAL (FamilyEnumeration).
# Значений "linux"/"independent" в нём нет: все Linux-дистрибутивы
# указываются как "unix", а конкретный дистрибутив — в <platform>.
FAMILY_LABELS = {
    "windows": "Windows",
    "unix": "Linux (Astra Linux, РЕД ОС, ALT Linux, Ubuntu, Debian)",
}
FAMILY_LABELS_EN = {
    "windows": "Windows",
    "unix": "Linux (Astra Linux, RED OS, ALT Linux, Ubuntu, Debian)",
}

OPERATION_LABELS = {
    "equals": "равно",
    "not equal": "не равно",
    "greater than": "больше",
    "greater than or equal": "больше или равно",
    "less than": "меньше",
    "less than or equal": "меньше или равно",
    "pattern match": "соответствует регулярному выражению",
}
OPERATION_LABELS_EN = {
    "equals": "equals",
    "not equal": "not equal",
    "greater than": "greater than",
    "greater than or equal": "greater than or equal",
    "less than": "less than",
    "less than or equal": "less than or equal",
    "pattern match": "pattern match",
}

DATATYPE_LABELS = {
    "string": "строка",
    "int": "целое число",
    "boolean": "логическое (true/false)",
    "version": "версия",
    "float": "дробное число",
    "evr_string": "EVR-строка (epoch:version-release)",
}
DATATYPE_LABELS_EN = {
    "string": "string",
    "int": "integer",
    "boolean": "boolean (true/false)",
    "version": "version",
    "float": "float",
    "evr_string": "EVR string (epoch:version-release)",
}

CHECK_LABELS = {
    "all": "все",
    "at least one": "хотя бы один",
    "none satisfy": "ни один не соответствует",
    "none exist": "ни один не существует",
    "only one": "ровно один",
}
CHECK_LABELS_EN = {
    "all": "all",
    "at least one": "at least one",
    "none satisfy": "none satisfy",
    "none exist": "none exist",
    "only one": "only one",
}

CHECK_EXISTENCE_LABELS = {
    "at_least_one_exists": "существует хотя бы один",
    "all_exist": "существуют все",
    "any_exist": "существует любой",
    "none_exist": "не существует ни одного",
    "only_one_exists": "существует ровно один",
}
CHECK_EXISTENCE_LABELS_EN = {
    "at_least_one_exists": "at least one exists",
    "all_exist": "all exist",
    "any_exist": "any exist",
    "none_exist": "none exist",
    "only_one_exists": "only one exists",
}


def all_labels():
    """Русские подписи перечислений (обратная совместимость)."""
    return {
        "status": STATUS_LABELS,
        "klass": CLASS_LABELS,
        "family": FAMILY_LABELS,
        "operation": OPERATION_LABELS,
        "datatype": DATATYPE_LABELS,
        "check": CHECK_LABELS,
        "check_existence": CHECK_EXISTENCE_LABELS,
    }


def all_labels_en():
    """Английские подписи перечислений (для дублирования по xml:lang)."""
    return {
        "status": STATUS_LABELS_EN,
        "klass": CLASS_LABELS_EN,
        "family": FAMILY_LABELS_EN,
        "operation": OPERATION_LABELS_EN,
        "datatype": DATATYPE_LABELS_EN,
        "check": CHECK_LABELS_EN,
        "check_existence": CHECK_EXISTENCE_LABELS_EN,
    }


# ---------------------------------------------------------------------------
# Подписи полей статического интерфейса (не связанных с OVAL-реестром типов):
# заголовки форм проекта/бенчмарка/профилей/правил/OVAL-файлов и т.п.
# Ключ — техническое имя поля, используемое в разметке (data-i18n-key).
# ---------------------------------------------------------------------------
UI_FIELD_LABELS = {
    "id": {"ru": "идентификатор", "en": "id"},
    "title": {"ru": "заголовок", "en": "title"},
    "description": {"ru": "описание", "en": "description"},
    "version": {"ru": "версия", "en": "version"},
    "status": {"ru": "статус", "en": "status"},
    "class": {"ru": "класс", "en": "class"},
    "family": {"ru": "платформа", "en": "family"},
    "check": {"ru": "условие проверки", "en": "check"},
    "check_existence": {"ru": "условие существования", "en": "check existence"},
    "comment": {"ru": "комментарий", "en": "comment"},
    "criteria": {"ru": "критерии", "en": "criteria"},
    "datatype": {"ru": "тип данных", "en": "datatype"},
    "object_ref": {"ru": "объект", "en": "object"},
    "state_ref": {"ru": "состояние", "en": "state"},
    "reference": {"ru": "ссылка на источник", "en": "reference"},
    "ident": {"ru": "идентификатор требования", "en": "ident"},
    "product_name": {"ru": "название продукта", "en": "product name"},
    "product_version": {"ru": "версия продукта", "en": "product version"},
    "schema_version": {"ru": "версия схемы OVAL", "en": "schema version"},
    "platforms": {"ru": "платформы (через запятую)", "en": "platforms (comma-separated)"},
    "xml_lang": {"ru": "язык (xml:lang)", "en": "language (xml:lang)"},
    "benchmark_id": {"ru": "идентификатор бенчмарка", "en": "benchmark id"},
    "check_content_href": {"ru": "OVAL-файл", "en": "OVAL file"},
    "check_content_name": {"ru": "определение OVAL", "en": "OVAL definition"},
    "test_type": {"ru": "тип проверки", "en": "check type"},
    "value": {"ru": "значение", "en": "value"},
    "file": {"ru": "файл", "en": "file"},
    "project_id_new": {"ru": "идентификатор нового проекта", "en": "new project id"},
    "project_id_folder": {"ru": "идентификатор проекта (папка)", "en": "project id (folder)"},
    "filename": {"ru": "имя файла", "en": "filename"},
    "selected": {"ru": "выбрано по умолчанию", "en": "selected by default"},
    "id_selects": {"ru": "правила профиля", "en": "profile rule selection"},
    "test_ref": {"ru": "тест", "en": "test"},
}


def ui_field_labels():
    return UI_FIELD_LABELS
