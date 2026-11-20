"""
Отчёт о покрытии нормативного документа.

Сохраняется в каталоге проекта (coverage.json) при сборке черновика и
выгружается самодостаточной HTML-страницей: без внешних ресурсов, со
стилями для печати — её можно открыть в любом браузере и сохранить в PDF.

Отчёт фиксирует состояние на момент сборки черновика. Если правила потом
меняли вручную, отчёт этого не отражает — об этом сказано в самом отчёте.
"""
import datetime
import html
import json
import os
import re

from . import i18n_en, storage

FILENAME = "coverage.json"

STATUS = {
    "applied": ("Проверяется автоматически", "ok"),
    "manual": ("Организационная мера", "manual"),
    "skipped": ("Без сопоставления", "none"),
    "excluded": ("Исключён при разборе", "excl"),
}
STATUS_EN = {
    "applied": "Checked automatically", "manual": "Organisational measure",
    "skipped": "Not matched", "excluded": "Excluded during review",
}

# Тексты страницы отчёта: ключ → (русский, английский)
TEXT = {
    "title": ("Отчёт о покрытии — %s", "Coverage report — %s"),
    "h1": ("Отчёт о покрытии требований", "Requirements coverage report"),
    "sub": ("%s · ОС: %s · проект %s · сформирован %s", "%s · OS: %s · project %s · created %s"),
    "no_os": ("не указана", "not specified"),
    "c_total": ("пунктов в документе", "items in the document"),
    "c_ok": ("проверяются автоматически (%s%%)", "checked automatically (%s%%)"),
    "c_rules": ("правил в профиле", "rules in the profile"),
    "c_manual": ("организационных мер", "organisational measures"),
    "c_none": ("без сопоставления", "not matched"),
    "c_excl": ("исключено при разборе", "excluded during review"),
    "th": (("Пункт", "Требование", "Статус", "Проверка или мера"),
           ("Item", "Requirement", "Status", "Check or measure")),
    "shared": ("(общее правило с другим пунктом)", "(rule shared with another item)"),
    "state": ("Отчёт отражает состояние на момент сборки черновика профиля. Изменения правил, сделанные позже, в нём не учтены.",
              "The report reflects the state at the time the draft profile was built. Later changes to the rules are not included."),
}


def _path(project_id):
    return os.path.join(str(storage.project_path(project_id)), FILENAME)


def save(project_id, report, document, os_name, min_confidence):
    data = dict(report)
    data.update({
        "format": 1,
        "document": document,
        "os": os_name or "",
        "min_confidence": min_confidence,
        "created": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
    })
    path = _path(project_id)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    return data


