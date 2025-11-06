import os, json, time, asyncio, logging, re
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import requests
from dotenv import load_dotenv
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    CallbackQueryHandler, ContextTypes, filters
)

import config

# ----------------- LOGS -----------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
log = logging.getLogger(__name__)

# ----------------- ENV -----------------
load_dotenv()
if not config.BOT_TOKEN or not config.BSC_API_KEY:
    log.error("Faltan variables: TELEGRAM_BOT_TOKEN o BSC_API_KEY")
    raise SystemExit(1)

# ----------------- PERSISTENCIA SIMPLE -----------------
SUBS_FILE = "subs.json"   # { user_id: { "until": ISO, "tx": "..."} }
def load_subs() -> Dict[str, Any]:
    if not os.path.exists(SUBS_FILE): return {}
    try:
        return json.load(open(SUBS_FILE, "r", encoding="utf-8"))
    except Exception:
        return {}

def save_subs(data: Dict[str, Any]):
    json.dump(data, open(SUBS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

subs = load_subs()

# ----------------- L10N -----------------
def t(lang: str, es: str, en: str) -> str:
    lang = (lang or "").lower()
    if lang.startswith("es"): return es
    if lang.startswith("en"): return en
    return f"{es}\n\n{en}"

def menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    es = [
        [InlineKeyboardButton("📢 Canal Público", url=f"https://t.me/{str(config.CHANNEL_ID).replace('-100','')}")],
        [InlineKeyboardButton("💬 Grupo de Alertas", url=f"https://t.me/{config.ALERTS_GROUP_USER.lstrip('@')}")],
        [InlineKeyboardButton("💎 Grupo VIP", url=f"https://t.me/{config.VIP_GROUP_USER.lstrip('@')}")],
        [InlineKeyboardButton("🌐 Web Oficial", url=config.OFFICIAL_WEB)],
    ]
    en = [
        [InlineKeyboardButton("📢 Public Channel", url=f"https://t.me/{str(config.CHANNEL_ID).replace('-100','')}")],
        [InlineKeyboardButton("💬 Alerts Group", url=f"https://t.me/{config.ALERTS_GROUP_USER.lstrip('@')}")],
        [InlineKeyboardButton("💎 VIP Group", url=f"https://t.me/{config.VIP_GROUP_USER.lstrip('@')}")],
        [InlineKeyboardButton("🌐 Official Website", url=config.OFFICIAL_WEB)],
    ]
    if (lang or "").lower().startswith("es"): return InlineKeyboardMarkup(es)
    if (lang or "").lower().startswith("en"): return InlineKeyboardMarkup(en)
    # mixto
    mixed = [
        [InlineKeyboardButton("📢 Canal / Channel", url=f"https://t.me/{str(config.CHANNEL_ID).replace('-100','')}")],
        [InlineKeyboardButton("💬 Alertas / Alerts", url=f"https://t.me/{config.ALERTS_GROUP_USER.lstrip('@')}")],
        [InlineKeyboardButton("💎 VIP", url=f"https://t.me/{config.VIP_GROUP_USER.lstrip('@')}")],
        [InlineKeyboardButton("🌐 Web / Website", url=config.OFFICIAL_WEB)],
    ]
    return InlineKeyboardMarkup(mixed)

# ----------------- HELPERS -----------------
def is_owner(user_id: int) -> bool:
    return int(user_id) == int(config.OWNER_ID)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def until_from_now(days: int) -> datetime:
    return now_utc() + timedelta(days=days)

def fmt_dt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

# BscScan verificación de USDT (BEP20) -> destinatario SUB_WALLET y cantidad >= PRICE_USDT
def verify_usdt_payment(tx: str) -> tuple[bool, str]:
    try:
        # 1) detalle de token transfers para TX usando 'tokentx' + filtrar por nuestro contrato USDT
        r = requests.get("https://api.bscscan.com/api", params={
            "module": "account",
            "action": "tokentx",
            "contractaddress": config.USDT_CONTRACT,
            "txhash": tx,
            "apikey": config.BSC_API_KEY
        }, timeout=15)
        data = r.json()

        if data.get("status") != "1" or not data.get("result"):
            return False, "No hay transferencias USDT en esa TX."

        rec = data["result"][0]  # debería ser único para esa tx y contrato
        to_addr = rec.get("to", "").lower()
        if to_addr != config.SUB_WALLET.lower():
            return False, "El destino no coincide con la wallet de suscripción."

        # cantidad
        decimals = int(rec.get("tokenDecimal", "18"))
        value = int(rec.get("value", "0")) / (10 ** decimals)
        if value + 1e-12 < config.PRICE_USDT:
            return False, f"Monto insuficiente: {value} USDT < {config.PRICE_USDT} USDT."

        # 2) estado de recibo
        r2 = requests.get("https://api.bscscan.com/api", params={
            "module": "transaction",
            "action": "gettxreceiptstatus",
            "txhash": tx,
            "apikey": config.BSC_API_KEY
        }, timeout=15)
        j2 = r2.json()
        if j2.get("status") != "1" or j2.get("result", {}).get("status") != "1":
            return False, "La transacción no está confirmada (receipt)."

        return True, f"Pago verificado {value:.2f} USDT."
    except Exception as e:
        return False, f"Error verificando en BscScan: {e}"

async def post_to_targets(context: ContextTypes.DEFAULT_TYPE, text: Optional[str] = None,
                          photo_file_id: Optional[str] = None,
                          video_file_id: Optional[str] = None):
    targets = [config.CHANNEL_ID, config.ALERTS_GROUP_USER, config.VIP_GROUP_USER]
    for target in targets:
        try:
            if video_file_id:
                await context.bot.send_video(chat_id=target, video=video_file_id, caption=text or "")
            elif photo_file_id:
                await context.bot.send_photo(chat_id=target, photo=photo_file_id, caption=text or "")
            else:
                await context.bot.send_message(chat_id=target, text=text or "")
            await asyncio.sleep(0.4)
        except Exception as e:
            log.error(f"Error publicando en {target}: {e}")

# ----------------- /start -----------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = (user.language_code or "es")
    name = user.first_name or user.username or "Trader"

    msg = t(
        lang,
        f"👋 Bienvenido {name} a **My Boost IQ**\n"
        f"💥 Donde los +1000% sí existen.\n\n"
        f"Usa /menu para ver opciones y /subscribe para VIP (50 USDT, 7 días, 2 pumps).\n"
        f"Web: {config.OFFICIAL_WEB}",

        f"👋 Welcome {name} to **My Boost IQ**\n"
        f"💥 Where +1000% gains are real.\n\n"
        f"Use /menu for options and /subscribe for VIP (50 USDT, 7 days, 2 pumps).\n"
        f"Web: {config.OFFICIAL_WEB}"
    )
    await update.message.reply_markdown(msg, reply_markup=menu_keyboard(lang))

# ----------------- /menu -----------------
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = (update.effective_user.language_code or "es")
    title = t(lang, "🟩 Menú", "🟩 Menu")
    await update.message.reply_text(title, reply_markup=menu_keyboard(lang))

# ----------------- /status -----------------
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    lang = (update.effective_user.language_code or "es")
    s = subs.get(uid)
    if not s:
        await update.message.reply_text(t(lang, "No tienes una suscripción activa.", "You have no active subscription."))
        return
    until = datetime.fromisoformat(s["until"])
    left = until - now_utc()
    days = max(0, left.days)
    hours = max(0, int(left.seconds/3600))
    await update.message.reply_text(
        t(lang,
          f"Tu suscripción VIP expira el {fmt_dt(until)}. Tiempo restante: {days}d {hours}h.",
          f"Your VIP subscription expires on {fmt_dt(until)}. Time left: {days}d {hours}h.")
    )

# ----------------- /subscribe (flujo) -----------------
ASK_HASH = 1

async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = (update.effective_user.language_code or "es")
    info = t(
        lang,
        f"💎 Suscripción VIP: 50 USDT por {config.DURATION_DAYS} días (2 pumps).\n"
        f"Red: BSC (BEP20)\n"
        f"Token: USDT\n"
        f"Wallet: `{config.SUB_WALLET}`\n\n"
        f"Envía el **hash** de tu pago para validar.",
        f"💎 VIP Subscription: 50 USDT for {config.DURATION_DAYS} days (2 pumps).\n"
        f"Network: BSC (BEP20)\n"
        f"Token: USDT\n"
        f"Wallet: `{config.SUB_WALLET}`\n\n"
        f"Send your payment **tx hash** to validate."
    )
    await update.message.reply_markdown(info)
    await update.message.reply_text(t(lang, "Pega el hash aquí:", "Paste the tx hash here:"))
    return ASK_HASH

TX_RE = re.compile(r"^0x[a-fA-F0-9]{64}$")

async def on_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = (update.effective_user.language_code or "es")
    tx = (update.message.text or "").strip()
    if not TX_RE.match(tx):
        await update.message.reply_text(t(lang, "Hash inválido. Intenta de nuevo.", "Invalid hash. Try again."))
        return ASK_HASH

    await update.message.reply_text(t(lang, "Validando pago en BscScan...", "Validating payment on BscScan..."))
    ok, detail = await asyncio.to_thread(verify_usdt_payment, tx)
    if not ok:
        await update.message.reply_text(t(lang, f"❌ Pago no válido: {detail}", f"❌ Payment invalid: {detail}"))
        return ConversationHandler.END

    # activar suscripción
    uid = str(update.effective_user.id)
    until = until_from_now(config.DURATION_DAYS)
    subs[uid] = {"until": until.isoformat(), "tx": tx}
    save_subs(subs)

    await update.message.reply_text(t(lang, f"✅ {detail}\nVIP activo hasta {fmt_dt(until)}.",
                                         f"✅ {detail}\nVIP active until {fmt_dt(until)}."))

    # invitar a VIP (enlace por username)
    vip_link = f"https://t.me/{config.VIP_GROUP_USER.lstrip('@')}"
    await update.message.reply_text(t(lang,
        f"Accede al Grupo VIP: {vip_link}",
        f"Access VIP Group: {vip_link}"))
    return ConversationHandler.END

async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado / Cancelled.")
    return ConversationHandler.END

# ----------------- /announce (solo OWNER) -----------------
ANN_DATE, ANN_TIME, ANN_CONTENT, ANN_CONFIRM = range(4)

def owner_required(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if not is_owner(uid):
            await update.message.reply_text("Unauthorized.")
            return ConversationHandler.END if isinstance(update, Update) else None
        return await func(update, context)
    return wrapper

@owner_required
async def cmd_announce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🇪🇸 Escribe la fecha (ej: 2025-11-07)\n🇬🇧 Enter date (YYYY-MM-DD)")
    return ANN_DATE

async def ann_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = (update.message.text or "").strip()
    await update.message.reply_text("🇪🇸 Escribe la hora (ej: 18:00 UTC)\n🇬🇧 Enter time (e.g. 18:00 UTC)")
    return ANN_TIME

async def ann_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["time"] = (update.message.text or "").strip()
    await update.message.reply_text("🇪🇸 Envía el texto o adjunta el flyer/video.\n🇬🇧 Send the text or attach flyer/video.")
    return ANN_CONTENT

async def ann_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.caption or update.message.text or ""
    context.user_data["text"] = text

    # guardar media opcional
    photo_id = None
    video_id = None
    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
    if update.message.video:
        video_id = update.message.video.file_id
    context.user_data["photo"] = photo_id
    context.user_data["video"] = video_id

    d = context.user_data.get("date")
    t = context.user_data.get("time")

    preview = (
        "🚀 My Boost IQ Official Announcement\n\n"
        f"🇪🇸 Próximo Pump\nFecha: {d}\nHora: {t}\nToken revelado al lanzamiento.\n\n"
        f"🇬🇧 Next Pump\nDate: {d}\nTime: {t}\nToken revealed at launch.\n\n"
        f"🌐 {config.OFFICIAL_WEB}"
    )
    await update.message.reply_text(preview + "\n\nPublicar? (yes/no)")
    return ANN_CONFIRM

async def ann_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conf = (update.message.text or "").strip().lower()
    if conf not in ("y", "yes", "si", "sí"):
        await update.message.reply_text("Cancelado.")
        return ConversationHandler.END

    text = context.user_data.get("text") or ""
    photo = context.user_data.get("photo")
    video = context.user_data.get("video")
    d = context.user_data.get("date")
    tm = context.user_data.get("time")

    final_text = (
        "🚀 **My Boost IQ Official Announcement**\n\n"
        f"🇪🇸 *Próximo Pump*\n"
        f"🔥 Fecha: {d}\n⏰ Hora: {tm}\n💥 Token revelado al lanzamiento.\n\n"
        f"🇬🇧 *Next Pump*\n"
        f"🔥 Date: {d}\n⏰ Time: {tm}\n💥 Token revealed at launch.\n\n"
        f"{text}\n\n"
        f"🌐 {config.OFFICIAL_WEB}"
    )

    await post_to_targets(context, text=final_text, photo_file_id=photo, video_file_id=video)
    await update.message.reply_text("Publicado en canal y grupos.")
    context.user_data.clear()
    return ConversationHandler.END

# ----------------- TAREAS: limpieza de suscripciones vencidas -----------------
async def expire_job(app):
    while True:
        try:
            changed = False
            for uid, data in list(subs.items()):
                until = datetime.fromisoformat(data["until"])
                if now_utc() > until:
                    subs.pop(uid, None)
                    changed = True
                    try:
                        # intento de notificar al usuario
                        await app.bot.send_message(chat_id=int(uid),
                            text="Tu suscripción VIP ha expirado. Renueva con /subscribe.")
                    except Exception:
                        pass
            if changed:
                save_subs(subs)
        except Exception as e:
            log.error(f"expire_job error: {e}")
        await asyncio.sleep(3600)  # cada hora

# ----------------- /help -----------------
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start /menu /subscribe /status\n"
        "Admin: /announce"
    )

# ----------------- MAIN -----------------
def build_application():
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()

    # comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("help", cmd_help))

    # subscribe flow
    sub_conv = ConversationHandler(
        entry_points=[CommandHandler("subscribe", cmd_subscribe)],
        states={
            ASK_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_hash)]
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
        allow_reentry=True
    )
    app.add_handler(sub_conv)

    # announce flow (owner only)
    ann_conv = ConversationHandler(
        entry_points=[CommandHandler("announce", cmd_announce)],
        states={
            ANN_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_date)],
            ANN_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_time)],
            ANN_CONTENT: [MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO) & ~filters.COMMAND, ann_content)],
            ANN_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, ann_confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
        allow_reentry=True
    )
    app.add_handler(ann_conv)

    return app

def main():
    log.info("Starting MyBoostIQ MasterBot…")
    app = build_application()
    # job de expiración
    app.post_init(lambda _: asyncio.create_task(expire_job(app)))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
