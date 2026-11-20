"""
Константы пространств имён, используемых в XCCDF и OVAL документах.
Вынесены в отдельный модуль, т.к. используются и при построении, и при
разборе XML (xccdf_xml.py, oval_xml.py, validation.py).
"""

XCCDF_NS = "http://checklists.nist.gov/xccdf/1.1"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
XML_NS = "http://www.w3.org/XML/1998/namespace"

OVAL_DEF_NS = "http://oval.mitre.org/XMLSchema/oval-definitions-5"
OVAL_COMMON_NS = "http://oval.mitre.org/XMLSchema/oval-common-5"

# Family-специфичные неймспейсы OVAL (используются в tests/objects/states)
OVAL_FAMILY_NS = {
    "independent": "http://oval.mitre.org/XMLSchema/oval-definitions-5#independent",
    "unix": "http://oval.mitre.org/XMLSchema/oval-definitions-5#unix",
    "linux": "http://oval.mitre.org/XMLSchema/oval-definitions-5#linux",
    "windows": "http://oval.mitre.org/XMLSchema/oval-definitions-5#windows",
}

# Префиксы, которые используются в примерах из PDF и в тексте требований
FAMILY_PREFIX = {
    "independent": "ind",
    "unix": "unix",
    "linux": "linux",
    "windows": "windows",
}

CHECK_SYSTEM_OVAL = "http://oval.mitre.org/XMLSchema/oval-definitions-5"

XCCDF_NSMAP = {
    None: XCCDF_NS,
    "xsi": XSI_NS,
}

XML_DECLARATION = b'<?xml version="1.0" encoding="UTF-8"?>\n'


def serialize_xml(tree_or_element):
    """Сериализует дерево в байты с XML-декларацией и отступами.
    Реализация — в xmlcompat.tostring (стандартная библиотека Python,
    одинаковый вывод на Python 3.5–3.13)."""
    from . import xmlcompat
    return xmlcompat.tostring(tree_or_element)


def write_xml(tree_or_element, path):
    from . import xmlcompat
    xmlcompat.write(tree_or_element, path)


def oval_nsmap(families_used):
    """nsmap для oval_definitions с учётом используемых семейств платформ"""
    nsmap = {
        None: OVAL_DEF_NS,
        "xsi": XSI_NS,
        "oval": OVAL_COMMON_NS,
    }
    for fam in families_used:
        nsmap[FAMILY_PREFIX[fam]] = OVAL_FAMILY_NS[fam]
    return nsmap
