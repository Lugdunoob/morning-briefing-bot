# Morning Briefing Bot — Setup Guide

## Étape 1 — Créer ton bot Telegram (5 min)

1. Ouvre Telegram et cherche **@BotFather**
2. Envoie `/newbot`
3. Donne un nom : `Mon Morning Briefing`
4. Donne un username : `mon_briefing_bot`
5. BotFather te donne un **token** → note-le (format : `123456789:AAF...`)

6. Pour obtenir ton **Chat ID** :
   - Cherche **@userinfobot** sur Telegram
   - Envoie n'importe quel message
   - Il te répond avec ton ID (ex : `123456789`)

## Étape 2 — Récupérer ta clé Anthropic

Va sur https://console.anthropic.com/settings/keys
Crée une clé API → note-la (format : `sk-ant-...`)

## Étape 3 — Tester localement (optionnel)

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-XXXX"
export TELEGRAM_BOT_TOKEN="123456:XXXX"
export TELEGRAM_CHAT_ID="123456789"

python morning_briefing_bot.py
```

## Étape 4 — Déployer sur Railway (gratuit, automatique)

Railway permet d'exécuter le script automatiquement chaque matin.

### 4a. Créer un compte Railway
Inscris-toi sur https://railway.app (gratuit, 500h/mois incluses)

### 4b. Nouveau projet
1. Clique **New Project** → **Deploy from GitHub repo**
2. Push ce dossier sur GitHub (ou utilise Railway CLI)
3. Ou : **New Project** → **Empty Service** → upload les fichiers

### 4c. Configurer les variables d'environnement
Dans Railway → ton service → **Variables** :
```
ANTHROPIC_API_KEY    = sk-ant-XXXX
TELEGRAM_BOT_TOKEN   = 123456:XXXX
TELEGRAM_CHAT_ID     = 123456789
```

### 4d. Configurer le CRON (envoi automatique chaque matin)
Dans Railway → **Settings** → **Cron Schedule** :
```
0 7 * * *
```
→ Exécute le script tous les jours à 7h00 UTC (= 8h00 Paris en hiver, 9h00 en été)

Pour 7h00 heure de Paris toute l'année :
- Hiver (UTC+1) : `0 6 * * *`
- Été (UTC+2)   : `0 5 * * *`

## Modifier les sujets du briefing

Dans `morning_briefing_bot.py`, modifie la liste `TOPICS` :

```python
TOPICS = [
    "Crypto & Bitcoin & Altcoins",
    "Marchés financiers & indices boursiers",
    "Tech & Intelligence Artificielle",
    "Macro-économie & Fed & BCE",
    "Podcasts recommandés pour traders",
    # Ajoute ce que tu veux :
    # "DeFi & protocoles on-chain",
    # "Régulation crypto Europe",
    # "Startups françaises",
]
```

## Coût estimé

| Service | Coût |
|---------|------|
| Railway (cron) | Gratuit (500h/mois) |
| Telegram Bot API | Gratuit |
| Anthropic API (claude-sonnet) | ~$0.02 par briefing |

→ Environ **0,60€/mois** pour un briefing quotidien.
