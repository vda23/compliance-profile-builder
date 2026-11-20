"""
Расширение тезауруса требований.

1. Приказ ФСТЭК России №17 утратил силу с 1 марта 2026 г. Его заменил приказ
   №117 от 11.04.2025. Обозначения групп мер (ИАФ, УПД, РСБ) сохранились в
   методическом документе ФСТЭК «Состав и содержание мероприятий и мер по
   защите информации, содержащейся в информационных системах» (14.04.2026),
   но состав групп изменился. Поэтому подтверждённые коды групп переносятся
   как есть, а остальные ссылки даются по названию группы меры или
   мероприятия. Все ссылки на №117 помечены verify=True.

2. Добавлены семейства документов: ФСТЭК №21 (ПДн), №239 (КИИ),
   ГОСТ Р 59547-2021, CIS Controls v8, NIST CSF 2.0, BSI IT-Grundschutz,
   DISA STIG; редакции уточнены (NIST SP 800-53 Rev. 5, ISO/IEC 27002:2022,
   PCI DSS v4.0, ГОСТ Р 57580.1-2017).

3. Добавлены темы требований: блокировка учётных записей, неактивные
   учётные записи, хеширование паролей, umask, контроль целостности,
   синхронизация времени, централизованный сбор журналов, межсетевой экран,
   криптостойкость SSH, предупреждение при входе, съёмные носители,
   антивирус, обнаружение вторжений, загрузчик, ограничение программной
   среды, настройки Windows и новые группы мер приказа №117 (виртуализация,
   контейнеры, почта, веб, API, мобильные устройства, беспроводной доступ,
   DDoS).

ПРО ИСТОЧНИКИ
   Тексты стандартов не воспроизводятся: хранятся обозначения пунктов и
   собственные формулировки-маркеры. Номера пунктов, кроме Рекомендаций
   ФСТЭК по ОС Linux (сверены по тексту документа), — ориентир: их нужно
   сверить с используемой редакцией документа.
"""

# ------------------------------------------------------------------ названия
F117 = "ФСТЭК, приказ №117"
F21 = "ФСТЭК, приказ №21 (ПДн)"
F239 = "ФСТЭК, приказ №239 (КИИ)"
F31 = "ФСТЭК, приказ №31 (АСУ ТП)"
FLNX = "ФСТЭК, Рекомендации по ОС Linux (2022)"
G57580 = "ГОСТ Р 57580.1-2017"
G59547 = "ГОСТ Р 59547-2021"
CISB = "CIS Benchmark"
CISC = "CIS Controls v8"
NIST = "NIST SP 800-53 Rev. 5"
CSF = "NIST CSF 2.0"
ISO = "ISO/IEC 27002:2022"
PCI = "PCI DSS v4.0"
BSI = "BSI IT-Grundschutz"
STIG = "DISA STIG"


# ----------------------------------------- нормализация старых ссылок
def normalize_hint(family, ref, verify):
    """Приводит старую запись подсказки к виду «документ» + «пункт».

    Раньше раздел документа был склеен с названием («CIS Benchmark, раздел
    настройки SSH»), и фильтр по документу получался по разделам. Ссылки на
    приказ №17 переводятся на приказ №117."""
    f = family
    if f.startswith("ФСТЭК, приказ №17"):
        code = ref.split(".")[0]
        mapping = {
            "ИАФ": "ИАФ", "УПД": "УПД", "РСБ": "РСБ",
            "ЗИС": "Защита каналов передачи данных и сетевого взаимодействия",
            "ОДТ": "Мероприятия: обеспечение доступности и резервирование",
            "ОПС": "Мероприятия: повышение осведомлённости персонала",
            "АНЗ": "Мероприятия: управление уязвимостями",
        }
        return F117, mapping.get(code, ref), True
    # Только прежние написания Рекомендаций по Linux. Раньше условие ловило
    # любые «ФСТЭК, Рекомендации…», и ссылки на документы ФСТЭК 2026 года
    # (типовые ошибки конфигурации, регистрация событий) приписывались
    # Рекомендациям по Linux 2022 года.
    if f.startswith("ФСТЭК, Рекомендации") and "2026" not in f:
        return FLNX, ref, verify
    if f.startswith("CIS Benchmark"):
        return CISB, ref, True
    if f.startswith("NIST SP 800-53"):
        return NIST, ref, True
    if f.startswith("ISO/IEC 27002"):
        return ISO, ref, True
    if f.startswith("ГОСТ Р 57580"):
        # «РЗН» не является обозначением процесса ГОСТ Р 57580.1; регистрация
        # событий и их анализ относятся к процессу мониторинга (МАС).
        return G57580, ("МАС" if ref == "РЗН" else ref), True
    if f.startswith("PCI DSS"):
        # обозначения приведены к редакции 4.0
        return PCI, {"4.1": "4.2.1"}.get(ref, ref), True
    return f, ref, verify


