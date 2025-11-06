# 🤖 myBoostiq Telegram Bot

Bot de Telegram para el proyecto myBoostiq que monitorea boosts en BSC y envía alertas VIP y públicas.

## 🎯 Características

- ✅ Registro de usuarios VIP mediante wallet
- ✅ Verificación de status VIP
- ✅ Monitoreo continuo de boosts (polling cada 30 seg)
- ✅ Alertas VIP 5 minutos antes del boost
- ✅ Alertas públicas cuando el boost inicia
- ✅ Manejo robusto de errores
- ✅ Logging completo

## 📋 Requisitos

- Python 3.10 o superior
- Cuenta de Telegram
- Token de bot (obtenido de [@BotFather](https://t.me/BotFather))
- Grupos de Telegram (VIP y Público)

## 🚀 Setup Local

### 1. Clonar el repositorio

```bash
git clone <tu-repo>
cd myboostiq-telegram-bot
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Copia `.env.example` a `.env` y completa las variables:

```bash
cp .env.example .env
```

Edita `.env` con tus valores:

```env
TELEGRAM_BOT_TOKEN=tu_token_aqui
VIP_CHAT_ID=-1001234567890
PUBLIC_CHAT_ID=-1009876543210
```

### 5. Ejecutar el bot

```bash
python bot.py
```

## 🔧 Configuración del Bot de Telegram

### Crear el bot con BotFather

1. Abre Telegram y busca [@BotFather](https://t.me/BotFather)
2. Envía `/newbot`
3. Sigue las instrucciones:
   - Nombre del bot: `myBoostiq VIP Bot`
   - Username: `myboostiq_bot` (debe terminar en 'bot')
4. Copia el token que te da BotFather
5. Pégalo en tu `.env` como `TELEGRAM_BOT_TOKEN`

### Configurar comandos del bot

Envía esto a @BotFather con `/setcommands`:

```
start - Mensaje de bienvenida
help - Mostrar comandos disponibles
register - Registrarse como VIP (uso: /register 0xWALLET)
check - Verificar status VIP
unregister - Eliminar registro VIP
```

### Obtener Chat IDs

Para los grupos VIP y Público:

1. Crea los grupos en Telegram
2. Agrega tu bot a cada grupo como administrador
3. Envía un mensaje en el grupo
4. Visita (reemplaza `<TOKEN>` con tu token):
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```
5. Busca `"chat":{"id":` en la respuesta - ese número es el Chat ID
6. Úsalo en tu `.env` (incluye el signo negativo si lo tiene)

## 📁 Estructura del Proyecto

```
myboostiq-telegram-bot/
├── bot.py              # Código principal
├── requirements.txt    # Dependencias Python
├── Procfile           # Configuración para Railway
├── .env.example       # Template de variables
├── .env               # Variables de entorno (no commitear)
├── .gitignore         # Archivos ignorados por git
└── README.md          # Esta documentación
```

## 🎮 Comandos del Bot

### Para Usuarios

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `/start` | Mensaje de bienvenida | `/start` |
| `/help` | Lista de comandos | `/help` |
| `/register` | Registrarse como VIP | `/register 0x1234...` |
| `/check` | Verificar status VIP | `/check` |
| `/unregister` | Eliminar registro VIP | `/unregister` |

### Validación de Wallets

El bot valida que las wallets tengan el formato correcto:
- Deben empezar con `0x`
- Deben tener exactamente 40 caracteres hexadecimales después del `0x`
- Ejemplo válido: `0x1234567890123456789012345678901234567890`

## 🔄 Flujo de Monitoreo

```
┌─────────────────────────────────────┐
│   Loop cada 30 segundos             │
└───────────────┬─────────────────────┘
                │
                ▼
┌─────────────────────────────────────┐
│   GET /api/status                   │
└───────────────┬─────────────────────┘
                │
                ▼
        ┌───────┴────────┐
        │ ¿Nuevo boost?  │
        └───────┬────────┘
         Sí     │     No
    ┌───────────┴───────────┐
    │                       │
    ▼                       ▼
┌────────┐            ┌──────────┐
│ Status │            │ Continuar│
│  "pre" │            │ monitoring│
└───┬────┘            └──────────┘
    │
    ▼
┌─────────────────┐
│ ¿Faltan <= 5min?│
└───┬─────────────┘
    │ Sí
    ▼
┌───────────────────┐
│ Enviar alerta VIP │
└───────────────────┘
```

## 📊 Logging

El bot genera logs detallados para debugging:

```
2025-11-04 10:30:00 - root - INFO - Starting myBoostiq Telegram Bot...
2025-11-04 10:30:01 - root - INFO - Monitoring thread started
2025-11-04 10:30:01 - root - INFO - Bot is running...
2025-11-04 10:30:32 - root - INFO - Status check - ID: 1, Status: pre
2025-11-04 10:35:00 - root - INFO - Sending VIP alert (5 min before start)
2025-11-04 10:35:01 - root - INFO - VIP alert sent for boost 1
```

## 🚀 Deploy en Railway

### Paso 1: Preparar el código

```bash
git init
git add .
git commit -m "Initial commit"
```

### Paso 2: Subir a GitHub

```bash
git remote add origin https://github.com/tuusuario/myboostiq-bot.git
git push -u origin main
```

### Paso 3: Desplegar en Railway

1. Ve a [railway.app](https://railway.app)
2. Click en "New Project"
3. Selecciona "Deploy from GitHub repo"
4. Conecta tu cuenta de GitHub
5. Selecciona el repositorio `myboostiq-bot`
6. Railway detectará automáticamente el `Procfile`

### Paso 4: Configurar variables de entorno

En Railway, ve a "Variables" y agrega:

```
TELEGRAM_BOT_TOKEN=tu_token
VIP_CHAT_ID=-1001234567890
PUBLIC_CHAT_ID=-1009876543210
API_BASE_URL=https://myboostiq-api-6do.pages.dev
ADMIN_TOKEN=MyBoost_IQ_1009
```

### Paso 5: Deploy automático

Railway desplegará automáticamente. El bot correrá 24/7.

## 💰 Costos

- **Railway Free Tier**: $5 de crédito mensual
- **Este bot usa**: ~$0-2/mes
- **Perfecto para**: Proyectos pequeños

Si excedes el free tier, Railway cobra por hora de uso.

## 🧪 Testing

### Test local

```bash
# Activar entorno virtual
source venv/bin/activate

# Ejecutar bot
python bot.py
```

Prueba los comandos en Telegram:
1. `/start` - Debe mostrar bienvenida
2. `/register 0x1234567890123456789012345678901234567890` - Debe registrar
3. `/check` - Debe mostrar VIP ACTIVE
4. `/unregister` - Debe eliminar registro

### Test de alertas

Para testear las alertas sin esperar 5 minutos reales:

1. En `bot.py`, línea ~320, cambia temporalmente:
   ```python
   if 0 < minutes_left <= 5:  # Original
   if 0 < minutes_left <= 60: # Test: alerta 1 hora antes
   ```

2. Programa un boost en la API para dentro de 1 hora
3. El bot enviará la alerta VIP al detectarlo

**¡No olvides revertir el cambio después del test!**

## 🐛 Troubleshooting

### Bot no responde

1. Verifica que el token sea correcto
2. Asegúrate que el bot esté corriendo (`python bot.py`)
3. Revisa los logs para errores

### No recibo alertas

1. Verifica que `VIP_CHAT_ID` y `PUBLIC_CHAT_ID` estén configurados
2. Asegúrate que el bot sea admin en los grupos
3. Revisa que la API esté respondiendo correctamente

### Error "Invalid wallet format"

La wallet debe:
- Empezar con `0x`
- Tener exactamente 40 caracteres hex después
- Sin espacios ni caracteres especiales

Correcto: `0x1234567890123456789012345678901234567890`
Incorrecto: `1234567890123456789012345678901234567890` (sin 0x)

### Error de API

Si ves `Error getting API status`, verifica:
1. Que la API esté online: https://myboostiq-api-6do.pages.dev/api/status
2. Tu conexión a internet
3. Los logs para más detalles

## 📝 Logs y Monitoring

### Ver logs en Railway

1. Ve a tu proyecto en Railway
2. Click en "Deployments"
3. Selecciona el deployment activo
4. Click en "View Logs"

### Logs importantes

```
# Bot iniciado correctamente
INFO - Starting myBoostiq Telegram Bot...
INFO - Monitoring thread started
INFO - Bot is running...

# Usuario registrado
INFO - User 123456 registered wallet: 0xabc...

# Alerta enviada
INFO - VIP alert sent for boost 1
INFO - Public alert sent for boost 1

# Errores de API
ERROR - Error getting API status: ...
ERROR - Error sending VIP alert: ...
```

## 🔒 Seguridad

- ✅ Nunca commitees el archivo `.env` (está en `.gitignore`)
- ✅ El `ADMIN_TOKEN` está protegido en variables de entorno
- ✅ Las validaciones de wallet previenen inputs maliciosos
- ✅ Los errores de API se manejan gracefully

## 🆘 Soporte

Si tienes problemas:

1. Revisa esta documentación completa
2. Verifica los logs del bot
3. Consulta los archivos adjuntos del proyecto:
   - `BRIEF_COMPLETO_CHATGPT.md`
   - `BOT_TELEGRAM_QUICK_START.md`
   - `DEPLOY_BOT_RAILWAY.md`

## 📚 Recursos

- [python-telegram-bot docs](https://docs.python-telegram-bot.org/)
- [Railway docs](https://docs.railway.app/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [myBoostiq App](https://myboostiq.app)

## 📄 Licencia

Este proyecto es parte de myBoostiq.

---

**¡Hecho con 🚀 para myBoostiq!**
