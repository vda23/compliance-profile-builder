"""
Разбор нормативного документа и сборка чернового профиля соответствия.

ЧТО ДЕЛАЕТ
    1. Читает документ (DOCX, ODT, TXT/MD) и выделяет пронумерованные пункты.
    2. Сопоставляет каждый пункт с записями каталога проверок.
    3. Разворачивает подтверждённые сопоставления в профиль, проставляя
       в идентификатор требования номер пункта исходного документа.

ПОЧЕМУ ИМЕННО DOCX/ODT
    Оба формата — это ZIP с XML внутри, текст размечен по абзацам и читается
    стандартной библиотекой. В PDF текст хранится как набор глифов, и при
    нестандартной кодировке шрифта кириллица извлекается искажённой —
    восстановить её без данных о шрифтах невозможно. Поэтому PDF
    поддерживается только как запасной вариант и с предупреждением.

ГРАНИЦЫ ПРИМЕНИМОСТИ
    Сопоставление опирается на две вещи: точные технические обозначения в
    тексте пункта (имена параметров, пути к файлам) и совпадение ключевых
    слов. Документы с конкретными формулировками («установить значение
    sysctl-опции kernel.kptr_restrict=2») сопоставляются надёжно. Документы
    с абстрактными мерами («обеспечить идентификацию пользователей»)
    достоверного сопоставления не дают — по ним выдаются только слабые
    кандидаты, и решение остаётся за человеком.

    Результат всегда считается ЧЕРНОВИКОМ и требует проверки специалистом.
"""
import os
import re
import tempfile
import zipfile

from . import catalog, coverage, i18n_en, knowledge, oval_xml, safezip, storage, xccdf_xml, xmlcompat

DISCLAIMER = (
    "Профиль создан автоматически по загруженному документу и является ЧЕРНОВИКОМ. "
    "Перед применением проверьте каждое правило: соответствие пункту документа, "
    "пути к файлам и эталонные значения для вашей версии операционной системы. "
    "Часть требований документа не проверяется техническими средствами — см. отчёт о покрытии. "
    "Любое правило можно изменить или удалить в конструкторе."
)

DISCLAIMER_EN = (
    "This profile was created automatically from the uploaded document and is a DRAFT. "
    "Before use, review every rule: that it matches the document item, the file paths "
    "and the reference values for your operating system version. "
    "Some requirements of the document cannot be checked by technical means — see the coverage report. "
    "Any rule can be changed or deleted in the builder."
)

# Причины в отчёте о покрытии: код → (русский, английский) текст
REASONS = {
    "org_decision": ("отнесено к организационным мерам при разборе документа",
                     "classified as an organisational measure during document review"),
    "no_match": ("нет уверенного сопоставления", "no confident match"),
    "org_measure": ("требуется организационная мера", "an organisational measure is required"),
}


def _titles(entry, lang):
    """Название проверки на языке профиля и в обоих языках — для интерфейса."""
    ru = entry.get("title") or ""
    en = i18n_en.translate(ru) or ru
    return {"title": en if lang == "en" else ru, "title_ru": ru, "title_en": en}


def disclaimer(lang):
    return DISCLAIMER_EN if lang == "en" else DISCLAIMER


def document_lang(items):
    """Язык документа по большинству пунктов: "en" или "ru"."""
    en = sum(1 for it in items if it.get("lang") == "en")
    return "en" if items and en * 2 > len(items) else "ru"


def _reason(code, entry=None):
    """Причина в обоих языках: {"reason": …, "reason_en": …}."""
    if entry is not None and entry.get("notes"):
        return {"reason": entry["notes"], "reason_en": i18n_en.translate(entry["notes"]) or entry["notes"]}
    ru, en = REASONS[code]
    return {"reason": ru, "reason_en": en}


SUPPORTED = (".docx", ".odt", ".txt", ".md")