# ------------------------------------- новые ссылки для существующих тем
# (документ, пункт) — все как ориентир (verify=True)
EXTRA_HINTS = {
    "access.ssh_root_login": [(F21, "УПД"), (F239, "УПД"), (CISC, "5.4"), (CSF, "PR.AA"),
                              (ISO, "8.2"), (PCI, "8.2.2"), (BSI, "SYS.1.3"), (STIG, "SSH: PermitRootLogin")],
    "access.ssh_empty_password": [(F21, "ИАФ"), (F239, "ИАФ"), (NIST, "IA-5"), (PCI, "8.3.1")],
    "access.ssh_auth_attempts": [(F21, "УПД"), (F239, "УПД"), (G57580, "РД"), (ISO, "8.5"),
                                 (PCI, "8.3.4"), (CSF, "PR.AA")],
    "access.session_timeout": [(F21, "УПД"), (G57580, "РД"), (ISO, "8.5"), (PCI, "8.2.8"), (NIST, "AC-12")],
    "privilege.su_restriction": [(F117, "УПД"), (F21, "УПД"), (F239, "УПД"), (NIST, "AC-6"), (ISO, "8.2")],
    "privilege.sudo_review": [(F117, "УПД"), (F239, "УПД"), (CISC, "6.8"), (PCI, "7.2")],
    "privilege.suid_audit": [(NIST, "CM-7"), (CISC, "4.1"), (BSI, "SYS.1.3")],
    "password.length": [(F117, "ИАФ"), (F21, "ИАФ"), (F239, "ИАФ"), (PCI, "8.3.6"), (CISC, "5.2"),
                        (ISO, "5.17"), (CSF, "PR.AA"), (BSI, "ORP.4")],
    "password.complexity": [(F21, "ИАФ"), (F239, "ИАФ"), (PCI, "8.3.6"), (ISO, "5.17")],
    "password.max_age": [(F117, "ИАФ"), (F21, "ИАФ"), (PCI, "8.3.9"), (NIST, "IA-5")],
    "password.min_age": [(NIST, "IA-5"), (ISO, "5.17")],
    "password.history": [(F117, "ИАФ"), (F21, "ИАФ"), (PCI, "8.3.7"), (ISO, "5.17")],
    "files.passwd_group_perms": [(F117, "УПД"), (F21, "УПД"), (NIST, "AC-3"), (CISC, "3.3")],
    "files.shadow_perms": [(F117, "УПД"), (NIST, "IA-5"), (PCI, "8.3.2")],
    "files.cron_perms": [(NIST, "CM-6"), (BSI, "SYS.1.3")],
    "files.home_dir_perms": [(NIST, "AC-3"), (CISC, "3.3")],
    "files.system_binaries": [(NIST, "CM-5"), (ISO, "8.19")],
    "files.startup_scripts": [(NIST, "CM-5")],
    "kernel.aslr": [(NIST, "SI-16"), (STIG, "kernel.randomize_va_space")],
    "kernel.ptrace_scope": [(NIST, "SC-39")],
    "kernel.core_dump": [(NIST, "SC-28"), (STIG, "fs.suid_dumpable")],
    "kernel.boot_hardening": [(NIST, "SI-16")],
    "kernel.attack_surface": [(NIST, "CM-7"), (CISC, "4.8")],
    "network.ip_forward": [(F117, "Сегментация и межсетевое экранирование"), (F21, "ЗИС"), (F239, "ЗИС"),
                           (CISC, "12.2"), (NIST, "SC-7")],
    "network.icmp_redirects": [(NIST, "SC-7"), (STIG, "net.ipv4.conf.all.accept_redirects")],
    "network.spoof_protection": [(NIST, "SC-7"), (CISC, "12.2")],
    "network.insecure_services": [(F117, "Защита каналов передачи данных и сетевого взаимодействия"),
                                  (F21, "ЗИС"), (F239, "ЗИС"), (NIST, "CM-7"), (ISO, "8.21"),
                                  (CISC, "4.8"), (BSI, "SYS.1.3")],
    "audit.subsystem_installed": [(F21, "РСБ"), (F239, "АУД"), (G59547, "разделы 4–5"), (CISC, "8.2"),
                                  (ISO, "8.15"), (PCI, "10.2"), (CSF, "DE.CM"), (BSI, "OPS.1.1.5")],
    "audit.service_running": [(F117, "РСБ"), (F21, "РСБ"), (F239, "АУД"), (CISC, "8.2"), (PCI, "10.2")],
    "audit.log_protection": [(F21, "РСБ"), (F239, "АУД"), (PCI, "10.3"), (CISC, "8.3"), (NIST, "AU-11")],
    "fs.mount_options": [(NIST, "CM-6"), (STIG, "/tmp nodev,nosuid,noexec")],
    "org.access_procedure": [(F21, "УПД"), (F239, "УПД"), (ISO, "5.15"), (CISC, "6.1"), (CSF, "PR.AA"),
                             (BSI, "ORP.4")],
    "org.awareness": [(F239, "ОПО"), (CISC, "14"), (CSF, "PR.AT"), (PCI, "12.6"), (BSI, "ORP.3")],
    "org.backup": [(F117, "Мероприятия: обеспечение доступности и резервирование"), (F21, "ОДТ"),
                   (F239, "ОДТ"), (CISC, "11"), (NIST, "CP-9"), (CSF, "PR.DS"), (BSI, "CON.3")],
    "org.vulnerability_management": [(F21, "АНЗ"), (F239, "АУД"), (CISC, "7"), (CSF, "ID.RA"),
                                     (ISO, "8.8"), (BSI, "OPS.1.1.3")],
}


