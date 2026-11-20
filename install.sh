#!/usr/bin/env bash
#
# Установка Compliance Profile Builder.
#
# Версия скрипта: 3.0
#   Сервис переведён на стандартную библиотеку Python: FastAPI, uvicorn и
#   lxml больше не нужны. Установка не обращается в интернет, не использует
#   pip, venv и компиляторы — достаточно системного python3.
#
# СИСТЕМНЫЕ ТРЕБОВАНИЯ (минимальные)
#   - 64-разрядная ОС из списка поддерживаемых (см. ниже);
#   - python3 версии 3.5 или новее (входит в штатную поставку всех
#     поддерживаемых дистрибутивов);
#   - systemd — для работы службы;
#   - openssl — только если нужен HTTPS (есть в штатной поставке);
#   - около 5 МБ свободного места.
#
# ПОДДЕРЖИВАЕМЫЕ ОС
#   - Альт Сервер 10 (64-разрядная)
#   - РЕД ОС 8 (64-разрядная)
#   - Astra Linux Common Edition 2.12 (64-разрядная)
#   - Astra Linux Special Edition РУСБ.10015-01 1.8 (64-разрядная),
#     в том числе в режиме замкнутой программной среды
#   - Debian 11.x (64-разрядная)
#   - Platform V SberLinux OS Server (SLO) 8.10.1 (64-разрядная)
#   - Platform V SberLinux OS Server (SLO) 9.5.1 (64-разрядная)
#   - Ubuntu Server 22 (64-разрядная)
#
# ЗАПУСК
#   sudo bash install.sh
#
set -euo pipefail

INSTALL_SCRIPT_VERSION="1.0"

INSTALL_DIR="/opt/compliance-profile-builder"
SERVICE_USER="cpbuilder"
SERVICE_NAME="compliance-profile-builder"
SERVICE_HOST="0.0.0.0"
SERVICE_PORT="8443"
SKIP_SERVICE="0"
TLS_ENABLED="1"
TLS_CERT_SRC=""
TLS_KEY_SRC=""
TLS_CN="$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo localhost)"
TLS_DAYS="825"
PORT_EXPLICIT="0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # корень распакованного архива

usage() {
  cat <<EOF
Compliance Profile Builder — установка / installation (${INSTALL_SCRIPT_VERSION})

Использование / Usage:  sudo bash install.sh [опции / options]

  --port <порт>           Порт / Port (по умолчанию / default: 8443 HTTPS, 8000 HTTP)
  --cert <файл.pem>       Свой сертификат HTTPS (PEM), вместе с --key
                          Your own HTTPS certificate (PEM), together with --key
  --key <файл.pem>        Закрытый ключ сертификата (PEM) / Certificate private key (PEM)
  --no-tls                HTTP вместо HTTPS / HTTP instead of HTTPS
  --host <адрес>          Адрес прослушивания / Listen address (default: ${SERVICE_HOST})
  --cn <имя>              Имя в самоподписанном сертификате / Self-signed certificate CN
                          (default: ${TLS_CN})
  --cert-days <дней>      Срок самоподписанного сертификата / Self-signed validity, days (default: ${TLS_DAYS})
  --install-dir <путь>    Каталог установки / Install directory (default: ${INSTALL_DIR})
  --user <имя>            Пользователь службы / Service user (default: ${SERVICE_USER})
  --no-service            Без службы systemd / Do not create a systemd service
  -h, --help              Справка / This help

Примеры / Examples:
  sudo bash install.sh
  sudo bash install.sh --port 9443
  sudo bash install.sh --port 443 --cert /etc/ssl/cpb.crt --key /etc/ssl/cpb.key
  sudo bash install.sh --no-tls --port 8080

Удаление / Removal:  sudo bash uninstall.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir) INSTALL_DIR="$2"; shift 2 ;;
    --host) SERVICE_HOST="$2"; shift 2 ;;
    --port) SERVICE_PORT="$2"; PORT_EXPLICIT="1"; shift 2 ;;
    --user) SERVICE_USER="$2"; shift 2 ;;
    --no-tls) TLS_ENABLED="0"; shift ;;
    --cert) TLS_CERT_SRC="$2"; shift 2 ;;
    --key) TLS_KEY_SRC="$2"; shift 2 ;;
    --cn) TLS_CN="$2"; shift 2 ;;
    --cert-days) TLS_DAYS="$2"; shift 2 ;;
    --no-service) SKIP_SERVICE="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) err "Неизвестный параметр: $1" "Unknown option: $1"; usage; exit 1 ;;
  esac
done

[[ "${PORT_EXPLICIT}" == "0" && "${TLS_ENABLED}" == "0" ]] && SERVICE_PORT="8000"

