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

from . import catalog, knowledge, oval_xml, storage, xccdf_xml, xmlcompat

DISCLAIMER = (
    "Профиль создан автоматически по загруженному документу и является ЧЕРНОВИКОМ. "
    "Перед применением проверьте каждое правило: соответствие пункту документа, "
    "пути к файлам и эталонные значения для вашей версии операционной системы. "
    "Часть требований документа не проверяется техническими средствами — см. отчёт о покрытии. "
    "Любое правило можно изменить или удалить в конструкторе."
)

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
        root = xmlcompat.fromstring(z.read("word/numbering.xml"))
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
        root = xmlcompat.fromstring(z.read("word/styles.xml"))
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
    with zipfile.ZipFile(path) as z:
        root = xmlcompat.fromstring(z.read("word/document.xml"))
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
    with zipfile.ZipFile(path) as z:
        root = xmlcompat.fromstring(z.read("content.xml"))
        roots = [root]
        try:
            roots.append(xmlcompat.fromstring(z.read("styles.xml")))
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
    items = []
    section = ""
    for p in paragraphs:
        m = _ITEM.match(p)
        if m:
            items.append({"number": m.group(1), "text": m.group(2).strip(), "section": section})
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


def match_concepts(text):
    """Темы требований, узнанные в тексте пункта, с перечнем сработавших
    формулировок. Работает и для русского, и для английского текста."""
    # Сравнение идёт по основам слов: в документе «регистрацию событий»,
    # в тезаурусе «регистрация событий» — без нормализации словоформ
    # такие совпадения теряются.
    norm = knowledge.normalize(text)          # обороты приведены к виду тезауруса
    tstems = knowledge.stems(norm)
    out = []
    for c in knowledge.load_concepts():
        # 1) точное вхождение формулировки — сильный признак
        hits = [ph for ph in (c.get("ru", []) + c.get("en", []))
                if knowledge.phrase_in_text(ph, tstems)]
        score = 3.0 * len(set(hits))
        # 2) частичное сходство — ловит формулировки, которых в тезаурусе нет
        sim, shared = knowledge.similarity(text, c["id"])
        if sim >= 0.45:
            score += sim
        if score <= 0:
            continue
        out.append({"concept_id": c["id"], "title": c.get("title"),
                    "hits": sorted(set(hits)), "similar": shared[:6],
                    "score": round(score, 2),
                    "kind": "формулировка" if hits else "сходство"})
    out.sort(key=lambda x: -x["score"])
    return out[:6]


def match_items(items, os_name=None, pack=None):
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
            # Ссылка на пункт прямо в записи каталога — самое сильное совпадение
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
                "manual": bool(entry.get("manual")),
                "score": int(round(score)),
                "matched_tokens": sorted(exact),
                "matched_keywords": sorted(kw_hits),
                "matched_concepts": sorted(shared),
            })
        cands.sort(key=lambda c: -c["score"])
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
                benchmark_id=None, profile_id=None):
    """Создаёт проект и разворачивает в него сопоставленные проверки.

    Берутся только кандидаты с уверенностью не ниже указанной: остальное
    остаётся человеку. Каждое правило получает идентификатор требования
    с номером пункта исходного документа."""
    order = {"высокая": 3, "средняя": 2, "низкая": 1, "нет": 0}
    floor = order.get(min_confidence, 2)

    storage.ensure_dirs()
    if not storage.project_exists(project_id):
        storage.create_project(project_id)
    xccdf_xml.create_benchmark(
        project_id,
        benchmark_id or "xccdf_custom_benchmark_%s" % re.sub(r"\W+", "_", project_id).strip("_"),
        "ru-RU", "draft",
        doc_title,
        "%s\n\n%s" % (doc_title, DISCLAIMER),
        "1.0",
    )
    oval_xml.create_oval_file(project_id, filename, "Custom", "1.0", "5.11.2")

    applied, manual, skipped, seen = [], [], [], set()
    for m in matches:
        if order.get(m["confidence"], 0) < floor or not m["candidates"]:
            skipped.append({"number": m["number"], "reason": "нет уверенного сопоставления",
                            "text": m["text"][:160]})
            continue
        best = m["candidates"][0]
        entry = catalog.get_entry(best["entry_id"])
        if entry.get("manual"):
            manual.append({"number": m["number"], "entry_id": entry["id"],
                           "title": entry.get("title"),
                           "reason": entry.get("notes") or "требуется организационная мера"})
            continue
        if entry["id"] in seen:          # одна проверка на несколько пунктов
            continue
        seen.add(entry["id"])
        catalog.apply_entry(project_id, filename, entry, os_name=os_name,
                            ident_system=doc_title, ident_value=m["number"])
        applied.append({"number": m["number"], "entry_id": entry["id"], "title": entry.get("title")})

    # профиль со всеми созданными правилами
    b = xccdf_xml.get_benchmark_dict(project_id)
    pid = profile_id or "xccdf_custom_profile_draft"
    if b["rules"]:
        xccdf_xml.add_profile(project_id, pid, "Черновой профиль: %s" % doc_title, DISCLAIMER)
        for r in b["rules"]:
            xccdf_xml.set_select(project_id, pid, r["id"], True)

    return {
        "disclaimer": DISCLAIMER,
        "project_id": project_id,
        "applied": applied,
        "manual": manual,
        "skipped": skipped,
        "summary": {
            "items_total": len(matches),
            "rules_created": len(applied),
            "items_manual": len(manual),
            "items_unmatched": len(skipped),
        },
    }