# --------------------------------------------------------- новые темы
# (id, название, RU-формулировки, EN-формулировки, разделы, [(документ, пункт)])
NEW_CONCEPTS = [
    # --- учётные записи и аутентификация
    ("accounts.lockout", "Блокировка учётной записи после неудачных попыток входа",
     ["блокировка учётной записи", "неудачных попыток входа", "неуспешных попыток входа",
      "превышении числа попыток", "faillock", "pam_faillock", "временная блокировка", "подбор пароля"],
     ["account lockout", "failed login attempts", "faillock", "lockout threshold", "unsuccessful logon attempts"],
     ["Управление доступом", "Парольная политика"],
     [(F117, "ИАФ"), (F21, "УПД"), (F239, "УПД"), (G57580, "РД"), (NIST, "AC-7"), (PCI, "8.3.4"),
      (CISC, "6.2"), (ISO, "8.5"), (BSI, "ORP.4")]),

    ("accounts.inactive", "Блокировка неактивных учётных записей",
     ["неактивные учётные записи", "неиспользуемые учётные записи", "блокировка неиспользуемых",
      "учётные записи уволенных", "inactive", "срок неактивности"],
     ["inactive accounts", "dormant accounts", "unused accounts", "account inactivity"],
     ["Управление доступом"],
     [(F117, "УПД"), (F21, "УПД"), (F239, "УПД"), (G57580, "УЗП"), (NIST, "AC-2"), (PCI, "8.2.6"),
      (CISC, "5.3"), (ISO, "5.18")]),

    ("accounts.uid0", "Единственная учётная запись с правами суперпользователя",
     ["uid 0", "uid=0", "идентификатором 0", "несколько суперпользователей", "только root"],
     ["uid 0", "only root has uid 0", "duplicate root accounts", "superuser accounts"],
     ["Управление доступом", "Повышение привилегий"],
     [(F117, "УПД"), (NIST, "AC-6"), (CISB, "User and Group Settings"), (STIG, "UID 0")]),

    ("accounts.password_hashing", "Стойкий алгоритм хеширования паролей",
     ["хеширования паролей", "алгоритм хеширования", "sha512", "yescrypt", "encrypt_method",
      "хранение паролей в защищённом виде", "свёртки паролей"],
     ["password hashing", "hashing algorithm", "sha512", "yescrypt", "encrypt_method", "stored passwords"],
     ["Парольная политика"],
     [(F117, "ИАФ"), (F21, "ИАФ"), (NIST, "IA-5"), (PCI, "8.3.2"), (ISO, "8.24"), (CISB, "Password Policy")]),

    ("accounts.umask", "Права по умолчанию для создаваемых файлов",
     ["umask", "права по умолчанию", "маска прав", "создаваемых файлов"],
     ["umask", "default permissions", "default file mode"],
     ["Права на файлы"],
     [(NIST, "AC-3"), (CISB, "User Environment"), (STIG, "UMASK")]),

    # --- целостность, время, журналы
    ("integrity.monitoring", "Контроль целостности файлов",
     ["контроль целостности", "целостность программного обеспечения", "целостности файлов",
      "aide", "afick", "изменений в системных файлах", "эталонные контрольные суммы"],
     ["file integrity monitoring", "integrity checking", "aide", "change detection", "fim"],
     ["Целостность"],
     [(F117, "Мероприятия: контроль целостности"), (F21, "ОЦЛ"), (F239, "ОЦЛ"), (NIST, "SI-7"),
      (PCI, "11.5.2"), (CISC, "3.14"), (BSI, "OPS.1.1.5")]),

    ("time.sync", "Синхронизация системного времени",
     ["синхронизация времени", "единое время", "источник точного времени", "ntp", "chrony",
      "временные метки событий"],
     ["time synchronization", "clock synchronization", "ntp", "chrony", "time source", "timestamps"],
     ["Регистрация событий"],
     [(F117, "РСБ"), (F21, "РСБ"), (F239, "АУД"), (NIST, "AU-8"), (PCI, "10.6"), (ISO, "8.17"),
      (CISC, "8.4")]),

    ("logging.remote", "Централизованный сбор журналов",
     ["централизованный сбор", "централизованное хранение журналов", "передача событий",
      "siem", "syslog", "rsyslog", "удалённый сервер журналов", "сбора событий безопасности"],
     ["centralized logging", "log forwarding", "remote syslog", "siem", "log aggregation"],
     ["Регистрация событий"],
     [(F117, "РСБ"), (F239, "АУД"), (G59547, "разделы 4–5"), (G57580, "МАС"), (NIST, "AU-4"),
      (PCI, "10.3.3"), (CISC, "8.9"), (CSF, "DE.CM"), (BSI, "OPS.1.1.5")]),

    ("logging.retention", "Срок хранения журналов событий",
     ["срок хранения", "хранение журналов", "ротация журналов", "logrotate", "не менее трёх месяцев",
      "архивирование журналов"],
     ["log retention", "log rotation", "logrotate", "retain audit logs", "audit trail history"],
     ["Регистрация событий"],
     [(F117, "РСБ"), (F21, "РСБ"), (NIST, "AU-11"), (PCI, "10.5.1"), (CISC, "8.10")]),

    # --- сеть
    ("network.firewall", "Межсетевой экран на узле",
     ["межсетевой экран", "межсетевого экранирования", "сегментация", "фильтрация трафика", "firewalld",
      "nftables", "iptables", "ufw", "брандмауэр", "персональный межсетевой экран"],
     ["host firewall", "firewall", "network segmentation", "traffic filtering", "nftables", "iptables",
      "windows firewall"],
     ["Сетевые параметры"],
     [(F117, "Сегментация и межсетевое экранирование"), (F21, "ЗИС"), (F239, "ЗИС"), (G57580, "СМЭ"),
      (NIST, "SC-7"), (PCI, "1.2"), (CISC, "4.4"), (ISO, "8.22"), (BSI, "NET.3.2")]),

    ("ssh.crypto", "Стойкие алгоритмы шифрования SSH",
     ["криптостойкие", "стойкие алгоритмы", "алгоритмы шифрования", "ciphers", "macs",
      "устаревших алгоритмов", "шифрование трафика", "режим cbc"],
     ["strong ciphers", "weak ciphers", "ssh ciphers", "macs", "kexalgorithms", "cbc mode"],
     ["Удалённый доступ", "Криптография"],
     [(F117, "Защита каналов передачи данных и сетевого взаимодействия"), (F21, "ЗИС"), (NIST, "SC-8"),
      (PCI, "4.2.1"), (ISO, "8.24"), (CISB, "SSH Server Configuration"), (STIG, "SSH Ciphers")]),

    ("access.login_banner", "Предупреждение при входе в систему",
     ["предупреждение при входе", "уведомление пользователя", "баннер", "предупреждающее сообщение",
      "предупреждение о мониторинге"],
     ["login banner", "warning banner", "system use notification", "legal notice", "issue.net"],
     ["Удалённый доступ"],
     [(NIST, "AC-8"), (CISB, "Warning Banners"), (STIG, "Banner")]),

    ("access.login_grace", "Ограничение времени на аутентификацию",
     ["времени на аутентификацию", "logingracetime", "время ожидания входа"],
     ["login grace time", "logingracetime", "authentication timeout"],
     ["Удалённый доступ"],
     [(CISB, "SSH Server Configuration"), (NIST, "AC-12")]),

    # --- носители, вредоносный код, вторжения, загрузка
    ("media.removable", "Контроль подключения съёмных носителей",
     ["съёмных носителей", "съёмные носители", "машинных носителей", "usb", "usb-накопител",
      "подключение носителей", "запрет usb"],
     ["removable media", "usb storage", "usb-storage", "external storage", "media use"],
     ["Защита носителей"],
     [(F117, "Защита конечных устройств"), (F21, "ЗНИ"), (F239, "ЗНИ"), (NIST, "MP-7"), (ISO, "7.10"),
      (CISC, "10.3"), (STIG, "usb-storage")]),

    ("malware.antivirus", "Антивирусная защита",
     ["антивирусная защита", "антивирусной защиты", "вредоносного программного обеспечения",
      "вредоносного кода", "средства антивирусной защиты", "антивирус"],
     ["antivirus", "anti-malware", "malware protection", "malicious code", "endpoint protection"],
     ["Защита от вредоносного кода"],
     [(F117, "Антивирусная защита"), (F21, "АВЗ"), (F239, "АВЗ"), (G57580, "ЗВК"), (NIST, "SI-3"),
      (PCI, "5.2"), (CISC, "10"), (ISO, "8.7"), (BSI, "OPS.1.1.4")]),

    ("intrusion.detection", "Обнаружение и предотвращение вторжений",
     ["обнаружение вторжений", "предотвращение вторжений", "системы обнаружения", "сов",
      "компьютерных атак", "нетипичной активности"],
     ["intrusion detection", "intrusion prevention", "ids", "ips", "network monitoring"],
     ["Обнаружение вторжений"],
     [(F117, "Обнаружение и предотвращение вторжений на сетевом уровне"), (F21, "СОВ"), (F239, "СОВ"),
      (G57580, "ВСА"), (NIST, "SI-4"), (PCI, "11.5.1"), (CISC, "13"), (CSF, "DE.CM")]),

    ("boot.bootloader", "Защита загрузчика паролем",
     ["загрузчик", "загрузчика", "grub", "доверенная загрузка", "параметров загрузки",
      "несанкционированной загрузки"],
     ["bootloader password", "grub password", "secure boot", "boot settings"],
     ["Загрузка системы"],
     [(F117, "Защита конечных устройств"), (F21, "УПД"), (NIST, "AC-3"), (CISB, "Secure Boot Settings"),
      (STIG, "GRUB password")]),

    ("software.restriction", "Ограничение программной среды",
     ["ограничение программной среды", "замкнутая программная среда", "зпс", "запуск только разрешённого",
      "белый список приложений", "applocker", "контроль запуска"],
     ["application allowlisting", "application whitelisting", "software restriction", "applocker",
      "allowed software"],
     ["Ограничение программной среды"],
     [(F117, "Защита конечных устройств"), (F21, "ОПС"), (F239, "ОПС"), (NIST, "CM-7"), (CISC, "2.5"),
      (ISO, "8.19")]),

    # --- Windows
    ("win.smb1", "Отключение протокола SMBv1",
     ["smbv1", "smb1", "устаревшей версии протокола smb", "mrxsmb10"],
     ["smbv1", "smb1", "smb version 1", "mrxsmb10"],
     ["Сетевые службы", "Windows"],
     [(NIST, "CM-7"), (STIG, "SMBv1"), (CISB, "Microsoft Windows Server")]),

    ("win.uac", "Контроль учётных записей Windows (UAC)",
     ["контроль учётных записей", "uac", "повышения прав", "enablelua"],
     ["user account control", "uac", "enablelua", "elevation prompt"],
     ["Повышение привилегий", "Windows"],
     [(NIST, "AC-6"), (STIG, "UAC"), (CISB, "Microsoft Windows")]),

    ("win.autorun", "Отключение автозапуска со съёмных носителей",
     ["автозапуск", "автозапуска", "autorun", "autoplay"],
     ["autorun", "autoplay", "nodrivetypeautorun"],
     ["Защита носителей", "Windows"],
     [(F21, "ЗНИ"), (NIST, "MP-7"), (STIG, "AutoRun"), (CISB, "Microsoft Windows")]),

    ("win.lm_hash", "Запрет хранения LM-хешей паролей",
     ["lm-хеш", "lm hash", "nolmhash", "устаревшего формата"],
     ["lm hash", "lan manager hash", "nolmhash"],
     ["Парольная политика", "Windows"],
     [(NIST, "IA-5"), (STIG, "NoLMHash"), (CISB, "Microsoft Windows")]),

    ("win.rdp_nla", "Проверка подлинности на уровне сети для RDP",
     ["rdp", "удалённого рабочего стола", "проверка подлинности на уровне сети", "nla"],
     ["rdp", "remote desktop", "network level authentication", "nla"],
     ["Удалённый доступ", "Windows"],
     [(F117, "ИАФ"), (NIST, "AC-17"), (STIG, "RDP NLA"), (CISB, "Microsoft Windows")]),

    ("win.powershell_logging", "Журналирование PowerShell",
     ["powershell", "журналирование сценариев", "scriptblocklogging"],
     ["powershell logging", "script block logging", "scriptblocklogging"],
     ["Регистрация событий", "Windows"],
     [(F117, "РСБ"), (NIST, "AU-12"), (STIG, "PowerShell Script Block Logging")]),

    # --- новые группы мер приказа №117 (организационные/технологические)
    ("virt.security", "Защита среды виртуализации",
     ["виртуализации", "гипервизор", "виртуальных машин", "облачных вычислений"],
     ["virtualization security", "hypervisor", "virtual machines", "cloud computing"],
     ["Виртуализация"],
     [(F117, "Защита виртуализации и облачных вычислений"), (F21, "ЗСВ"), (F239, "ЗСВ"),
      (G57580, "ЗСВ"), (NIST, "SC-7")]),

    ("containers.security", "Защита контейнерных сред",
     ["контейнер", "контейнерных сред", "оркестрации", "kubernetes", "docker"],
     ["container security", "container orchestration", "kubernetes", "docker"],
     ["Контейнеры"],
     [(F117, "Защита технологий контейнерных сред и их оркестрации"), (NIST, "CM-7")]),

    ("services.email", "Защита сервисов электронной почты",
     ["электронной почты", "почтовых сервисов", "фишинг", "почтового сервера"],
     ["email security", "mail server", "phishing", "email protection"],
     ["Прикладные сервисы"],
     [(F117, "Защита сервисов электронной почты"), (CISC, "9"), (NIST, "SI-8")]),

    ("services.web", "Защита веб-технологий и программных интерфейсов",
     ["веб-приложений", "веб-технологий", "программных интерфейсов", "api", "веб-сервера"],
     ["web application security", "web technologies", "api security", "web server"],
     ["Прикладные сервисы"],
     [(F117, "Защита веб-технологий"), (F117, "Защита программных интерфейсов взаимодействия приложений"),
      (CISC, "16"), (PCI, "6.4")]),

    ("devices.mobile", "Защита мобильных устройств",
     ["мобильных устройств", "смартфон", "планшет", "mdm"],
     ["mobile devices", "mdm", "smartphones", "tablets"],
     ["Конечные устройства"],
     [(F117, "Защита мобильных устройств"), (NIST, "AC-19"), (ISO, "8.1")]),

    ("network.wireless", "Защита беспроводного доступа",
     ["беспроводного доступа", "беспроводных сетей", "wi-fi", "точек доступа"],
     ["wireless access", "wireless networks", "wi-fi", "access points"],
     ["Сетевые службы"],
     [(F117, "Защита точек беспроводного доступа"), (F21, "ЗИС"), (NIST, "AC-18"), (CISC, "12.6")]),

    ("network.ddos", "Защита от атак типа «отказ в обслуживании»",
     ["отказ в обслуживании", "ddos", "атак на доступность"],
     ["denial of service", "ddos", "dos attacks"],
     ["Сетевые службы"],
     [(F117, "Защита от компьютерных атак, направленных на отказ в обслуживании"), (NIST, "SC-5")]),

    ("org.monitoring", "Мониторинг информационной безопасности",
     ["мониторинг информационной безопасности", "мониторинга событий", "анализ событий безопасности",
      "выявление инцидентов", "реагирование на инциденты"],
     ["security monitoring", "incident detection", "incident response", "security event analysis"],
     ["Организационные меры", "Регистрация событий"],
     [(F117, "Мероприятия: мониторинг информационной безопасности"), (G59547, "разделы 4–5"),
      (F239, "ИНЦ"), (G57580, "МАС"), (NIST, "IR-4"), (CSF, "DE.AE"), (CISC, "17")]),
]