log()  { echo -e "\033[1;36m[install]\033[0m $1"; [[ -n "${2:-}" ]] && echo -e "          $2"; return 0; }
warn() { echo -e "\033[1;33m[внимание / warning]\033[0m $1"; [[ -n "${2:-}" ]] && echo -e "                     $2"; return 0; }
err()  { echo -e "\033[1;31m[ошибка / error]\033[0m $1" >&2; [[ -n "${2:-}" ]] && echo -e "                  $2" >&2; return 0; }

log "Compliance Profile Builder — установка (версия скрипта ${INSTALL_SCRIPT_VERSION})" "Compliance Profile Builder — installation (script version ${INSTALL_SCRIPT_VERSION})"

# --- проверка значений ключей до каких-либо изменений в системе
if ! [[ "${SERVICE_PORT}" =~ ^[0-9]+$ ]] || (( SERVICE_PORT < 1 || SERVICE_PORT > 65535 )); then
  err "Неверный порт: ${SERVICE_PORT}. Укажите число от 1 до 65535." "Invalid port: ${SERVICE_PORT}. Use a number from 1 to 65535."
  exit 1
fi
for f in "${TLS_CERT_SRC}" "${TLS_KEY_SRC}"; do
  if [[ -n "$f" && ! -r "$f" ]]; then
    err "Файл не найден или недоступен для чтения: $f" "File not found or not readable: $f"
    exit 1
  fi
done

if [[ "${EUID}" -ne 0 ]]; then
  err "Запустите скрипт с правами root: sudo bash install.sh" "Run the script as root: sudo bash install.sh"
  exit 1
fi
if { [[ -n "${TLS_CERT_SRC}" ]] && [[ -z "${TLS_KEY_SRC}" ]]; } || { [[ -z "${TLS_CERT_SRC}" ]] && [[ -n "${TLS_KEY_SRC}" ]]; }; then
  err "Флаги --cert и --key указываются вместе." "--cert and --key must be given together."
  exit 1
fi

# ---------------------------------------------------------------------------
# 1. Проверка ОС
# ---------------------------------------------------------------------------
OS_NAME="неизвестная ОС"; OS_ID=""
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  OS_NAME="${PRETTY_NAME:-${NAME:-неизвестная ОС}}"
  OS_ID="${ID:-}"
fi
log "Операционная система: ${OS_NAME}" "Operating system: ${OS_NAME}"

ARCH="$(uname -m)"
if [[ "${ARCH}" != "x86_64" && "${ARCH}" != "aarch64" ]]; then
  warn "Архитектура ${ARCH} не входит в список проверенных (x86_64, aarch64)." "Architecture ${ARCH} is not on the tested list (x86_64, aarch64)."
fi

KNOWN=0
for id in altlinux alt redos astra debian ubuntu sberlinux slo; do
  [[ "${OS_ID,,}" == *"${id}"* ]] && KNOWN=1
done
if [[ "${KNOWN}" -eq 0 ]]; then
  warn "Эта ОС не входит в список поддерживаемых: Astra Linux, РЕД ОС, Альт, SberLinux, Debian, Ubuntu. Установка продолжится, работоспособность не гарантируется." \
       "This OS is not on the supported list: Astra Linux, RED OS, ALT, SberLinux, Debian, Ubuntu. Installation continues; operation is not guaranteed."
fi

# ---------------------------------------------------------------------------
# 2. Проверка python3 (единственная обязательная зависимость)
# ---------------------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
  err "Не найден python3. Установите его: apt-get install python3 (Astra Linux, Debian, Ubuntu) или dnf install python3 (РЕД ОС, Альт, SberLinux)." \
      "python3 not found. Install it: apt-get install python3 (Astra Linux, Debian, Ubuntu) or dnf install python3 (RED OS, ALT, SberLinux)."
  exit 1
fi
PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,5) else 1)'; then
  err "Требуется python3 версии 3.5 или новее, установлена ${PY_VER}." "python3 3.5 or newer is required, found ${PY_VER}."
  exit 1
fi
log "python3: ${PY_VER} — подходит (внешние пакеты не требуются)" "python3: ${PY_VER} — OK (no external packages required)"

# Astra Linux в режиме замкнутой программной среды: предупреждаем, но не
# блокируем — сервис состоит только из скриптов python и не содержит
# собственных бинарных модулей, поэтому ЗПС ему не мешает.
if [[ "${OS_ID,,}" == *astra* ]]; then
  if [[ "$(sysctl -n parsec.zpsflag 2>/dev/null || sysctl -n kernel.digsig_verif_mode 2>/dev/null || echo 0)" != "0" ]]; then
    log "Обнаружен режим замкнутой программной среды. Сервис использует только штатный python3 и не содержит бинарных модулей — подпись файлов не требуется." \
        "Closed software environment detected. The service uses only the system python3 and has no binary modules — no file signing needed."
  fi
