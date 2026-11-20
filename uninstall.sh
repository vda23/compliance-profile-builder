#!/usr/bin/env bash
#
# Полное удаление службы Compliance Profile Builder: systemd-юнит,
# каталог установки (включая сертификаты), системный пользователь.
#
# Использование:
#   sudo bash uninstall.sh                     # спросит подтверждение
#   sudo bash uninstall.sh --yes               # без подтверждения
#   sudo bash uninstall.sh --keep-data         # оставить каталог data/ с проектами
#
set -euo pipefail

INSTALL_DIR="/opt/compliance-profile-builder"
SERVICE_USER="cpbuilder"
SERVICE_NAME="compliance-profile-builder"
ASSUME_YES="0"
KEEP_DATA="0"

usage() {
  cat <<EOF
Использование / Usage: sudo bash uninstall.sh [опции / options]

Опции:
  --install-dir <путь>   Каталог установки / Install directory (default: ${INSTALL_DIR})
  --user <имя>            Пользователь службы / Service user (default: ${SERVICE_USER})
  --keep-data             Сохранить данные проектов / Keep project data (${INSTALL_DIR}/data)
                           — полезно перед переустановкой на новую версию
  --yes                   Без подтверждения / Do not ask for confirmation
  -h, --help               Показать эту справку
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2 ;;
    --user) SERVICE_USER="$2"; shift 2 ;;
    --keep-data) KEEP_DATA="1"; shift ;;
    --yes) ASSUME_YES="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) err "Неизвестный параметр: $1" "Unknown option: $1"; usage; exit 1 ;;
  esac
done

log()  { echo -e "\033[1;36m[uninstall]\033[0m $1"; [[ -n "${2:-}" ]] && echo -e "          $2"; return 0; }
warn() { echo -e "\033[1;33m[внимание / warning]\033[0m $1"; [[ -n "${2:-}" ]] && echo -e "                     $2"; return 0; }
err()  { echo -e "\033[1;31m[ошибка / error]\033[0m $1" >&2; [[ -n "${2:-}" ]] && echo -e "                  $2" >&2; return 0; }

if [[ "${EUID}" -ne 0 ]]; then
  err "Скрипт нужно запускать от root: sudo bash uninstall.sh" "Run the script as root: sudo bash uninstall.sh"
  exit 1
fi

echo "Будет удалено / To be removed:"
echo "  - служба / service ${SERVICE_NAME}"
echo "  - /etc/systemd/system/${SERVICE_NAME}.service"
echo "  - каталог / directory ${INSTALL_DIR} (certs/ включительно / including certs/)"
if [[ "${KEEP_DATA}" == "1" ]]; then
  echo "    -> данные проектов будут сохранены / project data will be kept: ${INSTALL_DIR}/data"
fi
echo "  - пользователь / user ${SERVICE_USER}"
echo

if [[ "${ASSUME_YES}" != "1" ]]; then
  read -r -p "Продолжить? / Continue? [y/N]: " CONFIRM
  if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
    echo "Отменено. / Cancelled."
    exit 0
  fi
fi

# ---------------------------------------------------------------------------
# 1. Остановка и удаление systemd-службы
# ---------------------------------------------------------------------------
if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
    log "Останавливаю и отключаю службу ${SERVICE_NAME}…" "Stopping and disabling service ${SERVICE_NAME}…"
    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
  else
    log "Служба ${SERVICE_NAME} не зарегистрирована в systemd — пропускаю." "Service ${SERVICE_NAME} is not registered in systemd — skipping."
  fi
  if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
    log "Удаляю /etc/systemd/system/${SERVICE_NAME}.service…" "Removing /etc/systemd/system/${SERVICE_NAME}.service…"
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
  fi
  # Без «|| true» скрипт прерывался там, где systemd установлен, но не
  # запущен (контейнеры, нестандартная загрузка), и до удаления
  # пользователя дело не доходило.
  systemctl daemon-reload 2>/dev/null || true
  systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true
else
  warn "systemctl не найден — пропускаю шаг остановки службы." "systemctl not found — skipping the service stop step."
fi