# Номер пункта в начале абзаца: 2.4.1 / 5.2 / 1.1.1.1
_ITEM = re.compile(r"^\s*(\d{1,2}(?:\.\d{1,2}){1,3})\.?\s+(.+)$", re.S)

# Технические обозначения, по которым сопоставление наиболее надёжно
_SYSCTL = re.compile(r"\b([a-z][a-z0-9_]*(?:\.[a-z0-9_]+)+)\s*=\s*([A-Za-z0-9,._/-]+)")
_DOTTED = re.compile(r"\b([a-z][a-z0-9_]*(?:\.[a-z0-9_]+){1,4})\b")
_PATH = re.compile(r"(/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.*-]+)*)")
_CAMEL = re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b")
_BOOTOPT = re.compile(r"\b([a-z][a-z0-9_]*(?:=[A-Za-z0-9,.-]+)?)\b")

_RU = re.compile(r"[А-Яа-яЁё]")


class ImportError_(Exception):
    pass


# ------------------------------------------------------------------ чтение

_TYPED_NUMBER = re.compile(r"^\s*\d{1,2}(?:\.\d{1,2})*\.?\s")


def _hier(counters, level):
    """Иерархический номер пункта по счётчикам уровней: 1, 1.2, 1.2.3."""
    return ".".join(str(max(c, 1)) for c in counters[:level + 1])


# ----------------------------------------------------------------- DOCX
#
# В Word номер пункта при автоматической нумерации НЕ хранится в тексте
# абзаца: у абзаца есть только ссылка на список (w:numPr — номер списка и
# уровень), а сам номер Word вычисляет при отображении. Нормативные
# документы почти всегда оформлены автонумерацией, поэтому без
# восстановления номеров пункты в них не находились вовсе.
#
# Номер восстанавливается по счётчикам уровней каждого списка. Маркированные
# списки (bullet) номеров не дают — это перечисления внутри пункта.

def _docx_numbering(z, W):
    """Описание списков: numId -> abstractNumId и форматы уровней."""
    num_to_abs, levels = {}, {}
    try:
        root = xmlcompat.fromstring_untrusted(safezip.read(z, "word/numbering.xml"))
    except KeyError:
        return num_to_abs, levels
    for an in root.iter(W + "abstractNum"):
        aid = an.get(W + "abstractNumId")
        lv = {}
        for l in an.iter(W + "lvl"):
            fmt = l.find(W + "numFmt")
            st = l.find(W + "start")
            lv[int(l.get(W + "ilvl", "0"))] = {
                "fmt": fmt.get(W + "val") if fmt is not None else "decimal",
                "start": int(st.get(W + "val")) if st is not None else 1,
            }
        levels[aid] = lv
    for n in root.iter(W + "num"):
        ab = n.find(W + "abstractNumId")
        if ab is not None:
            num_to_abs[n.get(W + "numId")] = ab.get(W + "val")
    return num_to_abs, levels


def _docx_style_numbering(z, W):
    """Нумерация, заданная через стиль абзаца (часто у заголовков)."""
    out = {}
    try:
        root = xmlcompat.fromstring_untrusted(safezip.read(z, "word/styles.xml"))
    except KeyError:
        return out
    for st in root.iter(W + "style"):
        np_ = st.find("%spPr/%snumPr" % (W, W))
        if np_ is None:
            continue
        nid = np_.find(W + "numId")
        il = np_.find(W + "ilvl")
        if nid is not None:
            out[st.get(W + "styleId")] = (nid.get(W + "val"), int(il.get(W + "val")) if il is not None else 0)
    return out


