# Compliance Profile Builder

Сервис для упрощения процесса написания профилей соответствия по стандарту OVAL.

> **Версия 1.0.** Актуальная версия — в ветке [`main`](https://github.com/vda23/compliance-profile-builder) и на странице [Releases](https://github.com/vda23/compliance-profile-builder/releases).

## Назначение

Веб-сервис для создания профилей соответствия в формате XCCDF/OVAL и выгрузки их в виде ZIP-архива для импорта в Kaspersky Vulnerability Management.

Профиль собирается в браузере: пошаговый мастер проводит через все элементы проверки, подставляет идентификаторы и не даёт сослаться на несуществующий элемент.

Готовый архив проверяется встроенным валидатором до выгрузки.

## Системные требования

### Поддерживаемые ОС

- Альт Сервер 10 (64-bit)
- РЕД ОС 8 (64-bit)
- Astra Linux Common Edition 2.12 (64-bit)
- Astra Linux Special Edition РУСБ.10015-01 (1.8, 64-bit)
- Debian 11.x (64-bit)
- Platform V SberLinux OS Server 8.10.1 (64-bit)
- Platform V SberLinux OS Server 9.5.1 (64-bit)
- Ubuntu Server 22 (64-bit)

### Что нужно перед установкой

- 64-разрядная ОС из списка выше — x86_64 или aarch64
- `python3` версии 3.5 или новее
- `systemd` — для работы службы
- `openssl` — только для HTTPS
- 5 МБ свободного места на диске (место под создаваемые профили необходимо выделять дополнительно)

## Установка

### 1. Скачайте архив и перенесите его на сервер

Архив `compliance-profile-builder-v1.0.zip` — на странице [Releases](https://github.com/vda23/compliance-profile-builder/releases/tag/v1.0).

Перенесите его на сервер любым доступным способом — scp, съёмный носитель, внутренний файловый шлюз:

```bash
scp compliance-profile-builder-v1.0.zip user@server:/tmp/
```

### 2. Распакуйте архив и перейдите в директорию с установщиком

```bash
cd /tmp
unzip compliance-profile-builder-v1.0.zip
cd compliance-profile-builder
```

Если в системе нет `unzip`, подойдёт любой штатный архиватор, например:

```bash
python3 -m zipfile -e compliance-profile-builder-v1.0.zip .
```

### 3. Запустите установку

```bash
sudo bash deploy/install.sh
```

#### Скрипт выполнит

- проверку операционной системы и версии python3;
- копирование файлов в `/opt/compliance-profile-builder`;
- создание системного пользователя `cpbuilder` (без права входа в систему);
- выпуск самоподписанного HTTPS-сертификата, в который попадёт IP-адрес сервера;
- создание и запуск службы `compliance-profile-builder`.

#### По завершении скрипт выведет адреса, по которым доступен сервис

```
https://127.0.0.1:8443/   (доступ с сервера)
https://10.0.0.15:8443/   (доступ по сети)
```

### 4. Откройте сервис в браузере

Перейдите по адресу из вывода установщика.

Браузер предупредит о недоверенном сертификате — это ожидаемо для самоподписанного сертификата. Нажмите «Дополнительно» → «Перейти на сайт».

Чтобы предупреждения не было, установите собственный сертификат по инструкции ниже.

## Параметры установки

Вывод списка: `bash deploy/install.sh --help`

Использование другого порта:

```bash
sudo bash deploy/install.sh --port 9443
```

Добавление собственного сертификата вместо самоподписанного:

```bash
sudo bash deploy/install.sh --cert /path/to/fullchain.pem --key /path/to/privkey.pem
```

Имя в сертификате и срок его действия:

```bash
sudo bash deploy/install.sh --cn profiles.example.local --cert-days 365
```

Без HTTPS (например, если TLS завершается на обратном прокси):

```bash
sudo bash deploy/install.sh --no-tls
```

Доступ только с самого сервера:

```bash
sudo bash deploy/install.sh --host 127.0.0.1
```

## Управление службой

```bash
systemctl status compliance-profile-builder     # состояние
systemctl restart compliance-profile-builder    # перезапуск
systemctl stop compliance-profile-builder       # остановка
journalctl -u compliance-profile-builder -n 50 --no-pager   # журнал
```

Данные (созданные профили) хранятся в `/opt/compliance-profile-builder/data/projects/` — по одной папке на проект, внутри обычные XML-файлы. Это же место нужно включить в резервное копирование.

## Удаление

```bash
sudo bash deploy/uninstall.sh              # с подтверждением
sudo bash deploy/uninstall.sh --yes        # без подтверждения
sudo bash deploy/uninstall.sh --keep-data  # сохранить созданные профили
```

Удаляются: служба, каталог установки, системный пользователь `cpbuilder`.

## Если что-то пошло не так

| Симптом | Что сделать |
|---|---|
| Не найден python3 | Установите штатный пакет: `apt-get install python3` или `dnf install python3` |
| Требуется python3 версии 3.5 или новее | Обновите python3 средствами дистрибутива |
| Не найден openssl | Установите openssl либо ставьте сервис с `--no-tls` |
| Служба не запустилась | `journalctl -u compliance-profile-builder -n 50 --no-pager` |
| Сервис недоступен по сети | Проверьте, что порт открыт в межсетевом экране: `firewall-cmd --add-port=8443/tcp` или `ufw allow 8443/tcp` |
| Порт занят | Переустановите с другим портом: `--port 9443` |

## Состав репозитория

```
backend/        сервер на стандартной библиотеке Python
  app/server.py     веб-сервер и REST API
  app/xmlcompat.py  работа с XML средствами стандартной библиотеки
  app/*.py          построители XCCDF/OVAL, валидатор, экспорт и импорт ZIP
frontend/       интерфейс (HTML, CSS, JavaScript, шрифт)
data/projects/  хранилище профилей (XML-файлы)
deploy/
  install.sh                          установка
  uninstall.sh                        удаление
  compliance-profile-builder.service  справочный вид systemd-юнита
  nginx.conf.example                  пример обратного прокси (необязательно)
docs/           краткое описание сервиса и руководство пользователя (PDF)
```

## Работа с сервисом

- Порядок создания профиля, назначение элементов XCCDF/OVAL и разбор типовых ошибок — в [USAGE.md](USAGE.md).
- [Руководство пользователя (PDF)](docs/user-guide-compliance-profile-builder.pdf)
- [Краткое описание сервиса (PDF)](docs/summary-compliance-profile-builder.pdf)

## Disclaimer

© Made by Kaspersky Presales Russia Team

Данный сервис распространяется «as is» без каких-либо гарантий. Перед использованием в продуктивной среде рекомендуется провести тестирование.

Представленные материалы не являются официальными, поэтому есть вероятность, что в определенных случаях техническая поддержка может отказать вам в помощи.

Но Вы всегда можете обратиться за помощью к [автору скрипта](https://t.me/vda_23 "автору скрипта").
