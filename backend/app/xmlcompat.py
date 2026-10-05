# -*- coding: utf-8 -*-
"""
Слой работы с XML на чистой стандартной библиотеке Python.

Зачем он нужен
--------------
Раньше сервис использовал lxml. Это бинарный пакет: его нужно ставить через
pip (а на серверах в закрытом контуре интернета нет), он компилируется под
конкретную версию Python и архитектуру процессора, а в режиме замкнутой
программной среды Astra Linux SE неподписанные .so-библиотеки блокируются.

Этот модуль повторяет ту небольшую часть API lxml.etree, которая реально
используется в проекте, поверх встроенного xml.etree.ElementTree. В итоге
сервису нужен только системный python3 — без pip, компиляторов и сети.

Собственный сериализатор
------------------------
Встроенная сериализация ElementTree ведёт себя по-разному в разных версиях
Python (до 3.8 сортирует атрибуты, объявляет только «задействованные»
пространства имён, не умеет задавать префиксы для конкретного документа).
Поэтому вывод формирует собственный сериализатор: он даёт одинаковый,
предсказуемый результат на Python 3.5–3.13 и совпадает по структуре с
эталонным комплектом, подтверждённым разработчиком продукта.

Совместимость: Python 3.5+ (Astra Linux CE 2.12 поставляется с Python 3.5).
В модуле намеренно нет f-строк и аннотаций переменных.
"""
import xml.etree.ElementTree as _ET

from .namespaces import (
    XCCDF_NS, XSI_NS, XML_NS, OVAL_DEF_NS, OVAL_COMMON_NS,
    OVAL_FAMILY_NS, FAMILY_PREFIX,
)

XMLSyntaxError = _ET.ParseError


# ------------------------------------------------------------------ фасад

def Element(tag, attrib=None, nsmap=None, **extra):
    """Аналог lxml.etree.Element. Параметр nsmap принимается ради
    совместимости вызовов и игнорируется: объявления пространств имён
    расставляет сериализатор."""
    el = _ET.Element(tag, dict(attrib or {}))
    for k, v in extra.items():
        el.set(k, v)
    return el


SubElement = _ET.SubElement
ElementTree = _ET.ElementTree


class QName(object):
    """Аналог lxml.etree.QName: принимает элемент или строку '{uri}name'."""

    def __init__(self, el_or_tag):
        tag = el_or_tag if isinstance(el_or_tag, str) else el_or_tag.tag
        if isinstance(tag, str) and tag.startswith("{"):
            self.namespace, self.localname = tag[1:].split("}", 1)
        else:
            self.namespace, self.localname = None, tag
        self.text = tag


def localname(tag):
    return QName(tag).localname


def _strip_blank(el):
    """Убирает «пустые» текстовые узлы из отступов, как делает
    lxml.XMLParser(remove_blank_text=True)."""
    children = list(el)
    if children and el.text is not None and not el.text.strip():
        el.text = None
    for child in children:
        if child.tail is not None and not child.tail.strip():
            child.tail = None
        _strip_blank(child)


def parse(path):
    tree = _ET.parse(str(path))
    _strip_blank(tree.getroot())
    return tree


def fromstring(data):
    root = _ET.fromstring(data)
    _strip_blank(root)
    return root


def insert_before(anchor_parent, anchor, new_el):
    """Замена lxml-методу anchor.addprevious(new_el): у ElementTree нет
    ссылки на родителя, поэтому родитель передаётся явно."""
    idx = list(anchor_parent).index(anchor)
    anchor_parent.insert(idx, new_el)


# ------------------------------------------------------------ сериализатор

# Канонический порядок атрибутов. Порядок атрибутов в XML не несёт смысла,
# но единообразный вывод удобнее читать и сравнивать с эталоном. Порядок
# подобран по эталонному комплекту (например: test_ref перед comment у
# criterion, datatype/operation/var_ref у сущностей).
_ATTR_ORDER = [
    "id", "idref", "version", "class", "selected",
    "check", "check_existence",
    "test_ref", "object_ref", "state_ref",
    "system", "href", "name", "family",
    "datatype", "operation", "var_ref",
    "{%s}lang" % XML_NS, "resolved", "style",
    "comment",
]
_ATTR_RANK = dict((name, i) for i, name in enumerate(_ATTR_ORDER))