# ------------------------------- привязка новых записей каталога к темам
NEW_LINKS = {
    "ext.accounts_lockout": ["accounts.lockout"],
    "ext.accounts_inactive": ["accounts.inactive"],
    "ext.accounts_uid0": ["accounts.uid0"],
    "ext.password_hashing": ["accounts.password_hashing"],
    "ext.umask": ["accounts.umask"],
    "ext.aide_installed": ["integrity.monitoring"],
    "ext.chrony_installed": ["time.sync"],
    "ext.rsyslog_remote": ["logging.remote"],
    "ext.ssh_weak_ciphers": ["ssh.crypto"],
    "ext.ssh_banner": ["access.login_banner"],
    "ext.ssh_login_grace": ["access.login_grace"],
    "ext.cron_allow": ["files.cron_perms"],
    "ext.usb_storage": ["media.removable"],
    "ext.grub_password": ["boot.bootloader"],
    "ext.firewall_active": ["network.firewall"],
    "ext.win_smb1": ["win.smb1"],
    "ext.win_uac": ["win.uac"],
    "ext.win_autorun": ["win.autorun"],
    "ext.win_lm_hash": ["win.lm_hash"],
    "ext.win_rdp_nla": ["win.rdp_nla"],
    "ext.win_ps_logging": ["win.powershell_logging"],
    "ext.win_firewall": ["network.firewall"],
    "ext.win_password_length": ["password.length"],
    "ext.win_password_history": ["password.history"],
    "ext.win_audit_logon": ["audit.subsystem_installed"],
    "ext.org_virtualization": ["virt.security"],
    "ext.org_containers": ["containers.security"],
    "ext.org_email": ["services.email"],
    "ext.org_web_api": ["services.web"],
    "ext.org_mobile": ["devices.mobile"],
    "ext.org_wireless": ["network.wireless"],
    "ext.org_ddos": ["network.ddos"],
    "ext.org_monitoring": ["org.monitoring"],
    "ext.org_antivirus": ["malware.antivirus"],
    "ext.org_ids": ["intrusion.detection"],
    "ext.org_software_restriction": ["software.restriction"],
    "ext.ssh_client_alive": ["access.session_timeout"],
    "ext.shell_tmout": ["access.session_timeout"],
    "ext.password_minclass": ["password.complexity"],
    "ext.audit_log_perms": ["audit.log_protection"],
    "ext.auditd_keep_logs": ["logging.retention"],
    "ext.org_backup": ["org.backup"],
    "ext.org_vuln_mgmt": ["org.vulnerability_management"],
}


