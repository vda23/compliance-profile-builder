"""
CRUD-операции над OVAL-файлом проекта (checks-*.xml).
Генерация/разбор test/object/state полностью управляется схемой из oval_registry.py —
добавление нового типа теста не требует правок в этом модуле.
"""
from datetime import datetime, timezone
from . import xmlcompat as etree

from . import storage
from .namespaces import (
    OVAL_DEF_NS, OVAL_COMMON_NS, OVAL_FAMILY_NS, FAMILY_PREFIX, oval_nsmap,
    write_xml, serialize_xml,
)
from .oval_registry import TEST_TYPES, get_type_config

O = "{{{}}}".format(OVAL_DEF_NS)
OC = "{{{}}}".format(OVAL_COMMON_NS)

_FAMILIES = list(OVAL_FAMILY_NS.keys())

_NS_TO_FAMILY = {uri: fam for fam, uri in OVAL_FAMILY_NS.items()}
_OBJECT_TAG_TO_TYPE = {
    (cfg["family"], "{}_object".format(cfg['tag'])): ttype for ttype, cfg in TEST_TYPES.items()
}
_STATE_TAG_TO_TYPE = {
    (cfg["family"], "{}_state".format(cfg['tag'])): ttype
    for ttype, cfg in TEST_TYPES.items() if cfg["state_fields"]
}
_TESTTAG_TO_TYPE = {
    (cfg["family"], "{}_test".format(cfg['tag'])): ttype for ttype, cfg in TEST_TYPES.items()
}


class OvalError(Exception):
    pass


