/* =============================================================================
 * Локализация интерфейса: русская (по умолчанию) и английская версии.
 *
 * Ключом словаря служит сам русский текст — благодаря этому в коде остаётся
 * читаемая русская строка (обёрнутая в t(...)), а перевод подставляется
 * только при переключении языка. Если перевода для строки нет, показывается
 * исходный русский текст, поэтому добавление новой строки в интерфейс
 * никогда не приводит к пустому месту на экране.
 *
 * Технические идентификаторы стандарта XCCDF/OVAL (definition, test, object,
 * state, variable, criteria, check-content-ref и т.п.) намеренно НЕ
 * переводятся ни на одном языке: это термины самого стандарта, они одинаково
 * пишутся в англоязычной и русскоязычной документации и совпадают с именами
 * элементов в генерируемом XML.
 * ========================================================================== */

const EN = {
  /* --- Шапка, боковая панель --- */
  "Конструктор профилей": "Compliance Profile Builder",
  "Проекты": "Projects",
  "Импорт ZIP…": "Import ZIP…",
  "Проектов пока нет": "No projects yet",
  "Новый проект": "New project",
  "Переключить тему / Switch theme": "Switch theme",
  "Сменить язык / Switch language": "Switch language",
  "Удалить проект": "Delete project",
  "Проект удалён": "Project deleted",
  "Проект создан": "Project created",
  "Создать проект": "Create project",
  "Импорт ZIP-архива": "Import ZIP archive",
  "Импортировать": "Import",
  "Архив импортирован": "Archive imported",
  "Выберите проект слева или создайте новый, чтобы начать составление профиля. / Select a project on the left or create a new one to start building a profile.":
    "Select a project on the left or create a new one to start building a profile.",

  /* --- Режимы и шаги мастера --- */
  "1. бенчмарк": "1. benchmark",
  "2. профили": "2. profiles",
  "3. правила": "3. rules",
  "4. oval-файлы": "4. OVAL files",
  "5. валидация и экспорт": "5. validation & export",
  "Добавить ещё?": "Add another?",

  "мастер": "wizard",
  "конструктор": "constructor",
  "← назад": "← back",
  "далее →": "next →",
  "понятно": "got it",
  "нет": "no",
  "да, добавить ещё": "yes, add another",
  "больше не показывать эту подсказку": "don't show this hint again",
  "Показать подсказку": "Show hint",
  "проект": "project",
  /* --- Подсказки шагов --- */
  "Заполните основные сведения о профиле соответствия: заголовок, описание, версию и статус документа. Это станет заголовком XCCDF Benchmark.":
    "Fill in the basic benchmark metadata: title, description, version and document status. This becomes the XCCDF Benchmark header.",
  "Создайте один или несколько профилей (например «базовый», «усиленный»). Профиль — это именованный набор правил, которые будут проверяться вместе.":
    "Create one or more profiles (e.g. \"baseline\", \"hardened\"). A profile is a named set of rules that will be evaluated together.",
  "Добавьте правила проверки и привяжите их к OVAL-определению (definition), которое опишет техническое условие. Не забудьте включить нужные правила в профиль на предыдущем шаге.":
    "Add compliance rules and link each one to an OVAL definition describing the technical condition. Remember to include the relevant rules in a profile from the previous step.",
  "Опишите техническую логику проверок: definitions (что проверяем), tests (как проверяем), objects/states (какие объекты и с какими значениями). Для каждого типа теста доступны свои поля.":
    "Describe the technical check logic: definitions (what is checked), tests (how it's checked), objects/states (which objects and expected values). Each test type exposes its own fields.",
  "Проверьте профиль на корректность и экспортируйте готовый пакет XCCDF/OVAL в ZIP-архив для развёртывания.":
    "Validate the profile for correctness and export the finished XCCDF/OVAL package as a ZIP archive for deployment.",
  "Ссылка на пункт внешнего стандарта (например, CIS Benchmark, приказ ФСТЭК), которому соответствует правило. Необязательно, но полезно для отчётности.":
    "Reference to an item in an external standard (e.g. a CIS Benchmark or a regulator's order) that this rule maps to. Optional, but useful for reporting.",
  "Критерии объединяют один или несколько tests логическим оператором (AND/OR). Definition считается выполненным, если критерии истинны.":
    "Criteria combine one or more tests with a logical operator (AND/OR). The definition is satisfied when the criteria evaluate to true.",
  "Сколько объектов из найденных должно удовлетворять состоянию (state), чтобы test считался истинным.":
    "How many of the matched objects must satisfy the state for the test to be true.",
  "Ссылка на ранее созданный object в этом же OVAL-файле — что именно проверяем (файл, ключ реестра, пакет и т.п.).":
    "Reference to a previously created object in this OVAL file — what exactly is being checked (file, registry key, package, etc.).",

  /* --- Вкладки --- */
  "Бенчмарк": "Benchmark",
  "Профили": "Profiles",
  "Правила": "Rules",
  "OVAL-файлы": "OVAL files",
  "Валидация и экспорт": "Validation & export",
  "Метаданные бенчмарка": "Benchmark metadata",

  /* --- Общие действия --- */
  "Сохранить": "Save",
  "Сохранено": "Saved",
  "Создать": "Create",
  "Отмена": "Cancel",
  "Изменить": "Edit",
  "Удалить": "Delete",
  "Удалить файл": "Delete file",
  "Закрыть": "Close",
  "Закрыть / Close": "Close",
  "Проверка…": "Checking…",
  "Латиница, цифры, - и _": "Latin letters, digits, - and _",

  /* --- Профили --- */
  "+ Профиль": "+ Profile",
  "Новый профиль": "New profile",
  "Профиль создан": "Profile created",
  "Профиль удалён": "Profile deleted",
  "Профили ещё не добавлены.": "No profiles added yet.",
  "Правила профиля": "Profile rules",
  "Состав профиля": "Profile contents",
  "Состав профиля сохранён": "Profile contents saved",
  "Сохранить состав": "Save contents",
  "Правил в составе": "Rules included",
  "В бенчмарке ещё нет правил.": "The benchmark has no rules yet.",
  "выбрано": "selected",
  "не выбрано": "not selected",
  "профиль": "profile",

  /* --- Правила --- */
  "+ Правило": "+ Rule",
  "Новое правило": "New rule",
  "Правило создано": "Rule created",
  "Правило удалено": "Rule deleted",
  "Правила ещё не добавлены.": "No rules added yet.",
  "правило": "rule",
  "Название": "Title",
  "По умолчанию": "Default",
  "Ссылка на проверку": "Check reference",
  "Сначала добавьте OVAL-файл на вкладке «OVAL-файлы».": "Add an OVAL file on the \"OVAL files\" tab first.",
  "Сначала добавьте OVAL-файл": "Add an OVAL file first",

  /* --- OVAL-файлы --- */
  "+ OVAL-файл": "+ OVAL file",
  "Новый OVAL-файл": "New OVAL file",
  "OVAL-файл создан": "OVAL file created",
  "OVAL-файл": "OVAL file",
  "Файл удалён": "File deleted",
  "OVAL-файлы ещё не добавлены.": "No OVAL files added yet.",
  "Генератор": "Generator",
  "схема OVAL": "OVAL schema",

  /* --- Definitions / tests / objects / states / variables --- */
  "Новое определение": "New definition",
  "Определение создано": "Definition created",
  "Определение удалено": "Definition deleted",
  "Определения ещё не добавлены.": "No definitions added yet.",
  "Новый тест": "New test",
  "Тест создан": "Test created",
  "Тест удалён": "Test deleted",
  "Тесты ещё не добавлены.": "No tests added yet.",
  "Новый объект": "New object",
  "Объект создан": "Object created",
  "Объект удалён": "Object deleted",
  "Объекты ещё не добавлены.": "No objects added yet.",
  "Новое состояние": "New state",
  "Состояние создано": "State created",
  "Состояние удалено": "State deleted",
  "Состояния ещё не добавлены.": "No states added yet.",
  "Нет типов проверок, поддерживающих состояние": "No test types support a state",
  "Новая переменная": "New variable (constant_variable)",
  "Переменная создана": "Variable created",
  "Переменная удалена": "Variable deleted",
  "Переменные ещё не добавлены.": "No variables added yet.",
  "переменную": "variable",
  "переменная": "variable",
  "— переменная —": "— variable —",
  "нет подходящих объектов": "no matching objects",
  "У этого типа проверки нет параметров объекта.": "This test type has no object fields.",
  "У этого типа проверки нет параметров состояния.": "This test type has no state fields.",
  "Класс": "Class",
  "Платформа": "Platform",
  "Критериев": "Criteria",
  "Тип теста": "Test type",
  "Тип": "Type",
  "Поля": "Fields",
  "Тип данных": "Datatype",
  "Значение": "Value",
  "значение": "value",
  " внутри OVAL ": " inside OVAL ",

  /* --- Валидация и экспорт --- */
  "Проверить проект": "Validate project",
  "Экспортировать ZIP": "Export ZIP",
  "Нажмите «Проверить проект», чтобы увидеть результат.": "Click \"Validate project\" to see the result.",
  "✓ Проект соответствует требованиям, ошибок и замечаний не найдено.":
    "✓ The project meets the requirements; no errors or warnings found.",
  "✓ Критичных ошибок нет (есть замечания ниже)": "✓ No critical errors (see warnings below)",
  "✕ Найдены ошибки — архив не пройдёт импорт, пока они не исправлены.":
    "✕ Errors found — the archive will not import until they are fixed.",

  "Выберите проект слева или создайте новый, чтобы начать составление профиля.":
    "Select a project on the left or create a new one to start building a profile.",
  "Действие необратимо.": "This cannot be undone.",
  "Ссылающиеся на него правила перестанут быть валидны.": "Rules referencing it will become invalid.",
  "Профили": "Profiles",
  "Правила": "Rules",
  /* --- Перестроенный интерфейс и русская терминология --- */
  "Перейти к шагу": "Go to step",
  "Больше не показывать эту подсказку": "Don't show this hint again",
  "Понятно": "Got it",
  "Мастер": "Wizard",
  "Конструктор": "Constructor",
  "Проект": "Project",
  "OVAL-проверки": "OVAL checks",
  "Проверка и экспорт": "Validation & export",
  "← Назад": "← Back",
  "Далее →": "Next →",
  "Идентификатор": "ID",
  "Файл создан. Нажмите «Далее», чтобы перейти к наполнению проверок.": "File created. Click \"Next\" to start filling in the checks.",
  "Переменные": "Variables",
  "Объекты": "Objects",
  "Состояния": "States",
  "Тесты": "Tests",
  "Определения": "Definitions",
  "+ Переменная": "+ Variable",
  "+ Объект": "+ Object",
  "+ Состояние": "+ State",
  "+ Тест": "+ Test",
  "+ Определение": "+ Definition",
  "+ Критерий": "+ Criterion",
  "Комментарий": "Comment",
  "У этого типа проверки нет полей объекта — объект описывает всю политику целиком.": "This check type has no object fields — the object describes the whole policy.",
  "Из переменной": "From variable",
  "— Переменная —": "— Variable —",
  "Операция сравнения": "Comparison operation",
  "У этого типа проверки нет полей состояния.": "This check type has no state fields.",
  "Тип проверки": "Check type",
  "Ожидаемые значения": "Expected values",
  "Нет типов проверок с полями состояния": "No check types with state fields",
  "Объект": "Object",
  "Состояние": "State",
  "без состояния": "no state",
  "Семейство ОС": "OS family",
  "Платформы": "Platforms",
  "— Тест —": "— Test —",
  "Например: Astra Linux": "For example: Astra Linux",
  "Определение": "Definition",
  "Новое определение": "New definition",
  "Новый тест": "New test",
  "Новый объект": "New object",
  "Новое состояние": "New state",
  "Новая переменная": "New variable",
  "Определение создано": "Definition created",
  "Определение удалено": "Definition deleted",
  "Тест создан": "Test created",
  "Тест удалён": "Test deleted",
  "Объект создан": "Object created",
  "Объект удалён": "Object deleted",
  "Состояние создано": "State created",
  "Состояние удалено": "State deleted",
  "Переменная создана": "Variable created",
  "Переменная удалена": "Variable deleted",
  "Нет типов проверок, поддерживающих состояние": "No check types support a state",
  "Удалить определение": "Delete definition",
  "Удалить тест": "Delete test",
  "Удалить объект": "Delete object",
  "Удалить состояние": "Delete state",
  "Удалить переменную": "Delete variable",
  "нет подходящих объектов": "no matching objects",
  "У этого типа проверки нет параметров объекта.": "This check type has no object parameters.",
  "У этого типа проверки нет параметров состояния.": "This check type has no state parameters.",
  "Определения ещё не добавлены.": "No definitions added yet.",
  "Тесты ещё не добавлены.": "No tests added yet.",
  "Объекты ещё не добавлены.": "No objects added yet.",
  "Состояния ещё не добавлены.": "No states added yet.",
  "Переменные ещё не добавлены.": "No variables added yet.",
  "Нет": "No",
  "Да, добавить ещё": "Yes, add another",
  "(Без названия)": "(Untitled)",
  "Требование (ident)": "Requirement (ident)",
  "Система (system)": "System",
  "Значение (value)": "Value",
  "+ Идентификатор требования": "+ Requirement identifier",
  "В этом файле нет определений": "This file has no definitions",
  "Правило": "Rule",
  "Состав": "Contents",
  "Выбрать все": "Select all",
  "Профиль": "Profile",
  "Без состояния": "No state",
  "Ошибка": "Error",
  "Замечание": "Warning",
  /* --- Прочее --- */
  "(без названия)": "(untitled)",
  "проект / project: ": "project: ",
  "Не удалось загрузить схему OVAL-типов: ": "Failed to load the OVAL type schema: ",
  "РЕД ОС, ALT Linux, Windows": "RED OS, ALT Linux, Windows",
};