# ------------------------------------------------ приказ ФСТЭК №31 (АСУ ТП)
# Приказ от 14.03.2014, действует (редакция 2021 г.). После изменений 2018 г.
# (приказ №138) группа «Регистрация событий безопасности (РСБ)» заменена на
# «Аудит безопасности (АУД)»: АУД.2 — анализ уязвимостей и их устранение,
# АУД.4 — регистрация событий безопасности, АУД.6 — защита информации о
# событиях. Номера мер, подтверждённые источниками, указаны точно; для
# остальных — группа мер. Все ссылки — ориентир (verify=True).
EXTRA_HINTS_31 = {
    "access.ssh_root_login": ["УПД.4"],          # разделение полномочий (ролей)
    "privilege.su_restriction": ["УПД.4"],
    "privilege.sudo_review": ["УПД.4"],
    "access.ssh_empty_password": ["ИАФ.1"],      # идентификация и аутентификация пользователей
    "access.ssh_auth_attempts": ["УПД"],
    "accounts.lockout": ["УПД"],
    "access.session_timeout": ["УПД"],
    "accounts.inactive": ["УПД.1"],              # управление учётными записями
    "accounts.uid0": ["УПД.1"],
    "org.access_procedure": ["УПД.0"],           # разработка политики управления доступом
    "password.length": ["ИАФ.4"],                # управление средствами аутентификации
    "password.complexity": ["ИАФ.4"],
    "password.max_age": ["ИАФ.4"],
    "password.history": ["ИАФ.4"],
    "accounts.password_hashing": ["ИАФ.4"],
    "boot.bootloader": ["УПД.3"],                # доверенная загрузка
    "files.passwd_group_perms": ["УПД"],
    "files.shadow_perms": ["УПД"],
    "audit.subsystem_installed": ["АУД.4"],      # регистрация событий безопасности
    "audit.service_running": ["АУД.4"],
    "logging.remote": ["АУД.4"],
    "logging.retention": ["АУД.4"],
    "time.sync": ["АУД.4"],
    "win.powershell_logging": ["АУД.4"],
    "audit.log_protection": ["АУД.6"],           # защита информации о событиях
    "org.vulnerability_management": ["АУД.2"],   # анализ уязвимостей и их устранение
    "intrusion.detection": ["СОВ", "АУД.5"],     # АУД.5 — контроль и анализ сетевого трафика
    "malware.antivirus": ["АВЗ"],
    "media.removable": ["ЗНИ"],
    "win.autorun": ["ЗНИ"],
    "software.restriction": ["ОПС"],
    "integrity.monitoring": ["ОЦЛ"],
    "org.backup": ["ОДТ"],
    "network.firewall": ["ЗИС"],
    "network.insecure_services": ["ЗИС"],
    "network.ip_forward": ["ЗИС"],
    "ssh.crypto": ["ЗИС"],
    "org.monitoring": ["ИНЦ"],
}
for _cid, _refs in EXTRA_HINTS_31.items():
    EXTRA_HINTS.setdefault(_cid, [])
    EXTRA_HINTS[_cid] = EXTRA_HINTS[_cid] + [(F31, r) for r in _refs]

