"""
Сборка ZIP-архива из проекта (для импорта в целевую систему) и разбор уже
готового архива обратно в проект (чтобы можно было доработать существующий
профиль, например поставляемый вместе с VMC).
"""
import io
import zipfile
from . import xmlcompat as etree
from . import storage
from . import oval_xml
from .namespaces import XCCDF_NS, OVAL_DEF_NS


class ExportError(Exception):
    pass


# ------------------------------------------------- приведение к схеме при экспорте
#
# Проекты, созданные ранними версиями сервиса или импортированные извне,
# могут нарушать схему: правило стоит раньше профиля, у сущности состояния
# с var_ref нет datatype. Сервис больше не создаёт таких документов, но
# уже сохранённые файлы остаются прежними. Поэтому при экспорте документ
# приводится к схеме — «старый» проект становится корректным без ручной правки.

_XCCDF_ORDER = ["status", "dc-status", "title", "description", "notice", "front-matter",
                "rear-matter", "reference", "plain-text", "platform", "version", "metadata",
                "model", "Profile", "Value", "Group", "Rule", "TestResult", "signature"]


def _normalize_xccdf(data):
    from . import xmlcompat
    from .namespaces import serialize_xml
    root = xmlcompat.fromstring(data)
    def prio(el):
        name = etree.QName(el).localname if isinstance(el.tag, str) else ""
        return _XCCDF_ORDER.index(name) if name in _XCCDF_ORDER else len(_XCCDF_ORDER)
    kids = [c for c in list(root) if isinstance(c.tag, str)]
    ordered = sorted(kids, key=prio)          # sorted устойчива: порядок внутри группы сохраняется
    if ordered != kids:
        for c in kids:
            root.remove(c)
        for c in ordered:
            root.append(c)
    return serialize_xml(root)


def _normalize_oval_states(project_id, fname):
    """Дописывает datatype и operation сущностям состояния, у которых
    они отсутствуют (характерно для var_ref из ранних версий)."""
    from .oval_registry import TEST_TYPES
    from .namespaces import OVAL_FAMILY_NS
    tree = oval_xml.load_tree(project_id, fname)
    root = tree.getroot()
    states = oval_xml._section(root, "states")
    by_tag = {}
    for tt, cfg in TEST_TYPES.items():
        ns = OVAL_FAMILY_NS.get(cfg["family"])
        if ns:
            by_tag["{%s}%s_state" % (ns, cfg["tag"])] = {f["name"]: f for f in cfg["state_fields"]}
    changed = False
    for st in list(states):
        fields = by_tag.get(st.tag)
        if not fields:
            continue
        for ent in list(st):
            name = etree.QName(ent).localname
            f = fields.get(name)
            if not f or f.get("is_plain_value"):
                continue
            if ent.get("datatype") is None:
                ent.set("datatype", f["datatype"]); changed = True
            if ent.get("operation") is None:
                ent.set("operation", f["default_operation"]); changed = True
    if changed:
        oval_xml.save_tree(project_id, fname, tree)