/* Подтверждения (confirm) — вынесены отдельно, т.к. собираются из шаблона. */
const EN_CONFIRM = {
  "Удалить профиль": "Delete profile",
  "Удалить правило": "Delete rule",
  "Удалить OVAL-файл": "Delete OVAL file",
  "Удалить определение": "Delete definition",
  "Удалить тест": "Delete test",
  "Удалить объект": "Delete object",
  "Удалить состояние": "Delete state",
  "Удалить переменную": "Delete variable",
  "Удалить проект": "Delete project",
  "вместе со всеми файлами": "along with all its files",
};

Object.assign(EN, EN_CONFIRM);

/* Текущий язык интерфейса. По умолчанию — русский. */
let CURRENT_LANG = (function () {
  try { return localStorage.getItem("cpb-lang") || "ru"; } catch (e) { return "ru"; }
})();

function getLang() { return CURRENT_LANG; }

function setLang(lang) {
  CURRENT_LANG = lang === "en" ? "en" : "ru";
  try { localStorage.setItem("cpb-lang", CURRENT_LANG); } catch (e) {}
  document.documentElement.setAttribute("lang", CURRENT_LANG);
}

/* Перевод строки. Ключ — русский текст; при отсутствии перевода
   возвращается исходная строка. */
function t(ru) {
  if (CURRENT_LANG !== "en") return ru;
  return Object.prototype.hasOwnProperty.call(EN, ru) ? EN[ru] : ru;
}