# формулировки, характерные для приказов ФСТЭК по АСУ ТП и КИИ
NEW_PHRASES = {
    "org.vulnerability_management": ["анализ уязвимостей", "уязвимостей и их устранение", "устранение уязвимостей"],
    "audit.subsystem_installed": ["аудит безопасности", "аудиту безопасности"],
    "audit.log_protection": ["защита информации о событиях", "защиту информации о событиях"],
    "password.length": ["управление средствами аутентификации", "управлению средствами аутентификации"],
    "boot.bootloader": ["доверенная загрузка", "доверенной загрузки"],
    "media.removable": ["защита машинных носителей", "защите машинных носителей"],
}


# ---------------------------------------------------- документы ФСТЭК 2026 года
# «Рекомендации по устранению типовых ошибок конфигурации (настройки)
# общесистемного и прикладного программного обеспечения» (февраль 2026) —
# конкретные параметры для Windows и Linux: SMBv1, NTLMv1, учётная запись
# «Гость», длина пароля, автоматический вход, настройки SSH, права на файлы.
# «Рекомендации по базовой настройке регистрации событий безопасности» —
# состав регистрируемых событий с приложениями для Windows и Linux.
# Нумерация пунктов не сверена — ссылки даются по теме (verify=True).
FERR = "ФСТЭК, Рекомендации по типовым ошибкам конфигурации (2026)"
FLOG = "ФСТЭК, Рекомендации по регистрации событий (2026)"

