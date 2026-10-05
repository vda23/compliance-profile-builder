"""
Тезаурус требований: формулировки нормативных документов и их связь
с записями технического каталога.

Файлы знаний лежат в backend/knowledge/*.json и загружаются без внешних
библиотек. Слой намеренно отделён от каталога проверок: каталог отвечает
на вопрос «как проверить», тезаурус — «как об этом пишут в документах».
"""
import json
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "knowledge")

_cache = {}


def _load():
    if "data" in _cache:
        return _cache["data"]
    concepts, links = [], {}
    if os.path.isdir(KNOWLEDGE_DIR):
        for name in sorted(os.listdir(KNOWLEDGE_DIR)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(KNOWLEDGE_DIR, name), encoding="utf-8") as f:
                data = json.load(f)
            concepts.extend(data.get("concepts", []))
            links.update(data.get("catalog_links", {}))
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
    """Семейства документов, упомянутые в тезаурусе, с числом тем."""
    out = {}
    for c in load_concepts():
        for h in c.get("doc_hints", []):
            fam = h.get("family", "").split(",")[0]
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

def _synonyms():
    if "syn" in _cache:
        return _cache["syn"]
    pairs = []
    path = os.path.join(KNOWLEDGE_DIR, "synonyms.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            pairs = [(a.lower(), b.lower()) for a, b in json.load(f).get("phrases", [])]
    # длинные обороты заменяются первыми, иначе короткий синоним «съест» часть длинного
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
