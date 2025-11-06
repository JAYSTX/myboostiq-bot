#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
myBoostiq Telegram Bot
Monitorea boosts y envía alertas VIP y públicas
"""

import os
import re
import time
import logging
import threading
import requests
from datetime import datetime
from typing import Optional, Dict, List
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variables de entorno
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
VIP_CHAT_ID = os.getenv('VIP_CHAT_ID')
PUBLIC_CHAT_ID = os.getenv('PUBLIC_CHAT_ID')
API_BASE_URL = os.getenv('API_BASE_URL', 'https://myboostiq-api-6do.pages.dev')
ADMIN_TOKEN = os.getenv('ADMIN_TOKEN', 'MyBoost_IQ_1009')

# Estado global del bot
class BotState:
    def __init__(self):
        self.last_boost_id: Optional[int] = None
        self.vip_alert_sent: bool = False
        self.public_alert_sent: bool = False
        self.application: Optional[Application] = None
        self.user_wallets: Dict[int, str] = {}  # user_id -> wallet
        
bot_state = BotState()


# ============================================
# UTILIDADES DE API
# ============================================

def validate_wallet(wallet: str) -> bool:
    """Valida formato de wallet (0x + 40 caracteres hexadecimales)"""
    pattern = r'^0x[a-fA-F0-9]{40}$'
    return bool(re.match(pattern, wallet))


def get_api_status() -> Optional[Dict]:
    """Obtiene el estado actual del boost desde la API"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/status",
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting API status: {e}")
        return None


def get_whitelist() -> List[str]:
    """Obtiene la lista de wallets VIP"""
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/whitelist",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get('whitelist', [])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error getting whitelist: {e}")
        return []


