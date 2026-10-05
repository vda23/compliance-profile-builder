# -*- coding: utf-8 -*-
"""
Веб-сервер Compliance Profile Builder на стандартной библиотеке Python
(раньше — FastAPI + uvicorn).

Отдаёт интерфейс (frontend/) и REST API (/api/...), при наличии сертификата
работает по HTTPS. Внешних зависимостей нет: нужен только системный python3
версии 3.5 и новее.

Запуск (обычно это делает systemd-служба, установленная install.sh):

    python3 -m app.server --host 0.0.0.0 --port 8443 \\
        --cert /opt/compliance-profile-builder/certs/server.crt \\
        --key  /opt/compliance-profile-builder/certs/server.key

Совместимость: Python 3.5+.
"""
import argparse
import json
import mimetypes
import os
import socket
import ssl
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

try:  # Python 3
    from urllib.parse import urlsplit, parse_qs, unquote
except ImportError:  # pragma: no cover
    raise SystemExit("Требуется Python 3.5 или новее.")

from . import api, storage

VERSION = "3.0"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

MAX_BODY = 50 * 1024 * 1024   # 50 МБ — с запасом для импорта ZIP-архивов

mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("font/ttf", ".ttf")


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Многопоточный сервер (класс ThreadingHTTPServer появился только в
    Python 3.7, поэтому объявлен здесь для совместимости с 3.5)."""
    daemon_threads = True
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = "ComplianceProfileBuilder/" + VERSION
    protocol_version = "HTTP/1.1"

    # --- журнал: коротко, в stderr → попадает в journalctl службы
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # --- отправка ответов
    def _send(self, status, body, content_type, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise api.ApiError(413, "Слишком большой запрос.")
        return self.rfile.read(length) if length > 0 else b""

    # --- статические файлы интерфейса
    def _static(self, path):
        if path in ("/", "/index.html"):
            full = os.path.join(FRONTEND_DIR, "index.html")
        elif path.startswith("/static/"):
            rel = unquote(path[len("/static/"):])
            full = os.path.normpath(os.path.join(STATIC_DIR, rel))
            # защита от выхода за пределы каталога (../)
            if not full.startswith(STATIC_DIR + os.sep):
                return self._json(404, {"detail": "Не найдено"})
        else:
            return self._json(404, {"detail": "Не найдено"})
        if not os.path.isfile(full):
            return self._json(404, {"detail": "Не найдено"})
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype == "application/javascript":
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            data = f.read()
        self._send(200, data, ctype)

    # --- API
    def _api(self, method, path, query):
        for r_method, regex, handler, kind in api.ROUTES:
            if r_method != method:
                continue
            m = regex.match(path)
            if not m:
                continue
            args = [unquote(g) for g in m.groups()]
            try:
                if kind == "none":
                    result = handler(*args)
                elif kind == "raw":
                    result = handler(query, self._read_body())
                else:
                    raw = self._read_body()
                    try:
                        body = json.loads(raw.decode("utf-8")) if raw else {}
                    except ValueError:
                        raise api.ApiError(400, "Некорректный JSON в теле запроса.")
                    result = handler(*(args + [body]))
            except api.ApiError as e:
                return self._json(e.status, {"detail": e.detail})
            except api.S.ValidationError as e:
                return self._json(422, {"detail": str(e)})
            except Exception as e:  # noqa: BLE001
                sys.stderr.write("Внутренняя ошибка: %r\n" % (e,))
                return self._json(500, {"detail": "Внутренняя ошибка сервера: %s" % e})

            if isinstance(result, api.BinaryResponse):
                headers = {}
                if result.filename:
                    headers["Content-Disposition"] = 'attachment; filename="%s"' % result.filename
                return self._send(200, result.data, result.content_type, headers)
            return self._json(200, result)
        return self._json(404, {"detail": "Метод API не найден: %s %s" % (method, path)})

    def _dispatch(self, method):
        parts = urlsplit(self.path)
        path, query = parts.path, parse_qs(parts.query)
        try:
            if path.startswith("/api/"):
                self._api(method, path, query)
            elif method in ("GET", "HEAD"):
                self._static(path)
            else:
                self._json(405, {"detail": "Метод не поддерживается"})
        except (BrokenPipeError, ConnectionResetError, socket.timeout):
            pass  # клиент закрыл соединение — не ошибка сервиса

    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")


def _tls_context(cert, key):
    # PROTOCOL_TLS_SERVER — Python 3.6+; в 3.5 используем PROTOCOL_SSLv23,
    # который тоже согласует наивысшую доступную версию TLS.
    proto = getattr(ssl, "PROTOCOL_TLS_SERVER", None) or ssl.PROTOCOL_SSLv23
    ctx = ssl.SSLContext(proto)
    # Отключаем устаревшие SSLv2/SSLv3/TLS 1.0/1.1. В Python 3.7+ для этого
    # есть minimum_version; в 3.5–3.6 — флаги OP_NO_* (в новых версиях они
    # помечены устаревшими, поэтому используются только как запасной путь).
    if hasattr(ctx, "minimum_version") and hasattr(ssl, "TLSVersion"):
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    else:
        for flag in ("OP_NO_SSLv2", "OP_NO_SSLv3", "OP_NO_TLSv1", "OP_NO_TLSv1_1"):
            ctx.options |= getattr(ssl, flag, 0)
    ctx.load_cert_chain(cert, key)
    return ctx


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compliance Profile Builder — веб-сервер")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--cert", help="сертификат HTTPS (PEM)")
    parser.add_argument("--key", help="закрытый ключ HTTPS (PEM)")
    args = parser.parse_args(argv)

    if sys.version_info < (3, 5):
        raise SystemExit("Требуется Python 3.5 или новее.")
    if bool(args.cert) != bool(args.key):
        raise SystemExit("Параметры --cert и --key указываются вместе.")

    storage.ensure_dirs()
    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    scheme = "http"
    if args.cert:
        httpd.socket = _tls_context(args.cert, args.key).wrap_socket(httpd.socket, server_side=True)
        scheme = "https"
    sys.stderr.write("Compliance Profile Builder %s: %s://%s:%d/ (Python %s)\n" % (
        VERSION, scheme, args.host, args.port, sys.version.split()[0]))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
