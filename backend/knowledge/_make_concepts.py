"""
Формирует тезаурус требований: слой между текстом нормативного документа и
техническим каталогом проверок.

ЗАЧЕМ ОТДЕЛЬНЫЙ СЛОЙ
    Одно и то же требование в разных документах звучит по-разному:
      ФСТЭК:  «обеспечить отключение входа суперпользователя по протоколу SSH»
      CIS:    «Ensure SSH root login is disabled»
      ISO:    «ограничение привилегированных прав доступа»
    Техническая проверка при этом одна. Если хранить формулировки внутри
    записей каталога, каталог придётся дублировать под каждый документ.
    Поэтому формулировки вынесены в концепты, а каталог привязан к ним.

СТРУКТУРА КОНЦЕПТА
    id          устойчивый ключ, например "access.ssh_root_login"
    title       название темы требования
    ru / en     формулировки-маркеры: слова и обороты, по которым тему
                узнают в тексте документа на русском и английском
    themes      разделы, к которым тема относится
    doc_hints   в каких семействах документов тема встречается и под каким
                обозначением

ВАЖНО ПРО doc_hints
    Тексты стандартов защищены авторским правом, поэтому здесь хранятся
    только ссылки-обозначения и собственные формулировки, а не выдержки из
    документов. Номера пунктов для зарубежных стандартов указаны как
    ориентир и помечены verify=true: нумерация меняется между редакциями,
    перед использованием её нужно сверить со своей копией документа.
"""
import json, os

