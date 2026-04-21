#!/usr/bin/env python3
"""
Morning Briefing Bot — Telegram
Génère un briefing quotidien via Claude API et l'envoie sur Telegram.
"""

import os
import json
import requests
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "6327266038")

TOPICS = [
    "Crypto et Bitcoin et Altcoins",
    "Marches financiers et indices boursiers",
    "Tech et Intelligence Artificielle",
    "Macro-economie et Fed et BCE",
    "Podcasts recommandes pour traders",
]

# ─────────────────────────────────────────────
# GÉNÉRATION VIA CLAUDE
# ─────────────────────────────────────────────

def generate_briefing():
    today    = datetime.now().strftime("%A %d %B %Y")
    topics_s = ", ".join(TOPICS)

    prompt = (
        "Tu es un assistant de veille pour un trader crypto francais.\n"
        "Aujourd'hui nous sommes le " + today + ".\n\n"
        "Genere un briefing matinal couvrant : " + topics_s + ".\n\n"
        "IMPORTANT : reponds UNIQUEMENT avec du JSON brut valide.\n"
        "Pas de markdown, pas de backticks, pas de texte avant ou apres.\n"
        "Commence directement par { et termine par }.\n\n"
        "Structure exacte a respecter :\n"
        '{\n'
        '  "headline": "phrase resumant le theme dominant du jour",\n'
        '  "markets": [\n'
        '    {"symbol": "BTC",    "price": "$84000", "change": 1.2,  "note": "info courte"},\n'
        '    {"symbol": "ETH",    "price": "$1600",  "change": -0.8, "note": "info courte"},\n'
        '    {"symbol": "SP500",  "price": "5200",   "change": 0.5,  "note": "info courte"},\n'
        '    {"symbol": "EURUSD", "price": "1.0820", "change": -0.1, "note": "info courte"}\n'
        '  ],\n'
        '  "news": [\n'
        '    {"title": "titre", "source": "CoinDesk",  "summary": "2 phrases.", "category": "crypto",     "url": null},\n'
        '    {"title": "titre", "source": "Bloomberg", "summary": "2 phrases.", "category": "macro",      "url": null},\n'
        '    {"title": "titre", "source": "The Block", "summary": "2 phrases.", "category": "regulation", "url": null},\n'
        '    {"title": "titre", "source": "Reuters",   "summary": "2 phrases.", "category": "tech",       "url": null}\n'
        '  ],\n'
        '  "podcasts": [\n'
        '    {"name": "nom", "episode": "description", "duration": "45 min", "why": "pertinent car..."},\n'
        '    {"name": "nom", "episode": "description", "duration": "30 min", "why": "pertinent car..."}\n'
        '  ],\n'
        '  "article_du_jour": {\n'
        '    "title": "titre article de fond",\n'
        '    "source": "source",\n'
        '    "summary": "3 phrases. Pourquoi le lire ?",\n'
        '    "url": null\n'
        '  },\n'
        '  "phrase_du_jour": "citation ou insight percutant"\n'
        '}'
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json={
            "model":      "claude-sonnet-4-6",
            "max_tokens": 2000,
            "messages":   [{"role": "user", "content": prompt}],
        },
        timeout=90,
    )

    if resp.status_code != 200:
        print("Erreur API Anthropic " + str(resp.status_code) + " : " + resp.text)
        resp.raise_for_status()

    data = resp.json()
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block["text"]

    text  = text.strip().replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end   = text.rfind("}") + 1

    if start == -1 or end == 0:
        raise ValueError("Aucun JSON dans la reponse : " + text[:300])

    return json.loads(text[start:end])


# ─────────────────────────────────────────────
# FORMATAGE HTML TELEGRAM
# ─────────────────────────────────────────────

CATEGORY_EMOJI = {
    "crypto":     "🟡",
    "tech":       "🔵",
    "macro":      "🟢",
    "regulation": "🔴",
}

def esc(val):
    s = str(val) if val is not None else ""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s

