"""
Реестр допустимых типов OVAL test/object/state, перечисленных в разделе
"Допустимые типы OVAL-тестов" требований.

Для каждого типа описана схема полей object и state в декларативном виде.
Схема используется в двух местах:
  1. Фронтенд запрашивает GET /api/oval-type-schemas и строит формы динамически.
  2. Бэкенд (oval_xml.py) использует ту же схему для сборки/разбора XML.

ВАЖНО: поля ниже покрывают наиболее употребимые сущности каждого типа
(достаточные для типовых compliance-проверок, как в примере password_hist_len
из требований). Полная схема OVAL 5.11.2 значительно шире; при необходимости
список entity можно расширить, не меняя остальную архитектуру — форма и
генератор XML полностью управляются этим реестром.
"""

def entity(name, label, datatype="string", default_operation="equals",
           required=False, allow_var_ref=False, is_plain_value=False,
           options=None, attrs=None, default=None):
    """
    is_plain_value=True  -> объектная сущность без operation/datatype атрибутов,
                             просто <tag>value</tag> (типично для object).
    is_plain_value=False -> "сравнивающая" сущность (типично для state):
                             <tag datatype=".." operation="..">value</tag>
                             либо <tag var_ref=".."/> если allow_var_ref.
    options              -> список допустимых значений для select в UI (не обязателен).
    attrs                -> атрибуты, которые всегда выводятся у объектной сущности.
                            Пример: pattern у textfilecontent54 обязан нести
                            operation="pattern match" — иначе действует equals,
                            и регулярное выражение сравнивается как обычная строка.
    default              -> значение, подставляемое, если поле не заполнено.
                            Нужно для сущностей, обязательных по схеме OVAL,
                            но не интересных пользователю (instance = 1).
    """
    return {
        "name": name,
        "label": label,
        "datatype": datatype,
        "default_operation": default_operation,
        "required": required,
        "allow_var_ref": allow_var_ref,
        "is_plain_value": is_plain_value,
        "options": options or [],
        "attrs": attrs or {},
        "default": default,
    }


