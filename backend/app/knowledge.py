"""
Тезаурус требований: формулировки нормативных документов и их связь
с записями технического каталога.

Файлы знаний лежат в backend/knowledge/*.json и загружаются без внешних
библиотек. Слой намеренно отделён от каталога проверок: каталог отвечает
на вопрос «как проверить», тезаурус — «как об этом пишут в документах».
"""
import json
import re
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")

_cache = {}


# ===================================================================
# Пользовательский слой базы знаний
#
# Поставляемая база (backend/knowledge/*.json) при обновлении сервиса
# заменяется целиком: install.sh перезаписывает backend/. Поэтому правки
# из редактора хранятся отдельно — в каталоге данных, который установщик
# сохраняет, рядом с проектами: data/knowledge/user-knowledge.json.
#
# Хранится не копия базы, а разница с ней: «добавлены такие формулировки,
# скрыты такие». Отсюда три свойства:
#   - обновление сервиса не трогает правки;
#   - темы и формулировки из новых версий подтягиваются сами;
#   - любую тему можно вернуть к поставляемому виду.
# ===================================================================

import copy
import re as _re_mod
import threading

_lock = threading.Lock()


def _user_path():
    from . import storage
    return os.path.join(str(storage.DATA_DIR), "knowledge", "user-knowledge.json")


def _empty_layer():
    return {"format": 1, "concepts": {}, "synonyms": {"add": [], "hide": []}}


def user_layer():
    """Слой правок как есть (для экспорта и редактора)."""
    if "user" in _cache:
        return _cache["user"]
    layer = _empty_layer()
    path = _user_path()
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            layer["concepts"] = data.get("concepts", {}) or {}
            syn = data.get("synonyms", {}) or {}
            layer["synonyms"] = {"add": syn.get("add", []) or [], "hide": syn.get("hide", []) or []}
        except (ValueError, OSError):
            # Повреждённый файл правок не должен ломать сервис: работаем на
            # поставляемой базе, файл остаётся на диске для разбора.
            layer = _empty_layer()
    _cache["user"] = layer
    return layer


def _save_layer(layer):
    path = _user_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(layer, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)          # атомарная замена: файл не бывает недописанным
    _cache.clear()


def _load_base():
    """Поставляемая база: темы и связи с каталогом."""
    if "base" in _cache:
        return _cache["base"]
    concepts, links = [], {}
    if os.path.isdir(KNOWLEDGE_DIR):
        for name in sorted(os.listdir(KNOWLEDGE_DIR)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(KNOWLEDGE_DIR, name), encoding="utf-8") as f:
                data = json.load(f)
            concepts.extend(data.get("concepts", []))
            links.update(data.get("catalog_links", {}))
    _cache["base"] = (concepts, links)
    return _cache["base"]


def _hint_key(h):
    return ((h.get("family") or "").strip(), (h.get("ref") or "").strip())


