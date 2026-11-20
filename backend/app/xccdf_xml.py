"""
CRUD-операции над XCCDF-файлом проекта (benchmark-xccdf.xml).
Каждая операция читает файл, изменяет lxml-дерево, сохраняет обратно.
Источник истины — сам XML-файл, промежуточное состояние нигде не кешируется.
"""
from . import xmlcompat as etree
from . import storage
from .namespaces import XCCDF_NS, XSI_NS, XML_NS, XCCDF_NSMAP, CHECK_SYSTEM_OVAL, write_xml

X = "{{{}}}".format(XCCDF_NS)
XML = "{{{}}}".format(XML_NS)


class XccdfError(Exception):
    pass


def _text_with_lang(parent, tag, text, lang):
    """Создаёт текстовый элемент (title/description).

    ВАЖНО: атрибут xml:lang на самих title/description НЕ выставляется —
    в эталонном комплекте, подтверждённом разработчиком продукта, язык
    указан только один раз, на корневом Benchmark/@xml:lang, а вложенные
    title/description идут без него. Текст требований показывает вариант
    с xml:lang на каждом элементе, но приоритет отдан реально принятому
    продуктом файлу: генерируемые профили должны быть идентичны ему.
    Параметр lang сохранён в сигнатуре для обратной совместимости вызовов.
    """
    el = etree.SubElement(parent, "{}{}".format(X, tag))
    el.text = text
    return el


def _get_localized_text(el):
    if el is None:
        return None, None
    return (el.text or ""), el.get("{}lang".format(XML))


# Схема XCCDF 1.1 задаёт строгий порядок дочерних элементов Benchmark: все
# Profile обязаны идти раньше всех Rule/Group/Value. Инструмент позволяет
# создавать профили и правила в любом порядке (например, сначала все
# правила, потом сгруппировать их в профиль) — но в файл они должны попасть
# в правильном порядке независимо от порядка создания в интерфейсе, иначе
# строгий валидатор XCCDF отклонит документ целиком (обычно без вразумительного
# сообщения об ошибке).
_PROFILE_RULE_PRIORITY = {"Profile": 0, "Rule": 1, "Group": 1, "Value": 1}


def _insert_ordered(root, new_el):
    new_tag = etree.QName(new_el).localname
    new_prio = _PROFILE_RULE_PRIORITY.get(new_tag, 1)
    for i, child in enumerate(root):
        if not isinstance(child.tag, str):
            continue
        child_tag = etree.QName(child).localname
        if child_tag not in _PROFILE_RULE_PRIORITY:
            continue
        if _PROFILE_RULE_PRIORITY[child_tag] > new_prio:
            root.insert(i, new_el)
            return
    root.append(new_el)


def create_benchmark(project_id, benchmark_id, xml_lang, status, title, description, version):
    path = storage.benchmark_file(project_id)
    if path.exists():
        raise XccdfError("benchmark-xccdf.xml уже существует в этом проекте.")

    root = etree.Element("{}Benchmark".format(X), nsmap=XCCDF_NSMAP)
    root.set("id", benchmark_id)
    root.set("{}lang".format(XML), xml_lang)
    root.set("resolved", "0")
    root.set("style", "SCAP_1.1")

    etree.SubElement(root, "{}status".format(X)).text = status
    _text_with_lang(root, "title", title, xml_lang)
    _text_with_lang(root, "description", description, xml_lang)
    etree.SubElement(root, "{}version".format(X)).text = version

    tree = etree.ElementTree(root)
    write_xml(tree, path)
    return load_tree(project_id)


def load_tree(project_id):
    path = storage.benchmark_file(project_id)
    if not path.exists():
        raise XccdfError("У проекта '{}' отсутствует benchmark-xccdf.xml.".format(project_id))
    return etree.parse(str(path))


def save_tree(project_id, tree):
    path = storage.benchmark_file(project_id)
    write_xml(tree, path)