def load(project_id):
    path = _path(project_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _natural(number):
    """Порядок пунктов как в документе: 2.10 после 2.9."""
    return [int(p) if p.isdigit() else p for p in re.split(r"[.\s]+", str(number)) if p]


def rows(report):
    """Все пункты документа в порядке документа, у каждого — один статус."""
    out = []
    for key in ("applied", "manual", "skipped", "excluded"):
        for x in report.get(key, []):
            out.append({
                "number": x.get("number", ""),
                "status": key,
                "check": x.get("title") if key in ("applied", "manual") else "",
                "text": x.get("text", ""),
                "shared": bool(x.get("shared")),
                "reason": x.get("reason", ""),
                "reason_en": x.get("reason_en", ""),
            })
    out.sort(key=lambda r: _natural(r["number"]))
    return out


_CSS = """
:root { --accent: #00A88E; --text: #1d1d1b; --dim: #6b6b6b; --line: #e3e3e3; }
* { box-sizing: border-box; }
body { font: 14px/1.5 -apple-system, "Segoe UI", Roboto, Arial, sans-serif; color: var(--text);
       margin: 0 auto; padding: 32px 40px; max-width: 1100px; }
h1 { font-size: 22px; margin: 0 0 4px; }
.sub { color: var(--dim); margin: 0 0 22px; }
.cards { display: flex; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }
.card { flex: 1; min-width: 140px; border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; }
.card b { display: block; font-size: 26px; color: var(--accent); line-height: 1.1; }
.card span { font-size: 12px; color: var(--dim); }
.bar { display: flex; height: 10px; border-radius: 5px; overflow: hidden; margin: 0 0 22px; background: var(--line); }
.bar i { display: block; height: 100%; }
.b-ok { background: var(--accent); } .b-manual { background: #8fb8d8; } .b-none { background: #e0b25a; } .b-excl { background: #c8c8c8; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--dim);
     border-bottom: 2px solid var(--line); padding: 8px 10px; }
td { border-bottom: 1px solid var(--line); padding: 8px 10px; vertical-align: top; }
td.num { font-family: Consolas, Menlo, monospace; white-space: nowrap; color: var(--accent); }
.st { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: 11.5px; white-space: nowrap; }
.st-ok { background: rgba(0,168,142,.14); color: #007a67; }
.st-manual { background: #e3eef7; color: #2f5d80; }
.st-none { background: #fbefd9; color: #8a5a00; }
.st-excl { background: #eeeeee; color: #6b6b6b; }
.note { color: var(--dim); font-size: 12px; }
.disclaimer { margin-top: 22px; padding: 12px 14px; border-left: 3px solid var(--accent);
              background: #f4faf9; font-size: 12.5px; color: #3b3b3b; }
footer { margin-top: 26px; font-size: 11.5px; color: var(--dim); }
@media print {
  body { padding: 0; max-width: none; font-size: 11pt; }
  .card, table, .disclaimer { break-inside: auto; }
  tr { break-inside: avoid; }
  thead { display: table-header-group; }
}
"""


def _check_title(title, lang):
    """Название проверки на языке отчёта: русское переводится по словарю,
    английское (черновик по английскому документу) — обратно."""
    if not title:
        return ""
    if lang == "en":
        return i18n_en.translate(title) or title
    return i18n_en.translate_back(title) or title


def render_html(project_id, report, lang=None):
    """Самодостаточная HTML-страница отчёта. Весь текст экранируется:
    формулировки пунктов приходят из документа пользователя."""
    from .docimport import disclaimer
    lang = lang or report.get("lang", "ru")
    en = lang == "en"
    T = lambda key: TEXT[key][1 if en else 0]
    e = html.escape
    s = report.get("summary", {})
    total = max(int(s.get("items_total", 0)), 1)
    counts = {
        "ok": len(report.get("applied", [])), "manual": len(report.get("manual", [])),
        "none": len(report.get("skipped", [])), "excl": len(report.get("excluded", [])),
    }
    share = round(100.0 * counts["ok"] / total)
    created = report.get("created", "")
    try:
        # Дату пишет сам сервис в формате ГГГГ-ММ-ДДTЧЧ:ММ:СС+00:00.
        # datetime.fromisoformat не используется: её нет в Python 3.5–3.6.
        created_h = datetime.datetime.strptime(created[:19], "%Y-%m-%dT%H:%M:%S").strftime(
            "%Y-%m-%d %H:%M UTC" if en else "%d.%m.%Y %H:%M UTC")
    except (ValueError, TypeError):
        created_h = created

    bar = "".join('<i class="b-%s" style="width:%.2f%%"></i>' % (k, 100.0 * v / total)
                  for k, v in counts.items() if v)
    body_rows = []
    for r in rows(report):
        label, cls = STATUS[r["status"]]
        if en:
            label = STATUS_EN[r["status"]]
        check = e(_check_title(r["check"], lang))
        if r["shared"]:
            check += ' <span class="note">%s</span>' % e(T("shared"))
        reason = (r["reason_en"] or i18n_en.translate(r["reason"]) or r["reason"]) if en else r["reason"]
        if r["status"] in ("manual", "skipped") and reason:
            check += '<div class="note">%s</div>' % e(reason)
        body_rows.append(
            '<tr><td class="num">%s</td><td>%s</td><td><span class="st st-%s">%s</span></td><td>%s</td></tr>'
            % (e(r["number"]), e(r["text"]), cls, e(label), check or '<span class="note">—</span>'))

    th = "".join("<th>%s</th>" % e(h) for h in T("th"))
    card = '<div class="card"><b>%s</b><span>%s</span></div>'
    cards = [card % (s.get("items_total", 0), e(T("c_total"))),
             card % (counts["ok"], e(T("c_ok") % share)),
             card % (s.get("rules_created", 0), e(T("c_rules"))),
             card % (counts["manual"], e(T("c_manual"))),
             card % (counts["none"], e(T("c_none")))]
    if counts["excl"]:
        cards.append(card % (counts["excl"], e(T("c_excl"))))
    doc = report.get("document", "")
    page = """<!DOCTYPE html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style></head>
<body>
<h1>{h1}</h1>
<p class="sub">{sub}</p>
<div class="cards">
  {cards}
</div>
<div class="bar">{bar}</div>
<table>
<thead><tr>{th}</tr></thead>
<tbody>
{rows}
</tbody></table>
<div class="disclaimer">{disclaimer}<br><br>{state}</div>
<footer>Compliance Profile Builder</footer>
</body></html>
""".format(
        lang=lang, title=e(T("title") % doc), h1=e(T("h1")), css=_CSS,
        sub=e(T("sub") % (doc, report.get("os", "") or T("no_os"), project_id, created_h)),
        cards="\n  ".join(cards), bar=bar, th=th, rows="\n".join(body_rows),
        disclaimer=e(disclaimer(lang)), state=e(T("state")))
    return page.encode("utf-8")