def _load():
    """Итоговая база: поставляемая + правки пользователя."""
    if "data" in _cache:
        return _cache["data"]
    base_concepts, base_links = _load_base()
    layer = user_layer()
    patches = layer.get("concepts", {})

    concepts = []
    links = {eid: list(cids) for eid, cids in base_links.items()}
    base_ids = set()
    for c in base_concepts:
        base_ids.add(c["id"])
        c = copy.deepcopy(c)
        p = patches.get(c["id"])
        c["user_created"] = False
        c["user_modified"] = bool(p)
        c["user_ru"], c["user_en"] = [], []
        c["hidden_ru"], c["hidden_en"] = [], []
        if p:
            if p.get("title"):
                c["title"] = p["title"]
            if p.get("title_en"):
                c["title_en"] = p["title_en"]
            for lang in ("ru", "en"):
                hide = set(p.get("hide_" + lang, []))
                add = [x for x in p.get("add_" + lang, []) if x not in c.get(lang, [])]
                c["hidden_" + lang] = [x for x in c.get(lang, []) if x in hide]
                c[lang] = [x for x in c.get(lang, []) if x not in hide] + add
                c["user_" + lang] = add
            hide_h = {_hint_key(h) for h in p.get("hide_hints", [])}
            hints = [h for h in c.get("doc_hints", []) if _hint_key(h) not in hide_h]
            have = {_hint_key(h) for h in hints}
            for h in p.get("add_hints", []):
                if _hint_key(h) not in have:
                    hints.append({"family": h["family"], "ref": h.get("ref", ""), "verify": False, "user": True})
            c["doc_hints"] = hints
        concepts.append(c)

    # темы, созданные пользователем
    for cid, p in patches.items():
        if not p.get("new") or cid in base_ids:
            continue
        concepts.append({
            "id": cid, "title": p.get("title") or cid, "title_en": p.get("title_en") or None,
            "themes": p.get("themes", []) or ["Пользовательские темы"],
            "ru": list(p.get("add_ru", [])), "en": list(p.get("add_en", [])),
            "doc_hints": [{"family": h["family"], "ref": h.get("ref", ""), "verify": False, "user": True}
                          for h in p.get("add_hints", [])],
            "user_created": True, "user_modified": True,
            "user_ru": list(p.get("add_ru", [])), "user_en": list(p.get("add_en", [])),
            "hidden_ru": [], "hidden_en": [],
        })

    # связи с каталогом
    for cid, p in patches.items():
        for eid in p.get("hide_links", []):
            if eid in links and cid in links[eid]:
                links[eid] = [x for x in links[eid] if x != cid]
        for eid in p.get("add_links", []):
            links.setdefault(eid, [])
            if cid not in links[eid]:
                links[eid].append(cid)

    _cache["data"] = (concepts, links)
    return _cache["data"]


def load_concepts():
    """Все концепты тезауруса."""
    return _load()[0]


def catalog_links():
    """Связь «запись каталога → концепты»."""
    return _load()[1]


def get_concept(concept_id):
    for c in load_concepts():
        if c["id"] == concept_id:
            return c
    return None


def document_families():
    """Документы, упомянутые в тезаурусе, с числом тем. Считаются именно темы,
    а не ссылки: одна тема может ссылаться на документ дважды (например, на
    две группы мер), и тогда число на плашке расходилось с результатом
    фильтра по ней."""
    out = {}
    for c in load_concepts():
        for fam in {h.get("family", "") for h in c.get("doc_hints", [])}:
            out[fam] = out.get(fam, 0) + 1
    return out


def concepts_for_catalog_entry(entry_id):
    ids = catalog_links().get(entry_id, [])
    return [c for c in load_concepts() if c["id"] in ids]


# ----------------------------------------------------- нормализация словоформ

import re as _re

# Окончания русских слов, отбрасываемые при сравнении. Список намеренно
# короткий: задача — свести словоформы одного слова к общей основе, а не
# построить полноценный морфологический разбор.
_ENDINGS = (
    "иями", "ями", "ами", "иях", "ях", "ах", "ов", "ев", "ий", "ие", "ия", "ию", "ий",
    "ых", "их", "ым", "им", "ом", "ем", "ой", "ей", "ая", "яя", "ую", "юю", "ое", "ее",
    "ы", "и", "а", "я", "о", "е", "у", "ю", "й", "ь",
)


def stem(word):
    """Грубая основа слова: отбрасывается наиболее длинное известное
    окончание. Для английских слов возвращается слово как есть.

    Знаки препинания по краям снимаются: точка в конце предложения иначе
    приклеивается к слову и ломает сравнение («паролей.» против «паролей»).
    Внутри слова точка и дефис сохраняются — на них держатся имена
    параметров и пути (kernel.kptr_restrict, /etc/passwd)."""
    w = word.lower().replace("ё", "е").strip(".,;:!?()«»" + chr(34) + chr(39))
    if len(w) < 5 or not _re.search(r"[а-я]", w):
        return w
    for end in _ENDINGS:
        if w.endswith(end) and len(w) - len(end) >= 4:
            return w[: -len(end)]
    return w


_WORD = _re.compile(r"[A-Za-zА-Яа-яЁё0-9_./-]+")