fi

# ---------------------------------------------------------------------------
# 3. Копирование файлов
# ---------------------------------------------------------------------------
log "Копирую файлы в ${INSTALL_DIR}…" "Copying files to ${INSTALL_DIR}…"
mkdir -p "${INSTALL_DIR}"
for d in backend frontend; do
  rm -rf "${INSTALL_DIR:?}/${d}"
  cp -a "${SCRIPT_DIR}/${d}" "${INSTALL_DIR}/"
done
# Скрипты установки и удаления — в корень каталога установки: удалить сервис
# можно и без исходного архива: sudo bash ${INSTALL_DIR}/uninstall.sh
cp -a "${SCRIPT_DIR}/install.sh" "${SCRIPT_DIR}/uninstall.sh" "${INSTALL_DIR}/"
# прежние установки хранили скрипты в подкаталоге deploy
rm -rf "${INSTALL_DIR:?}/deploy"
[[ -f "${SCRIPT_DIR}/README.md" ]] && cp -a "${SCRIPT_DIR}/README.md" "${INSTALL_DIR}/" || true
mkdir -p "${INSTALL_DIR}/data/projects"
# Демонстрационные проекты копируются только при первой установке, чтобы
# обновление сервиса не затирало созданные пользователем профили.
if [[ -d "${SCRIPT_DIR}/data/projects" ]] && [[ -z "$(ls -A "${INSTALL_DIR}/data/projects" 2>/dev/null)" ]]; then
  cp -a "${SCRIPT_DIR}/data/projects/." "${INSTALL_DIR}/data/projects/" 2>/dev/null || true
fi
find "${INSTALL_DIR}" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

if [[ ! -f "${INSTALL_DIR}/frontend/static/fonts/KasperskySans-Regular.ttf" ]]; then
  warn "Не найден файл шрифта frontend/static/fonts/KasperskySans-Regular.ttf — интерфейс будет работать с системным шрифтом." \

       "Font file frontend/static/fonts/KasperskySans-Regular.ttf not found — the interface will use a system font."
fi

# ---------------------------------------------------------------------------
# 4. Системный пользователь
# ---------------------------------------------------------------------------
if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  log "Создаю системного пользователя ${SERVICE_USER}…" "Creating system user ${SERVICE_USER}…"
  useradd --system --no-create-home --shell /usr/sbin/nologin "${SERVICE_USER}" 2>/dev/null \
    || useradd --system --no-create-home --shell /sbin/nologin "${SERVICE_USER}"
fi
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${INSTALL_DIR}"