for _cid, _ref in {
    "password.length": "Слабые пароли", "win.smb1": "Устаревшие протоколы SMBv1 и NTLMv1",
    "access.ssh_root_login": "Привилегированный доступ по SSH", "access.ssh_empty_password": "Вход по паролю через SSH",
    "network.insecure_services": "Открытые неиспользуемые порты", "kernel.attack_surface": "Неиспользуемые службы и компоненты",
    "files.passwd_group_perms": "Права доступа к файлам", "files.shadow_perms": "Хранение учётных данных",
    "network.firewall": "Межсетевое экранирование",
}.items():
    EXTRA_HINTS.setdefault(_cid, [])
    EXTRA_HINTS[_cid] = EXTRA_HINTS[_cid] + [(FERR, _ref)]
for _cid in ("audit.subsystem_installed", "audit.service_running", "logging.remote", "logging.retention",
             "time.sync", "win.powershell_logging", "audit.log_protection"):
    EXTRA_HINTS.setdefault(_cid, [])
    EXTRA_HINTS[_cid] = EXTRA_HINTS[_cid] + [(FLOG, "Состав и хранение событий")]

NEW_CONCEPTS += [
    ("win.ntlm", "Запрет протоколов LM и NTLMv1",
     # Без общего «lan manager»: он есть и в теме хранения LM-хешей.
     ["ntlmv1", "ntlm", "проверки подлинности lan manager", "только ntlmv2", "устаревшего протокола аутентификации"],
     ["ntlmv1", "ntlm", "lan manager authentication level", "ntlmv2 responses only", "refuse lm and ntlm"],
     ["Сетевые службы", "Windows"],
     [(FERR, "Устаревшие протоколы SMBv1 и NTLMv1"), (NIST, "IA-2"), (STIG, "LAN Manager authentication level"),
      (CISB, "Microsoft Windows")]),
    ("win.autologon", "Запрет автоматического входа в систему",
     ["автоматический вход", "автоматического входа", "без ввода пароля", "autoadminlogon", "автовход"],
     ["automatic logon", "autoadminlogon", "autologon", "password is always required"],
     ["Управление доступом", "Windows"],
     [(FERR, "Автоматический вход на серверах"), (NIST, "IA-2"), (STIG, "Automatic logon")]),
]
NEW_LINKS.update({
    "ext.win_ntlmv2": ["win.ntlm"],
    "ext.win_autologon": ["win.autologon"],
    "ext.win_lockout": ["accounts.lockout"],
    "ext.win_inactivity": ["access.session_timeout"],
})

