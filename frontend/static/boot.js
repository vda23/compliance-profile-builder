/* Ранняя инициализация: применяет сохранённые тему и язык до отрисовки
   страницы, чтобы не было «мигания» не той темой. Подключается в <head>
   отдельным файлом — встроенных скриптов страница не содержит (строгая CSP). */
  // Применяем сохранённые тему и язык до отрисовки страницы, чтобы избежать
  // "мигания" не той темой и не тем языком при загрузке.
  // По умолчанию: тема — светлая, язык — русский.
  (function () {
    try {
      var theme = localStorage.getItem("cpb-theme") || "light";
      document.documentElement.setAttribute("data-theme", theme);
      var lang = localStorage.getItem("cpb-lang") || "ru";
      document.documentElement.setAttribute("lang", lang);
    } catch (e) {
      document.documentElement.setAttribute("data-theme", "light");
    }
  })();