def stems(text):
    """Последовательность основ слов текста."""
    return [stem(w) for w in _WORD.findall(text or "")]


def phrase_in_text(phrase, text_stems):
    """Встречается ли формулировка в тексте с учётом словоформ:
    основы слов формулировки должны идти подряд."""
    ph = stems(phrase)
    if not ph:
        return False
    n = len(ph)
    for i in range(len(text_stems) - n + 1):
        if text_stems[i:i + n] == ph:
            return True
    return False


# ------------------------------------- синонимы и частичное сходство

def _base_synonyms():
    path = os.path.join(KNOWLEDGE_DIR, "synonyms.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [(a, b) for a, b in json.load(f).get("phrases", [])]


def _synonyms():
    if "syn" in _cache:
        return _cache["syn"]
    pairs = [(a.lower(), b.lower()) for a, b in _base_synonyms()]
    syn = user_layer().get("synonyms", {})
    hide = {(a.lower(), b.lower()) for a, b in syn.get("hide", [])}
    pairs = [x for x in pairs if x not in hide]
    for a, b in syn.get("add", []):
        if (a.lower(), b.lower()) not in pairs:
            pairs.append((a.lower(), b.lower()))
    # длинные обороты заменяются первыми, иначе короткий синоним «съест» часть длинного
    # Текст перед заменой приводится к «е» вместо «ё» (см. normalize), поэтому
    # и синоним приводится так же — иначе «учётка» никогда не совпадёт.
    pairs = [(a.replace("ё", "е"), b) for a, b in pairs]
    pairs.sort(key=lambda p: -len(p[0]))
    _cache["syn"] = pairs
    return pairs


def normalize(text):
    """Приводит обороты документа к формулировкам тезауруса по словарю
    синонимов. Нужен, потому что одно и то же требование в разных
    документах называют по-разному: «секретный код» и «пароль»."""
    low = (text or "").lower().replace("\u0451", "\u0435")
    for variant, canon in _synonyms():
        if variant in low:
            low = low.replace(variant, canon)
    return low


def _concept_bags():
    """Мешки основ по концептам и частота основы по всему тезаурусу.
    Частая основа («система», «обеспечить») почти ничего не говорит о теме,
    поэтому её вклад в оценку меньше."""
    if "bags" in _cache:
        return _cache["bags"]
    bags, df = {}, {}
    for c in load_concepts():
        words = [c.get("title", "")] + c.get("ru", []) + c.get("en", []) + c.get("themes", [])
        bag = set(stems(" ".join(words)))
        bag = {w for w in bag if len(w) > 3}
        bags[c["id"]] = bag
        for w in bag:
            df[w] = df.get(w, 0) + 1
    _cache["bags"] = (bags, df)
    return _cache["bags"]


def similarity(text, concept_id):
    """Частичное сходство текста пункта с темой: доля общих основ с учётом
    их информативности. Ловит формулировки, которых нет в тезаурусе
    дословно, но которые говорят о том же."""
    bags, df = _concept_bags()
    bag = bags.get(concept_id)
    if not bag:
        return 0.0, []
    tset = {w for w in stems(normalize(text)) if len(w) > 3}
    shared = tset & bag
    if not shared:
        return 0.0, []
    total = len(load_concepts())
    weight = sum(1.0 + (total / (1.0 + df.get(w, 1))) / total for w in shared)
    return weight / (len(bag) ** 0.5), sorted(shared)


def synonym_pairs():
    """Пары «как пишут в документе → формулировка тезауруса»."""
    return [{"variant": a, "canonical": b} for a, b in _synonyms()]


# ===================================================================
# Изменение базы знаний из редактора
# ===================================================================

class KnowledgeError(Exception):
    pass


_MAX_PHRASE = 120
_MAX_TITLE = 200


def _clean_phrases(items):
    """Формулировки: без пустых, без повторов (без учёта регистра), не длиннее
    120 символов. Длинная «формулировка» — это уже текст пункта, а не маркер:
    по такой строке тема не найдётся почти никогда."""
    out, seen = [], set()
    for x in items or []:
        x = re.sub(r"\s+", " ", str(x)).strip()
        if not x:
            continue
        if len(x) > _MAX_PHRASE:
            raise KnowledgeError("Формулировка длиннее %d символов: «%s…». Формулировка — это короткий "
                                 "характерный оборот, а не текст пункта целиком." % (_MAX_PHRASE, x[:40]))
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out


def _clean_hints(items):
    out, seen = [], set()
    for h in items or []:
        fam = re.sub(r"\s+", " ", str(h.get("family", ""))).strip()
        ref = re.sub(r"\s+", " ", str(h.get("ref", ""))).strip()
        if not fam:
            continue
        if len(fam) > 120 or len(ref) > 120:
            raise KnowledgeError("Слишком длинное название документа или пункта (больше 120 символов).")
        if (fam, ref) not in seen:
            seen.add((fam, ref))
            out.append({"family": fam, "ref": ref})
    return out


def _base_concept(cid):
    for c in _load_base()[0]:
        if c["id"] == cid:
            return c
    return None


def _base_checks(cid):
    return [eid for eid, cids in _load_base()[1].items() if cid in cids]


def _validate_checks(checks, known_ids):
    unknown = [c for c in checks if c not in known_ids]
    if unknown:
        raise KnowledgeError("Нет таких записей каталога: %s." % ", ".join(unknown))


def set_concept(cid, desired, known_check_ids):
    """Сохраняет желаемый вид темы. Для поставляемой темы хранится разница с
    базой; если разницы нет — правка удаляется, тема снова «исходная»."""
    title = re.sub(r"\s+", " ", str(desired.get("title", ""))).strip()
    # Английское название необязательно: у поставляемых тем оно есть в
    # словаре переводов, своё можно задать при правке в английском интерфейсе.
    title_en = re.sub(r"\s+", " ", str(desired.get("title_en") or "")).strip()
    title = title or title_en
    if not title:
        raise KnowledgeError("У темы должно быть название.")
    if len(title) > _MAX_TITLE or len(title_en) > _MAX_TITLE:
        raise KnowledgeError("Название темы длиннее %d символов." % _MAX_TITLE)
    ru = _clean_phrases(desired.get("ru"))
    en = _clean_phrases(desired.get("en"))
    hints = _clean_hints(desired.get("hints"))
    checks = list(dict.fromkeys(desired.get("checks") or []))
    _validate_checks(checks, known_check_ids)
    if not ru and not en:
        raise KnowledgeError("Нужна хотя бы одна формулировка — по ним тема узнаётся в тексте документа.")

    with _lock:
        layer = copy.deepcopy(user_layer())
        base = _base_concept(cid)
        existing = layer["concepts"].get(cid, {})
        if base is None and not existing.get("new"):
            raise KnowledgeError("Тема «%s» не найдена." % cid)

        if base is None:            # тема, созданная пользователем
            layer["concepts"][cid] = {
                "new": True, "title": title, "title_en": title_en or None,
                "themes": existing.get("themes") or ["Пользовательские темы"],
                "add_ru": ru, "add_en": en, "add_hints": hints, "add_links": checks,
            }
        else:
            base_hints = {_hint_key(h) for h in base.get("doc_hints", [])}
            want_hints = {(h["family"], h["ref"]) for h in hints}
            base_checks = _base_checks(cid)
            patch = {
                "title": title if title != base["title"] else None,
                "title_en": title_en if title_en and title_en != _default_title_en(base) else None,
                "add_ru": [x for x in ru if x not in base.get("ru", [])],
                "hide_ru": [x for x in base.get("ru", []) if x not in ru],
                "add_en": [x for x in en if x not in base.get("en", [])],
                "hide_en": [x for x in base.get("en", []) if x not in en],
                "add_hints": [h for h in hints if (h["family"], h["ref"]) not in base_hints],
                "hide_hints": [{"family": f, "ref": r} for f, r in base_hints if (f, r) not in want_hints],
                "add_links": [e for e in checks if e not in base_checks],
                "hide_links": [e for e in base_checks if e not in checks],
            }
            patch = {k: v for k, v in patch.items() if v}
            if patch:
                layer["concepts"][cid] = patch
            else:
                layer["concepts"].pop(cid, None)
        _save_layer(layer)
    return get_concept(cid)


def _default_title_en(concept):
    from . import i18n_en
    return i18n_en.translate(concept.get("title")) or ""


def _slug(title):
    tr = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
          "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
          "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y",
          "ь": "", "э": "e", "ю": "yu", "я": "ya"}
    s = "".join(tr.get(ch, ch) for ch in title.lower())
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")[:40].rstrip("_")
    return s or "topic"