TEST_TYPES = {
    # ---------- Проверки Linux (общие) ----------
    "ind:textfilecontent54_test": {
        "family": "independent",
        "tag": "textfilecontent54",
        "object_fields": [
            entity("path", "Путь к каталогу", required=True, is_plain_value=True),
            entity("filename", "Имя файла", required=True, is_plain_value=True),
            entity("pattern", "Регулярное выражение", required=True, is_plain_value=True,
                   attrs={"operation": "pattern match"}),
            # instance обязателен по схеме; «>= 1» означает «все совпадения»
            entity("instance", "Номер совпадения", is_plain_value=True,
                   attrs={"datatype": "int", "operation": "greater than or equal"},
                   default="1"),
        ],
        "state_fields": [
            entity("subexpression", "Значение (subexpression)", allow_var_ref=True,
                   default_operation="pattern match"),
        ],
    },
    "ind:variable_test": {
        "family": "independent",
        "tag": "variable",
        "object_fields": [
            entity("var_ref", "Идентификатор переменной (var_ref)", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("value", "Ожидаемое значение", allow_var_ref=True),
        ],
    },
    "linux:inetlisteningservers_test": {
        "family": "linux",
        "tag": "inetlisteningservers",
        "object_fields": [
            entity("protocol", "Протокол (tcp/udp)", required=True, is_plain_value=True, default="tcp"),
            # Адрес обязателен по схеме; «любой адрес» задаётся шаблоном
            entity("local_address", "Локальный адрес", required=True, is_plain_value=True,
                   attrs={"operation": "pattern match"}, default=".*"),
            entity("local_port", "Локальный порт", required=True, is_plain_value=True,
                   attrs={"datatype": "int"}),
        ],
        "state_fields": [
            entity("protocol", "Протокол"),
            entity("local_address", "Локальный адрес"),
            entity("local_port", "Локальный порт", datatype="int"),
            entity("program_name", "Имя программы"),
            entity("user_id", "UID процесса", datatype="int"),
            entity("pid", "PID", datatype="int"),
        ],
    },
    "linux:partition_test": {
        "family": "linux",
        "tag": "partition",
        "object_fields": [
            entity("mount_point", "Точка монтирования", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("fs_type", "Тип файловой системы"),
            entity("mount_options", "Опции монтирования"),
            entity("total_space", "Общий размер (KB)", datatype="int"),
            entity("space_used", "Использовано (KB)", datatype="int"),
            entity("space_left", "Свободно (KB)", datatype="int"),
        ],
    },
    "linux:systemdunitproperty_test": {
        "family": "linux",
        "tag": "systemdunitproperty",
        "object_fields": [
            entity("unit", "Unit (например, sshd.service)", required=True, is_plain_value=True),
            entity("property", "Свойство (например, UnitFileState)", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("value", "Ожидаемое значение", allow_var_ref=True),
        ],
    },
    "unix:file_test": {
        "family": "unix",
        "tag": "file",
        "object_fields": [
            entity("path", "Путь к каталогу", required=True, is_plain_value=True),
            entity("filename", "Имя файла (пусто = сам каталог)", is_plain_value=True),
        ],
        "state_fields": [
            entity("type", "Тип объекта", options=["file", "directory", "symbolic link"]),
            entity("user_id", "UID владельца", datatype="int"),
            entity("group_id", "GID группы", datatype="int"),
            entity("suid", "SUID", datatype="boolean"),
            entity("sgid", "SGID", datatype="boolean"),
            entity("sticky", "Sticky bit", datatype="boolean"),
            entity("uread", "uread"), entity("uwrite", "uwrite"), entity("uexec", "uexec"),
            entity("gread", "gread"), entity("gwrite", "gwrite"), entity("gexec", "gexec"),
            entity("oread", "oread"), entity("owrite", "owrite"), entity("oexec", "oexec"),
        ],
    },
    "unix:password_test": {
        "family": "unix",
        "tag": "password",
        "object_fields": [
            entity("username", "Имя пользователя", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("password", "Поле пароля (обычно 'x')"),
            entity("user_id", "UID", datatype="int"),
            entity("group_id", "GID", datatype="int"),
            entity("gecos", "GECOS"),
            entity("home_dir", "Домашний каталог"),
            entity("login_shell", "Login shell"),
        ],
    },
    "unix:sysctl_test": {
        "family": "unix",
        "tag": "sysctl",
        "object_fields": [
            entity("name", "Имя параметра (например, net.ipv4.ip_forward)", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("value", "Ожидаемое значение", allow_var_ref=True),
        ],
    },

    # ---------- Проверки DEB-пакетов ----------
    "linux:dpkginfo_test": {
        "family": "linux",
        "tag": "dpkginfo",
        "object_fields": [
            entity("name", "Имя пакета", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("version", "Версия", default_operation="greater than or equal"),
            entity("arch", "Архитектура"),
            entity("epoch", "Epoch"),
            entity("release", "Release"),
            entity("evr", "EVR (epoch:version-release)", datatype="version",
                   default_operation="greater than or equal"),
        ],
    },

    # ---------- Проверки RPM-пакетов ----------
    "linux:rpminfo_test": {
        "family": "linux",
        "tag": "rpminfo",
        "object_fields": [
            entity("name", "Имя пакета", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("version", "Версия", default_operation="greater than or equal"),
            entity("release", "Release"),
            entity("arch", "Архитектура"),
            entity("evr", "EVR (epoch:version-release)", datatype="version",
                   default_operation="greater than or equal"),
            entity("signature_keyid", "ID ключа подписи"),
        ],
    },

    # ---------- Проверки Windows ----------
    "windows:auditeventpolicysubcategories_test": {
        "family": "windows",
        "tag": "auditeventpolicysubcategories",
        "object_fields": [
            entity("auditing_subcategory", "Подкатегория аудита (например, Logon)",
                   required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("audit_success", "Аудит успеха", datatype="boolean"),
            entity("audit_failure", "Аудит отказа", datatype="boolean"),
        ],
    },
    "windows:lockoutpolicy_test": {
        "family": "windows",
        "tag": "lockoutpolicy",
        "object_fields": [],  # объект не содержит фильтрующих полей
        "state_fields": [
            entity("lockout_duration", "Продолжительность блокировки (мин)",
                   datatype="int", allow_var_ref=True,
                   default_operation="greater than or equal"),
            entity("lockout_bad_count", "Порог блокировки (число попыток)",
                   datatype="int", allow_var_ref=True,
                   default_operation="less than or equal"),
            entity("lockout_reset_count", "Сброс счётчика через (мин)",
                   datatype="int", allow_var_ref=True,
                   default_operation="greater than or equal"),
        ],
    },
    "windows:passwordpolicy_test": {
        "family": "windows",
        "tag": "passwordpolicy",
        "object_fields": [],
        "state_fields": [
            entity("max_passwd_age", "Максимальный срок действия пароля (дни)",
                   datatype="int", allow_var_ref=True,
                   default_operation="less than or equal"),
            entity("min_passwd_age", "Минимальный срок действия пароля (дни)",
                   datatype="int", allow_var_ref=True,
                   default_operation="greater than or equal"),
            entity("min_passwd_len", "Минимальная длина пароля",
                   datatype="int", allow_var_ref=True,
                   default_operation="greater than or equal"),
            entity("password_hist_len", "Длина истории паролей",
                   datatype="int", allow_var_ref=True,
                   default_operation="greater than or equal"),
            entity("passwd_complexity", "Требования к сложности пароля",
                   datatype="boolean", allow_var_ref=True),
            entity("clear_text_passwd", "Хранение пароля в открытом виде запрещено",
                   datatype="boolean", allow_var_ref=True),
        ],
    },
    "windows:registry_test": {
        "family": "windows",
        "tag": "registry",
        "object_fields": [
            entity("hive", "Куст реестра", required=True, is_plain_value=True,
                   options=["HKEY_LOCAL_MACHINE", "HKEY_CURRENT_USER", "HKEY_USERS",
                            "HKEY_CLASSES_ROOT", "HKEY_CURRENT_CONFIG"]),
            entity("key", "Ключ реестра", required=True, is_plain_value=True),
            entity("name", "Имя параметра (value name)", is_plain_value=True),
        ],
        "state_fields": [
            entity("type", "Тип значения",
                   options=["reg_sz", "reg_dword", "reg_binary", "reg_multi_sz",
                            "reg_expand_sz", "reg_qword"]),
            entity("value", "Значение", allow_var_ref=True),
        ],
    },
    "windows:sid_sid_test": {
        "family": "windows",
        "tag": "sid_sid",
        "object_fields": [
            entity("trustee_name", "Имя учётной записи (trustee_name)", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("trustee_sid", "SID"),
        ],
    },
    "windows:user_sid55_test": {
        "family": "windows",
        "tag": "user_sid55",
        "object_fields": [
            entity("user", "Пользователь", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("trustee_sid", "SID"),
            entity("trustee_domain", "Домен"),
            entity("trustee_name", "Имя учётной записи"),
        ],
    },
    "windows:userright_test": {
        "family": "windows",
        "tag": "userright",
        "object_fields": [
            entity("user_right", "Право (например, SeRemoteInteractiveLogonRight)",
                   required=True, is_plain_value=True),
            entity("trustee_sid", "Фильтр по SID (опционально)", is_plain_value=True),
        ],
        "state_fields": [
            entity("trustee_sid", "SID"),
            entity("trustee_name", "Имя учётной записи"),
            entity("trustee_domain", "Домен"),
        ],
    },
    "windows:wmi57_test": {
        "family": "windows",
        "tag": "wmi57",
        "object_fields": [
            entity("namespace", "WMI namespace (например, root\\cimv2)",
                   required=True, is_plain_value=True),
            entity("wql", "WQL-запрос", required=True, is_plain_value=True),
        ],
        "state_fields": [
            entity("result", "Ожидаемый результат", allow_var_ref=True),
        ],
    },
}


# Человекочитаемые русскоязычные названия типов тестов (для выпадающих
# списков и подписей на фронтенде). Технический идентификатор (ключ TEST_TYPES)
# всегда остаётся английским, т.к. это часть стандарта OVAL/XCCDF.
TEST_TYPE_LABELS = {
    "ind:textfilecontent54_test": "Содержимое текстового файла (по шаблону)",
    "ind:variable_test": "Значение переменной",
    "linux:inetlisteningservers_test": "Прослушиваемые сетевые порты",
    "linux:partition_test": "Точка монтирования",
    "linux:systemdunitproperty_test": "Свойство systemd-юнита",
    "unix:file_test": "Файл (права доступа, владелец)",
    "unix:password_test": "Учётная запись (/etc/passwd)",
    "unix:sysctl_test": "Параметр sysctl",
    "linux:dpkginfo_test": "Пакет DEB (dpkg)",
    "linux:rpminfo_test": "Пакет RPM",
    "windows:auditeventpolicysubcategories_test": "Политика аудита (подкатегории событий)",
    "windows:lockoutpolicy_test": "Политика блокировки учётных записей",
    "windows:passwordpolicy_test": "Политика паролей",
    "windows:registry_test": "Параметр реестра",
    "windows:sid_sid_test": "Соответствие SID учётной записи",
    "windows:user_sid55_test": "SID пользователя",
    "windows:userright_test": "Право пользователя (user right)",
    "windows:wmi57_test": "WMI-запрос",
}

# Те же названия по-английски (дублирование подписи по xml:lang в интерфейсе).
# =====================================================================
# Сверка со схемами OVAL 5.11.2
#
# Определения ниже замещают ранние описания полей для типов, где те
# расходились со схемой: неверные имена (gecos вместо gcos,
# passwd_complexity вместо password_complexity, выдуманные
# lockout_bad_count и auditing_subcategory) и неверный порядок элементов.
# Порядок важен: схема задаёт элементы как xsd:sequence, и документ с
# переставленными полями не проходит проверку (oscap oval validate).
#
# Сверка выполнялась автоматически: имена и порядок прочитаны из XSD
# (/usr/share/openscap/schemas/oval/5.11.2/*-definitions-schema.xsd).
# =====================================================================

_AUDIT = ["AUDIT_NONE", "AUDIT_SUCCESS", "AUDIT_FAILURE", "AUDIT_SUCCESS_FAILURE"]

def _audit(name, label):
    return entity(name, label, options=_AUDIT)

_SCHEMA_FIXES = {
    "linux:inetlisteningservers_test": {"state_fields": [
        entity("protocol", "Протокол"),
        entity("local_address", "Локальный адрес"),
        entity("local_port", "Локальный порт", datatype="int"),
        entity("program_name", "Имя программы"),
        entity("pid", "PID процесса", datatype="int"),
        entity("user_id", "UID владельца процесса", datatype="int"),
    ]},
    "unix:file_test": {"state_fields": [
        entity("type", "Тип файла"),
        entity("group_id", "GID группы", datatype="int"),
        entity("user_id", "UID владельца", datatype="int"),
        entity("suid", "SUID", datatype="boolean"),
        entity("sgid", "SGID", datatype="boolean"),
        entity("sticky", "Sticky-бит", datatype="boolean"),
        entity("uread", "Чтение для владельца", datatype="boolean"),
        entity("uwrite", "Запись для владельца", datatype="boolean"),
        entity("uexec", "Выполнение для владельца", datatype="boolean"),
        entity("gread", "Чтение для группы", datatype="boolean"),
        entity("gwrite", "Запись для группы", datatype="boolean"),
        entity("gexec", "Выполнение для группы", datatype="boolean"),
        entity("oread", "Чтение для прочих", datatype="boolean"),
        entity("owrite", "Запись для прочих", datatype="boolean"),
        entity("oexec", "Выполнение для прочих", datatype="boolean"),
    ]},
    "linux:dpkginfo_test": {"state_fields": [
        entity("arch", "Архитектура"),
        entity("epoch", "Эпоха"),
        entity("release", "Выпуск"),
        entity("version", "Версия", datatype="version"),
        entity("evr", "Полная версия (EVR)", datatype="evr_string"),
    ]},
    "linux:rpminfo_test": {"state_fields": [
        entity("arch", "Архитектура"),
        entity("release", "Выпуск"),
        entity("version", "Версия", datatype="version"),
        entity("evr", "Полная версия (EVR)", datatype="evr_string"),
        entity("signature_keyid", "Идентификатор ключа подписи"),
    ]},
    "windows:auditeventpolicysubcategories_test": {
        # Объект пустой: политика аудита одна на систему. Каждая подкатегория —
        # отдельное поле состояния со значением из перечня AUDIT_*.
        "object_fields": [],
        "state_fields": [
            _audit("credential_validation", "Проверка учётных данных"),
            _audit("security_group_management", "Управление группами безопасности"),
            _audit("user_account_management", "Управление учётными записями"),
            _audit("process_creation", "Создание процессов"),
            _audit("account_lockout", "Блокировка учётных записей"),
            _audit("logoff", "Выход из системы"),
            _audit("logon", "Вход в систему"),
            _audit("special_logon", "Специальный вход"),
            _audit("audit_policy_change", "Изменение политики аудита"),
            _audit("authentication_policy_change", "Изменение политики проверки подлинности"),
            _audit("sensitive_privilege_use", "Использование важных привилегий"),
            _audit("security_state_change", "Изменение состояния безопасности"),
            _audit("security_system_extension", "Расширение системы безопасности"),
            _audit("system_integrity", "Целостность системы"),
        ],
    },
    "windows:lockoutpolicy_test": {"state_fields": [
        entity("force_logoff", "Принудительный выход по истечении времени", datatype="int"),
        entity("lockout_duration", "Длительность блокировки, с", datatype="int", allow_var_ref=True),
        entity("lockout_observation_window", "Окно подсчёта неудачных попыток, с", datatype="int", allow_var_ref=True),
        entity("lockout_threshold", "Порог блокировки (число попыток)", datatype="int",
               default_operation="less than or equal", allow_var_ref=True),
    ]},
    "windows:passwordpolicy_test": {"state_fields": [
        entity("max_passwd_age", "Максимальный срок действия пароля, с", datatype="int",
               default_operation="less than or equal", allow_var_ref=True),
        entity("min_passwd_age", "Минимальный срок действия пароля, с", datatype="int",
               default_operation="greater than or equal", allow_var_ref=True),
        entity("min_passwd_len", "Минимальная длина пароля", datatype="int",
               default_operation="greater than or equal", allow_var_ref=True),
        entity("password_hist_len", "Длина истории паролей", datatype="int",
               default_operation="greater than or equal", allow_var_ref=True),
        entity("password_complexity", "Требования к сложности пароля", datatype="boolean"),
        entity("reversible_encryption", "Хранение паролей с обратимым шифрованием", datatype="boolean"),
    ]},
    "windows:sid_sid_test": {
        "object_fields": [entity("trustee_sid", "SID учётной записи", required=True, is_plain_value=True)],
        "state_fields": [
            entity("trustee_sid", "SID учётной записи"),
            entity("trustee_name", "Имя учётной записи"),
            entity("trustee_domain", "Домен учётной записи"),
        ],
    },
    "windows:user_sid55_test": {
        "object_fields": [entity("user_sid", "SID пользователя", required=True, is_plain_value=True)],
        "state_fields": [
            entity("user_sid", "SID пользователя"),
            entity("enabled", "Учётная запись включена", datatype="boolean"),
            entity("group_sid", "SID группы"),
        ],
    },
    "windows:userright_test": {
        "object_fields": [entity("userright", "Право пользователя", required=True, is_plain_value=True)],
        "state_fields": [
            entity("userright", "Право пользователя"),
            entity("trustee_name", "Имя учётной записи"),
            entity("trustee_sid", "SID учётной записи"),
        ],
    },
}

# Права пользователей Windows — закрытое перечисление схемы: произвольное
# значение не пройдёт проверку, поэтому поле выводится выпадающим списком.
_USERRIGHTS = ["SE_ASSIGNPRIMARYTOKEN_NAME", "SE_AUDIT_NAME", "SE_BACKUP_NAME", "SE_CHANGE_NOTIFY_NAME", "SE_CREATE_GLOBAL_NAME", "SE_CREATE_PAGEFILE_NAME", "SE_CREATE_PERMANENT_NAME", "SE_CREATE_SYMBOLIC_LINK_NAME", "SE_CREATE_TOKEN_NAME", "SE_DEBUG_NAME", "SE_ENABLE_DELEGATION_NAME", "SE_IMPERSONATE_NAME", "SE_INC_BASE_PRIORITY_NAME", "SE_INCREASE_QUOTA_NAME", "SE_INC_WORKING_SET_NAME", "SE_LOAD_DRIVER_NAME", "SE_LOCK_MEMORY_NAME", "SE_MACHINE_ACCOUNT_NAME", "SE_MANAGE_VOLUME_NAME", "SE_PROF_SINGLE_PROCESS_NAME", "SE_RELABEL_NAME", "SE_REMOTE_SHUTDOWN_NAME", "SE_RESTORE_NAME", "SE_SECURITY_NAME", "SE_SHUTDOWN_NAME", "SE_SYNC_AGENT_NAME", "SE_SYSTEM_ENVIRONMENT_NAME", "SE_SYSTEM_PROFILE_NAME", "SE_SYSTEMTIME_NAME", "SE_TAKE_OWNERSHIP_NAME", "SE_TCB_NAME", "SE_TIME_ZONE_NAME", "SE_TRUSTED_CREDMAN_ACCESS_NAME", "SE_UNDOCK_NAME", "SE_UNSOLICITED_INPUT_NAME", "SE_BATCH_LOGON_NAME", "SE_DENY_BATCH_LOGON_NAME", "SE_DENY_INTERACTIVE_LOGON_NAME", "SE_DENY_NETWORK_LOGON_NAME", "SE_DENY_REMOTE_INTERACTIVE_LOGON_NAME", "SE_DENY_SERVICE_LOGON_NAME", "SE_INTERACTIVE_LOGON_NAME", "SE_NETWORK_LOGON_NAME", "SE_REMOTE_INTERACTIVE_LOGON_NAME", "SE_SERVICE_LOGON_NAME"]
for _f in _SCHEMA_FIXES["windows:userright_test"]["object_fields"] + _SCHEMA_FIXES["windows:userright_test"]["state_fields"]:
    if _f["name"] == "userright":
        _f["options"] = _USERRIGHTS

# У wmi57_state поле result — составная запись (record), а не строка:
# простым значением его задать нельзя, поэтому из формы оно исключено.
_SCHEMA_FIXES["windows:wmi57_test"] = {"state_fields": [
    entity("namespace", "Пространство имён WMI"),
    entity("wql", "Запрос WQL"),
]}

for _t, _fix in _SCHEMA_FIXES.items():
    if _t in TEST_TYPES:
        TEST_TYPES[_t].update(_fix)

# unix:password_state: поле называется gcos (а не gecos)
for _f in TEST_TYPES.get("unix:password_test", {}).get("state_fields", []):
    if _f["name"] == "gecos":
        _f["name"] = "gcos"


TEST_TYPE_LABELS_EN = {
    "ind:textfilecontent54_test": "Text file content (pattern match)",
    "ind:variable_test": "Variable value",
    "linux:inetlisteningservers_test": "Listening network ports",
    "linux:partition_test": "Mount point",
    "linux:systemdunitproperty_test": "systemd unit property",
    "unix:file_test": "File (permissions, owner)",
    "unix:password_test": "Account (/etc/passwd)",
    "unix:sysctl_test": "sysctl parameter",
    "linux:dpkginfo_test": "DEB package (dpkg)",
    "linux:rpminfo_test": "RPM package",
    "windows:auditeventpolicysubcategories_test": "Audit policy (event subcategories)",
    "windows:lockoutpolicy_test": "Account lockout policy",
    "windows:passwordpolicy_test": "Password policy",
    "windows:registry_test": "Registry value",
    "windows:sid_sid_test": "Account SID mapping",
    "windows:user_sid55_test": "User SID",
    "windows:userright_test": "User right",
    "windows:wmi57_test": "WMI query",
}


def _humanize_en(name):
    """Автоматически строит английскую подпись поля из его технического
    имени OVAL-сущности (эти имена уже являются частью стандарта и всегда
    английские, поэтому такой перевод корректен и не требует ручного
    дублирования сотен строк)."""
    return name.replace("_", " ").strip()


for _ttype, _cfg in TEST_TYPES.items():
    _cfg["label"] = TEST_TYPE_LABELS.get(_ttype, _ttype)
    _cfg["label_en"] = TEST_TYPE_LABELS_EN.get(_ttype, _ttype)
    for _f in _cfg["object_fields"]:
        _f.setdefault("label_en", _humanize_en(_f["name"]))
    for _f in _cfg["state_fields"]:
        _f.setdefault("label_en", _humanize_en(_f["name"]))


def type_correspondence():
    return {
        t: {
            "object_type": "{}_object".format(t.rsplit('_test', 1)[0]),
            "state_type": "{}_state".format(t.rsplit('_test', 1)[0]) if cfg["state_fields"] else None,
        }
        for t, cfg in TEST_TYPES.items()
    }


def allowed_test_types():
    return sorted(TEST_TYPES.keys())


def get_type_config(test_type: str):
    return TEST_TYPES.get(test_type)
