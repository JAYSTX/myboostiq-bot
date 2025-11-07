import os, json, re, asyncio, logging, requests
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)
import config

# ---------- LOG ----------
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
log = logging.getLogger("boostiq-bot")

# ---------- LANGUAGE MEMORY ----------
LANG_FILE = "langs.json"
if not os.path.exists(LANG_FILE):
    json.dump({}, open(LANG_FILE, "w"))
langs = json.load(open(LANG_FILE))
def get_lang(uid): return langs.get(str(uid), "en")
def set_lang(uid, lang): langs[str(uid)] = lang; json.dump(langs, open(LANG_FILE, "w"))

# ---------- UTILS ----------
def now(): return datetime.now(timezone.utc)
def until(days): return now() + timedelta(days=days)
def fmt(dt): return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def check_payment(tx):
    try:
        r = requests.get("https://api.bscscan.com/api", params={
            "module":"account","action":"tokentx",
            "contractaddress":config.USDT_CONTRACT,
            "txhash":tx,"apikey":config.BSC_API_KEY},timeout=15)
        j = r.json()
        if j.get("status")!="1" or not j.get("result"): return False,"No USDT transfers found."
        d=j["result"][0]
        if d["to"].lower()!=config.SUB_WALLET.lower(): return False,"Wrong destination wallet."
        val=int(d["value"])/(10**int(d["tokenDecimal"]))
        if val<config.PRICE_USDT: return False,f"Insufficient amount ({val} USDT)"
        r2=requests.get("https://api.bscscan.com/api",params={
            "module":"transaction","action":"gettxreceiptstatus",
            "txhash":tx,"apikey":config.BSC_API_KEY},timeout=15).json()
        if r2.get("status")!="1" or r2.get("result",{}).get("status")!="1": return False,"TX not confirmed."
        return True,f"Payment verified {val:.2f} USDT."
    except Exception as e: return False,str(e)

# ---------- STORAGE ----------
SUBS_FILE="subs.json"
if not os.path.exists(SUBS_FILE): json.dump({},open(SUBS_FILE,"w"))
def load_subs(): 
    try: return json.load(open(SUBS_FILE))
    except: return {}
def save_subs(d): json.dump(d,open(SUBS_FILE,"w"),indent=2)

# ---------- MENUS ----------
def kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Public Channel",url=f"https://t.me/{str(config.CHANNEL_ID).replace('-100','')}")],
        [InlineKeyboardButton("💬 Alerts Group",url="https://t.me/myboostiqalerts")],
        [InlineKeyboardButton("💎 VIP Group",url="https://t.me/myboostiqVIP")],
        [InlineKeyboardButton("🌐 Official Website",url=config.OFFICIAL_WEB)]
    ])

async def start(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    lang=get_lang(uid)
    name=update.effective_user.first_name
    if lang=="es":
        msg=(f"👋 Bienvenido {name} a <b>My Boost IQ</b>\n"
             f"💥 Donde los +1000 % sí existen.\n\n"
             f"Usa /menu para opciones o /subscribe para VIP (50 USDT, 7 días, 2 pumps).")
    else:
        msg=(f"👋 Welcome {name} to <b>My Boost IQ</b>\n"
             f"💥 Where +1000 % gains are real.\n\n"
             f"Use /menu for options or /subscribe for VIP (50 USDT, 7 days, 2 pumps).")
    await update.message.reply_html(msg,reply_markup=kb())

async def menu(update,ctx): 
    await update.message.reply_text("Menu",reply_markup=kb())

# ---------- LANGUAGE ----------
async def cmd_lang(update:Update,ctx:ContextTypes.DEFAULT_TYPE):
    uid=update.effective_user.id
    args=(ctx.args or [])
    if not args:
        await update.message.reply_text("Usage: /lang en or /lang es")
        return
    lang=args[0].lower()
    if lang not in ("en","es"):
        await update.message.reply_text("Invalid. Use en/es.")
        return
    set_lang(uid,lang)
    await update.message.reply_text(f"Language set to {'English' if lang=='en' else 'Español'}.")

# ---------- SUBSCRIBE ----------
ASK_HASH=1
async def subscribe(update,ctx):
    lang=get_lang(update.effective_user.id)
    if lang=="es":
        msg=(f"💎 Suscripción VIP: {config.PRICE_USDT} USDT por {config.DURATION_DAYS} días (2 pumps)\n"
             f"Red: BSC (BEP20)\nToken: USDT\nWallet: <code>{config.SUB_WALLET}</code>\n\n"
             f"Envía el hash de tu pago para validar.")
    else:
        msg=(f"💎 VIP Subscription: {config.PRICE_USDT} USDT for {config.DURATION_DAYS} days (2 pumps)\n"
             f"Network: BSC (BEP20)\nToken: USDT\nWallet: <code>{config.SUB_WALLET}</code>\n\n"
             f"Send your payment hash to validate.")
    await update.message.reply_html(msg)
    return ASK_HASH

TX_RE=re.compile(r"^0x[a-fA-F0-9]{64}$")
async def on_hash(update,ctx):
    tx=(update.message.text or "").strip()
    if not TX_RE.match(tx):
        await update.message.reply_text("Invalid hash.")
        return ASK_HASH
    ok,detail=await asyncio.to_thread(check_payment,tx)
    if not ok:
        await update.message.reply_text(f"❌ {detail}")
        return ConversationHandler.END
    uid=str(update.effective_user.id)
    data=load_subs(); until=(now()+timedelta(days=config.DURATION_DAYS))
    data[uid]={"until":until.isoformat(),"tx":tx}
    save_subs(data)
    await update.message.reply_text(f"✅ {detail}\nVIP active until {fmt(until)}.")
    await update.message.reply_text("VIP Group → https://t.me/myboostiqVIP")
    return ConversationHandler.END

# ---------- EXPIRE JOB ----------
async def expire_job(app):
    while True:
        try:
            subs=load_subs(); changed=False
            for uid,s in list(subs.items()):
                if now()>datetime.fromisoformat(s["until"]):
                    changed=True; subs.pop(uid)
                    try:
                        await app.bot.send_message(int(uid),"Your VIP subscription has expired.")
                        await app.bot.ban_chat_member(config.VIP_CHAT_ID,int(uid))
                    except Exception as e: log.warning(f"Expire fail {uid}: {e}")
            if changed: save_subs(subs)
        except Exception as e: log.error(f"expire_job error: {e}")
        await asyncio.sleep(3600)

# ---------- MAIN ----------
def build():
    app=ApplicationBuilder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("menu",menu))
    app.add_handler(CommandHandler("lang",cmd_lang))
    sub=ConversationHandler(
        entry_points=[CommandHandler("subscribe",subscribe)],
        states={ASK_HASH:[MessageHandler(filters.TEXT & ~filters.COMMAND,on_hash)]},
        fallbacks=[])
    app.add_handler(sub)
    return app

def main():
    log.info("Starting BoostIQ Bot v2…")
    app=build()
    app.post_init(lambda _: asyncio.create_task(expire_job(app)))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# ---------- KEEP-ALIVE SERVER FOR REPLIT ----------
# Creates a minimal Flask web server so external pingers can keep the bot alive.
from flask import Flask
import threading

app_web = Flask(__name__)

@app_web.route("/")
def home():
    return "BoostIQ Bot v2 alive", 200

def run_web():
    app_web.run(host="0.0.0.0", port=8080)

# Launch the tiny web server in background
threading.Thread(target=run_web, daemon=True).start()
# ---------- END KEEP-ALIVE ----------

if __name__=="__main__":
    main()