def format_message(b):
    today = datetime.now().strftime("%d/%m/%Y")
    L = []

    L.append("☀️ <b>MORNING BRIEFING — " + today + "</b>")
    if b.get("headline"):
        L.append("<i>" + esc(b["headline"]) + "</i>")
    L.append("")

    markets = b.get("markets", [])
    if markets:
        L.append("📊 <b>MARCHES</b>")
        for m in markets:
            change = float(m.get("change", 0))
            arrow  = "▲" if change >= 0 else "▼"
            sign   = "+" if change >= 0 else ""
            note   = "  <i>" + esc(m["note"]) + "</i>" if m.get("note") else ""
            L.append(
                "<code>" + esc(m["symbol"]) + "</code>  "
                + esc(m["price"]) + "   "
                + arrow + " " + sign + str(change) + "%" + note
            )
        L.append("")

    news = b.get("news", [])
    if news:
        L.append("📰 <b>ACTUALITES CLES</b>")
        for n in news:
            emoji = CATEGORY_EMOJI.get(n.get("category", ""), "⚪")
            L.append(emoji + " <b>" + esc(n.get("title", "")) + "</b>")
            L.append("   <i>" + esc(n.get("source", "")) + "</i>")
            L.append("   " + esc(n.get("summary", "")))
            url = n.get("url")
            if url and url != "null":
                L.append('   <a href="' + esc(url) + '">Lire</a>')
            L.append("")

    podcasts = b.get("podcasts", [])
    if podcasts:
        L.append("🎙 <b>PODCASTS DU JOUR</b>")
        for p in podcasts:
            dur = " (" + esc(p["duration"]) + ")" if p.get("duration") else ""
            L.append("<b>" + esc(p.get("name", "")) + "</b>" + dur)
            L.append("   " + esc(p.get("episode", "")))
            if p.get("why"):
                L.append("   💡 " + esc(p["why"]))
            L.append("")

    a = b.get("article_du_jour")
    if a:
        L.append("📖 <b>ARTICLE DU JOUR</b>")
        L.append("<b>" + esc(a.get("title", "")) + "</b>")
        L.append("<i>" + esc(a.get("source", "")) + "</i>")
        L.append(esc(a.get("summary", "")))
        url = a.get("url")
        if url and url != "null":
            L.append('<a href="' + esc(url) + '">Lire</a>')
        L.append("")

    phrase = b.get("phrase_du_jour")
    if phrase:
        L.append("💬 <i>" + esc(phrase) + "</i>")

    L.append("")
    L.append("<i>Genere automatiquement par ton Morning Briefing Bot</i>")
    return "\n".join(L)


# ─────────────────────────────────────────────
# ENVOI TELEGRAM
# ─────────────────────────────────────────────

def send_telegram(message):
    url  = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id":                  TELEGRAM_CHAT_ID,
            "text":                     message,
            "parse_mode":               "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print("Erreur Telegram " + str(resp.status_code) + " : " + resp.text)
        resp.raise_for_status()
    return resp.json().get("ok", False)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    ts = "[" + datetime.now().strftime("%H:%M:%S") + "] "
    print(ts + "Demarrage Morning Briefing Bot")

    if not ANTHROPIC_API_KEY:
        print("ERREUR FATALE : ANTHROPIC_API_KEY manquante dans Railway Variables")
        return
    if not TELEGRAM_BOT_TOKEN:
        print("ERREUR FATALE : TELEGRAM_BOT_TOKEN manquante dans Railway Variables")
        return

    print(ts + "Variables OK — Appel Claude en cours...")

    try:
        briefing = generate_briefing()
        print(ts + "Briefing genere OK")

        message = format_message(briefing)
        print(ts + "Message formate — Envoi Telegram...")

        ok = send_telegram(message)
        if ok:
            print(ts + "SUCCES — Message envoye sur Telegram !")
        else:
            print(ts + "ECHEC — Telegram a retourne ok=false")

    except requests.exceptions.HTTPError as e:
        print(ts + "Erreur HTTP : " + str(e))
    except requests.exceptions.ConnectionError as e:
        print(ts + "Erreur connexion : " + str(e))
    except requests.exceptions.Timeout:
        print(ts + "Timeout — pas de reponse en 90s")
    except json.JSONDecodeError as e:
        print(ts + "Erreur parsing JSON : " + str(e))
    except Exception as e:
        print(ts + "Erreur inattendue : " + str(e))
        raise


if __name__ == "__main__":
    main()
