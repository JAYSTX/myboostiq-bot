import os

# --- ENV OBLIGATORIAS ---
BOT_TOKEN         = os.getenv("8091608519:AAHV2vqBBORkjjwxXlHFjSwHyp2uAzHS0to")            # token del bot
BSC_API_KEY       = os.getenv("BSC_API_KEY")                   # API Key de BscScan
OWNER_ID          = int(os.getenv("OWNER_ID", "5712520691"))   # @CRIPTOJAY
SUB_WALLET        = os.getenv("SUB_WALLET", "0xbad5eebd86acebf1a9457ef881b0e22a1fb5b56d")

# --- DESTINOS ---
CHANNEL_ID        = int(os.getenv("CHANNEL_ID", "-1003251195251"))  # canal @MyBoostIQchannel (numérico)
ALERTS_GROUP_USER = os.getenv("ALERTS_GROUP_USER", "@myboostiqalerts")
VIP_GROUP_USER    = os.getenv("VIP_GROUP_USER", "@myboostiqVIP")     # privado; usa link si aplica
VIP_GROUP_ID      = os.getenv("VIP_GROUP_ID")  # opcional: si lo conoces (numérico). Si no, se usa username.

# --- SUSCRIPCIÓN ---
USDT_CONTRACT     = os.getenv("USDT_CONTRACT", "0x55d398326f99059fF775485246999027B3197955") # USDT BEP20
PRICE_USDT        = float(os.getenv("PRICE_USDT", "50"))
DURATION_DAYS     = int(os.getenv("DURATION_DAYS", "7"))

# --- SITIO ---
OFFICIAL_WEB      = os.getenv("OFFICIAL_WEB", "https://myboostiq.app")
