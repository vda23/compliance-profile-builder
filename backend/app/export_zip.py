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
        zf.write(xccdf_path, arcname="benchmark-xccdf.xml")
        for fname in oval_files:
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

    names = [n for n in zf.namelist() if not n.endswith("/")]
    for n in names:
        if "/" in n or "\\" in n:
            raise ExportError(
                "Файл '{}' находится во вложенном каталоге — размещение "
                "файлов во вложенных каталогах не поддерживается.".format(n)
            )

    xccdf_candidates = []
    oval_candidates = []

    for n in names:
        if not n.lower().endswith(".xml"):
            continue
        try:
            root = etree.fromstring(zf.read(n))
        except etree.XMLSyntaxError:
            raise ExportError("Файл '{}' не является валидным XML.".format(n))

        tag = etree.QName(root.tag)
        if tag.namespace == XCCDF_NS and tag.localname == "Benchmark":
            xccdf_candidates.append(n)
        elif tag.namespace == OVAL_DEF_NS and tag.localname == "oval_definitions":
            oval_candidates.append(n)
        elif "scap" in tag.localname.lower() or "data-stream" in tag.localname.lower():
            raise ExportError("Файл '{}' похож на SCAP DataStream — такой формат импорта не поддерживается.".format(n))

    if len(xccdf_candidates) != 1:
        raise ExportError(
            "В архиве должен быть ровно один XCCDF-файл (Benchmark). Найдено: {}.".format(len(xccdf_candidates))
        )
    if not oval_candidates:
        raise ExportError("В архиве должен быть хотя бы один OVAL-файл (oval_definitions).")

    path = storage.create_project(project_id)
    xccdf_name = xccdf_candidates[0]
    (path / "benchmark-xccdf.xml").write_bytes(zf.read(xccdf_name))
    for n in oval_candidates:
        (path / n).write_bytes(zf.read(n))

    return {
        "project_id": project_id,
        "xccdf_source_name": xccdf_name,
        "oval_files": oval_candidates,
    }
