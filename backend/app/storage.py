"""
Файловое хранилище "проектов". Никакой БД — источник истины это сами XML-файлы
на диске, расположенные так же, как они лягут в итоговый ZIP-архив:

data/projects/<project_id>/
    benchmark-xccdf.xml
    checks-1-oval.xml
    checks-2-oval.xml
    ...

project_id — техническое имя папки (slug), не путать с Benchmark/@id.
"""
import os
import re
import shutil
from pathlib import Path

DATA_DIR = Path(os.environ.get("CPB_DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data"))
PROJECTS_DIR = DATA_DIR / "projects"

SLUG_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class ProjectError(Exception):
    pass


def ensure_dirs():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def validate_slug(slug: str):
    if not SLUG_RE.match(slug):
        raise ProjectError(
            "Идентификатор проекта должен содержать только латинские буквы, "
            "цифры, '-' и '_' (1-64 символа)."
        )


def project_path(project_id: str) -> Path:
    validate_slug(project_id)
    return PROJECTS_DIR / project_id


def project_exists(project_id: str) -> bool:
    return project_path(project_id).is_dir()


def list_projects():
    ensure_dirs()
    result = []
    for p in sorted(PROJECTS_DIR.iterdir()):
        if p.is_dir():
            result.append(p.name)
    return result


def create_project(project_id: str):
    ensure_dirs()
    path = project_path(project_id)
    if path.exists():
        raise ProjectError("Проект '{}' уже существует.".format(project_id))
    path.mkdir(parents=True)
    return path


def delete_project(project_id: str):
    path = project_path(project_id)
    if not path.is_dir():
        raise ProjectError("Проект '{}' не найден.".format(project_id))
    shutil.rmtree(path)


def benchmark_file(project_id: str) -> Path:
    return project_path(project_id) / "benchmark-xccdf.xml"


def oval_file(project_id: str, filename: str) -> Path:
    if "/" in filename or "\\" in filename or filename in ("", ".", ".."):
        raise ProjectError("Недопустимое имя OVAL-файла.")
    return project_path(project_id) / filename


def list_oval_files(project_id: str):
    path = project_path(project_id)
    if not path.is_dir():
        raise ProjectError("Проект '{}' не найден.".format(project_id))
    return sorted(
        f.name for f in path.iterdir()
        if f.is_file() and f.name != "benchmark-xccdf.xml" and f.suffix == ".xml"
    )


def delete_oval_file(project_id: str, filename: str):
    path = oval_file(project_id, filename)
    if not path.exists():
        raise ProjectError("Файл '{}' не найден в проекте '{}'.".format(filename, project_id))
    path.unlink()