# (id, название, RU-маркеры, EN-маркеры, темы, подсказки по документам)
CONCEPTS = [
    # ---------------------------------------------------- удалённый доступ
    ("access.ssh_root_login", "Запрет удалённого входа суперпользователя",
     ["вход суперпользователя", "permitrootlogin", "удалённый вход root", "прямой вход root",
      "привилегированная учётная запись", "отключение входа суперпользователя"],
     ["root login", "remote root access", "disable root login", "direct root login", "privileged account"],
     ["Удалённый доступ", "Управление доступом"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.1.2", False),
      ("CIS Benchmark, раздел настройки SSH", "SSH Server Configuration", True),
      ("NIST SP 800-53", "AC-6", True)]),

    ("access.ssh_empty_password", "Запрет аутентификации с пустым паролем",
     ["пустой пароль", "пустыми паролями", "permitemptypasswords", "без пароля"],
     ["empty password", "blank password", "null password"],
     ["Удалённый доступ", "Парольная политика"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.1.1", False),
      ("CIS Benchmark, раздел настройки SSH", "SSH Server Configuration", True)]),

    ("access.ssh_auth_attempts", "Ограничение числа попыток аутентификации",
     ["попыток аутентификации", "maxauthtries", "подбор пароля", "перебор паролей",
      "число неудачных попыток", "блокировка после неудачных",
      "неуспешных попыток", "неудачных попыток входа", "попыток входа",
      "количество неуспешных попыток", "блокировка учётной записи"],
     ["authentication attempts", "maxauthtries", "brute force", "failed login attempts", "lockout threshold"],
     ["Удалённый доступ", "Управление доступом"],
     [("ФСТЭК, приказ №17", "ИАФ", True),
      ("CIS Benchmark, раздел настройки SSH", "SSH Server Configuration", True),
      ("NIST SP 800-53", "AC-7", True)]),

    ("access.session_timeout", "Ограничение времени неактивной сессии",
     ["время неактивности", "таймаут сессии", "clientaliveinterval", "завершение сеанса",
      "блокировка сеанса", "бездействие"],
     ["session timeout", "idle timeout", "clientaliveinterval", "session termination", "inactivity"],
     ["Удалённый доступ", "Управление доступом"],
     [("ФСТЭК, приказ №17", "УПД", True), ("NIST SP 800-53", "AC-11", True)]),

    # ------------------------------------------------ повышение привилегий
    ("privilege.su_restriction", "Ограничение доступа к команде su",
     ["команде su", "pam_wheel", "группы wheel", "ограничение доступа к su"],
     ["su command", "pam_wheel", "wheel group", "restrict su"],
     ["Повышение привилегий", "Управление доступом"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.2.1", False),
      ("CIS Benchmark, раздел ограничения su", "Restrict su", True)]),

    ("privilege.sudo_review", "Пересмотр прав на использование sudo",
     ["sudoers", "команду sudo", "список пользователей sudo", "пересмотр прав",
      "разрешённых команд", "ролевая модель"],
     ["sudoers", "sudo privileges", "least privilege", "privilege review", "authorized commands"],
     ["Повышение привилегий", "Организационные меры"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.2.2", False),
      ("ISO/IEC 27002, управление привилегированным доступом", "8.2", True),
      ("NIST SP 800-53", "AC-6(7)", True)]),

    ("privilege.suid_audit", "Контроль SUID/SGID-приложений",
     ["suid", "sgid", "suid/sgid", "битов suid", "белый список приложений"],
     ["suid", "sgid", "setuid", "setgid", "privilege escalation binaries"],
     ["Повышение привилегий", "Права на файлы"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.3.9", False),
      ("CIS Benchmark, раздел аудита SUID", "Audit SUID executables", True)]),

    # ---------------------------------------------------- парольная политика
    ("password.length", "Минимальная длина пароля",
     ["длина пароля", "минимальная длина", "minlen", "длиной не менее", "количество символов пароля"],
     ["password length", "minimum length", "minlen", "minimum password length"],
     ["Парольная политика"],
     [("ФСТЭК, приказ №17", "ИАФ.1", True),
      ("ГОСТ Р 57580.1, парольная защита", "РД.1", True),
      ("CIS Benchmark, раздел парольной политики", "Password Policy", True),
      ("NIST SP 800-53", "IA-5", True)]),

    ("password.complexity", "Сложность пароля",
     ["сложность пароля", "алфавит пароля", "dcredit", "ucredit", "символов разных регистров",
      "цифр и специальных символов"],
     ["password complexity", "character classes", "dcredit", "ucredit", "special characters"],
     ["Парольная политика"],
     [("ФСТЭК, приказ №17", "ИАФ.1", True), ("NIST SP 800-53", "IA-5(1)", True)]),

    ("password.max_age", "Максимальный срок действия пароля",
     ["срок действия пароля", "pass_max_days", "периодическая смена", "смены пароля не реже"],
     ["password expiration", "pass_max_days", "maximum password age", "password rotation"],
     ["Парольная политика"],
     [("ФСТЭК, приказ №17", "ИАФ.1", True), ("ГОСТ Р 57580.1, парольная защита", "РД.1", True)]),

    ("password.min_age", "Минимальный интервал смены пароля",
     ["pass_min_days", "минимальный срок", "интервал между сменами"],
     ["pass_min_days", "minimum password age"],
     ["Парольная политика"], [("CIS Benchmark, раздел парольной политики", "Password Policy", True)]),

    ("password.history", "История паролей",
     ["история паролей", "повторное использование пароля", "ранее использованных паролей",
      "password_hist_len", "remember"],
     ["password history", "password reuse", "remember previous passwords"],
     ["Парольная политика"],
     [("ФСТЭК, приказ №17", "ИАФ.1", True), ("NIST SP 800-53", "IA-5(1)", True)]),

    # ------------------------------------------------------- права на файлы
    ("files.passwd_group_perms", "Права доступа к перечням пользователей и групп",
     ["/etc/passwd", "/etc/group", "перечнями пользовательских идентификаторов",
      "файлам настройки пользователей", "списка групп"],
     ["/etc/passwd", "/etc/group", "user account files", "group file permissions"],
     ["Права на файлы", "Управление доступом"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.3.1", False),
      ("CIS Benchmark, раздел прав на системные файлы", "System File Permissions", True)]),

    ("files.shadow_perms", "Защита хранилища хешей паролей",
     ["/etc/shadow", "хешей паролей", "хранилищам хешей", "go-rwx"],
     ["/etc/shadow", "password hashes", "shadow file permissions"],
     ["Права на файлы", "Парольная политика"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.3.1", False),
      ("CIS Benchmark, раздел прав на системные файлы", "System File Permissions", True)]),

    ("files.cron_perms", "Права доступа к заданиям планировщика",
     ["cron", "crontab", "планировщика задач", "cron.d", "cron.daily", "файлам заданий"],
     ["cron", "crontab", "scheduled tasks", "cron.d", "job files"],
     ["Права на файлы"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.3.6", False),
      ("CIS Benchmark, раздел настройки cron", "Configure cron", True)]),

    ("files.home_dir_perms", "Права доступа к домашним каталогам",
     ["домашних директорий", "домашним директориям", "домашние каталоги", "bash_history",
      "bashrc", "profile", "rhosts"],
     ["home directories", "home directory permissions", "dot files", "bash_history"],
     ["Права на файлы"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.3.10", False),
      ("CIS Benchmark, раздел пользовательских настроек", "User Home Directories", True)]),

    ("files.system_binaries", "Права доступа к исполняемым файлам и библиотекам",
     ["исполняемым файлам", "библиотекам", "модулям ядра", "системным библиотекам", "utilities"],
     ["system binaries", "libraries", "kernel modules", "executable permissions"],
     ["Права на файлы"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.3.8", False)]),

    ("files.startup_scripts", "Права доступа к стартовым скриптам",
     ["стартовым скриптам", "rc#.d", ".service", "автозапуска"],
     ["startup scripts", "init scripts", "service files", "boot scripts"],
     ["Права на файлы"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.3.5", False)]),

    # ---------------------------------------------------------- ядро Linux
    ("kernel.dmesg_restrict", "Ограничение доступа к журналу ядра",
     ["журналу ядра", "dmesg", "kernel.dmesg_restrict", "cap_syslog"],
     ["kernel log", "dmesg", "kernel.dmesg_restrict"],
     ["Параметры ядра"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.4.1", False)]),

    ("kernel.kptr_restrict", "Скрытие адресов ядра",
     ["ядерные адреса", "kernel.kptr_restrict", "адреса в /proc", "заменить адреса"],
     ["kernel pointers", "kptr_restrict", "kernel address exposure"],
     ["Параметры ядра"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.4.2", False)]),

    ("kernel.aslr", "Рандомизация адресного пространства",
     ["рандомизация адресного пространства", "randomize_va_space", "переполнение буфера", "aslr"],
     ["address space layout randomization", "aslr", "randomize_va_space", "buffer overflow"],
     ["Параметры ядра"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.5.11", False),
      ("CIS Benchmark, раздел параметров ядра", "Kernel Parameters", True)]),

    ("kernel.ptrace_scope", "Ограничение отладочного интерфейса ptrace",
     ["ptrace", "подключение к другим процессам", "yama"],
     ["ptrace", "process tracing", "yama", "debugging interface"],
     ["Параметры ядра"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.6.1", False)]),

    ("kernel.bpf_restrict", "Ограничение подсистемы eBPF",
     ["bpf", "ebpf", "unprivileged_bpf", "bpf_jit_harden"],
     ["bpf", "ebpf", "unprivileged bpf", "jit hardening"],
     ["Параметры ядра"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.4.8", False)]),

    ("kernel.user_namespaces", "Ограничение user namespaces",
     ["user namespaces", "max_user_namespaces", "пространства имён"],
     ["user namespaces", "unprivileged user namespaces"],
     ["Параметры ядра"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.5.5", False)]),

    ("kernel.fs_protections", "Защита от подмены ссылок и файлов",
     ["символическим ссылкам", "жёсткими ссылками", "symlinks", "hardlinks",
      "protected_fifos", "protected_regular", "непреднамеренной записи"],
     ["symlink protection", "hardlink protection", "protected fifos", "protected regular"],
     ["Параметры ядра", "Файловые системы"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.6.2", False)]),

    ("kernel.core_dump", "Ограничение создания дампов памяти",
     ["core dump", "suid_dumpable", "дамп памяти"],
     ["core dump", "suid_dumpable", "memory dump"],
     ["Параметры ядра"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.6.6", False)]),

    ("kernel.boot_hardening", "Параметры усиления при загрузке ядра",
     ["опции загрузки ядра", "параметры загрузки", "cmdline", "init_on_alloc", "slab_nomerge",
      "iommu", "mitigations", "vsyscall", "tsx", "randomize_kstack"],
     ["kernel boot parameters", "cmdline", "init_on_alloc", "slab_nomerge", "iommu",
      "mitigations", "vsyscall", "tsx"],
     ["Параметры загрузки ядра"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.4.3", False)]),

    ("kernel.attack_surface", "Уменьшение периметра атаки ядра",
     ["периметр атаки", "kexec_load", "debugfs", "perf_event_paranoid", "userfaultfd",
      "ldisc_autoload", "mmap_min_addr"],
     ["attack surface", "kexec", "debugfs", "perf_event_paranoid", "userfaultfd", "mmap_min_addr"],
     ["Параметры ядра"],
     [("ФСТЭК, Рекомендации по настройке ОС Linux (2022)", "2.5.1", False)]),

    # -------------------------------------------------------- сеть и службы
    ("network.ip_forward", "Запрет транзитной передачи пакетов",
     ["переадресация", "ip_forward", "маршрутизация пакетов", "транзитный трафик"],
     ["ip forwarding", "packet forwarding", "routing"],
     ["Сетевые параметры"],
     [("CIS Benchmark, раздел сетевых параметров", "Network Parameters", True),
      ("ФСТЭК, приказ №17", "ЗИС", True)]),

    ("network.icmp_redirects", "Запрет ICMP-перенаправлений",
     ["icmp", "перенаправлений", "accept_redirects", "send_redirects"],
     ["icmp redirects", "accept_redirects", "send_redirects"],
     ["Сетевые параметры"],
     [("CIS Benchmark, раздел сетевых параметров", "Network Parameters", True)]),

    ("network.spoof_protection", "Защита от подмены адреса источника",
     ["подмена адреса", "rp_filter", "обратного пути", "spoofing"],
     ["source address spoofing", "reverse path filter", "rp_filter"],
     ["Сетевые параметры"],
     [("CIS Benchmark, раздел сетевых параметров", "Network Parameters", True)]),

    ("network.insecure_services", "Запрет незащищённых сетевых служб",
     ["telnet", "ftp", "rsh", "открытых портов", "незащищённый протокол", "открытом виде"],
     ["telnet", "ftp", "rsh", "insecure services", "cleartext protocol", "unencrypted"],
     ["Сетевые службы"],
     [("CIS Benchmark, раздел сетевых служб", "Special Purpose Services", True),
      ("ФСТЭК, приказ №17", "ЗИС", True),
      ("PCI DSS, защита передаваемых данных", "4.1", True)]),

    # ------------------------------------------------------ аудит и журналы
    ("audit.subsystem_installed", "Наличие подсистемы аудита",
     ["подсистема аудита", "auditd", "регистрация событий", "журналирование событий"],
     ["audit subsystem", "auditd", "audit daemon", "event logging"],
     ["Регистрация событий"],
     [("ФСТЭК, приказ №17", "РСБ.1", True),
      ("ГОСТ Р 57580.1, регистрация событий", "РЗН", True),
      ("CIS Benchmark, раздел аудита", "Configure System Accounting", True),
      ("NIST SP 800-53", "AU-2", True)]),

    ("audit.service_running", "Работа подсистемы аудита",
     ["служба аудита", "запущена", "активна", "auditd.service"],
     ["audit service", "auditd enabled", "service running"],
     ["Регистрация событий"],
     [("ФСТЭК, приказ №17", "РСБ", True), ("NIST SP 800-53", "AU-12", True)]),

    ("audit.log_protection", "Защита журналов от изменения",
     ["защита журналов", "изменение журналов", "целостность журналов", "хранение журналов"],
     ["log protection", "log integrity", "audit log retention"],
     ["Регистрация событий"],
     [("ФСТЭК, приказ №17", "РСБ.3", True), ("NIST SP 800-53", "AU-9", True),
      ("ISO/IEC 27002, журналирование", "8.15", True)]),

    # ------------------------------------------------- файловые системы
    ("fs.mount_options", "Параметры монтирования разделов",
     ["параметры монтирования", "nodev", "nosuid", "noexec", "/tmp", "разделов"],
     ["mount options", "nodev", "nosuid", "noexec", "partition"],
     ["Файловые системы"],
     [("CIS Benchmark, раздел файловых систем", "Filesystem Configuration", True)]),

    # ---------------------------------------------------- организационные
    ("org.access_procedure", "Порядок управления доступом",
     ["порядок предоставления", "пересмотр прав доступа", "матрица доступа",
      "ответственные", "регламент"],
     ["access control procedure", "access review", "authorization process"],
     ["Организационные меры"],
     [("ФСТЭК, приказ №17", "УПД.1", True),
      ("ISO/IEC 27002, управление доступом", "5.15", True),
      ("NIST SP 800-53", "AC-1", True)]),

    ("org.awareness", "Обучение и информирование персонала",
     ["обучение", "инструктаж", "осведомлённость", "информирование персонала"],
     ["security awareness", "training", "personnel briefing"],
     ["Организационные меры"],
     [("ФСТЭК, приказ №17", "ОПС", True),
      ("ISO/IEC 27002, осведомлённость", "6.3", True),
      ("NIST SP 800-53", "AT-2", True)]),

    ("org.backup", "Резервное копирование",
     ["резервное копирование", "резервных копий", "восстановление данных"],
     ["backup", "data recovery", "restore"],
     ["Организационные меры"],
     [("ФСТЭК, приказ №17", "ОДТ", True), ("ISO/IEC 27002, резервное копирование", "8.13", True)]),

    ("org.vulnerability_management", "Управление уязвимостями и обновлениями",
     ["управление уязвимостями", "обновления безопасности", "устранение уязвимостей", "патчи"],
     ["vulnerability management", "patch management", "security updates"],
     ["Организационные меры"],
     [("ФСТЭК, приказ №17", "АНЗ.1", True),
      ("NIST SP 800-53", "RA-5", True),
      ("PCI DSS, управление уязвимостями", "6.3", True)]),
]

# Привязка записей каталога к концептам
CATALOG_LINKS = {
    "ssh.permit_root_login": ["access.ssh_root_login"],
    "ssh.permit_empty_passwords": ["access.ssh_empty_password"],
    "ssh.max_auth_tries": ["access.ssh_auth_attempts"],
    "ssh.x11_forwarding": ["access.ssh_root_login"],
    "password.minlen": ["password.length"],
    "password.max_days": ["password.max_age"],
    "password.min_days": ["password.min_age"],
    "sysctl.ip_forward": ["network.ip_forward"],
    "sysctl.accept_redirects": ["network.icmp_redirects"],
    "sysctl.send_redirects": ["network.icmp_redirects"],
    "sysctl.rp_filter": ["network.spoof_protection"],
    "sysctl.aslr": ["kernel.aslr"],
    "file.passwd_owner": ["files.passwd_group_perms"],
    "file.shadow_not_world_readable": ["files.shadow_perms"],
    "file.crontab_owner": ["files.cron_perms"],
    "audit.package_installed": ["audit.subsystem_installed"],
    "password.history": ["password.history"],
    "audit.service_active": ["audit.service_running"],
    "net.telnet_port_closed": ["network.insecure_services"],
    "mount.tmp_nodev": ["fs.mount_options"],
    "org.access_control_procedure": ["org.access_procedure"],
    "org.security_awareness": ["org.awareness"],
    # пакет по Рекомендациям ФСТЭК
    "fstec.2_1_2": ["access.ssh_root_login"],
    "fstec.2_1_1": ["access.ssh_empty_password"],
    "fstec.2_2_1": ["privilege.su_restriction"],
    "fstec.2_2_2": ["privilege.sudo_review"],
    "fstec.2_3_1a": ["files.passwd_group_perms"],
    "fstec.2_3_1b": ["files.passwd_group_perms"],
    "fstec.2_3_1c": ["files.shadow_perms"],
    "fstec.2_3_5": ["files.startup_scripts"],
    "fstec.2_3_6": ["files.cron_perms"],
    "fstec.2_3_8": ["files.system_binaries"],
    "fstec.2_3_9": ["privilege.suid_audit"],
    "fstec.2_3_10": ["files.home_dir_perms"],
    "fstec.2_3_11": ["files.home_dir_perms"],
    "fstec.2_4_1": ["kernel.dmesg_restrict"],
    "fstec.2_4_2": ["kernel.kptr_restrict"],
    "fstec.2_4_8": ["kernel.bpf_restrict"],
    "fstec.2_5_6": ["kernel.bpf_restrict"],
    "fstec.2_5_5": ["kernel.user_namespaces"],
    "fstec.2_5_11": ["kernel.aslr"],
    "fstec.2_6_1": ["kernel.ptrace_scope"],
    "fstec.2_6_2": ["kernel.fs_protections"],
    "fstec.2_6_3": ["kernel.fs_protections"],
    "fstec.2_6_4": ["kernel.fs_protections"],
    "fstec.2_6_5": ["kernel.fs_protections"],
    "fstec.2_6_6": ["kernel.core_dump"],
    "fstec.2_4_3": ["kernel.boot_hardening"],
    "fstec.2_4_4": ["kernel.boot_hardening"],
    "fstec.2_4_5a": ["kernel.boot_hardening"],
    "fstec.2_4_5b": ["kernel.boot_hardening"],
    "fstec.2_4_5c": ["kernel.boot_hardening"],
    "fstec.2_4_6": ["kernel.boot_hardening"],
    "fstec.2_4_7": ["kernel.boot_hardening"],
    "fstec.2_5_1": ["kernel.attack_surface"],
    "fstec.2_5_2": ["kernel.attack_surface"],
    "fstec.2_5_3": ["kernel.attack_surface"],
    "fstec.2_5_4": ["kernel.attack_surface"],
    "fstec.2_5_7": ["kernel.attack_surface"],
    "fstec.2_5_8": ["kernel.attack_surface"],
    "fstec.2_5_9": ["kernel.boot_hardening"],
    "fstec.2_5_10": ["kernel.attack_surface"],
    "fstec.2_3_2": ["files.system_binaries"],
    "fstec.2_3_3": ["files.cron_perms"],
    "fstec.2_3_4": ["privilege.sudo_review"],
    "fstec.2_3_7": ["files.cron_perms"],
}

concepts = []
for cid, title, ru, en, themes, hints in CONCEPTS:
    concepts.append({
        "id": cid,
        "title": title,
        "ru": ru,
        "en": en,
        "themes": themes,
        "doc_hints": [{"family": f, "ref": r, "verify": v} for f, r, v in hints],
    })

out = {
    "knowledge": "requirements-thesaurus",
    "title": "Тезаурус требований: формулировки нормативных документов",
    "description": (
        "Слой между текстом нормативного документа и техническим каталогом проверок. "
        "Хранит формулировки-маркеры на русском и английском, по которым тема требования "
        "узнаётся в тексте, и ссылки на семейства документов, где тема встречается. "
        "Тексты стандартов не воспроизводятся: хранятся только обозначения и собственные "
        "формулировки. Ссылки с verify=true — ориентир, требующий сверки с вашей редакцией документа."
    ),
    "concepts": concepts,
    "catalog_links": CATALOG_LINKS,
}

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "concepts.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

fams = sorted({h["family"].split(",")[0] for c in concepts for h in c["doc_hints"]})
print("концептов: %d, формулировок RU/EN: %d/%d, привязок каталога: %d"
      % (len(concepts),
         sum(len(c["ru"]) for c in concepts),
         sum(len(c["en"]) for c in concepts),
         len(CATALOG_LINKS)))
print("семейства документов:", ", ".join(fams))