# Порядок объявления пространств имён OVAL-семейств в корне документа.
_FAMILY_ORDER = ["independent", "unix", "linux", "windows"]
_NS_TO_FAMILY = dict((uri, fam) for fam, uri in OVAL_FAMILY_NS.items())


def _attr_key(item):
    name = item[0]
    return (_ATTR_RANK.get(name, len(_ATTR_ORDER)), name)


def _escape_text(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _escape_attr(s):
    return (_escape_text(s).replace('"', "&quot;")
            .replace("\n", "&#10;").replace("\r", "&#13;").replace("\t", "&#9;"))


def _namespace_decls(root):
    """Список (префикс, uri) для объявления в корневом элементе.

    Для XCCDF и OVAL набор совпадает с эталоном: основное пространство
    имён по умолчанию, затем xsi, затем (для OVAL) oval и только те
    семейства проверок (ind/unix/linux/windows), что реально встречаются
    в документе. Незнакомые пространства имён (например, в импортированном
    стороннем файле) получают автоматические префиксы ns0, ns1, …
    """
    used = set()
    for el in root.iter():
        if isinstance(el.tag, str) and el.tag.startswith("{"):
            used.add(el.tag[1:].split("}", 1)[0])
        for k in el.attrib:
            if k.startswith("{"):
                used.add(k[1:].split("}", 1)[0])

    root_ns = QName(root).namespace
    decls = []
    if root_ns == XCCDF_NS:
        decls = [(None, XCCDF_NS), ("xsi", XSI_NS)]
    elif root_ns == OVAL_DEF_NS:
        decls = [(None, OVAL_DEF_NS), ("xsi", XSI_NS), ("oval", OVAL_COMMON_NS)]
        fams = set(_NS_TO_FAMILY[u] for u in used if u in _NS_TO_FAMILY)
        for fam in _FAMILY_ORDER:
            if fam in fams:
                decls.append((FAMILY_PREFIX[fam], OVAL_FAMILY_NS[fam]))
    elif root_ns:
        decls = [(None, root_ns)]

    known = set(uri for _, uri in decls)
    auto = 0
    for uri in sorted(used):
        if uri in known or uri == XML_NS:
            continue
        decls.append(("ns%d" % auto, uri))
        known.add(uri)
        auto += 1
    return decls


def _qname(tag, prefixes, is_attr=False):
    if not tag.startswith("{"):
        return tag
    uri, local = tag[1:].split("}", 1)
    if uri == XML_NS:
        return "xml:" + local
    prefix = prefixes.get(uri)
    # У атрибутов пространство имён по умолчанию не наследуется, поэтому
    # атрибут из основного пространства имён пишем без префикса только для
    # элементов; для атрибутов используем явный префикс, если он есть.
    if prefix is None:
        return local
    return prefix + ":" + local


def tostring(root, indent="  "):
    """Сериализует дерево в байты UTF-8 с XML-декларацией."""
    if hasattr(root, "getroot"):
        root = root.getroot()
    decls = _namespace_decls(root)
    prefixes = {}
    for prefix, uri in decls:
        prefixes[uri] = prefix  # None — пространство имён по умолчанию

    out = ['<?xml version="1.0" encoding="UTF-8"?>\n']

    def write(el, level, is_root):
        pad = indent * level
        name = _qname(el.tag, prefixes)
        parts = [pad, "<", name]
        if is_root:
            for prefix, uri in decls:
                if prefix is None:
                    parts.append(' xmlns="%s"' % _escape_attr(uri))
                else:
                    parts.append(' xmlns:%s="%s"' % (prefix, _escape_attr(uri)))
        for k, v in sorted(el.attrib.items(), key=_attr_key):
            parts.append(' %s="%s"' % (_qname(k, prefixes, True), _escape_attr(v)))
        children = [c for c in el if isinstance(c.tag, str)]
        text = el.text
        if not children and not (text and text.strip()):
            parts.append("/>\n")
            out.append("".join(parts))
            return
        parts.append(">")
        if children:
            out.append("".join(parts) + "\n")
            for c in children:
                write(c, level + 1, False)
            out.append("%s</%s>\n" % (pad, name))
        else:
            out.append("".join(parts) + _escape_text(text) + "</%s>\n" % name)

    write(root, 0, True)
    return "".join(out).encode("utf-8")


def write(tree_or_element, path):
    data = tostring(tree_or_element)
    with open(str(path), "wb") as f:
        f.write(data)