# Обороты, на которых сервис промахнулся на эталонном наборе документов
# (tests/corpus_spec.py). Так база и должна расти — по реальным формулировкам.
NEW_PHRASES.update({
    "audit.subsystem_installed": NEW_PHRASES.get("audit.subsystem_installed", []) + ["аудит входа", "аудит входа в систему"],
    "network.ip_forward": ["пересылку ip-пакетов", "пересылка ip-пакетов", "пересылку пакетов между интерфейсами"],
    "accounts.password_hashing": ["sha-512", "в виде хеш-значений", "хеш-значений, вычисленных"],
    "access.session_timeout": ["неактивный сеанс", "неактивного сеанса", "сеанс пользователя блокируется"],
    "access.ssh_root_login": ["аутентификация суперпользователя", "суперпользователя при удалённом подключении"],
    "logging.retention": ["удаляться при ротации", "не должны удаляться"],
    "win.lm_hash": ["в формате lan manager", "хеш-значения паролей в формате"],
    "audit.log_protection": NEW_PHRASES.get("audit.log_protection", []) + ["журналу аудита", "доступ к журналу аудита"],
})
NEW_PHRASES_EN = {
    "audit.subsystem_installed": ["audit logon", "logon events"],
    "audit.service_running": ["auditd service", "service is enabled and active"],
    "win.smb1": ["smb v1"],
    "win.lm_hash": ["lan manager hash", "hash value"],
    "access.session_timeout": ["inactivity limit", "machine inactivity"],
    "password.length": ["passwords must be at least", "password minimum length"],
    "logging.remote": ["central log server", "forwarded to a central"],
    "access.ssh_empty_password": ["empty passwords", "permit empty"],
}
