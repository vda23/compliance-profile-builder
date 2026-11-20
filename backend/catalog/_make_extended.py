"""Пакет каталога «Расширенные проверки».

Технические проверки к темам, добавленным в базу знаний: блокировка учётных
записей, неактивные учётные записи, хеширование паролей, контроль
целостности, синхронизация времени, централизованный сбор журналов,
криптостойкость SSH, съёмные носители, загрузчик, межсетевой экран и
типовые настройки Windows. Плюс организационные меры для новых групп мер
приказа ФСТЭК №117, которые техническими средствами не проверяются.

Каждая проверка проходит проверку схемы OVAL 5.11.2 (oscap oval validate).
"""
import json, os

LNX = ["Astra Linux", "Debian", "Ubuntu", "РЕД ОС", "ALT Linux", "SberLinux"]
WIN = ["Windows 10", "Windows 11", "Windows Server 2016", "Windows Server 2019", "Windows Server 2022"]
SP = "[[:space:]]"


def tfc(id_, title, cat, path, fname, pattern, value, why, fix, kw, notes=None, exist="at_least_one_exists"):
    """Проверка содержимого конфигурационного файла по шаблону."""
    e = {
        "id": id_, "title": title, "category": cat,
        "description": "Проверяется содержимое файла %s/%s." % (path, fname),
        "rationale": why, "keywords": kw,
        "platforms": {"family": "unix", "os": LNX},
        "params": [] if value is None else [{"name": "value", "title": "Допустимые значения (регулярное выражение)",
                                              "default": value, "datatype": "string"}],
        "check": {
            "type": "ind:textfilecontent54_test",
            "object": {"path": path, "filename": fname, "pattern": pattern},
            "state": {} if value is None else
                     {"subexpression": {"value": "{{value}}", "operation": "pattern match", "datatype": "string"}},
            "check": "all", "check_existence": exist,
        },
        "remediation": fix,
    }
    if notes:
        e["notes"] = notes
    return e


def pkg(id_, title, cat, deb, rpm, why, fix, kw, notes=None):
    e = {
        "id": id_, "title": title, "category": cat,
        "description": "Проверяется, что установлен пакет %s." % (deb if deb == rpm else "%s (DEB) / %s (RPM)" % (deb, rpm)),
        "rationale": why, "keywords": kw,
        "platforms": {"family": "unix", "os": LNX},
        "params": [],
        "check": {"type": "pkg", "object": {"name": {"deb": deb, "rpm": rpm}}, "state": {},
                  "check": "all", "check_existence": "at_least_one_exists"},
        "remediation": fix,
    }
    if notes:
        e["notes"] = notes
    return e


def reg(id_, title, cat, key, name, value, why, fix, kw, op="equals"):
    """Параметр реестра Windows (REG_DWORD)."""
    return {
        "id": id_, "title": title, "category": cat,
        "description": "Проверяется параметр реестра HKLM\\%s\\%s." % (key, name),
        "rationale": why, "keywords": kw,
        "platforms": {"family": "windows", "os": WIN},
        "params": [{"name": "value", "title": "Ожидаемое значение", "default": value, "datatype": "int"}],
        "check": {
            "type": "windows:registry_test",
            "object": {"hive": "HKEY_LOCAL_MACHINE", "key": key, "name": name},
            "state": {"value": {"value": "{{value}}", "operation": op, "datatype": "int"}},
            "check": "all", "check_existence": "at_least_one_exists",
        },
        "remediation": fix,
    }


def manual(id_, title, desc, why, kw, os_family="unix"):
    return {
        "id": id_, "title": title, "category": "Организационные меры",
        "description": desc, "rationale": why, "keywords": kw,
        "platforms": {"family": os_family, "os": []},
        "manual": True, "remediation": desc, "notes": why,
    }


