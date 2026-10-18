"""Bot de Telegram con shell, Open Interpreter y tareas de Google.

Preparación local (usa el mismo Python con el que ejecutas el bot):
  python -m pip install python-telegram-bot google-api-python-client google-auth-oauthlib
  mkdir -p ~/.config/another121servant
  # Descarga un cliente OAuth de escritorio y guarda el JSON como:
  # ~/.config/another121servant/google_client.json
  python another121servant_tasks_bot.py --autorizar-tareas

La API de Google Tasks debe estar habilitada en el proyecto de Google Cloud.
La autorización se hace en el navegador local, nunca en Telegram.
"""

import asyncio
import logging
import os
import pty
import re
import signal
import sys
import threading
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

ANSI = re.compile(r"\x1bP.*?\x1b\\|\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-_]|\r", re.S)
GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
PRIORIDAD = re.compile(r"^Prioridad: (10|[1-9])/10(?:\n|$)")
ZONA = ZoneInfo("America/Guatemala")
SCOPES = ["https://www.googleapis.com/auth/tasks"]
DATOS = Path.home() / ".config" / "another121servant"
CLIENTE = DATOS / "google_client.json"
TOKEN_GOOGLE = DATOS / "google_tasks_token.json"
LISTA = "Prioridades Telegram"
LOCK_TOKEN = threading.Lock()

CUF = re.compile(r"\x1b\[(\d*)C")
master = None
pid = None
buf = b""
chat_id = None
flush_task = None

COMANDOS = {
    "oi": ("🤖 Open Interpreter", "~/.local/bin/oi"),
    # Conserva aquí cualquier otro comando de tu bot.
}


