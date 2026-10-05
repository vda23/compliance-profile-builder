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
           options=None):
    """
    is_plain_value=True  -> объектная сущность без operation/datatype атрибутов,
                             просто <tag>value</tag> (типично для object).
    is_plain_value=False -> "сравнивающая" сущность (типично для state):
                             <tag datatype=".." operation="..">value</tag>
                             либо <tag var_ref=".."/> если allow_var_ref.
    options              -> список допустимых значений для select в UI (не обязателен).
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
    }


TEST_TYPES = {
    # ---------- Проверки Linux (общие) ----------
    "ind:textfilecontent54_test": {
        "family": "independent",
        "tag": "textfilecontent54",
        "object_fields": [
            entity("path", "Путь к каталогу", required=True, is_plain_value=True),
            entity("filename", "Имя файла", required=True, is_plain_value=True),
            entity("pattern", "Регулярное выражение", required=True, is_plain_value=True),
            entity("instance", "Instance (номер совпадения)", is_plain_value=True),
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
            entity("protocol", "Протокол (tcp/udp)", is_plain_value=True),
            entity("local_address", "Локальный адрес", is_plain_value=True),
            entity("local_port", "Локальный порт", is_plain_value=True),
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
            entity("uid", "UID владельца", datatype="int"),
            entity("gid", "GID группы", datatype="int"),
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