checks = [
    # ---------------------------------------------------- учётные записи
    tfc("ext.accounts_lockout", "Блокировка учётной записи после неудачных попыток входа", "Парольная политика",
        "/etc/security", "faillock.conf", "^%s*deny%s*=%s*([0-9]+)" % (SP, SP, SP), "^[1-5]$",
        "Блокировка после нескольких неудачных попыток делает подбор пароля практически невозможным.",
        "В /etc/security/faillock.conf задать deny = 5 (или меньше) и подключить pam_faillock в стеке PAM.",
        ["блокировка", "faillock", "попытки входа", "подбор пароля"],
        "Файл faillock.conf поддерживается PAM версии 1.4 и новее. В старых системах параметр deny задаётся в строке pam_faillock.so или pam_tally2.so стека PAM."),
    tfc("ext.accounts_inactive", "Блокировка неактивных учётных записей", "Управление доступом",
        "/etc/default", "useradd", "^%s*INACTIVE%s*=%s*([0-9-]+)" % (SP, SP, SP), "^([1-9]|[1-3][0-9]|4[0-5])$",
        "Учётная запись, которой давно не пользуются, — удобная цель: её компрометацию никто не заметит.",
        "В /etc/default/useradd задать INACTIVE=45 (или меньше); для существующих — chage --inactive 45 <пользователь>.",
        ["неактивные учётные записи", "inactive", "useradd"],
        "Параметр применяется к создаваемым учётным записям. Для существующих срок задаётся командой chage."),
    tfc("ext.accounts_uid0", "Единственная учётная запись с UID 0", "Управление доступом",
        "/etc", "passwd", "^([^:]+):[^:]*:0:", "^root$",
        "Каждая учётная запись с UID 0 обладает полными правами суперпользователя; лишние такие записи — скрытый административный доступ.",
        "Удалить или переназначить UID у всех учётных записей с UID 0, кроме root.",
        ["uid 0", "суперпользователь", "passwd"]),
    tfc("ext.password_hashing", "Стойкий алгоритм хеширования паролей", "Парольная политика",
        "/etc", "login.defs", "^%s*ENCRYPT_METHOD%s+([A-Za-z0-9]+)" % (SP, SP), "^(SHA512|YESCRYPT)$",
        "Слабый алгоритм хеширования позволяет быстро подобрать пароли по украденному файлу хешей.",
        "В /etc/login.defs задать ENCRYPT_METHOD SHA512 (или YESCRYPT, если поддерживается).",
        ["хеширование паролей", "sha512", "yescrypt", "login.defs"]),
    tfc("ext.umask", "Права по умолчанию для создаваемых файлов", "Права на файлы",
        "/etc", "login.defs", "^%s*UMASK%s+([0-7]+)" % (SP, SP), "^0?(27|77)$",
        "Маска 022 делает новые файлы пользователей читаемыми всеми; 027 закрывает их от посторонних.",
        "В /etc/login.defs задать UMASK 027.",
        ["umask", "права по умолчанию", "login.defs"]),

    # ------------------------------------------- целостность, время, журналы
    pkg("ext.aide_installed", "Средство контроля целостности файлов", "Целостность", "aide", "aide",
        "Контроль целостности выявляет подмену системных файлов и конфигураций.",
        "Установить пакет aide, инициализировать базу (aideinit / aide --init) и настроить периодическую проверку.",
        ["контроль целостности", "aide"],
        "В Astra Linux штатное средство контроля целостности — AFICK; при его использовании проверку стоит заменить на наличие пакета afick."),
    pkg("ext.chrony_installed", "Служба синхронизации времени", "Регистрация событий", "chrony", "chrony",
        "Без единого времени события из разных журналов невозможно сопоставить при разборе инцидента.",
        "Установить chrony и указать в /etc/chrony.conf источник точного времени организации.",
        ["синхронизация времени", "chrony", "ntp"],
        "Если в организации используется systemd-timesyncd или ntpd, проверку стоит заменить на соответствующий пакет."),
    tfc("ext.rsyslog_remote", "Передача журналов на централизованный сервер", "Регистрация событий",
        "/etc", "rsyslog.conf", "^[^#]*(@@?[A-Za-z0-9._-]+|target=\"[A-Za-z0-9._-]+\")", None,
        "Журналы, хранящиеся только на самом узле, злоумышленник может удалить вместе со следами атаки.",
        "Добавить в /etc/rsyslog.conf пересылку на сервер сбора событий, например: *.* @@siem.example.local:514",
        ["централизованный сбор", "rsyslog", "siem", "syslog"],
        "Проверяется основной файл /etc/rsyslog.conf. Если пересылка настроена в /etc/rsyslog.d/, укажите путь к нужному файлу в объекте."),

    # ------------------------------------------------------------- SSH
    tfc("ext.ssh_weak_ciphers", "SSH не использует устаревшие алгоритмы шифрования", "Удалённый доступ",
        "/etc/ssh", "sshd_config", "^%s*Ciphers%s+(.*(cbc|arcfour|3des).*)" % (SP, SP), None,
        "Режим CBC, RC4 и 3DES уязвимы; их наличие в списке позволяет понизить стойкость соединения.",
        "Задать в sshd_config список только стойких алгоритмов, например: Ciphers aes256-gcm@openssh.com,chacha20-poly1305@openssh.com,aes256-ctr",
        ["ciphers", "шифрование", "ssh", "cbc"],
        "Проверка от обратного: нарушение — наличие в строке Ciphers устаревшего алгоритма.",
        exist="none_exist"),
    tfc("ext.ssh_banner", "Предупреждение при входе по SSH", "Удалённый доступ",
        "/etc/ssh", "sshd_config", "^%s*Banner%s+([^#%s]+)" % (SP, SP, SP), "^/.+",
        "Предупреждение о мониторинге и ответственности — обязательное условие для правового преследования нарушителя во многих юрисдикциях.",
        "Задать Banner /etc/issue.net и разместить в нём текст предупреждения.",
        ["баннер", "предупреждение", "issue.net", "ssh"]),
    tfc("ext.ssh_login_grace", "Ограничение времени на аутентификацию по SSH", "Удалённый доступ",
        "/etc/ssh", "sshd_config", "^%s*LoginGraceTime%s+([0-9]+)" % (SP, SP), "^([1-9]|[1-5][0-9]|60)$",
        "Долгое ожидание аутентификации позволяет держать множество незавершённых подключений и исчерпать ресурсы сервера.",
        "Задать LoginGraceTime 60 (или меньше) в /etc/ssh/sshd_config.",
        ["logingracetime", "ssh", "тайм-аут"]),

    # ----------------------------------------------- планировщик, носители
    {
        "id": "ext.cron_allow", "title": "Доступ к планировщику по списку разрешённых", "category": "Права на файлы",
        "description": "Проверяется наличие файла /etc/cron.allow.",
        "rationale": "Без списка разрешённых пользоваться планировщиком может любой пользователь — это способ закрепиться в системе.",
        "keywords": ["cron.allow", "планировщик", "cron"],
        "platforms": {"family": "unix", "os": LNX},
        "params": [],
        "check": {"type": "unix:file_test", "object": {"path": "/etc", "filename": "cron.allow"}, "state": {},
                  "check": "all", "check_existence": "at_least_one_exists"},
        "remediation": "Создать /etc/cron.allow со списком пользователей, которым разрешён планировщик (обычно только root), права 600.",
    },
    tfc("ext.usb_storage", "Запрет подключения USB-накопителей", "Защита носителей",
        "/etc/modprobe.d", "usb-storage.conf", "^%s*(install%s+usb-storage%s+/bin/(true|false)|blacklist%s+usb-storage)" % (SP, SP, SP, SP), None,
        "Съёмные носители — канал утечки данных и занесения вредоносного кода.",
        "Создать /etc/modprobe.d/usb-storage.conf со строками: install usb-storage /bin/false и blacklist usb-storage",
        ["usb", "съёмные носители", "modprobe"],
        "Проверяется файл /etc/modprobe.d/usb-storage.conf. Если запрет задан в другом файле каталога, укажите его имя в объекте."),
    {
        **tfc("ext.grub_password", "Пароль на изменение параметров загрузчика", "Загрузка системы",
              "{{grubdir}}", "grub.cfg", "^%s*password_pbkdf2%s+([A-Za-z0-9_.-]+)" % (SP, SP), None,
              "Без пароля загрузчика любой с физическим доступом может загрузиться в однопользовательский режим и получить права root.",
              "Задать пароль: grub-mkpasswd-pbkdf2, добавить set superusers и password_pbkdf2 в /etc/grub.d/40_custom, затем update-grub.",
              ["grub", "загрузчик", "пароль загрузчика"],
              "Каталог загрузчика: /boot/grub в Debian, Ubuntu, Astra Linux; /boot/grub2 в РЕД ОС, ALT Linux, SberLinux — задаётся параметром."),
        "params": [{"name": "grubdir", "title": "Каталог загрузчика", "default": "/boot/grub", "datatype": "string",
                    "default_by_family": {"deb": "/boot/grub", "rpm": "/boot/grub2"}}],
    },
    {
        "id": "ext.firewall_active", "title": "Межсетевой экран на узле запущен", "category": "Сетевые параметры",
        "description": "Проверяется, что служба межсетевого экрана активна.",
        "rationale": "Межсетевой экран на узле ограничивает доступ к сетевым службам и сдерживает распространение атаки внутри сети.",
        "keywords": ["межсетевой экран", "nftables", "firewalld", "ufw"],
        "platforms": {"family": "unix", "os": LNX},
        "params": [{"name": "unit", "title": "Служба межсетевого экрана", "default": "nftables.service", "datatype": "string"}],
        "check": {"type": "linux:systemdunitproperty_test",
                  "object": {"unit": "{{unit}}", "property": "ActiveState"},
                  "state": {"value": {"value": "active", "operation": "equals", "datatype": "string"}},
                  "check": "all", "check_existence": "at_least_one_exists"},
        "remediation": "Включить и запустить межсетевой экран: systemctl enable --now nftables (или firewalld, ufw).",
        "notes": "Служба задаётся параметром: nftables.service, firewalld.service или ufw.service — в зависимости от принятого в организации средства.",
    },

    # ------------------------------------------------------------- Windows
    reg("ext.win_smb1", "Отключение клиента SMBv1", "Сетевые службы",
        "SYSTEM\\CurrentControlSet\\Services\\mrxsmb10", "Start", "4",
        "Протокол SMBv1 устарел и использовался в массовых атаках (WannaCry, NotPetya).",
        "Отключить компонент SMB 1.0/CIFS или задать значение Start = 4 для службы mrxsmb10.",
        ["smbv1", "smb1", "mrxsmb10"]),
    reg("ext.win_uac", "Контроль учётных записей (UAC) включён", "Повышение привилегий",
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System", "EnableLUA", "1",
        "Без UAC любая программа, запущенная администратором, работает с полными правами.",
        "Включить политику «Контроль учётных записей: все администраторы работают в режиме одобрения».",
        ["uac", "enablelua", "контроль учётных записей"]),
    reg("ext.win_autorun", "Автозапуск отключён для всех типов носителей", "Защита носителей",
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer", "NoDriveTypeAutoRun", "255",
        "Автозапуск со съёмного носителя — классический способ заражения.",
        "Задать политику «Отключить автозапуск» для всех дисков (NoDriveTypeAutoRun = 255).",
        ["autorun", "автозапуск"]),
    reg("ext.win_lm_hash", "Хеши LAN Manager не хранятся", "Парольная политика",
        "SYSTEM\\CurrentControlSet\\Control\\Lsa", "NoLMHash", "1",
        "LM-хеши подбираются за минуты; их хранение сводит на нет требования к сложности паролей.",
        "Включить политику «Сетевая безопасность: не хранить хеш-значения LAN Manager».",
        ["lm hash", "nolmhash"]),
    reg("ext.win_rdp_nla", "Проверка подлинности на уровне сети для RDP", "Удалённый доступ",
        "SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp", "UserAuthentication", "1",
        "Без NLA сеанс RDP создаётся до проверки подлинности, что расширяет поверхность атаки на службу.",
        "Включить «Требовать проверку подлинности пользователя на уровне сети» для удалённых подключений.",
        ["rdp", "nla", "удалённый рабочий стол"]),
    reg("ext.win_ps_logging", "Журналирование блоков сценариев PowerShell", "Регистрация событий",
        "SOFTWARE\\Policies\\Microsoft\\Windows\\PowerShell\\ScriptBlockLogging", "EnableScriptBlockLogging", "1",
        "PowerShell — основной инструмент атак без файлов; без журналирования их действия не видны.",
        "Включить политику «Включить ведение журнала блоков сценариев PowerShell».",
        ["powershell", "журналирование"]),
    reg("ext.win_firewall", "Брандмауэр Windows включён (стандартный профиль)", "Сетевые параметры",
        "SYSTEM\\CurrentControlSet\\Services\\SharedAccess\\Parameters\\FirewallPolicy\\StandardProfile", "EnableFirewall", "1",
        "Брандмауэр на узле ограничивает доступ к сетевым службам и распространение атаки внутри сети.",
        "Включить брандмауэр Windows для всех профилей.",
        ["брандмауэр", "firewall", "межсетевой экран"]),
    {
        "id": "ext.win_password_length", "title": "Минимальная длина пароля (Windows)", "category": "Парольная политика",
        "description": "Проверяется, что минимальная длина пароля не меньше заданной.",
        "rationale": "Короткий пароль подбирается перебором за приемлемое время.",
        "keywords": ["длина пароля", "парольная политика", "windows"],
        "platforms": {"family": "windows", "os": WIN},
        "params": [{"name": "value", "title": "Минимальная длина", "default": "14", "datatype": "int"}],
        "check": {"type": "windows:passwordpolicy_test", "object": {},
                  "state": {"min_passwd_len": {"value": "{{value}}", "operation": "greater than or equal", "datatype": "int"}},
                  "check": "all", "check_existence": "at_least_one_exists"},
        "remediation": "Задать политику «Минимальная длина пароля» не менее 14 символов.",
    },
    {
        "id": "ext.win_password_history", "title": "История паролей (Windows)", "category": "Парольная политика",
        "description": "Проверяется, что система хранит историю ранее использованных паролей.",
        "rationale": "Без истории пользователь возвращается к прежнему паролю, и периодическая смена теряет смысл.",
        "keywords": ["история паролей", "windows"],
        "platforms": {"family": "windows", "os": WIN},
        "params": [{"name": "value", "title": "Глубина истории", "default": "24", "datatype": "int"}],
        "check": {"type": "windows:passwordpolicy_test", "object": {},
                  "state": {"password_hist_len": {"value": "{{value}}", "operation": "greater than or equal", "datatype": "int"}},
                  "check": "all", "check_existence": "at_least_one_exists"},
        "remediation": "Задать политику «Вести журнал паролей» не менее 24.",
    },
    {
        "id": "ext.win_audit_logon", "title": "Аудит входа в систему (Windows)", "category": "Регистрация событий",
        "description": "Проверяется, что регистрируются успешные и неудачные попытки входа.",
        "rationale": "Без аудита входа попытки подбора пароля и вход под чужой учётной записью остаются незамеченными.",
        "keywords": ["аудит", "вход в систему", "windows"],
        "platforms": {"family": "windows", "os": WIN},
        "params": [],
        "check": {"type": "windows:auditeventpolicysubcategories_test", "object": {},
                  "state": {"logon": {"value": "AUDIT_SUCCESS_FAILURE", "operation": "equals", "datatype": "string"}},
                  "check": "all", "check_existence": "at_least_one_exists"},
        "remediation": "Включить аудит подкатегории «Вход в систему» для успешных и неудачных событий.",
    },

    # ------------------------------------------------------------
    # Тайм-аут сессии, сложность пароля,
    # защита и хранение журналов.
    tfc("ext.ssh_client_alive", "Завершение неактивных SSH-сеансов", "Удалённый доступ",
        "/etc/ssh", "sshd_config", "^%s*ClientAliveInterval%s+([0-9]+)" % (SP, SP), "^([1-9]|[1-9][0-9]|[1-8][0-9]{2}|900)$",
        "Оставленный открытым сеанс администратора позволяет воспользоваться им любому, кто окажется за терминалом.",
        "Задать в /etc/ssh/sshd_config ClientAliveInterval 900 (или меньше) и ClientAliveCountMax 0, перезапустить sshd.",
        ["clientaliveinterval", "тайм-аут", "неактивный сеанс", "ssh"],
        "Значение 0 отключает проверку активности, поэтому допустимый диапазон — от 1 до 900 секунд."),
    tfc("ext.shell_tmout", "Автоматическое завершение неактивной сессии оболочки", "Удалённый доступ",
        "/etc/profile.d", "tmout.sh", "^%s*[a-z ]*TMOUT=([0-9]+)" % SP, "^([1-9]|[1-9][0-9]|[1-8][0-9]{2}|900)$",
        "Переменная TMOUT завершает бездействующую сессию оболочки — и локальную, и удалённую.",
        "Создать /etc/profile.d/tmout.sh со строками: readonly TMOUT=900 и export TMOUT",
        ["tmout", "тайм-аут", "бездействие", "оболочка"],
        "Проверяется файл /etc/profile.d/tmout.sh. Если TMOUT задан в другом файле, укажите его в объекте. Значение 0 отключает тайм-аут."),
    tfc("ext.password_minclass", "Сложность пароля: символы разных классов", "Парольная политика",
        "/etc/security", "pwquality.conf", "^%s*minclass%s*=%s*([0-9]+)" % (SP, SP, SP), "^[3-4]$",
        "Пароль только из букв или только из цифр подбирается в разы быстрее, чем пароль из символов нескольких классов.",
        "В /etc/security/pwquality.conf задать minclass = 3 (строчные, прописные, цифры, спецсимволы — не менее трёх классов).",
        ["сложность пароля", "minclass", "pwquality", "классы символов"]),
    {
        "id": "ext.audit_log_perms", "title": "Журнал аудита недоступен прочим пользователям", "category": "Регистрация событий",
        "description": "Проверяется, что у файла /var/log/audit/audit.log сняты права чтения и записи для категории «прочие».",
        "rationale": "Журнал аудита содержит сведения о действиях пользователей; доступ на запись позволяет стереть следы, на чтение — изучить защиту.",
        "keywords": ["журнал аудита", "права доступа", "audit.log", "защита журналов"],
        "platforms": {"family": "unix", "os": LNX},
        "params": [],
        "check": {"type": "unix:file_test", "object": {"path": "/var/log/audit", "filename": "audit.log"},
                  "state": {"oread": {"value": "false", "operation": "equals", "datatype": "boolean"},
                            "owrite": {"value": "false", "operation": "equals", "datatype": "boolean"}},
                  "check": "all", "check_existence": "at_least_one_exists"},
        "remediation": "Выполнить chmod 0600 /var/log/audit/audit.log и chmod 0750 /var/log/audit; в /etc/audit/auditd.conf задать log_group = root.",
    },
    tfc("ext.auditd_keep_logs", "Журналы аудита не удаляются при ротации", "Регистрация событий",
        "/etc/audit", "auditd.conf", "^%s*max_log_file_action%s*=%s*([A-Za-z_]+)" % (SP, SP, SP), "^[Kk][Ee][Ee][Pp]_[Ll][Oo][Gg][Ss]$",
        "При действии ROTATE старые журналы удаляются после заданного числа файлов; KEEP_LOGS сохраняет их для разбора инцидентов.",
        "В /etc/audit/auditd.conf задать max_log_file_action = keep_logs и обеспечить архивирование журналов.",
        ["хранение журналов", "auditd.conf", "max_log_file_action", "ротация"],
        "При keep_logs журналы накапливаются — нужен регламент их архивирования и контроль свободного места."),

    # ------------------------------------------- Windows: NTLM, автовход, диапазоны
    reg("ext.win_ntlmv2", "Только NTLMv2: LM и NTLMv1 запрещены", "Сетевые службы",
        "SYSTEM\\CurrentControlSet\\Control\\Lsa", "LmCompatibilityLevel", "5",
        "LM и NTLMv1 позволяют перехватить и подобрать хеш пароля; ФСТЭК относит их использование к типовым ошибкам конфигурации.",
        "Задать политику «Сетевая безопасность: уровень проверки подлинности LAN Manager» = «Отправлять только NTLMv2-ответ. Отказывать LM и NTLM».",
        ["ntlm", "ntlmv1", "ntlmv2", "lan manager", "lmcompatibilitylevel"], op="greater than or equal"),
    {
        "id": "ext.win_autologon", "title": "Автоматический вход в систему отключён", "category": "Управление доступом",
        "description": "Проверяется, что параметр AutoAdminLogon не включает автоматический вход.",
        "rationale": "При автоматическом входе пароль хранится в реестре, а сеанс открывается без участия пользователя.",
        "keywords": ["autoadminlogon", "автовход", "автоматический вход"],
        "platforms": {"family": "windows", "os": WIN},
        "params": [],
        "check": {"type": "windows:registry_test",
                  "object": {"hive": "HKEY_LOCAL_MACHINE",
                             "key": "SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Winlogon", "name": "AutoAdminLogon"},
                  "state": {"value": {"value": "0", "operation": "equals", "datatype": "string"}},
                  # Нет параметра — автоматический вход не настроен, требование выполнено.
                  "check": "all", "check_existence": "any_exist"},
        "remediation": "Задать AutoAdminLogon = 0 и удалить параметр DefaultPassword в ключе Winlogon.",
    },
    {
        "id": "ext.win_lockout", "title": "Блокировка учётной записи после неудачных попыток входа (Windows)",
        "category": "Парольная политика",
        "description": "Проверяется, что порог блокировки учётной записи задан и не превышает допустимого.",
        "rationale": "Блокировка после нескольких неудачных попыток делает подбор пароля практически невозможным.",
        "keywords": ["блокировка", "lockout", "неудачные попытки входа"],
        "platforms": {"family": "windows", "os": WIN},
        "params": [{"name": "value", "title": "Наибольший допустимый порог", "default": "5", "datatype": "int"}],
        # Диапазон от 1 до value: значение 0 означает «блокировка отключена».
        "checks": [
            {"type": "windows:lockoutpolicy_test", "object": {},
             "state": {"lockout_threshold": {"value": "{{value}}", "operation": "less than or equal", "datatype": "int"}},
             "check": "all", "check_existence": "at_least_one_exists"},
            {"type": "windows:lockoutpolicy_test", "object": {},
             "state": {"lockout_threshold": {"value": "0", "operation": "greater than", "datatype": "int"}},
             "check": "all", "check_existence": "at_least_one_exists"},
        ],
        "remediation": "Задать политику «Пороговое значение блокировки» от 1 до 5 неудачных попыток.",
    },
    {
        "id": "ext.win_inactivity", "title": "Блокировка сеанса при бездействии (Windows)", "category": "Управление доступом",
        "description": "Проверяется, что сеанс блокируется после заданного времени бездействия.",
        "rationale": "Оставленный открытым сеанс позволяет воспользоваться им любому, кто окажется за компьютером.",
        "keywords": ["бездействие", "блокировка сеанса", "inactivity"],
        "platforms": {"family": "windows", "os": WIN},
        "params": [{"name": "value", "title": "Наибольшее время бездействия, секунд", "default": "900", "datatype": "int"}],
        # Диапазон от 1 до value секунд: 0 означает «блокировка отключена».
        "checks": [
            {"type": "windows:registry_test",
             "object": {"hive": "HKEY_LOCAL_MACHINE", "key": "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
                        "name": "InactivityTimeoutSecs"},
             "state": {"value": {"value": "{{value}}", "operation": "less than or equal", "datatype": "int"}},
             "check": "all", "check_existence": "at_least_one_exists"},
            {"type": "windows:registry_test",
             "object": {"hive": "HKEY_LOCAL_MACHINE", "key": "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
                        "name": "InactivityTimeoutSecs"},
             "state": {"value": {"value": "0", "operation": "greater than", "datatype": "int"}},
             "check": "all", "check_existence": "at_least_one_exists"},
        ],
        "remediation": "Задать политику «Интерактивный вход в систему: предел простоя компьютера» не более 900 секунд.",
    },

    # ------------------------- организационные меры по новым группам приказа №117
    manual("ext.org_virtualization", "Защита среды виртуализации",
           "Защита гипервизора, виртуальных машин и средств управления средой виртуализации.",
           "Требование относится к инфраструктуре виртуализации, а не к настройкам отдельного узла.",
           ["виртуализация", "гипервизор"]),
    manual("ext.org_containers", "Защита контейнерных сред",
           "Защита сред выполнения контейнеров, образов и средств оркестрации.",
           "Проверяется средствами защиты контейнерной инфраструктуры, а не OVAL-проверками узла.",
           ["контейнеры", "оркестрация"]),
    manual("ext.org_email", "Защита сервисов электронной почты",
           "Фильтрация почтового трафика, защита от фишинга и вредоносных вложений.",
           "Требование относится к почтовой инфраструктуре организации.",
           ["электронная почта", "фишинг"]),
    manual("ext.org_web_api", "Защита веб-технологий и программных интерфейсов",
           "Защита веб-приложений и программных интерфейсов (API), включая межсетевые экраны уровня приложений.",
           "Требование относится к прикладным сервисам и их окружению.",
           ["веб-приложения", "api"]),
    manual("ext.org_mobile", "Защита мобильных устройств",
           "Управление мобильными устройствами и контроль их доступа к информационным ресурсам.",
           "Требование реализуется средствами управления мобильными устройствами.",
           ["мобильные устройства", "mdm"]),
    manual("ext.org_wireless", "Защита беспроводного доступа",
           "Контроль точек беспроводного доступа и защита беспроводных соединений.",
           "Требование относится к сетевой инфраструктуре.",
           ["wi-fi", "беспроводной доступ"]),
    manual("ext.org_ddos", "Защита от атак «отказ в обслуживании»",
           "Защита сервисов от атак на доступность.",
           "Требование реализуется на уровне сетевого периметра и провайдера.",
           ["ddos", "отказ в обслуживании"]),
    manual("ext.org_monitoring", "Мониторинг информационной безопасности",
           "Сбор, анализ событий безопасности и реагирование на инциденты.",
           "Требование относится к процессам мониторинга; техническая часть — сбор журналов — проверяется отдельно.",
           ["мониторинг", "инциденты", "siem"]),
    manual("ext.org_antivirus", "Антивирусная защита",
           "Применение средств антивирусной защиты на узлах и регулярное обновление баз.",
           "Наличие и работа средства антивирусной защиты проверяются средствами управления этим средством.",
           ["антивирус", "вредоносный код"]),
    manual("ext.org_ids", "Обнаружение и предотвращение вторжений",
           "Применение средств обнаружения и предотвращения вторжений на сетевом уровне.",
           "Требование реализуется сетевыми средствами защиты, а не настройками отдельного узла.",
           ["обнаружение вторжений", "сов"]),
    manual("ext.org_backup", "Резервное копирование",
           "Регулярное резервное копирование информации и конфигураций, проверка восстановления из резервных копий.",
           "Требование относится к процессу резервного копирования: подтверждается регламентом, журналами заданий и тестами восстановления.",
           ["резервное копирование", "восстановление"]),
    manual("ext.org_vuln_mgmt", "Управление уязвимостями и обновлениями",
           "Регулярное выявление уязвимостей, оценка и своевременная установка обновлений безопасности.",
           "Требование относится к процессу управления уязвимостями; его выполнение показывают средства сканирования и управления обновлениями, а не настройки отдельного узла.",
           ["уязвимости", "обновления безопасности", "патчи"]),
    manual("ext.org_software_restriction", "Ограничение программной среды",
           "Запуск только разрешённого программного обеспечения: замкнутая программная среда, контроль запуска приложений.",
           "Реализуется встроенными механизмами ОС (например, ЗПС в Astra Linux SE, AppLocker в Windows) и проверяется их средствами.",
           ["замкнутая программная среда", "applocker", "белый список"]),
]

out = {
    "pack": "extended-2026",
    "title": "Расширенные проверки (Linux и Windows)",
    "description": ("Дополнительные технические проверки к темам базы знаний и организационные "
                    "меры по новым группам мер приказа ФСТЭК №117."),
    "checks": checks,
}
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extended-2026.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
auto = [c for c in checks if not c.get("manual")]
print("записей: %d (технических %d, организационных %d)" % (len(checks), len(auto), len(checks) - len(auto)))
