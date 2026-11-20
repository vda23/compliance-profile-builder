"""
Английские версии справочного содержимого: каталог проверок, темы базы
знаний, разделы, документы.

Справочные данные (catalog/*.json, knowledge/*.json) хранятся на русском.
Английский текст ищется по русскому: сначала в словаре MANUAL
(i18n_en_data.py), затем по шаблонам PATTERNS — так типовые формулировки
вида «Проверяется содержимое файла …» переводятся без отдельной записи.

Если перевода нет, translate() возвращает None, и интерфейс показывает
русский текст. Автотест test_i18n.py следит, чтобы для поставляемых
данных перевод был всегда.
"""
import re

from .i18n_en_data import MANUAL

_SYSCTL_FILE = " in /etc/sysctl.d/ and apply it with sysctl -p."
_BOOT = " to the kernel boot parameters (GRUB_CMDLINE_LINUX in /etc/default/grub) and update the bootloader."

PATTERNS = [
    (r"Проверяется содержимое файла (\S+)\.", r"Checks the contents of \1."),
    (r"Проверяется параметр реестра (\S+(?: \S+)*?)\.$", r"Checks the registry value \1."),
    (r"Проверяется, что параметр ядра (\S+) (?:имеет значение|равен) (\S+)\.", r"Checks that kernel parameter \1 is set to \2."),
    (r"Проверяется, что в параметрах загрузки ядра задано (\S+)\.", r"Checks that the kernel boot parameters include \1."),
    (r"Проверяется атрибут (\S+) файла (\S+)\.", r"Checks the \1 attribute of \2."),
    (r"Проверяется наличие файла (\S+)\.", r"Checks that \1 exists."),
    (r"Проверяется, что установлен пакет (\S+)\.", r"Checks that the \1 package is installed."),
    (r"Проверяется, что владельцем файла (\S+) является суперпользователь \(uid 0\)\.", r"Checks that \1 is owned by the superuser (uid 0)."),
    (r"Задать (\S+) = (\S+) в /etc/sysctl\.d/ и применить sysctl -p\.", r"Set \1 = \2" + _SYSCTL_FILE),
    (r"Добавить (\S+) в параметры загрузки ядра \(GRUB_CMDLINE_LINUX в /etc/default/grub\) и обновить загрузчик\.", r"Add \1" + _BOOT),
    (r"Привести права доступа к файлу (\S+) в соответствие с рекомендацией\.", r"Set the permissions of \1 as recommended."),
]
_COMPILED = [(re.compile("^" + p.lstrip("^") + ("" if p.endswith("$") else "$")), r) for p, r in PATTERNS]


def translate(text):
    """Английская версия справочного текста или None."""
    if not text:
        return text
    if text in MANUAL:
        return MANUAL[text]
    for rx, repl in _COMPILED:
        if rx.match(text):
            return rx.sub(repl, text)
    return None


_BACK = None


def translate_back(text):
    """Русская версия английского справочного текста (по словарю) или None."""
    global _BACK
    if _BACK is None:
        _BACK = {en: ru for ru, en in MANUAL.items()}
    return _BACK.get(text)


def entry_en(entry):
    """Поля записи каталога на английском — только те, для которых есть перевод."""
    out = {}
    for f in ("title", "description", "rationale", "remediation", "notes", "category"):
        v = translate(entry.get(f))
        if v:
            out[f + "_en"] = v
    return out
