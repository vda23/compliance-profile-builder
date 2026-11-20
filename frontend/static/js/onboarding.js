/* Быстрый старт и настройки подсказок.
   Обычный скрипт без сборки: файлы интерфейса подключаются по порядку и
   разделяют общую область видимости (см. index.html). */

/* ===================== Быстрый старт =====================
   Открывается при первом запуске и по ссылке «Справка» в боковой панели.
   Отвечает на вопросы, которые чаще всего возникали у первых
   пользователей: с чего начать, чем мастер отличается от конструктора и
   как отключить всплывающие подсказки. */

function openOnboarding() {
  const hintsOn = !hintsDisabled();
  const askMore = localStorage.getItem("cpb-no-add-another") !== "1";
  openModal(t("Быстрый старт"), `
    <div class="onboarding">
      <p>${t("Сервис собирает профиль соответствия — пару файлов XCCDF и OVAL — и выгружает его ZIP-архивом для импорта в Kaspersky Vulnerability Management.")}</p>

      <h3>${t("С чего начать")}</h3>
      <ol>
        <li>${t("Откройте пример — он покажет, как выглядит готовый профиль.")}</li>
        <li>${t("Создайте проект кнопкой «+» или загрузите нормативный документ — сервис соберёт черновик.")}</li>
        <li>${t("Пройдите шаги мастера и на последнем шаге выгрузите архив.")}</li>
      </ol>

      <h3>${t("Мастер или конструктор")}</h3>
      <div class="mode-compare">
        <div><b>${t("Мастер")}</b><span>${t("Ведёт по шагам в нужном порядке и подсказывает на каждом. Для первого профиля и для тех, кто не помнит устройство XCCDF и OVAL.")}</span></div>
        <div><b>${t("Конструктор")}</b><span>${t("Все разделы сразу, в любом порядке. Для правки готового или импортированного профиля.")}</span></div>
      </div>
      <p class="muted">${t("Данные у режимов общие: переключаться можно в любой момент, ничего не теряется.")}</p>

      <h3>${t("Настройки")}</h3>
      <label class="row-check"><input type="checkbox" id="ob-hints" ${hintsOn ? "checked" : ""}> ${t("Показывать подсказку при первом открытии каждого шага")}</label>
      <label class="row-check"><input type="checkbox" id="ob-more" ${askMore ? "checked" : ""}> ${t("Предлагать добавить ещё один элемент после создания")}</label>
    </div>
    <div class="modal-actions">
      <button type="button" class="btn" ${on("click", "openKnowledgeBase")} style="margin-right:auto;">${t("База знаний")}</button>
      <button type="button" class="btn" ${on("click", "finishOnboarding", false)}>${t("Начать")}</button>
      <button type="button" class="btn btn-primary" ${on("click", "finishOnboarding", true)}>${t("Открыть пример")}</button>
    </div>`, true);
}

async function finishOnboarding(openExample) {
  if (checked("ob-hints")) localStorage.removeItem("cpb-hints-off");
  else localStorage.setItem("cpb-hints-off", "1");
  if (checked("ob-more")) localStorage.removeItem("cpb-no-add-another");
  else localStorage.setItem("cpb-no-add-another", "1");
  localStorage.setItem("cpb-onboarded", "1");
  closeModal();
  if (openExample) {
    const ex = (state.projects || []).find(p => p.startsWith("example_astra")) ||
               (state.projects || []).find(p => p.startsWith("example_"));
    if (ex) await selectProject(ex);
  }
}