def guardar_token(creds):
    DATOS.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(TOKEN_GOOGLE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as archivo:
        os.fchmod(archivo.fileno(), 0o600)
        archivo.write(creds.to_json())


def autorizar_tareas():
    """Se invoca una sola vez en la computadora con --autorizar-tareas."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CLIENTE.is_file():
        raise SystemExit(f"Falta el cliente OAuth: {CLIENTE}")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENTE), SCOPES)
    creds = flow.run_local_server(port=0)
    guardar_token(creds)
    print("Google Tasks autorizado. Ya puedes iniciar el bot.")


def servicio_tareas():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    if not TOKEN_GOOGLE.is_file():
        raise RuntimeError("Primero ejecuta --autorizar-tareas en tu computadora")
    with LOCK_TOKEN:
        creds = Credentials.from_authorized_user_file(str(TOKEN_GOOGLE), SCOPES)
        if not creds.valid:
            if not creds.refresh_token:
                raise RuntimeError("La autorización caducó; vuelve a ejecutar --autorizar-tareas")
            creds.refresh(Request())
            guardar_token(creds)
    return build("tasks", "v1", credentials=creds, cache_discovery=False)


def lista_tareas(service):
    pagina = None
    while True:
        resultado = service.tasklists().list(pageToken=pagina).execute()
        for lista in resultado.get("items", []):
            if lista.get("title") == LISTA:
                return lista["id"]
        pagina = resultado.get("nextPageToken")
        if not pagina:
            break
    return service.tasklists().insert(body={"title": LISTA}).execute()["id"]


def importancia(task):
    match = PRIORIDAD.match(task.get("notes", ""))
    return int(match.group(1)) if match else None


def pendientes(service, list_id):
    items = []
    pagina = None
    while True:
        resultado = service.tasks().list(
            tasklist=list_id, pageToken=pagina, showCompleted=False,
            showHidden=False, showDeleted=False, maxResults=100,
        ).execute()
        items.extend(
            task for task in resultado.get("items", [])
            if task.get("status") == "needsAction" and importancia(task) is not None
        )
        pagina = resultado.get("nextPageToken")
        if not pagina:
            break
    return sorted(items, key=lambda task: (importancia(task), task.get("title", "").casefold()))


def crear_tarea(titulo, valor):
    service = servicio_tareas()
    list_id = lista_tareas(service)
    fecha = datetime.now(ZONA).date().isoformat()
    task = service.tasks().insert(tasklist=list_id, body={
        "title": titulo,
        "notes": f"Prioridad: {valor}/10",
        "due": f"{fecha}T00:00:00.000Z",
        "status": "needsAction",
    }).execute()
    # Ordena la lista de Google Tasks además de la vista de Telegram.
    anterior = None
    for actual in pendientes(service, list_id):
        parametros = {"tasklist": list_id, "task": actual["id"]}
        if anterior is not None:
            parametros["previous"] = anterior
        service.tasks().move(**parametros).execute()
        anterior = actual["id"]
    return task


def consultar_pendientes():
    service = servicio_tareas()
    return pendientes(service, lista_tareas(service))


def completar_tarea(task_id):
    service = servicio_tareas()
    list_id = lista_tareas(service)
    task = service.tasks().get(tasklist=list_id, task=task_id).execute()
    if importancia(task) is None or task.get("status") != "needsAction":
        return False
    service.tasks().patch(
        tasklist=list_id, task=task_id, body={"status": "completed"}
    ).execute()
    return True


def start_shell():
    global master, pid
    pid, master = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "dumb"
        os.environ["PS1"] = "$ "
        os.environ["POWERLEVEL9K_DISABLE_CONFIGURATION_WIZARD"] = "true"
        os.chdir(os.path.expanduser("~"))
        os.execvp("bash", ["bash", "--norc", "--noprofile", "-i"])


async def flush(app):
    global buf
    await asyncio.sleep(0.8)
    salida = buf.decode(errors="replace")
    buf = b""
    salida = GOOGLE_KEY.sub("[CLAVE_OCULTA]", ANSI.sub("", salida)).strip()
    if not salida or chat_id is None:
        return
    for indice in range(0, len(salida), 4000):
        await app.bot.send_message(chat_id, salida[indice:indice + 4000])


def on_data(app):
    global buf, flush_task
    try:
        data = os.read(master, 4096)
    except OSError:
        asyncio.get_running_loop().remove_reader(master)
        return
    buf += data
    if chat_id and (flush_task is None or flush_task.done()):
        flush_task = asyncio.create_task(flush(app))


def attach(app):
    asyncio.get_running_loop().add_reader(master, on_data, app)


async def post_init(app):
    start_shell()
    attach(app)
    await app.bot.set_my_commands([
        BotCommand("commands", "Lista de comandos y tareas"),
        BotCommand("cancel", "Cancelar una tarea nueva"),
        BotCommand("c", "Ctrl+C"),
        BotCommand("d", "Ctrl+D"),
        BotCommand("reset", "Reiniciar shell"),
    ])


def allowed(update):
    return bool(update.effective_user and update.effective_user.id == int(os.environ["TG_USER_ID"]))


async def text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global chat_id
    if not allowed(update):
        return
    chat_id = update.effective_chat.id
    nuevo = ctx.user_data.get("nueva_tarea")
    if nuevo and nuevo["chat_id"] == chat_id:
        entrada = update.message.text.strip()
        if nuevo["paso"] == "titulo":
            if not entrada or len(entrada) > 200:
                await update.message.reply_text("Escribe un nombre de 1 a 200 caracteres.")
                return
            nuevo["titulo"] = entrada
            nuevo["paso"] = "valor"
            await update.message.reply_text(
                f"Importancia de «{entrada}»: escribe un número del 1 al 10 "
                "(1 = menor importancia, 10 = mayor)."
            )
            return
        if not entrada.isdecimal() or not 1 <= int(entrada) <= 10:
            await update.message.reply_text("Escribe un número entero del 1 al 10, o /cancel.")
            return
        try:
            task = await asyncio.to_thread(crear_tarea, nuevo["titulo"], int(entrada))
        except Exception:
            logging.exception("No se pudo crear la tarea")
            await update.message.reply_text("No pude guardarla en Google Tasks. Revisa el registro del bot.")
            return
        ctx.user_data.pop("nueva_tarea", None)
        await update.message.reply_text(
            f"✅ Guardada para hoy: {task['title']} · importancia {entrada}/10. "
            "Puedes verla en Google Calendar y completarla desde Pendientes."
        )
        return
    os.write(master, (update.message.text + "\n").encode())


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if allowed(update):
        ctx.user_data.pop("nueva_tarea", None)
        await update.message.reply_text("Creación de tarea cancelada.")


async def ctrl_c(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global chat_id
    if allowed(update):
        chat_id = update.effective_chat.id
        os.write(master, b"\x03")


async def ctrl_d(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global chat_id
    if allowed(update):
        chat_id = update.effective_chat.id
        os.write(master, b"\x04")


async def reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global chat_id
    if not allowed(update):
        return
    chat_id = update.effective_chat.id
    asyncio.get_running_loop().remove_reader(master)
    try:
        os.kill(pid, signal.SIGKILL)
        os.waitpid(pid, 0)
        os.close(master)
    except OSError:
        pass
    start_shell()
    attach(ctx.application)
    await update.message.reply_text("Shell reiniciada")


async def commands(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return
    botones = [
        [InlineKeyboardButton(nombre, callback_data=f"cmd:{clave}")]
        for clave, (nombre, _) in COMANDOS.items()
    ]
    botones.extend([
        [InlineKeyboardButton("➕ Nueva tarea", callback_data="task:new")],
        [InlineKeyboardButton("📋 Pendientes (1 → 10)", callback_data="task:page:0")],
        [InlineKeyboardButton("📅 Google Calendar", url="https://calendar.google.com/calendar/")],
    ])
    await update.message.reply_text("Comandos:", reply_markup=InlineKeyboardMarkup(botones))


async def mostrar_pendientes(ctx, mensaje, pagina=0):
    items = await asyncio.to_thread(consultar_pendientes)
    if not items:
        ctx.user_data["tareas_visibles"] = []
        await mensaje.reply_text("No tienes tareas pendientes en Prioridades Telegram.")
        return
    ctx.user_data["tareas_visibles"] = [item["id"] for item in items]
    cantidad = 10
    pagina = max(0, min(pagina, (len(items) - 1) // cantidad))
    visibles = items[pagina * cantidad:(pagina + 1) * cantidad]
    lineas = [f"📋 Pendientes · prioridad menor → mayor ({len(items)} en total):"]
    botones = []
    for idx, task in enumerate(visibles, start=pagina * cantidad):
        nombre = task.get("title", "(Sin título)")
        lineas.append(f"{idx + 1}. [{importancia(task)}/10] {nombre[:160]}")
        botones.append([InlineKeyboardButton(
            f"✅ {idx + 1}. {nombre[:28]}", callback_data=f"task:done:{idx}"
        )])
    navegacion = []
    if pagina:
        navegacion.append(InlineKeyboardButton("◀️", callback_data=f"task:page:{pagina - 1}"))
    if (pagina + 1) * cantidad < len(items):
        navegacion.append(InlineKeyboardButton("▶️", callback_data=f"task:page:{pagina + 1}"))
    if navegacion:
        botones.append(navegacion)
    await mensaje.reply_text("\n".join(lineas), reply_markup=InlineKeyboardMarkup(botones))


async def boton(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global chat_id
    if not allowed(update):
        return
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat_id
    dato = q.data
    if dato.startswith("cmd:"):
        clave = dato.removeprefix("cmd:")
        if clave in COMANDOS:
            os.write(master, (COMANDOS[clave][1] + "\n").encode())
        return
    if dato == "task:new":
        ctx.user_data["nueva_tarea"] = {"chat_id": chat_id, "paso": "titulo"}
        await q.message.reply_text("¿Cómo se llama la tarea? Escríbela aquí, o /cancel.")
        return
    if dato.startswith("task:page:"):
        try:
            pagina = int(dato.rsplit(":", 1)[1])
            await mostrar_pendientes(ctx, q.message, pagina)
        except Exception:
            logging.exception("No se pudieron consultar las tareas")
            await q.message.reply_text("No pude consultar Google Tasks. Revisa el registro del bot.")
        return
    if dato.startswith("task:done:"):
        try:
            indice = int(dato.rsplit(":", 1)[1])
            ids = ctx.user_data.get("tareas_visibles", [])
            if not 0 <= indice < len(ids):
                await q.message.reply_text("La lista caducó. Pulsa Pendientes de nuevo.")
                return
            completada = await asyncio.to_thread(completar_tarea, ids[indice])
            await q.message.reply_text(
                "✅ Tarea completada." if completada else "Esa tarea ya no está pendiente."
            )
        except Exception:
            logging.exception("No se pudo completar la tarea")
            await q.message.reply_text("No pude completarla. Revisa el registro del bot.")


def main():
    if sys.argv[1:] == ["--autorizar-tareas"]:
        autorizar_tareas()
        return
    if sys.argv[1:]:
        raise SystemExit("Uso: python bot.py [--autorizar-tareas]")
    token = os.environ["TG_TOKEN"]
    os.environ["TG_USER_ID"]  # Comprueba que exista antes de arrancar.
    app = ApplicationBuilder().token(token).post_init(post_init).build()
    app.add_handler(CommandHandler("commands", commands))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(boton, pattern=r"^(?:cmd:|task:)"))
    app.add_handler(CommandHandler("c", ctrl_c))
    app.add_handler(CommandHandler("d", ctrl_d))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))
    app.run_polling()


if __name__ == "__main__":
    main()