def export_project_zip(project_id) -> bytes:
    path = storage.project_path(project_id)
    if not path.is_dir():
        raise ExportError("Проект '{}' не найден.".format(project_id))

    xccdf_path = storage.benchmark_file(project_id)
    if not xccdf_path.exists():
        raise ExportError("В проекте отсутствует benchmark-xccdf.xml.")

    oval_files = storage.list_oval_files(project_id)
    if not oval_files:
        raise ExportError("В проекте нет ни одного OVAL-файла.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("benchmark-xccdf.xml", _normalize_xccdf(xccdf_path.read_bytes()))
        for fname in oval_files:
            _normalize_oval_states(project_id, fname)
            # При экспорте объявляем в OVAL-файле только реально
            # используемые family-namespace'ы (ind/unix/linux/windows) —
            # как в эталонном примере из требований к формату, а не все
            # четыре сразу, как хранится в рабочей копии проекта.
            zf.writestr(fname, oval_xml.serialize_for_export(project_id, fname))

    buf.seek(0)
    return buf.read()


def import_zip(project_id, zip_bytes: bytes):
    if storage.project_exists(project_id):
        raise ExportError("Проект '{}' уже существует.".format(project_id))

    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        raise ExportError("Файл не является корректным ZIP-архивом.")

    # --- Отбор файлов архива ---------------------------------------------
    # Служебные файлы ОС не учитываются: macOS при сжатии добавляет папку
    # __MACOSX с двоичными копиями вида ._benchmark-xccdf.xml (их имя тоже
    # оканчивается на .xml), Windows и macOS — Thumbs.db и .DS_Store.
    def _is_junk(n):
        base = n.rsplit("/", 1)[-1]
        return (n.startswith("__MACOSX/") or "/__MACOSX/" in n
                or base.startswith("._") or base in (".DS_Store", "Thumbs.db", "desktop.ini"))

    names = [n for n in zf.namelist() if not n.endswith("/") and not _is_junk(n)]

    # Архив, упакованный через «Сжать папку», содержит файлы внутри одной
    # папки верхнего уровня. Такой случай разворачиваем; более глубокую
    # вложенность и смешанную структуру — нет, чтобы не перепутать файлы.
    prefix = ""
    if names and all("/" in n for n in names):
        tops = {n.split("/", 1)[0] for n in names}
        if len(tops) == 1:
            prefix = tops.pop() + "/"
    flat = {}
    for n in names:
        rel = n[len(prefix):] if prefix and n.startswith(prefix) else n
        if "/" in rel or "\\" in rel:
            raise ExportError(
                "Файл '{}' находится во вложенном каталоге. Поместите XCCDF- и OVAL-файлы "
                "в корень архива (допускается одна общая папка верхнего уровня).".format(n))
        if rel in flat:
            raise ExportError("В архиве несколько файлов с именем '{}'.".format(rel))
        flat[rel] = n

    XCCDF_12 = "http://checklists.nist.gov/xccdf/1.2"
    xccdf_candidates, oval_candidates, seen = [], [], []

    for rel, full in flat.items():
        if not rel.lower().endswith(".xml"):
            continue
        try:
            root = etree.fromstring(zf.read(full))
        except etree.XMLSyntaxError:
            raise ExportError("Файл '{}' не является корректным XML.".format(rel))

        tag = etree.QName(root.tag)
        seen.append("{} — <{}>".format(rel, tag.localname))
        if tag.namespace == XCCDF_NS and tag.localname == "Benchmark":
            xccdf_candidates.append(rel)
        elif tag.namespace == XCCDF_12 and tag.localname == "Benchmark":
            raise ExportError(
                "Файл '{}' — XCCDF версии 1.2. Kaspersky Vulnerability Management принимает "
                "профили в формате XCCDF 1.1, поэтому импорт версии 1.2 не поддерживается.".format(rel))
        elif tag.namespace == OVAL_DEF_NS and tag.localname == "oval_definitions":
            oval_candidates.append(rel)
        elif "scap" in tag.localname.lower() or "data-stream" in tag.localname.lower():
            raise ExportError("Файл '{}' похож на SCAP DataStream — такой формат импорта "
                              "не поддерживается.".format(rel))

    if len(xccdf_candidates) != 1:
        found = "; ".join(seen) if seen else "XML-файлов не найдено"
        raise ExportError(
            "В архиве должен быть ровно один XCCDF-файл (корневой элемент Benchmark "
            "в пространстве имён XCCDF 1.1). Найдено: {}. Содержимое архива: {}.".format(
                len(xccdf_candidates), found))
    if not oval_candidates:
        raise ExportError("В архиве должен быть хотя бы один OVAL-файл (oval_definitions).")

    path = storage.create_project(project_id)
    xccdf_name = xccdf_candidates[0]
    (path / "benchmark-xccdf.xml").write_bytes(zf.read(flat[xccdf_name]))
    for n in oval_candidates:
        (path / n).write_bytes(zf.read(flat[n]))

    return {
        "project_id": project_id,
        "xccdf_source_name": xccdf_name,
        "oval_files": oval_candidates,
    }