def add_to_whitelist(wallet: str) -> bool:
    """Agrega una wallet a la whitelist"""
    try:
        headers = {
            'Authorization': f'Bearer {ADMIN_TOKEN}',
            'Content-Type': 'application/json'
        }
        data = {
            'action': 'add_whitelist',
            'wallet_address': wallet
        }
        response = requests.post(
            f"{API_BASE_URL}/api/admin",
            json=data,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error adding to whitelist: {e}")
        return False


def remove_from_whitelist(wallet: str) -> bool:
    """Elimina una wallet de la whitelist"""
    try:
        headers = {
            'Authorization': f'Bearer {ADMIN_TOKEN}',
            'Content-Type': 'application/json'
        }
        data = {
            'action': 'remove_whitelist',
            'wallet_address': wallet
        }
        response = requests.post(
            f"{API_BASE_URL}/api/admin",
            json=data,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error removing from whitelist: {e}")
        return False


# ============================================
# COMANDOS DEL BOT
# ============================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start - Mensaje de bienvenida"""
    welcome_message = (
        "🚀 *Welcome to myBoostiq VIP Bot!*\n\n"
        "Get early access to boost alerts and maximize your profits!\n\n"
        "💎 *VIP BENEFITS:*\n"
        "• 2 Pumps per week\n"
        "• Alerts 5 minutes BEFORE boost starts\n"
        "• Buy signal 5 min early\n"
        "• Sell signal 5 min early\n"
        "• Exclusive VIP channel access\n\n"
        "💰 *SUBSCRIPTION:*\n"
        "• 50 USDT per week (Monday-Sunday)\n"
        "• Payment: BEP-20 (BSC Network)\n\n"
        "*To subscribe:*\n"
        "1️⃣ Use `/subscribe` to see payment instructions\n"
        "2️⃣ Send 50 USDT to our wallet\n"
        "3️⃣ Register with `/register 0xYOUR_WALLET`\n\n"
        "*Commands:*\n"
        "• `/subscribe` - Payment instructions\n"
        "• `/register` - Register as VIP\n"
        "• `/check` - Verify VIP status\n"
        "• `/help` - Show all commands\n\n"
        "🌐 Visit: https://myboostiq.app"
    )
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help - Muestra ayuda"""
    help_message = (
        "📚 *myBoostiq Bot Commands*\n\n"
        "*Subscription:*\n"
        "• `/subscribe` - View payment instructions\n"
        "• `/register 0xWALLET` - Register as VIP after payment\n"
        "• `/unregister` - Cancel VIP subscription\n\n"
        "*Status:*\n"
        "• `/check` - Check if you're VIP\n\n"
        "*Information:*\n"
        "• `/start` - Show welcome message\n"
        "• `/help` - Show this help\n\n"
        "💎 *VIP BENEFITS:*\n"
        "✅ 2 Pumps per week guaranteed\n"
        "✅ Buy alerts 5 minutes before public\n"
        "✅ Sell alerts 5 minutes before public\n"
        "✅ Exclusive VIP channel\n"
        "✅ Maximum profit potential\n\n"
        "💰 *SUBSCRIPTION:*\n"
        "• 50 USDT/week (Mon-Sun)\n"
        "• BEP-20 Network (BSC)\n\n"
        "🌐 https://myboostiq.app"
    )
    await update.message.reply_text(
        help_message,
        parse_mode='Markdown'
    )


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /subscribe - Muestra instrucciones de pago"""
    subscribe_message = (
        "💎 *VIP SUBSCRIPTION - myBoostiq*\n\n"
        "🎯 *BENEFITS:*\n"
        "• 2 Pumps guaranteed per week\n"
        "• Buy signals 5 minutes EARLY\n"
        "• Sell signals 5 minutes EARLY\n"
        "• Exclusive VIP alerts\n"
        "• Maximum profit advantage\n\n"
        "💰 *PAYMENT DETAILS:*\n\n"
        "*Amount:* 50 USDT\n"
        "*Period:* Weekly (Monday to Sunday)\n"
        "*Network:* BEP-20 (Binance Smart Chain)\n\n"
        "📍 *Send payment to:*\n"
        "`0xbad5eebd86acebf1a9457ef881b0e22a1fb5b56d`\n\n"
        "⚠️ *IMPORTANT:*\n"
        "• Use BEP-20 network only (BSC)\n"
        "• Send exactly 50 USDT\n"
        "• First subscription is full week (even if you start mid-week)\n"
        "• Renewal: Every Monday\n\n"
        "✅ *AFTER PAYMENT:*\n"
        "1️⃣ Register with: `/register 0xYOUR_WALLET`\n"
        "2️⃣ You'll be added to VIP within minutes\n"
        "3️⃣ Start receiving early alerts!\n\n"
        "🔍 *Verify payment on:*\n"
        "[BscScan](https://bscscan.com/address/0xbad5eebd86acebf1a9457ef881b0e22a1fb5b56d)\n\n"
        "📞 Support: Contact admin if issues\n\n"
        "🌐 https://myboostiq.app"
    )
    await update.message.reply_text(
        subscribe_message,
        parse_mode='Markdown',
        disable_web_page_preview=False
    )


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /register - Registra wallet como VIP"""
    user_id = update.effective_user.id
    
    # Verificar que se proporcionó una wallet
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ *Usage:* `/register 0xYOUR_WALLET`\n\n"
            "Example:\n"
            "`/register 0x1234567890123456789012345678901234567890`\n\n"
            "⚠️ *Before registering:*\n"
            "Make sure you've sent 50 USDT to:\n"
            "`0xbad5eebd86acebf1a9457ef881b0e22a1fb5b56d`\n\n"
            "Use `/subscribe` for payment details.",
            parse_mode='Markdown'
        )
        return
    
    wallet = context.args[0].strip()
    
    # Validar formato de wallet
    if not validate_wallet(wallet):
        await update.message.reply_text(
            "❌ *Invalid wallet format!*\n\n"
            "Wallet must be:\n"
            "• Start with `0x`\n"
            "• Have exactly 40 hexadecimal characters\n\n"
            "Example:\n"
            "`0x1234567890123456789012345678901234567890`",
            parse_mode='Markdown'
        )
        return
    
    # Agregar a whitelist via API
    await update.message.reply_text(
        "⏳ *Registering wallet...*\n\n"
        "⚠️ Make sure you've sent 50 USDT payment first!",
        parse_mode='Markdown'
    )
    
    success = add_to_whitelist(wallet)
    
    if success:
        bot_state.user_wallets[user_id] = wallet
        await update.message.reply_text(
            f"✅ *Successfully registered as VIP!*\n\n"
            f"Wallet: `{wallet}`\n\n"
            f"💎 *Your VIP benefits:*\n"
            f"• 2 Pumps per week\n"
            f"• Buy alerts 5 minutes early\n"
            f"• Sell alerts 5 minutes early\n"
            f"• Exclusive VIP channel\n\n"
            f"🔔 You'll now receive early boost alerts!\n\n"
            f"📅 *Subscription:* Weekly (Mon-Sun)\n"
            f"💰 *Next payment:* Next Monday (50 USDT)\n\n"
            f"🚀 Welcome to myBoostiq VIP!",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} registered wallet: {wallet}")
    else:
        await update.message.reply_text(
            "❌ *Registration failed!*\n\n"
            "There was an error connecting to the API.\n"
            "Please try again later or contact support.",
            parse_mode='Markdown'
        )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /check - Verifica status VIP"""
    user_id = update.effective_user.id
    
    # Obtener wallet del usuario si la tiene guardada
    wallet = bot_state.user_wallets.get(user_id)
    
    if not wallet:
        await update.message.reply_text(
            "❌ *Not registered as VIP*\n\n"
            "Use `/register 0xYOUR_WALLET` to become VIP!",
            parse_mode='Markdown'
        )
        return
    
    # Verificar en whitelist
    await update.message.reply_text("⏳ *Checking VIP status...*", parse_mode='Markdown')
    
    whitelist = get_whitelist()
    
    if wallet.lower() in [w.lower() for w in whitelist]:
        await update.message.reply_text(
            f"✅ *VIP STATUS: ACTIVE*\n\n"
            f"Wallet: `{wallet}`\n\n"
            f"You're receiving early boost alerts! 🎯",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ *VIP STATUS: INACTIVE*\n\n"
            f"Wallet: `{wallet}`\n\n"
            f"Your wallet is not in the VIP list.\n"
            f"Contact support if this is an error.",
            parse_mode='Markdown'
        )


async def unregister_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /unregister - Elimina wallet de VIP"""
    user_id = update.effective_user.id
    
    wallet = bot_state.user_wallets.get(user_id)
    
    if not wallet:
        await update.message.reply_text(
            "❌ You don't have a wallet registered.",
            parse_mode='Markdown'
        )
        return
    
    await update.message.reply_text("⏳ *Removing VIP status...*", parse_mode='Markdown')
    
    success = remove_from_whitelist(wallet)
    
    if success:
        del bot_state.user_wallets[user_id]
        await update.message.reply_text(
            f"✅ *VIP status removed*\n\n"
            f"Wallet `{wallet}` is no longer VIP.\n\n"
            f"You can register again anytime with `/register`",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} unregistered wallet: {wallet}")
    else:
        await update.message.reply_text(
            "❌ *Error removing VIP status*\n\n"
            "Please try again later.",
            parse_mode='Markdown'
        )


# ============================================
# ALERTAS
# ============================================

async def send_vip_alert(boost_data: Dict):
    """Envía alerta a grupo VIP"""
    try:
        pair_symbol = boost_data.get('pair_symbol', 'Unknown')
        contract = boost_data.get('pair', 'Unknown')
        start_time = boost_data.get('start_time', 0)
        
        # Calcular minutos restantes
        now = int(time.time())
        minutes_left = max(0, (start_time - now) // 60)
        
        # Crear links
        dexscreener_link = f"https://dexscreener.com/bsc/{contract}"
        
        message = (
            "🚨 *VIP BOOST ALERT* 🚨\n\n"
            f"*Pair:* `{pair_symbol}`\n"
            f"*Contract:* `{contract}`\n"
            f"*Starts in:* {minutes_left} minutes\n\n"
            f"📊 [Chart]({dexscreener_link})\n"
            f"🌐 [Join Boost](https://myboostiq.app)\n\n"
            f"⏰ *Prepare your position NOW!*"
        )
        
        await bot_state.application.bot.send_message(
            chat_id=VIP_CHAT_ID,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        
        logger.info(f"VIP alert sent for boost {boost_data.get('id')}")
        bot_state.vip_alert_sent = True
        
    except Exception as e:
        logger.error(f"Error sending VIP alert: {e}")


async def send_public_alert(boost_data: Dict):
    """Envía alerta al grupo público"""
    try:
        pair_symbol = boost_data.get('pair_symbol', 'Unknown')
        status = boost_data.get('status', 'Unknown').upper()
        
        message = (
            "🔥 *BOOST LIVE NOW!*\n\n"
            f"*Pair:* `{pair_symbol}`\n"
            f"*Phase:* {status}\n"
            f"*Status:* ACTIVE ✅\n\n"
            f"🌐 [Join at myBoostiq](https://myboostiq.app)\n\n"
            f"⚡ *ACT FAST!*"
        )
        
        await bot_state.application.bot.send_message(
            chat_id=PUBLIC_CHAT_ID,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=False
        )
        
        logger.info(f"Public alert sent for boost {boost_data.get('id')}")
        bot_state.public_alert_sent = True
        
    except Exception as e:
        logger.error(f"Error sending public alert: {e}")


# ============================================
# MONITORING LOOP
# ============================================

def monitoring_loop():
    """Loop principal de monitoreo (corre en background)"""
    logger.info("Starting monitoring loop...")
    
    while True:
        try:
            # Obtener estado actual
            status = get_api_status()
            
            if not status:
                logger.warning("No status data received, retrying in 30s...")
                time.sleep(30)
                continue
            
            boost_id = status.get('id')
            boost_status = status.get('status')
            start_time = status.get('start_time', 0)
            
            logger.info(f"Status check - ID: {boost_id}, Status: {boost_status}")
            
            # Detectar nuevo boost
            if boost_id != bot_state.last_boost_id:
                logger.info(f"New boost detected: {boost_id}")
                bot_state.last_boost_id = boost_id
                bot_state.vip_alert_sent = False
                bot_state.public_alert_sent = False
            
            # Si el boost está en estado "pre" y no se ha enviado alerta VIP
            if boost_status == "pre" and not bot_state.vip_alert_sent:
                now = int(time.time())
                minutes_left = (start_time - now) / 60
                
                logger.info(f"Boost in 'pre' status. Minutes left: {minutes_left:.2f}")
                
                # Enviar alerta VIP si faltan <= 5 minutos
                if 0 < minutes_left <= 5:
                    logger.info("Sending VIP alert (5 min before start)")
                    import asyncio
                    asyncio.run(send_vip_alert(status))
            
            # Si el boost está activo (buy o sell) y no se ha enviado alerta pública
            if boost_status in ["buy", "sell"] and not bot_state.public_alert_sent:
                logger.info("Boost is live, sending public alert")
                import asyncio
                asyncio.run(send_public_alert(status))
            
            # Reset si el boost cerró
            if boost_status == "closed":
                if bot_state.vip_alert_sent or bot_state.public_alert_sent:
                    logger.info("Boost closed, resetting alert flags")
                    bot_state.vip_alert_sent = False
                    bot_state.public_alert_sent = False
            
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
        
        # Esperar 30 segundos antes del próximo check
        time.sleep(30)


# ============================================
# MAIN
# ============================================

def main():
    """Función principal"""
    
    # Validar variables de entorno
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return
    
    if not VIP_CHAT_ID or not PUBLIC_CHAT_ID:
        logger.warning("VIP_CHAT_ID or PUBLIC_CHAT_ID not set. Alerts will fail.")
    
    logger.info("Starting myBoostiq Telegram Bot...")
    logger.info(f"API Base URL: {API_BASE_URL}")
    
    # Crear aplicación
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot_state.application = application
    
    # Registrar comandos
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    application.add_handler(CommandHandler("register", register_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("unregister", unregister_command))
    
    # Iniciar monitoring loop en thread separado
    monitor_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitor_thread.start()
    logger.info("Monitoring thread started")
    
    # Iniciar bot
    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
