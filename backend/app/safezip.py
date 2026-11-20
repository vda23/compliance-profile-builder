"""
Безопасное чтение ZIP-архивов из файлов пользователя.

Импортируемые проекты, DOCX и ODT — это ZIP-архивы. Ограничение размера
запроса (50 МБ) защищает только от большого архива, но не от «ZIP-бомбы»:
архив в сотни килобайт может распаковываться в гигабайты и исчерпать
память сервера.

Защита двухуровневая:
  1. по заголовкам архива — число файлов и заявленные размеры;
  2. при чтении — фактический объём распакованных данных, на случай если
     заголовки подделаны и занижают размер.
"""
import zipfile

MAX_ENTRIES = 2000
MAX_MEMBER = 64 * 1024 * 1024     # 64 МБ на один файл: document.xml такого размера не бывает
MAX_TOTAL = 256 * 1024 * 1024     # 256 МБ на архив целиком
CHUNK = 1024 * 1024


class SafeZipError(ValueError):
    pass


def _mb(n):
    return "%d МБ" % (n // (1024 * 1024))


def check(zf):
    """Проверка архива по заголовкам до чтения содержимого."""
    infos = zf.infolist()
    if len(infos) > MAX_ENTRIES:
        raise SafeZipError("В архиве слишком много файлов (%d, допустимо до %d)." % (len(infos), MAX_ENTRIES))
    total = 0
    for i in infos:
        if i.file_size > MAX_MEMBER:
            raise SafeZipError("Файл «%s» в архиве слишком большой после распаковки (%s, допустимо до %s)."
                               % (i.filename, _mb(i.file_size), _mb(MAX_MEMBER)))
        total += i.file_size
    if total > MAX_TOTAL:
        raise SafeZipError("Архив слишком большой после распаковки (%s, допустимо до %s)."
                           % (_mb(total), _mb(MAX_TOTAL)))


def read(zf, name, limit=MAX_MEMBER):
    """Чтение файла из архива с контролем фактического объёма."""
    out = bytearray()
    with zf.open(name) as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            out += chunk
            if len(out) > limit:
                raise SafeZipError("Файл «%s» в архиве слишком большой после распаковки (больше %s)."
                                   % (name, _mb(limit)))
    return bytes(out)


def open_checked(source):
    """Открывает архив (путь или файловый объект) и сразу проверяет заголовки."""
    zf = zipfile.ZipFile(source)
    try:
        check(zf)
    except SafeZipError:
        zf.close()
        raise
    return zf