def _docx_paragraphs(path):
    """Абзацы DOCX с восстановленными номерами автоматической нумерации."""
    W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    with safezip.open_checked(path) as z:
        root = xmlcompat.fromstring_untrusted(safezip.read(z, "word/document.xml"))
        num_to_abs, levels = _docx_numbering(z, W)
        style_num = _docx_style_numbering(z, W)

    counters = {}          # abstractNumId -> [счётчик уровня 0, 1, ...]
    out = []
    for p in root.iter(W + "p"):
        text = "".join((t.text or "") for t in p.iter(W + "t")).strip()
        if not text:
            continue

        num_id, ilvl = None, 0
        ppr = p.find(W + "pPr")
        if ppr is not None:
            np_ = ppr.find(W + "numPr")
            if np_ is not None:
                nid = np_.find(W + "numId")
                il = np_.find(W + "ilvl")
                num_id = nid.get(W + "val") if nid is not None else None
                ilvl = int(il.get(W + "val")) if il is not None else 0
            elif ppr.find(W + "pStyle") is not None:
                sid = ppr.find(W + "pStyle").get(W + "val")
                if sid in style_num:
                    num_id, ilvl = style_num[sid]

        aid = num_to_abs.get(num_id) if num_id not in (None, "0") else None
        lvl = (levels.get(aid) or {}).get(ilvl, {"fmt": "decimal", "start": 1}) if aid else None

        if lvl and lvl["fmt"] not in ("bullet", "none") and not _TYPED_NUMBER.match(text):
            c = counters.setdefault(aid, [0] * 9)
            c[ilvl] = c[ilvl] + 1 if c[ilvl] else lvl["start"]
            for deeper in range(ilvl + 1, 9):      # вложенные уровни начинаются заново
                c[deeper] = 0
            text = "%s. %s" % (_hier(c, ilvl), text)
        out.append(text)
    return out


# ------------------------------------------------------------------ ODT
#
# В ODT нумерованный список — это вложенные text:list / text:list-item;
# номер, как и в Word, вычисляется при отображении. Является ли уровень
# нумерованным или маркированным, определяет стиль списка.

def _odt_list_styles(roots, T):
    """Стиль списка -> {уровень: True, если нумерованный}."""
    out = {}
    for r in roots:
        for ls in r.iter(T + "list-style"):
            name = ls.get(T + "name") or ls.get("{urn:oasis:names:tc:opendocument:xmlns:style:1.0}name")
            lv = {}
            for ch in ls:
                tag = ch.tag.split("}")[-1]
                level = int(ch.get(T + "level", "1"))
                lv[level] = (tag == "list-level-style-number")
            if name:
                out[name] = lv
    return out


def _odt_paragraphs(path):
    """Абзацы ODT с восстановленными номерами нумерованных списков."""
    T = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
    with safezip.open_checked(path) as z:
        root = xmlcompat.fromstring_untrusted(safezip.read(z, "content.xml"))
        roots = [root]
        try:
            roots.append(xmlcompat.fromstring_untrusted(safezip.read(z, "styles.xml")))
        except KeyError:
            pass
    list_styles = _odt_list_styles(roots, T)
    out = []

    def para_text(el):
        return "".join(el.itertext()).strip()

    def walk_list(lst, depth, counters, style):
        style = lst.get(T + "style-name") or style
        numbered = (list_styles.get(style) or {}).get(depth + 1, True)
        for item in lst:
            if item.tag != T + "list-item":
                continue
            counters[depth] += 1
            for deeper in range(depth + 1, len(counters)):
                counters[deeper] = 0
            first = True
            for ch in item:
                if ch.tag in (T + "p", T + "h"):
                    text = para_text(ch)
                    if not text:
                        continue
                    if first and numbered and not _TYPED_NUMBER.match(text):
                        text = "%s. %s" % (_hier(counters, depth), text)
                    first = False
                    out.append(text)
                elif ch.tag == T + "list":
                    walk_list(ch, depth + 1, counters, style)

    def walk(node, top_counters):
        for ch in node:
            if ch.tag == T + "list":
                # новый список верхнего уровня начинает нумерацию заново,
                # если явно не указано продолжение
                if ch.get(T + "continue-numbering") != "true" and not ch.get(T + "continue-list"):
                    top_counters[:] = [0] * 9
                walk_list(ch, 0, top_counters, None)
            elif ch.tag in (T + "p", T + "h"):
                text = para_text(ch)
                if text:
                    out.append(text)
            else:
                walk(ch, top_counters)

    walk(root, [0] * 9)
    return out