def get_benchmark_dict(project_id):
    tree = load_tree(project_id)
    root = tree.getroot()

    title_text, title_lang = _get_localized_text(root.find("{}title".format(X)))
    desc_text, desc_lang = _get_localized_text(root.find("{}description".format(X)))
    status_el = root.find("{}status".format(X))
    version_el = root.find("{}version".format(X))

    profiles = []
    for prof in root.findall("{}Profile".format(X)):
        profiles.append(_profile_to_dict(prof))

    rules = []
    for rule in root.findall("{}Rule".format(X)):
        rules.append(_rule_to_dict(rule))

    return {
        "id": root.get("id"),
        "xml_lang": root.get("{}lang".format(XML)),
        "status": status_el.text if status_el is not None else None,
        "title": title_text,
        "title_lang": title_lang,
        "description": desc_text,
        "description_lang": desc_lang,
        "version": version_el.text if version_el is not None else None,
        "profiles": profiles,
        "rules": rules,
    }


def update_benchmark_meta(project_id, status=None, title=None, description=None, version=None):
    tree = load_tree(project_id)
    root = tree.getroot()

    if status is not None:
        root.find("{}status".format(X)).text = status
    if title is not None:
        root.find("{}title".format(X)).text = title
    if description is not None:
        root.find("{}description".format(X)).text = description
    if version is not None:
        root.find("{}version".format(X)).text = version

    save_tree(project_id, tree)
    return get_benchmark_dict(project_id)


def _profile_to_dict(prof):
    title_text, _ = _get_localized_text(prof.find("{}title".format(X)))
    desc_text, _ = _get_localized_text(prof.find("{}description".format(X)))
    ref_el = prof.find("{}reference".format(X))
    selects = [
        {"idref": s.get("idref"), "selected": s.get("selected") == "true"}
        for s in prof.findall("{}select".format(X))
    ]
    return {
        "id": prof.get("id"),
        "title": title_text,
        "description": desc_text,
        "reference": ref_el.text if ref_el is not None else None,
        "selects": selects,
    }


def add_profile(project_id, profile_id, title, description, reference=None):
    tree = load_tree(project_id)
    root = tree.getroot()
    lang = root.get("{}lang".format(XML))

    if root.find("{}Profile[@id='{}']".format(X, profile_id)) is not None:
        raise XccdfError("Профиль с id='{}' уже существует.".format(profile_id))

    prof = etree.Element("{}Profile".format(X))
    prof.set("id", profile_id)
    _text_with_lang(prof, "title", title, lang)
    _text_with_lang(prof, "description", description, lang)
    if reference:
        etree.SubElement(prof, "{}reference".format(X)).text = reference
    _insert_ordered(root, prof)

    save_tree(project_id, tree)
    return get_benchmark_dict(project_id)


def update_profile(project_id, profile_id, title=None, description=None, reference=None):
    tree = load_tree(project_id)
    root = tree.getroot()
    prof = root.find("{}Profile[@id='{}']".format(X, profile_id))
    if prof is None:
        raise XccdfError("Профиль '{}' не найден.".format(profile_id))

    if title is not None:
        prof.find("{}title".format(X)).text = title
    if description is not None:
        prof.find("{}description".format(X)).text = description
    if reference is not None:
        ref_el = prof.find("{}reference".format(X))
        if ref_el is None:
            # reference должен стоять перед select по схеме XCCDF — если
            # к этому моменту у профиля уже есть select-ы (правило добавили
            # в состав раньше, чем задали reference), вставляем перед первым
            # select, а не в конец.
            ref_el = etree.Element("{}reference".format(X))
            first_select = prof.find("{}select".format(X))
            if first_select is not None:
                etree.insert_before(prof, first_select, ref_el)
            else:
                prof.append(ref_el)
        ref_el.text = reference

    save_tree(project_id, tree)
    return get_benchmark_dict(project_id)


def delete_profile(project_id, profile_id):
    tree = load_tree(project_id)
    root = tree.getroot()
    prof = root.find("{}Profile[@id='{}']".format(X, profile_id))
    if prof is None:
        raise XccdfError("Профиль '{}' не найден.".format(profile_id))
    root.remove(prof)
    save_tree(project_id, tree)
    return get_benchmark_dict(project_id)


def set_select(project_id, profile_id, idref, selected):
    tree = load_tree(project_id)
    root = tree.getroot()
    prof = root.find("{}Profile[@id='{}']".format(X, profile_id))
    if prof is None:
        raise XccdfError("Профиль '{}' не найден.".format(profile_id))

    sel = prof.find("{}select[@idref='{}']".format(X, idref))
    if sel is None:
        sel = etree.SubElement(prof, "{}select".format(X))
        sel.set("idref", idref)
    sel.set("selected", "true" if selected else "false")

    save_tree(project_id, tree)
    return get_benchmark_dict(project_id)