def create_concept(desired, known_check_ids):
    """Новая тема. Идентификатор — «user.<транслит названия>», чтобы
    пользовательские темы никогда не совпали с поставляемыми."""
    title = str(desired.get("title", "") or desired.get("title_en", "") or "").strip()
    base_id = "user." + _slug(title)
    ids = {c["id"] for c in load_concepts()}
    cid, n = base_id, 2
    while cid in ids:
        cid = "%s_%d" % (base_id, n)
        n += 1
    with _lock:
        layer = copy.deepcopy(user_layer())
        layer["concepts"][cid] = {"new": True, "title": title or cid, "themes": ["Пользовательские темы"]}
        _save_layer(layer)
    try:
        return set_concept(cid, desired, known_check_ids)
    except KnowledgeError:
        with _lock:            # не оставляем заготовку темы, если данные не прошли проверку
            layer = copy.deepcopy(user_layer())
            layer["concepts"].pop(cid, None)
            _save_layer(layer)
        raise


def reset_concept(cid):
    """Поставляемая тема — вернуть к исходному виду; своя тема — удалить."""
    with _lock:
        layer = copy.deepcopy(user_layer())
        if cid not in layer["concepts"]:
            raise KnowledgeError("У темы «%s» нет правок." % cid)
        created = bool(layer["concepts"][cid].get("new")) and _base_concept(cid) is None
        layer["concepts"].pop(cid)
        _save_layer(layer)
    return {"id": cid, "deleted": created, "reset": not created}