def _plain_paragraphs(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return [ln.strip() for ln in f if ln.strip()]


def read_document_bytes(data, filename):
    """Абзацы документа, переданного содержимым файла.

    Формат определяется по имени файла. Данные кладутся во временный файл:
    и DOCX, и ODT читаются как ZIP-архивы, а zipfile работает с путём."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in SUPPORTED:
        raise ImportError_(
            "Формат %s не поддерживается. Загрузите документ в формате DOCX, ODT или TXT. "
            "PDF не используется: в нём текст хранится как набор глифов, и при нестандартной "
            "кодировке шрифта кириллица извлекается искажённой." % (ext or "без расширения"))
    fd, tmp = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        return read_document(tmp)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def read_document(path):
    """Абзацы документа. Формат определяется расширением."""
    try:
        return _read_document(path)
    except safezip.SafeZipError as e:
        raise ImportError_(str(e) + " Документ не обработан: похоже на повреждённый или вредоносный файл.")
    except xmlcompat.UnsafeXmlError as e:
        raise ImportError_(str(e))
    except (zipfile.BadZipFile, KeyError):
        # DOCX и ODT — это ZIP-архивы. Если архив не открывается или в нём
        # нет основного содержимого, файл повреждён или переименован из
        # другого формата (например, .doc или .pdf).
        raise ImportError_(
            "Не удалось прочитать документ: файл повреждён или не является настоящим "
            "DOCX/ODT. Откройте его в текстовом редакторе и сохраните заново в формате DOCX или ODT.")


def _read_document(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return _docx_paragraphs(path)
    if ext == ".odt":
        return _odt_paragraphs(path)
    if ext in (".txt", ".md"):
        return _plain_paragraphs(path)
    raise ImportError_(
        "Формат %s не поддерживается. Загрузите документ в формате DOCX, ODT или TXT. "
        "PDF не используется: в нём текст хранится как набор глифов, и при нестандартной "
        "кодировке шрифта кириллица извлекается искажённой." % (ext or "без расширения")
    )


# ------------------------------------------------------- выделение пунктов

def extract_items(paragraphs):
    """Пронумерованные пункты документа.

    Абзац без номера присоединяется к предыдущему пункту — так подхватывается
    текст, разорванный переносами строк."""
    # Заголовок раздела одного уровня («2. Парольная защита») — граница
    # между пунктами, а не продолжение текста. Раньше он приклеивался к
    # предыдущему пункту, и слова заголовка искажали сопоставление.
    # Название раздела сохраняется как контекст: «Парольная защита» —
    # сильная подсказка о теме пунктов 2.1 и 2.2.
    section_re = re.compile(r"^\s*(\d{1,2})\.?\s+(.{1,120})$")
    # Одноуровневые пункты («21. Меры по идентификации…») — так нумеруются
    # пункты приказов ФСТЭК и многих регламентов. Раньше они считались
    # заголовками разделов, и в приказе не находилось ни одного требования.
    # Отличаем пункт от заголовка по виду: заголовок короткий и не
    # заканчивается знаком препинания («2. Парольная защита»), пункт —
    # длинный или оканчивается точкой, точкой с запятой или двоеточием.
    single_re = re.compile(r"^\s*(\d{1,3})\.\s+(.+)$", re.S)
    roman_re = re.compile(r"^\s*([IVXLC]{1,6})\.\s+(.{1,160})$")

    def is_heading(text):
        t = text.strip()
        return len(t) <= 90 and not re.search(r"[.;:]\s*$", t)

    items = []
    section = ""
    for p in paragraphs:
        m = _ITEM.match(p)
        if m:
            items.append({"number": m.group(1), "text": m.group(2).strip(), "section": section})
            continue
        rm = roman_re.match(p)
        if rm and is_heading(rm.group(2)):
            section = rm.group(2).strip()          # «III. Требования к мерам защиты…»
            if items:
                items[-1]["closed"] = True
            continue
        sm = single_re.match(p)
        if sm and not is_heading(sm.group(2)):
            items.append({"number": sm.group(1), "text": sm.group(2).strip(), "section": section})
            continue
        sm = section_re.match(p)
        if sm and len(p) <= 120:
            section = sm.group(2).strip()
            if items:
                items[-1]["closed"] = True   # дальше текст к пункту не добавляется
            continue
        if items and not items[-1].get("closed"):
            items[-1]["text"] += " " + p

    # Отсев оглавления: там те же номера, но текст короткий и заканчивается
    # приклеенным номером страницы. Из дублей оставляем самый длинный —
    # это запись из тела документа, а не из содержания.
    best = {}
    for it in items:
        prev = best.get(it["number"])
        if prev is None or len(it["text"]) > len(prev["text"]):
            best[it["number"]] = it
    items = [best[n] for n in sorted(best, key=lambda x: [int(p) for p in x.split(".")])]

    # Пункт-заголовок с вводной фразой: «2.2 Ограничение механизмов получения
    # привилегий. При ограничении … необходимо:». Требования — в дочерних
    # пунктах 2.2.1, 2.2.2. Признаки: у пункта есть дочерние пункты и его
    # текст заканчивается двоеточием. Такой пункт становится разделом для
    # дочерних, а не требованием: иначе он получал проверку и завышал
    # покрытие в отчёте.
    numbers = [it["number"] for it in items]
    parents = set()
    for it in items:
        txt = re.sub(r"\s+", " ", it["text"]).strip()
        has_children = any(n.startswith(it["number"] + ".") for n in numbers)
        if has_children and txt.endswith(":"):
            parents.add(it["number"])
            title = re.split(r"(?<=[a-zа-яё)])\s+(?=[А-ЯA-Z])", txt, maxsplit=1)[0]
            for child in items:
                if child["number"].startswith(it["number"] + "."):
                    child["section"] = title[:120]
    items = [it for it in items if it["number"] not in parents]

    for it in items:
        it["text"] = re.sub(r"\s+", " ", it["text"]).strip()
        it["lang"] = "ru" if _RU.search(it["text"]) else "en"
        it["tokens"] = _tokens(it["text"])
    return items


def _tokens(text):
    """Технические обозначения из текста пункта: параметры вида a.b.c=знач,
    точечные имена, пути к файлам, параметры в CamelCase."""
    out = set()
    for name, value in _SYSCTL.findall(text):
        out.add(name.lower())
        out.add(("%s=%s" % (name, value)).lower().rstrip("."))
    for d in _DOTTED.findall(text):
        if "." in d and not d.startswith("."):
            out.add(d.lower().rstrip("."))
    for p in _PATH.findall(text):
        out.add(p.lower().rstrip("."))
        out.add(os.path.basename(p).lower().rstrip("."))
    for c in _CAMEL.findall(text):
        out.add(c.lower())
    return {t for t in out if len(t) > 2}


# ------------------------------------------------------------ сопоставление

def _entry_signature(entry):
    """Опорные обозначения записи каталога: то, по чему её можно узнать
    в тексте пункта."""
    sig = set()
    check = entry.get("check") or {}
    obj = check.get("object") or {}
    for key in ("name", "unit", "property"):
        v = obj.get(key)
        if isinstance(v, str) and v:
            sig.add(v.lower())
    path, fname = obj.get("path"), obj.get("filename")
    if isinstance(path, str) and isinstance(fname, str):
        sig.add(("%s/%s" % (path.rstrip("/"), fname)).lower())
        sig.add(fname.lower())
    pattern = obj.get("pattern")
    if isinstance(pattern, str):
        # литералы из регулярного выражения: имена параметров конфигурации
        for lit in re.findall(r"[A-Za-z][A-Za-z0-9_.]{3,}", pattern):
            if lit not in ("space", "za", "az"):
                sig.add(lit.lower().replace("\\", ""))
    return {s for s in sig if len(s) > 2}


def _phrase_hit(phrase, text_stems, text_lower):
    """Совпадение формулировки с текстом пункта.

    Формулировка с точкой или косой чертой — имя файла или путь
    («.service», «/etc/shadow»): она совпадает только буквально. При
    сравнении по основам слов точка и черта отбрасываются, и «.service»
    превращался в обычное слово service — пункт «auditd service is
    enabled» уходил в тему прав на файлы служб."""
    if "." in phrase or "/" in phrase:
        return phrase.lower() in text_lower
    return knowledge.phrase_in_text(phrase, text_stems)


def match_concepts(text):
    """Темы требований, узнанные в тексте пункта, с перечнем сработавших
    формулировок. Работает и для русского, и для английского текста."""
    # Сравнение идёт по основам слов: в документе «регистрацию событий»,
    # в тезаурусе «регистрация событий» — без нормализации словоформ
    # такие совпадения теряются.
    norm = knowledge.normalize(text)          # обороты приведены к виду тезауруса
    tstems = knowledge.stems(norm)
    low = (text or "").lower()
    out = []
    for c in knowledge.load_concepts():
        # 1) точное вхождение формулировки — сильный признак
        hits = [ph for ph in (c.get("ru", []) + c.get("en", []))
                if _phrase_hit(ph, tstems, low)]
        score = 3.0 * len(set(hits))
        # 2) частичное сходство — ловит формулировки, которых в тезаурусе нет
        sim, shared = knowledge.similarity(text, c["id"])
        if sim >= 0.45:
            score += sim
        if score <= 0:
            continue
        out.append({"concept_id": c["id"], "title": c.get("title"),
                    "title_en": c.get("title_en") or i18n_en.translate(c.get("title")),
                    "hits": sorted(set(hits)), "similar": shared[:6],
                    "score": round(score, 2),
                    "kind": "формулировка" if hits else "сходство"})
    out.sort(key=lambda x: -x["score"])
    return out[:6]


def match_items(items, os_name=None, pack=None, ref_pack=None):
    """Для каждого пункта — кандидаты из каталога с оценкой уверенности.

    Оценка складывается из двух источников:
      - совпадение технического обозначения (имя параметра, путь) — сильный
        признак, документ и каталог говорят буквально одним словом;
      - совпадение ключевых слов — слабый признак, помогает на общих
        формулировках, но самостоятельным основанием не является.
    """
    entries = catalog.entries_for_os(os_name) if os_name else catalog.load_catalog()
    if pack:
        entries = [e for e in entries if e.get("pack") == pack]
    prepared = [(e, _entry_signature(e), {k.lower() for k in e.get("keywords", [])}) for e in entries]

    links = knowledge.catalog_links()
    results = []
    for it in items:
        low = it["text"].lower()
        concepts = match_concepts(it["text"])
        if not concepts and it.get("section"):
            # текст пункта темы не дал — пробуем название раздела
            concepts = [dict(c, kind="раздел") for c in match_concepts(it["section"])]
        concept_ids = {c["concept_id"] for c in concepts}
        top = max((c["score"] for c in concepts), default=0) or 1
        concept_weight = {c["concept_id"]: c["score"] / top for c in concepts}
        cands = []
        for entry, sig, kws in prepared:
            exact = it["tokens"] & sig
            score = 100 * len(exact)
            # Ссылка на пункт прямо в записи каталога — самое сильное совпадение,
            # но только если загружен именно этот документ (пакет указан явно
            # или определён по содержимому документа). Раньше совпадение номера
            # давало бонус для любого документа: пункт «2.1.1» чужого регламента
            # получал проверку ФСТЭК 2.1.1 с высокой уверенностью.
            if pack or (ref_pack and entry.get("pack") == ref_pack):
                for r in entry.get("refs", []):
                    if r.get("value") == it["number"]:
                        score += 500
            kw_hits = {k for k in kws if len(k) > 3 and k in low}
            score += 8 * len(kw_hits)
            # Тема требования, узнанная по тезаурусу: связывает формулировку
            # документа с проверкой, даже когда общих слов у них нет.
            shared = concept_ids & set(links.get(entry["id"], []))
            # Вклад темы пропорционален её силе: главная тема пункта даёт
            # полный вес, побочная — долю. Раньше любая общая тема давала
            # одинаковые +60, и проверка по случайной побочной теме
            # перевешивала проверку по главной.
            score += sum(60 * concept_weight.get(cid, 0) for cid in shared)
            if score <= 0:
                continue
            cands.append({
                "entry_id": entry["id"],
                "title": entry.get("title"),
                "title_en": i18n_en.translate(entry.get("title")),
                "manual": bool(entry.get("manual")),
                "score": int(round(score)),
                "matched_tokens": sorted(exact),
                "matched_keywords": sorted(kw_hits),
                "matched_concepts": sorted(shared),
            })
        # При равных баллах: техническая проверка раньше организационной меры,
        # затем — больше общих слов в названии проверки и тексте пункта
        # («…при входе по SSH» → «Запрет входа по SSH с пустым паролем»).
        item_stems = set(knowledge.stems(it["text"]))
        for c in cands:
            c["_title_overlap"] = len(item_stems & set(knowledge.stems(c["title"] or "")))
        cands.sort(key=lambda c: (-c["score"], c["manual"], -c["_title_overlap"]))
        for c in cands:
            c.pop("_title_overlap", None)
        best = cands[0]["score"] if cands else 0
        results.append({
            "number": it["number"],
            "section": it.get("section", ""),
            "text": it["text"][:400],
            "lang": it["lang"],
            "concepts": concepts[:4],
            "candidates": cands[:5],
            "confidence": "высокая" if best >= 500 else "средняя" if best >= 60 else "низкая" if best > 0 else "нет",
        })
    return results


# --------------------------------------------------- сборка чернового профиля

def build_draft(project_id, matches, doc_title, os_name=None,
                filename="checks-oval.xml", min_confidence="средняя",
                benchmark_id=None, profile_id=None, lang=None):
    """Создаёт проект и разворачивает в него сопоставленные проверки.

    Берутся только кандидаты с уверенностью не ниже указанной: остальное
    остаётся человеку. Каждое правило получает идентификатор требования
    с номером пункта исходного документа."""
    order = {"высокая": 3, "средняя": 2, "низкая": 1, "нет": 0}
    floor = order.get(min_confidence, 2)
    # Язык профиля — язык документа: по английскому документу правила,
    # описания и заголовки создаются на английском (xml:lang en-US).
    if lang not in ("ru", "en"):
        lang = document_lang(matches)
    note = disclaimer(lang)

    storage.ensure_dirs()
    if not storage.project_exists(project_id):
        storage.create_project(project_id)
    xccdf_xml.create_benchmark(
        project_id,
        benchmark_id or "xccdf_custom_benchmark_%s" % re.sub(r"\W+", "_", project_id).strip("_"),
        "en-US" if lang == "en" else "ru-RU", "draft",
        doc_title,
        "%s\n\n%s" % (doc_title, note),
        "1.0",
    )
    oval_xml.create_oval_file(project_id, filename, "Custom", "1.0", "5.11.2")

    # Решение по каждому пункту (поле decision, задаётся на экране разбора):
    #   "auto" или нет поля — лучший кандидат, если уверенность не ниже порога;
    #   "exclude"           — пункт исключён пользователем;
    #   "manual"            — пользователь отнёс пункт к организационным мерам;
    #   идентификатор записи каталога — выбранная проверка, независимо от порога.
    #
    # Каждый пункт попадает в отчёт ровно в одну категорию. Раньше пункт,
    # сопоставленный с уже использованной проверкой, молча пропадал; теперь
    # он ссылается на то же правило, а правило получает его идентификатор.
    applied, manual, skipped, excluded = [], [], [], []
    rule_by_entry, extra_idents = {}, {}
    for m in matches:
        decision = m.get("decision") or "auto"
        if decision == "exclude":
            excluded.append({"number": m["number"], "text": m["text"][:300]})
            continue
        if decision == "manual":
            manual.append(dict({"number": m["number"], "entry_id": None, "title": "",
                                "text": m["text"][:300]}, **_reason("org_decision")))
            continue
        if decision == "auto":
            if order.get(m["confidence"], 0) < floor or not m["candidates"]:
                skipped.append(dict({"number": m["number"], "text": m["text"][:300]},
                                    **_reason("no_match")))
                continue
            entry_id = m["candidates"][0]["entry_id"]
        else:
            entry_id = decision
        entry = catalog.get_entry(entry_id)
        if entry.get("manual"):
            manual.append(dict({"number": m["number"], "entry_id": entry["id"],
                                "text": m["text"][:300]}, **dict(_titles(entry, lang), **_reason("org_measure", entry))))
            continue
        if entry["id"] in rule_by_entry:          # одна проверка закрывает несколько пунктов
            rid = rule_by_entry[entry["id"]]
            extra_idents.setdefault(rid, []).append({"system": doc_title, "value": m["number"]})
            applied.append(dict({"number": m["number"], "entry_id": entry["id"],
                                 "rule_id": rid, "shared": True, "text": m["text"][:300]}, **_titles(entry, lang)))
            continue
        res = catalog.apply_entry(project_id, filename, entry, os_name=os_name,
                                  ident_system=doc_title, ident_value=m["number"], lang=lang)
        rid = res["created"]["rules"][0]
        rule_by_entry[entry["id"]] = rid
        applied.append(dict({"number": m["number"], "entry_id": entry["id"],
                             "rule_id": rid, "shared": False, "text": m["text"][:300]}, **_titles(entry, lang)))

    # дополнительные идентификаторы требований у общих правил
    if extra_idents:
        rules = {r["id"]: r for r in xccdf_xml.get_benchmark_dict(project_id)["rules"]}
        for rid, more in extra_idents.items():
            xccdf_xml.update_rule(project_id, rid, idents=list(rules[rid]["idents"]) + more)

    # профиль со всеми созданными правилами
    b = xccdf_xml.get_benchmark_dict(project_id)
    pid = profile_id or "xccdf_custom_profile_draft"
    if b["rules"]:
        xccdf_xml.add_profile(project_id, pid,
                              ("Draft profile: %s" if lang == "en" else "Черновой профиль: %s") % doc_title, note)
        for r in b["rules"]:
            xccdf_xml.set_select(project_id, pid, r["id"], True)

    report = {
        "disclaimer": note,
        "disclaimer_ru": DISCLAIMER,
        "disclaimer_en": DISCLAIMER_EN,
        "lang": lang,
        "project_id": project_id,
        "applied": applied,
        "manual": manual,
        "skipped": skipped,
        "excluded": excluded,
        "summary": {
            "items_total": len(matches),
            "items_covered": len(applied),
            "rules_created": len(rule_by_entry),
            "items_manual": len(manual),
            "items_unmatched": len(skipped),
            "items_excluded": len(excluded),
        },
    }
    # Отчёт о покрытии сохраняется в проекте: его можно открыть позже
    # и выгрузить для заказчика (см. coverage.py).
    coverage.save(project_id, report, doc_title, os_name, min_confidence)
    return report