def delete_select(project_id, profile_id, idref):
    tree = load_tree(project_id)
    root = tree.getroot()
    prof = root.find("{}Profile[@id='{}']".format(X, profile_id))
    if prof is None:
        raise XccdfError("Профиль '{}' не найден.".format(profile_id))
    sel = prof.find("{}select[@idref='{}']".format(X, idref))
    if sel is None:
        raise XccdfError("select для '{}' не найден в профиле '{}'.".format(idref, profile_id))
    prof.remove(sel)
    save_tree(project_id, tree)
    return get_benchmark_dict(project_id)


def _rule_to_dict(rule):
    title_text, _ = _get_localized_text(rule.find("{}title".format(X)))
    desc_text, _ = _get_localized_text(rule.find("{}description".format(X)))
    idents = [
        {"system": i.get("system"), "value": i.text}
        for i in rule.findall("{}ident".format(X))
    ]
    check_el = rule.find("{}check".format(X))
    href, name, system = None, None, None
    if check_el is not None:
        system = check_el.get("system")
        ref = check_el.find("{}check-content-ref".format(X))
        if ref is not None:
            href = ref.get("href")
            name = ref.get("name")

    return {
        "id": rule.get("id"),
        "selected": rule.get("selected") == "true",
        "title": title_text,
        "description": desc_text,
        "idents": idents,
        "check_system": system,
        "check_href": href,
        "check_name": name,
    }


def add_rule(project_id, rule_id, selected, title, description, idents, check_href, check_name):
    tree = load_tree(project_id)
    root = tree.getroot()
    lang = root.get("{}lang".format(XML))

    if root.find("{}Rule[@id='{}']".format(X, rule_id)) is not None:
        raise XccdfError("Правило с id='{}' уже существует.".format(rule_id))

    rule = etree.Element("{}Rule".format(X))
    rule.set("id", rule_id)
    rule.set("selected", "true" if selected else "false")
    _text_with_lang(rule, "title", title, lang)
    _text_with_lang(rule, "description", description, lang)

    for ident in idents or []:
        ident_el = etree.SubElement(rule, "{}ident".format(X))
        ident_el.set("system", ident["system"])
        ident_el.text = ident["value"]

    check_el = etree.SubElement(rule, "{}check".format(X))
    check_el.set("system", CHECK_SYSTEM_OVAL)
    ref_el = etree.SubElement(check_el, "{}check-content-ref".format(X))
    ref_el.set("href", check_href)
    ref_el.set("name", check_name)

    _insert_ordered(root, rule)

    save_tree(project_id, tree)
    return get_benchmark_dict(project_id)


def update_rule(project_id, rule_id, selected=None, title=None, description=None,
                 idents=None, check_href=None, check_name=None):
    tree = load_tree(project_id)
    root = tree.getroot()
    rule = root.find("{}Rule[@id='{}']".format(X, rule_id))
    if rule is None:
        raise XccdfError("Правило '{}' не найдено.".format(rule_id))

    if selected is not None:
        rule.set("selected", "true" if selected else "false")
    if title is not None:
        rule.find("{}title".format(X)).text = title
    if description is not None:
        rule.find("{}description".format(X)).text = description
    if idents is not None:
        for old in rule.findall("{}ident".format(X)):
            rule.remove(old)
        check_el = rule.find("{}check".format(X))
        for ident in idents:
            ident_el = etree.Element("{}ident".format(X))
            ident_el.set("system", ident["system"])
            ident_el.text = ident["value"]
            etree.insert_before(rule, check_el, ident_el)
    if check_href is not None or check_name is not None:
        ref_el = rule.find("{}check/{}check-content-ref".format(X, X))
        if check_href is not None:
            ref_el.set("href", check_href)
        if check_name is not None:
            ref_el.set("name", check_name)

    save_tree(project_id, tree)
    return get_benchmark_dict(project_id)


def delete_rule(project_id, rule_id):
    tree = load_tree(project_id)
    root = tree.getroot()
    rule = root.find("{}Rule[@id='{}']".format(X, rule_id))
    if rule is None:
        raise XccdfError("Правило '{}' не найдено.".format(rule_id))
    root.remove(rule)
    save_tree(project_id, tree)
    return get_benchmark_dict(project_id)