def synonym_entries():
    """Синонимы с пометкой происхождения — для редактора."""
    base = [(a, b) for a, b in _base_synonyms()]
    syn = user_layer().get("synonyms", {})
    hide = {(a.lower(), b.lower()) for a, b in syn.get("hide", [])}
    out = [{"variant": a, "canonical": b, "user": False}
           for a, b in base if (a.lower(), b.lower()) not in hide]
    out += [{"variant": a, "canonical": b, "user": True} for a, b in syn.get("add", [])]
    return out


def set_synonyms(pairs):
    """Сохраняет желаемый список синонимов целиком; хранится разница с базой."""
    clean, seen = [], set()
    for p in pairs or []:
        a = re.sub(r"\s+", " ", str(p.get("variant", ""))).strip()
        b = re.sub(r"\s+", " ", str(p.get("canonical", ""))).strip()
        if not a or not b:
            continue
        if a.lower() == b.lower():
            raise KnowledgeError("Синоним «%s» совпадает со своей заменой." % a)
        if len(a) > _MAX_PHRASE or len(b) > _MAX_PHRASE:
            raise KnowledgeError("Синоним длиннее %d символов." % _MAX_PHRASE)
        k = (a.lower(), b.lower())
        if k not in seen:
            seen.add(k)
            clean.append((a, b))
    base = [(a, b) for a, b in _base_synonyms()]
    base_k = {(a.lower(), b.lower()) for a, b in base}
    with _lock:
        layer = copy.deepcopy(user_layer())
        layer["synonyms"] = {
            "add": [[a, b] for a, b in clean if (a.lower(), b.lower()) not in base_k],
            "hide": [[a, b] for a, b in base if (a.lower(), b.lower()) not in seen],
        }
        _save_layer(layer)
    return synonym_entries()