# ---------------------------------------------------------------------------
# 5. HTTPS-сертификат
# ---------------------------------------------------------------------------
CERT_PATH=""; KEY_PATH=""
if [[ "${TLS_ENABLED}" == "1" ]]; then
  if ! command -v openssl >/dev/null 2>&1; then
    err "Не найден openssl — он нужен для создания HTTPS-сертификата. Установите openssl или запустите установку с ключом --no-tls." \
        "openssl not found — it is needed to create the HTTPS certificate. Install openssl or run the installer with --no-tls."
    exit 1
  fi
  CERT_DIR="${INSTALL_DIR}/certs"; mkdir -p "${CERT_DIR}"
  CERT_PATH="${CERT_DIR}/server.crt"; KEY_PATH="${CERT_DIR}/server.key"

  if [[ -n "${TLS_CERT_SRC}" ]]; then
    log "Устанавливаю предоставленный сертификат…" "Installing the provided certificate…"
    cp "${TLS_CERT_SRC}" "${CERT_PATH}"; cp "${TLS_KEY_SRC}" "${KEY_PATH}"
  elif [[ -f "${CERT_PATH}" && -f "${KEY_PATH}" ]]; then
    log "Использую ранее созданный сертификат из ${CERT_DIR}." "Using the existing certificate from ${CERT_DIR}."
  else
    # В сертификат добавляются все IP-адреса сервера, чтобы к сервису можно
    # было обращаться по адресу, а не только по имени.
    RAW_IPS="127.0.0.1"
    command -v hostname >/dev/null 2>&1 && RAW_IPS="${RAW_IPS} $(hostname -I 2>/dev/null || true)"
    # 0.0.0.0 — это «слушать на всех интерфейсах», а не адрес сервера:
    # в сертификат он попадать не должен.
    if [[ "${SERVICE_HOST}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ && "${SERVICE_HOST}" != "0.0.0.0" ]]; then
      RAW_IPS="${RAW_IPS} ${SERVICE_HOST}"
    fi
    UNIQUE_IPS="$(echo "${RAW_IPS}" | tr ' ' '\n' | awk 'NF && !seen[$0]++')"
    SAN="DNS:${TLS_CN},DNS:localhost"
    for ip in ${UNIQUE_IPS}; do SAN="${SAN},IP:${ip}"; done
    log "Создаю самоподписанный сертификат (CN=${TLS_CN}, срок ${TLS_DAYS} дн.)…" "Creating a self-signed certificate (CN=${TLS_CN}, valid ${TLS_DAYS} days)…"
    log "Адреса в сертификате: ${SAN}" "Certificate addresses: ${SAN}"
    openssl req -x509 -nodes -newkey rsa:2048 \
      -keyout "${KEY_PATH}" -out "${CERT_PATH}" -days "${TLS_DAYS}" \
      -subj "/C=RU/O=Compliance Profile Builder/CN=${TLS_CN}" \
      -addext "subjectAltName=${SAN}" >/dev/null 2>&1
    warn "Сертификат самоподписанный: браузер покажет предупреждение. Для эксплуатации укажите сертификат организации: --cert и --key." \
         "The certificate is self-signed: browsers will show a warning. For production use your organisation's certificate: --cert and --key."
  fi
  chown -R "${SERVICE_USER}:${SERVICE_USER}" "${CERT_DIR}"
  chmod 600 "${KEY_PATH}"; chmod 644 "${CERT_PATH}"
fi

# ---------------------------------------------------------------------------
# 6. Служба systemd
# ---------------------------------------------------------------------------
PYTHON_BIN="$(command -v python3)"
EXEC="${PYTHON_BIN} -m app.server --host ${SERVICE_HOST} --port ${SERVICE_PORT}"
[[ "${TLS_ENABLED}" == "1" ]] && EXEC="${EXEC} --cert ${CERT_PATH} --key ${KEY_PATH}"

if [[ "${SKIP_SERVICE}" == "1" ]]; then
  log "Флаг --no-service: служба не создаётся. Ручной запуск:" "--no-service: no service is created. Start manually:"
  log "  cd ${INSTALL_DIR}/backend && CPB_DATA_DIR=${INSTALL_DIR}/data ${EXEC}"
elif ! command -v systemctl >/dev/null 2>&1; then
  warn "systemd не найден — служба не создана. Ручной запуск:" "systemd not found — no service created. Start manually:"
  warn "  cd ${INSTALL_DIR}/backend && CPB_DATA_DIR=${INSTALL_DIR}/data ${EXEC}"
else
  log "Создаю службу ${SERVICE_NAME}…" "Creating service ${SERVICE_NAME}…"
  cat > "/etc/systemd/system/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Compliance Profile Builder (конструктор профилей XCCDF/OVAL)
After=network.target

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${INSTALL_DIR}/backend
Environment=CPB_DATA_DIR=${INSTALL_DIR}/data
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=${EXEC}
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}" >/dev/null 2>&1
  # restart, а не start: при обновлении служба уже работает, и «enable --now»
  # её не перезапускал — в памяти оставался старый код сервера, а интерфейс
  # с диска отдавался уже новый. Новые функции интерфейса получали ответ
  # «Метод API не найден».
  systemctl restart "${SERVICE_NAME}"
  sleep 2
  if systemctl is-active --quiet "${SERVICE_NAME}"; then
    log "Служба ${SERVICE_NAME} запущена." "Service ${SERVICE_NAME} is running."
  else
    err "Служба не запустилась. Журнал: journalctl -u ${SERVICE_NAME} -n 50 --no-pager" "The service failed to start. Log: journalctl -u ${SERVICE_NAME} -n 50 --no-pager"
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# Итог
# ---------------------------------------------------------------------------
SCHEME="http"; [[ "${TLS_ENABLED}" == "1" ]] && SCHEME="https"
echo
log "Установка завершена." "Installation complete."
echo "  Каталог / Directory:        ${INSTALL_DIR}"
echo "  Данные / Data:              ${INSTALL_DIR}/data"
[[ "${TLS_ENABLED}" == "1" ]] && echo "  Сертификат / Certificate:   ${CERT_PATH}"
echo "  Служба / Service:           systemctl status ${SERVICE_NAME}"
echo
echo "  Адрес сервиса / Service URL:"
echo "    ${SCHEME}://127.0.0.1:${SERVICE_PORT}/   (с этого сервера / from this server)"
if [[ "${SERVICE_HOST}" == "0.0.0.0" ]] && command -v hostname >/dev/null 2>&1; then
  for ip in $(hostname -I 2>/dev/null | tr ' ' '\n' | awk 'NF && !seen[$0]++'); do
    [[ "${ip}" == "127.0.0.1" ]] && continue
    echo "    ${SCHEME}://${ip}:${SERVICE_PORT}/   (по сети / over the network)"
  done
fi
echo
echo "  Удаление / Removal:         sudo bash ${INSTALL_DIR}/uninstall.sh"