# ---------------------------------------------------------------------------
# 2. Удаление каталога установки
# ---------------------------------------------------------------------------
if [[ -d "${INSTALL_DIR}" ]]; then
  if [[ "${KEEP_DATA}" == "1" && -d "${INSTALL_DIR}/data" ]]; then
    BACKUP_DIR="$(dirname "${INSTALL_DIR}")/compliance-profile-builder-data-backup-$(date +%Y%m%d%H%M%S)"
    log "Сохраняю ${INSTALL_DIR}/data в ${BACKUP_DIR} перед удалением…" "Saving ${INSTALL_DIR}/data to ${BACKUP_DIR} before removal…"
    mv "${INSTALL_DIR}/data" "${BACKUP_DIR}"
    log "Удаляю ${INSTALL_DIR}…" "Removing ${INSTALL_DIR}…"
    rm -rf "${INSTALL_DIR}"
    log "Данные проектов сохранены здесь: ${BACKUP_DIR}" "Project data saved here: ${BACKUP_DIR}"
  else
    log "Удаляю ${INSTALL_DIR}…" "Removing ${INSTALL_DIR}…"
    rm -rf "${INSTALL_DIR}"
  fi
else
  log "Каталог ${INSTALL_DIR} не найден — пропускаю." "Directory ${INSTALL_DIR} not found — skipping."
fi

# ---------------------------------------------------------------------------
# 3. Удаление системного пользователя
# ---------------------------------------------------------------------------
if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  log "Удаляю системного пользователя ${SERVICE_USER}…" "Removing system user ${SERVICE_USER}…"

  # userdel лежит в /usr/sbin. При входе в root через «su» без дефиса этого
  # каталога может не быть в PATH — тогда команда «не найдена».
  USERDEL="$(command -v userdel 2>/dev/null || true)"
  [[ -z "${USERDEL}" && -x /usr/sbin/userdel ]] && USERDEL=/usr/sbin/userdel
  [[ -z "${USERDEL}" && -x /sbin/userdel ]] && USERDEL=/sbin/userdel

  # userdel отказывается удалять пользователя, от имени которого работают
  # процессы — например, сервер, запущенный вручную, а не службой.
  if command -v pgrep >/dev/null 2>&1 && pgrep -u "${SERVICE_USER}" >/dev/null 2>&1; then
    log "Останавливаю процессы пользователя ${SERVICE_USER}:" "Stopping processes of user ${SERVICE_USER}:"
    pgrep -u "${SERVICE_USER}" -a 2>/dev/null | sed 's/^/    /' || true
    pkill -TERM -u "${SERVICE_USER}" 2>/dev/null || true
    for _ in 1 2 3 4 5; do
      pgrep -u "${SERVICE_USER}" >/dev/null 2>&1 || break
      sleep 1
    done
    pkill -KILL -u "${SERVICE_USER}" 2>/dev/null || true
    sleep 1
  fi

  if [[ -z "${USERDEL}" ]]; then
    warn "Команда userdel не найдена. Удалите пользователя вручную: sudo /usr/sbin/userdel ${SERVICE_USER}" "userdel not found. Remove the user manually: sudo /usr/sbin/userdel ${SERVICE_USER}"
  elif ERR="$("${USERDEL}" "${SERVICE_USER}" 2>&1)"; then
    log "Пользователь ${SERVICE_USER} удалён." "User ${SERVICE_USER} removed."
  else
    # Раньше причина отказа скрывалась — теперь выводится как есть.
    warn "Не удалось удалить пользователя ${SERVICE_USER}: ${ERR}" "Failed to remove user ${SERVICE_USER}: ${ERR}"
    warn "Удалите вручную: sudo pkill -u ${SERVICE_USER}; sudo ${USERDEL} ${SERVICE_USER}" "Remove manually: sudo pkill -u ${SERVICE_USER}; sudo ${USERDEL} ${SERVICE_USER}"
  fi

  # Группа с тем же именем обычно удаляется вместе с пользователем,
  # но на некоторых системах остаётся.
  if getent group "${SERVICE_USER}" >/dev/null 2>&1; then
    GROUPDEL="$(command -v groupdel 2>/dev/null || echo /usr/sbin/groupdel)"
    [[ -x "${GROUPDEL}" ]] && "${GROUPDEL}" "${SERVICE_USER}" 2>/dev/null || true
  fi
else
  log "Пользователь ${SERVICE_USER} не найден — пропускаю." "User ${SERVICE_USER} not found — skipping."
fi

echo
log "Удаление завершено. Служба, файлы и связанные зависимости удалены." "Removal complete. The service, files and related items have been removed."
if [[ "${KEEP_DATA}" == "1" ]]; then
  log "Не забудьте про сохранённую резервную копию данных проектов (см. выше)." "Remember the saved backup of project data (see above)."
fi