def import_layer(data, known_check_ids, mode="merge"):
    """Импорт правок с другого сервера. merge — правки тем из файла заменяют
    правки тех же тем здесь, остальные сохраняются; replace — слой целиком."""
    if not isinstance(data, dict) or not isinstance(data.get("concepts", {}), dict):
        raise KnowledgeError("Файл не похож на выгрузку правок базы знаний.")
    incoming = data.get("concepts", {})
    for cid, p in incoming.items():
        if not isinstance(p, dict):
            raise KnowledgeError("Повреждена правка темы «%s»." % cid)
        _validate_checks(p.get("add_links", []), known_check_ids)
        for lang in ("add_ru", "add_en"):
            _clean_phrases(p.get(lang, []))
    with _lock:
        layer = _empty_layer() if mode == "replace" else copy.deepcopy(user_layer())
        layer["concepts"].update(incoming)
        syn = data.get("synonyms", {}) or {}
        for k in ("add", "hide"):
            have = {tuple(x) for x in layer["synonyms"].get(k, [])}
            for pair in syn.get(k, []):
                if isinstance(pair, (list, tuple)) and len(pair) == 2 and tuple(pair) not in have:
                    layer["synonyms"].setdefault(k, []).append(list(pair))
        _save_layer(layer)
    return {"concepts": len(incoming), "mode": mode}


# ------------------------------------------- поиск тем по слову (окно проверки формулировки)

def _prefix_match(a, b):
    """Слова считаются совпадающими, если одно начинается с другого и общая
    часть не короче 4 букв: «парольн» ~ «парол», «блокировк» ~ «блокир»."""
    n = min(len(a), len(b))
    # Для латиницы хватает трёх букв: ssh, usb, rdp, uid — короткие термины.
    need = 3 if re.match(r"^[a-z0-9_]+$", a) and re.match(r"^[a-z0-9_]+$", b) else 4
    return n >= need and (a.startswith(b) or b.startswith(a))


def search_concepts(query, limit=10):
    """Темы, в названии, формулировках, разделах или связанных проверках
    которых встречаются слова запроса. Это поиск, а не распознавание: он
    нужен, когда пользователь проверяет одно-два слова, которых недостаточно
    для уверенного сопоставления пункта документа."""
    # Русские слова короче 4 букв — служебные («для», «при»); латинские
    # из трёх букв — чаще всего термины (ssh, usb, rdp).
    q = [w for w in stems(normalize(query))
         if len(w) >= 4 or (len(w) == 3 and re.match(r"^[a-z0-9]+$", w))]
    if not q:
        return []
    # Названия связанных проверок каталога тоже участвуют в поиске: человек
    # ищет словами из проверок («ssh»), а в названии темы их может не быть
    # («Запрет удалённого входа суперпользователя»).
    from . import catalog
    check_titles = {}
    try:
        titles = {e["id"]: e.get("title", "") for e in catalog.load_catalog()}
        for eid, cids in catalog_links().items():
            for cid in cids:
                check_titles.setdefault(cid, []).append(titles.get(eid, ""))
    except Exception:  # noqa: BLE001 — без каталога поиск работает по самой базе
        pass
    from . import i18n_en
    out = []
    for c in load_concepts():
        title_en = c.get("title_en") or i18n_en.translate(c.get("title")) or ""
        title_words = set(stems(c.get("title", "") + " " + title_en))
        other_words = set(stems(" ".join(c.get("ru", []) + c.get("en", []) + c.get("themes", [])
                                         + check_titles.get(c["id"], []))))
        hit_title = [w for w in q if any(_prefix_match(w, t) for t in title_words)]
        hit_other = [w for w in q if w not in hit_title and any(_prefix_match(w, t) for t in other_words)]
        if not hit_title and not hit_other:
            continue
        score = 3 * len(hit_title) + len(hit_other)
        out.append({"concept_id": c["id"], "title": c.get("title"), "title_en": title_en or None,
                    "matched": sorted(set(hit_title + hit_other)), "in_title": bool(hit_title), "score": score})
    out.sort(key=lambda x: (-x["score"], x["title"]))
    return out[:limit]