def create_oval_file(project_id, filename, product_name, product_version, schema_version="5.11.2"):
    if not filename.endswith(".xml"):
        raise OvalError("Имя OVAL-файла должно иметь расширение .xml")
    path = storage.oval_file(project_id, filename)
    if path.exists():
        raise OvalError("Файл '{}' уже существует в проекте.".format(filename))

    root = etree.Element("{}oval_definitions".format(O), nsmap=oval_nsmap(_FAMILIES))

    generator = etree.SubElement(root, "{}generator".format(O))
    etree.SubElement(generator, "{}product_name".format(OC)).text = product_name
    etree.SubElement(generator, "{}schema_version".format(OC)).text = schema_version
    etree.SubElement(generator, "{}timestamp".format(OC)).text = (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    etree.SubElement(generator, "{}product_version".format(OC)).text = product_version

    etree.SubElement(root, "{}definitions".format(O))
    etree.SubElement(root, "{}tests".format(O))
    etree.SubElement(root, "{}objects".format(O))
    etree.SubElement(root, "{}states".format(O))
    etree.SubElement(root, "{}variables".format(O))

    tree = etree.ElementTree(root)
    write_xml(tree, path)
    return get_oval_dict(project_id, filename)


def load_tree(project_id, filename):
    path = storage.oval_file(project_id, filename)
    if not path.exists():
        raise OvalError("Файл '{}' не найден в проекте '{}'.".format(filename, project_id))
    return etree.parse(str(path))


def save_tree(project_id, filename, tree):
    path = storage.oval_file(project_id, filename)
    write_xml(tree, path)


def _section(root, name):
    el = root.find("{}{}".format(O, name))
    if el is None:
        el = etree.SubElement(root, "{}{}".format(O, name))
    return el


def _family_of(qname_namespace):
    return _NS_TO_FAMILY.get(qname_namespace)


def _build_entity_container(local_tag, family, fields_config, values):
    ns = OVAL_FAMILY_NS[family]
    el = etree.Element("{{{}}}{}".format(ns, local_tag))
    # Защита от опечатки в имени поля: раньше неизвестные имена молча
    # игнорировались, и на выходе получался пустой object/state — тест
    # формально валиден, но фактически ничего не проверяет. Лучше сразу
    # сказать об ошибке, чем отдать пользователю бессмысленную проверку.
    known = {f["name"] for f in fields_config}
    unknown = [k for k in (values or {}) if k not in known]
    if unknown:
        raise OvalError(
            "Неизвестные поля для этого типа: " + ", ".join(sorted(unknown)) +
            ". Допустимые поля: " + (", ".join(sorted(known)) if known else "(нет)")
        )
    for field in fields_config:
        fname = field["name"]
        if fname not in values or values[fname] in (None, ""):
            continue
        raw = values[fname]
        child = etree.SubElement(el, "{{{}}}{}".format(ns, fname))
        if field["is_plain_value"]:
            child.text = str(raw)
        else:
            operation = (raw.get("operation") if isinstance(raw, dict) else None) or field["default_operation"]
            datatype = (raw.get("datatype") if isinstance(raw, dict) else None) or field["datatype"]
            # datatype/operation выставляются всегда — в том числе когда
            # значение берётся из переменной (var_ref). В эталонном
            # комплекте, подтверждённом разработчиком продукта, сущность
            # с var_ref содержит все три атрибута:
            #   <windows:password_hist_len datatype="int"
            #                              operation="greater than or equal"
            #                              var_ref="oval:custom:var:1"/>
            child.set("datatype", datatype)
            child.set("operation", operation)
            if isinstance(raw, dict) and raw.get("var_ref"):
                child.set("var_ref", raw["var_ref"])
            else:
                text = raw.get("value") if isinstance(raw, dict) else raw
                child.text = str(text)
    return el


def _parse_entity_container(el, family, fields_config):
    ns = OVAL_FAMILY_NS[family]
    result = {}
    for field in fields_config:
        fname = field["name"]
        child = el.find("{{{}}}{}".format(ns, fname))
        if child is None:
            continue
        if field["is_plain_value"]:
            result[fname] = child.text
        elif child.get("var_ref"):
            result[fname] = {
                "var_ref": child.get("var_ref"),
                "operation": child.get("operation"),
                "datatype": child.get("datatype"),
            }
        else:
            result[fname] = {
                "value": child.text,
                "operation": child.get("operation"),
                "datatype": child.get("datatype"),
            }
    return result


def add_definition(project_id, filename, def_id, version, klass, title, description,
                    family, platforms, criteria):
    tree = load_tree(project_id, filename)
    root = tree.getroot()
    defs = _section(root, "definitions")

    if defs.find("{}definition[@id='{}']".format(O, def_id)) is not None:
        raise OvalError("Definition с id='{}' уже существует в этом файле.".format(def_id))

    d = etree.SubElement(defs, "{}definition".format(O))
    d.set("id", def_id)
    d.set("version", str(version))
    d.set("class", klass)

    meta = etree.SubElement(d, "{}metadata".format(O))
    etree.SubElement(meta, "{}title".format(O)).text = title
    etree.SubElement(meta, "{}description".format(O)).text = description
    if family:
        affected = etree.SubElement(meta, "{}affected".format(O))
        affected.set("family", family)
        for p in platforms or []:
            etree.SubElement(affected, "{}platform".format(O)).text = p

    criteria_el = etree.SubElement(d, "{}criteria".format(O))
    for c in criteria or []:
        crit = etree.SubElement(criteria_el, "{}criterion".format(O))
        crit.set("test_ref", c["test_ref"])
        if c.get("comment"):
            crit.set("comment", c["comment"])

    save_tree(project_id, filename, tree)
    return get_oval_dict(project_id, filename)


def update_definition(project_id, filename, def_id, version=None, klass=None, title=None,
                       description=None, family=None, platforms=None, criteria=None):
    tree = load_tree(project_id, filename)
    root = tree.getroot()
    defs = _section(root, "definitions")
    d = defs.find("{}definition[@id='{}']".format(O, def_id))
    if d is None:
        raise OvalError("Definition '{}' не найден.".format(def_id))

    if version is not None:
        d.set("version", str(version))
    if klass is not None:
        d.set("class", klass)

    meta = d.find("{}metadata".format(O))
    if title is not None:
        meta.find("{}title".format(O)).text = title
    if description is not None:
        meta.find("{}description".format(O)).text = description
    if family is not None or platforms is not None:
        old_affected = meta.find("{}affected".format(O))
        if old_affected is not None:
            meta.remove(old_affected)
        if family:
            affected = etree.SubElement(meta, "{}affected".format(O))
            affected.set("family", family)
            for p in platforms or []:
                etree.SubElement(affected, "{}platform".format(O)).text = p

    if criteria is not None:
        old_criteria = d.find("{}criteria".format(O))
        d.remove(old_criteria)
        criteria_el = etree.SubElement(d, "{}criteria".format(O))
        for c in criteria:
            crit = etree.SubElement(criteria_el, "{}criterion".format(O))
            crit.set("test_ref", c["test_ref"])
            if c.get("comment"):
                crit.set("comment", c["comment"])

    save_tree(project_id, filename, tree)
    return get_oval_dict(project_id, filename)


def delete_definition(project_id, filename, def_id):
    tree = load_tree(project_id, filename)
    root = tree.getroot()
    defs = _section(root, "definitions")
    d = defs.find("{}definition[@id='{}']".format(O, def_id))
    if d is None:
        raise OvalError("Definition '{}' не найден.".format(def_id))
    defs.remove(d)
    save_tree(project_id, filename, tree)
    return get_oval_dict(project_id, filename)


def add_test(project_id, filename, test_type, test_id, version, object_ref, state_ref=None,
             check="all", check_existence="at_least_one_exists", comment=None):
    cfg = get_type_config(test_type)
    if cfg is None:
        raise OvalError("Тип теста '{}' не входит в список допустимых.".format(test_type))

    tree = load_tree(project_id, filename)
    root = tree.getroot()
    tests = _section(root, "tests")

    family = cfg["family"]
    ns = OVAL_FAMILY_NS[family]
    local_tag = "{}_test".format(cfg['tag'])

    if tests.find("{{{}}}{}[@id='{}']".format(ns, local_tag, test_id)) is not None:
        raise OvalError("Тест с id='{}' уже существует.".format(test_id))

    t = etree.SubElement(tests, "{{{}}}{}".format(ns, local_tag))
    t.set("id", test_id)
    t.set("version", str(version))
    if check:
        t.set("check", check)
    if check_existence:
        t.set("check_existence", check_existence)
    if comment:
        t.set("comment", comment)

    obj_el = etree.SubElement(t, "{{{}}}object".format(ns))
    obj_el.set("object_ref", object_ref)

    if state_ref:
        if not cfg["state_fields"]:
            raise OvalError("Тип теста '{}' не поддерживает state.".format(test_type))
        ste_el = etree.SubElement(t, "{{{}}}state".format(ns))
        ste_el.set("state_ref", state_ref)

    save_tree(project_id, filename, tree)
    return get_oval_dict(project_id, filename)


def delete_test(project_id, filename, test_id):
    tree = load_tree(project_id, filename)
    root = tree.getroot()
    tests = _section(root, "tests")
    for child in list(tests):
        if child.get("id") == test_id:
            tests.remove(child)
            save_tree(project_id, filename, tree)
            return get_oval_dict(project_id, filename)
    raise OvalError("Тест '{}' не найден.".format(test_id))


def add_object(project_id, filename, test_type, obj_id, version, fields, comment=None):
    cfg = get_type_config(test_type)
    if cfg is None:
        raise OvalError("Тип теста '{}' не входит в список допустимых.".format(test_type))

    tree = load_tree(project_id, filename)
    root = tree.getroot()
    objects = _section(root, "objects")

    family = cfg["family"]
    local_tag = "{}_object".format(cfg['tag'])
    ns = OVAL_FAMILY_NS[family]

    if objects.find("{{{}}}{}[@id='{}']".format(ns, local_tag, obj_id)) is not None:
        raise OvalError("Object с id='{}' уже существует.".format(obj_id))

    el = _build_entity_container(local_tag, family, cfg["object_fields"], fields or {})
    el.set("id", obj_id)
    el.set("version", str(version))
    if comment:
        el.set("comment", comment)
    objects.append(el)

    save_tree(project_id, filename, tree)
    return get_oval_dict(project_id, filename)


def delete_object(project_id, filename, obj_id):
    tree = load_tree(project_id, filename)
    root = tree.getroot()
    objects = _section(root, "objects")
    for child in list(objects):
        if child.get("id") == obj_id:
            objects.remove(child)
            save_tree(project_id, filename, tree)
            return get_oval_dict(project_id, filename)
    raise OvalError("Object '{}' не найден.".format(obj_id))


def add_state(project_id, filename, test_type, ste_id, version, fields, comment=None):
    cfg = get_type_config(test_type)
    if cfg is None:
        raise OvalError("Тип теста '{}' не входит в список допустимых.".format(test_type))
    if not cfg["state_fields"]:
        raise OvalError("Тип теста '{}' не поддерживает state.".format(test_type))

    tree = load_tree(project_id, filename)
    root = tree.getroot()
    states = _section(root, "states")

    family = cfg["family"]
    local_tag = "{}_state".format(cfg['tag'])
    ns = OVAL_FAMILY_NS[family]

    if states.find("{{{}}}{}[@id='{}']".format(ns, local_tag, ste_id)) is not None:
        raise OvalError("State с id='{}' уже существует.".format(ste_id))

    el = _build_entity_container(local_tag, family, cfg["state_fields"], fields or {})
    el.set("id", ste_id)
    el.set("version", str(version))
    if comment:
        el.set("comment", comment)
    states.append(el)

    save_tree(project_id, filename, tree)
    return get_oval_dict(project_id, filename)


def delete_state(project_id, filename, ste_id):
    tree = load_tree(project_id, filename)
    root = tree.getroot()
    states = _section(root, "states")
    for child in list(states):
        if child.get("id") == ste_id:
            states.remove(child)
            save_tree(project_id, filename, tree)
            return get_oval_dict(project_id, filename)
    raise OvalError("State '{}' не найден.".format(ste_id))


def add_variable(project_id, filename, var_id, version, datatype, value, comment=None):
    tree = load_tree(project_id, filename)
    root = tree.getroot()
    variables = _section(root, "variables")

    if variables.find("{}constant_variable[@id='{}']".format(O, var_id)) is not None:
        raise OvalError("Variable с id='{}' уже существует.".format(var_id))

    el = etree.SubElement(variables, "{}constant_variable".format(O))
    el.set("id", var_id)
    el.set("version", str(version))
    el.set("datatype", datatype)
    if comment:
        el.set("comment", comment)
    etree.SubElement(el, "{}value".format(O)).text = str(value)

    save_tree(project_id, filename, tree)
    return get_oval_dict(project_id, filename)


def delete_variable(project_id, filename, var_id):
    tree = load_tree(project_id, filename)
    root = tree.getroot()
    variables = _section(root, "variables")
    for child in list(variables):
        if child.get("id") == var_id:
            variables.remove(child)
            save_tree(project_id, filename, tree)
            return get_oval_dict(project_id, filename)
    raise OvalError("Variable '{}' не найден.".format(var_id))


def get_oval_dict(project_id, filename):
    tree = load_tree(project_id, filename)
    root = tree.getroot()

    gen = root.find("{}generator".format(O))
    generator = {}
    if gen is not None:
        generator = {
            "product_name": gen.findtext("{}product_name".format(OC)),
            "schema_version": gen.findtext("{}schema_version".format(OC)),
            "timestamp": gen.findtext("{}timestamp".format(OC)),
            "product_version": gen.findtext("{}product_version".format(OC)),
        }

    definitions = []
    defs_section = root.find("{}definitions".format(O))
    if defs_section is not None:
        for d in defs_section.findall("{}definition".format(O)):
            meta = d.find("{}metadata".format(O))
            title = meta.findtext("{}title".format(O)) if meta is not None else None
            desc = meta.findtext("{}description".format(O)) if meta is not None else None
            affected = meta.find("{}affected".format(O)) if meta is not None else None
            family = affected.get("family") if affected is not None else None
            platforms = (
                [p.text for p in affected.findall("{}platform".format(O))]
                if affected is not None else []
            )
            criteria_el = d.find("{}criteria".format(O))
            criteria = []
            if criteria_el is not None:
                for c in criteria_el.findall("{}criterion".format(O)):
                    criteria.append({"test_ref": c.get("test_ref"), "comment": c.get("comment")})
            definitions.append({
                "id": d.get("id"), "version": d.get("version"), "class": d.get("class"),
                "title": title, "description": desc, "family": family, "platforms": platforms,
                "criteria": criteria,
            })

    tests = []
    tests_section = root.find("{}tests".format(O))
    if tests_section is not None:
        for t in tests_section:
            qn = etree.QName(t.tag)
            family = _family_of(qn.namespace)
            ttype = _TESTTAG_TO_TYPE.get((family, qn.localname))
            obj_ref, ste_ref = None, None
            for child in t:
                cqn = etree.QName(child.tag)
                if cqn.localname == "object":
                    obj_ref = child.get("object_ref")
                elif cqn.localname == "state":
                    ste_ref = child.get("state_ref")
            tests.append({
                "id": t.get("id"), "version": t.get("version"), "type": ttype,
                "check": t.get("check"), "check_existence": t.get("check_existence"),
                "comment": t.get("comment"), "object_ref": obj_ref, "state_ref": ste_ref,
            })

    objects = []
    objects_section = root.find("{}objects".format(O))
    if objects_section is not None:
        for o in objects_section:
            qn = etree.QName(o.tag)
            family = _family_of(qn.namespace)
            ttype = _OBJECT_TAG_TO_TYPE.get((family, qn.localname))
            cfg = get_type_config(ttype) if ttype else None
            fields = _parse_entity_container(o, family, cfg["object_fields"]) if cfg else {}
            objects.append({
                "id": o.get("id"), "version": o.get("version"), "comment": o.get("comment"),
                "type": ttype, "fields": fields,
            })

    states = []
    states_section = root.find("{}states".format(O))
    if states_section is not None:
        for s in states_section:
            qn = etree.QName(s.tag)
            family = _family_of(qn.namespace)
            ttype = _STATE_TAG_TO_TYPE.get((family, qn.localname))
            cfg = get_type_config(ttype) if ttype else None
            fields = _parse_entity_container(s, family, cfg["state_fields"]) if cfg else {}
            states.append({
                "id": s.get("id"), "version": s.get("version"), "comment": s.get("comment"),
                "type": ttype, "fields": fields,
            })

    variables = []
    variables_section = root.find("{}variables".format(O))
    if variables_section is not None:
        for v in variables_section:
            value_el = v.find("{}value".format(O))
            variables.append({
                "id": v.get("id"), "version": v.get("version"),
                "datatype": v.get("datatype"), "comment": v.get("comment"),
                "value": value_el.text if value_el is not None else None,
            })

    return {
        "filename": filename,
        "generator": generator,
        "definitions": definitions,
        "tests": tests,
        "objects": objects,
        "states": states,
        "variables": variables,
    }


def used_families(root):
    """Семейства платформ (independent/unix/linux/windows), реально
    встречающиеся в дереве — используется, чтобы при экспорте объявлять в
    OVAL-файле только фактически задействованные xmlns (как в эталонном
    примере из требований к формату), а не все четыре сразу."""
    used = set()
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.startswith("{"):
            uri = el.tag[1:].split("}")[0]
            fam = _NS_TO_FAMILY.get(uri)
            if fam:
                used.add(fam)
    return used


def serialize_for_export(project_id, filename):
    """Сериализует OVAL-файл для экспорта. Сериализатор (xmlcompat)
    объявляет в корне только реально задействованные пространства имён
    семейств (ind/unix/linux/windows) — как в эталонном комплекте."""
    return serialize_xml(load_tree(project_id, filename))
