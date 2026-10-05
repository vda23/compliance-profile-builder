#!/usr/bin/env bash
#
# Полное удаление службы Compliance Profile Builder: systemd-юнит,
# каталог установки (включая сертификаты), системный пользователь.
#
# Использование:
#   sudo bash deploy/uninstall.sh              # спросит подтверждение
#   sudo bash deploy/uninstall.sh --yes          # без подтверждения
#   sudo bash deploy/uninstall.sh --keep-data    # оставить каталог data/ с проектами
#
set -euo pipefail

INSTALL_DIR="/opt/compliance-profile-builder"
SERVICE_USER="cpbuilder"
SERVICE_NAME="compliance-profile-builder"
ASSUME_YES="0"
KEEP_DATA="0"

usage() {
  cat <<EOF
Использование: sudo bash deploy/uninstall.sh [опции]

Опции:
  --install-dir <путь>   Каталог установки (по умолчанию: ${INSTALL_DIR})
  --user <имя>            Системный пользователь службы (по умолчанию: ${SERVICE_USER})
  --keep-data             Не удалять каталог с данными проектов (${INSTALL_DIR}/data)
                           — полезно перед переустановкой на новую версию
  --yes                   Не спрашивать подтверждение
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
    *) echo "Неизвестный параметр: $1"; usage; exit 1 ;;
  esac
done

log()  { echo -e "\033[1;36m[uninstall]\033[0m $1"; }
warn() { echo -e "\033[1;33m[внимание]\033[0m $1"; }
err()  { echo -e "\033[1;31m[ошибка]\033[0m $1" >&2; }

if [[ "${EUID}" -ne 0 ]]; then
  err "Скрипт нужно запускать от root (sudo bash deploy/uninstall.sh)."
  exit 1
fi

echo "Будет удалено:"
echo "  - systemd-служба ${SERVICE_NAME} (остановлена и отключена)"
echo "  - файл /etc/systemd/system/${SERVICE_NAME}.service"
echo "  - каталог установки ${INSTALL_DIR} (включая certs/)"
if [[ "${KEEP_DATA}" == "1" ]]; then
  echo "    -> данные проектов (${INSTALL_DIR}/data) будут сохранены отдельно"
fi
echo "  - системный пользователь ${SERVICE_USER}"
echo

if [[ "${ASSUME_YES}" != "1" ]]; then
  read -r -p "Продолжить? [y/N]: " CONFIRM
  if [[ ! "${CONFIRM}" =~ ^[Yy]$ ]]; then
    echo "Отменено."
    exit 0
  fi
fi

# ---------------------------------------------------------------------------
# 1. Остановка и удаление systemd-службы
# ---------------------------------------------------------------------------
if command -v systemctl >/dev/null 2>&1; then
  if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
    log "Останавливаю и отключаю службу ${SERVICE_NAME}…"
    systemctl stop "${SERVICE_NAME}" 2>/dev/null || true
    systemctl disable "${SERVICE_NAME}" 2>/dev/null || true
  else
    log "Служба ${SERVICE_NAME} не зарегистрирована в systemd — пропускаю."
  fi
  if [[ -f "/etc/systemd/system/${SERVICE_NAME}.service" ]]; then
    log "Удаляю /etc/systemd/system/${SERVICE_NAME}.service…"
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
  fi
  systemctl daemon-reload
  systemctl reset-failed "${SERVICE_NAME}" 2>/dev/null || true
else
  warn "systemctl не найден — пропускаю шаг остановки службы."
fi

# ---------------------------------------------------------------------------
# 2. Удаление каталога установки
# ---------------------------------------------------------------------------
if [[ -d "${INSTALL_DIR}" ]]; then
  if [[ "${KEEP_DATA}" == "1" && -d "${INSTALL_DIR}/data" ]]; then
    BACKUP_DIR="$(dirname "${INSTALL_DIR}")/compliance-profile-builder-data-backup-$(date +%Y%m%d%H%M%S)"
    log "Сохраняю ${INSTALL_DIR}/data в ${BACKUP_DIR} перед удалением…"
    mv "${INSTALL_DIR}/data" "${BACKUP_DIR}"
    log "Удаляю ${INSTALL_DIR}…"
    rm -rf "${INSTALL_DIR}"
    log "Данные проектов сохранены здесь: ${BACKUP_DIR}"
  else
    log "Удаляю ${INSTALL_DIR}…"
    rm -rf "${INSTALL_DIR}"
  fi
else
  log "Каталог ${INSTALL_DIR} не найден — пропускаю."
fi

# ---------------------------------------------------------------------------
# 3. Удаление системного пользователя
# ---------------------------------------------------------------------------
if id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  log "Удаляю системного пользователя ${SERVICE_USER}…"
  userdel "${SERVICE_USER}" 2>/dev/null || warn "Не удалось удалить пользователя ${SERVICE_USER} — удалите вручную (userdel ${SERVICE_USER})."
else
  log "Пользователь ${SERVICE_USER} не найден — пропускаю."
fi

echo
log "Удаление завершено. Служба, файлы и связанные зависимости удалены."
if [[ "${KEEP_DATA}" == "1" ]]; then
  log "Не забудьте про сохранённую резервную копию данных проектов (см. выше)."
fi
