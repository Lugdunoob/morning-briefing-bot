#!/usr/bin/env python3
"""
Morning Briefing Bot — Telegram
Génère un briefing quotidien via Claude API et l'envoie sur Telegram.
Gère automatiquement le découpage si le message dépasse 4000 chars.
"""

import os
import json
import requests
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "6327266038")
TELEGRAM_LIMIT     = 4000  # marge sous la limite de 4096

TOPICS = [
    "Crypto et Bitcoin et Altcoins",
    "Marches financiers et indices boursiers",
    "Tech et Intelligence Artificielle",
    "Macro-economie",
    "Podcasts pour traders",
]

# ─────────────────────────────────────────────
# GÉNÉRATION VIA CLAUDE
# ─────────────────────────────────────────────

def generate_briefing():
    today    = datetime.now().strftime("%A %d %B %Y")
    topics_s = ", ".join(TOPICS)

    prompt = (
        "Tu es un assistant de veille pour un trader crypto francais. "
        "Aujourd'hui nous sommes le " + today + ". "
        "Genere un briefing matinal CONCIS couvrant : " + topics_s + ". "
        "Sois bref : max 1 phrase par news, max 1 phrase par podcast. "
        "IMPORTANT : reponds UNIQUEMENT avec du JSON brut valide. "
        "Pas de markdown, pas de backticks, pas de texte avant ou apres. "
        "Commence par { et termine par }.\n\n"
        "Structure :\n"
        '{"headline":"une phrase","markets":['
        '{"symbol":"BTC","price":"$84000","change":1.2},'
        '{"symbol":"ETH","price":"$1600","change":-0.8},'
        '{"symbol":"SP500","price":"5200","change":0.5},'
        '{"symbol":"EURUSD","price":"1.0820","change":-0.1}],'
        '"news":['
        '{"title":"titre court","source":"source","summary":"1 phrase max.","category":"crypto"},'
        '{"title":"titre court","source":"source","summary":"1 phrase max.","category":"macro"},'
        '{"title":"titre court","source":"source","summary":"1 phrase max.","category":"tech"},'
        '{"title":"titre court","source":"source","summary":"1 phrase max.","category":"regulation"}],'
        '"podcasts":['
        '{"name":"nom","episode":"titre episode","duration":"45 min"},'
        '{"name":"nom","episode":"titre episode","duration":"30 min"}],'
        '"article_du_jour":{"title":"titre","source":"source","summary":"2 phrases max."},'
        '"phrase_du_jour":"citation courte"}'
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
            "max_tokens": 1500,
            "messages":   [{"role": "user", "content": prompt}],
        },
        timeout=90,
    )

    if resp.status_code != 200:
        print("Erreur API Anthropic " + str(resp.status_code) + " : " + resp.text[:300])
        resp.raise_for_status()

    data  = resp.json()
    text  = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block["text"]

    text  = text.strip().replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("Aucun JSON dans la reponse : " + text[:200])

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
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def format_message(b):
    today = datetime.now().strftime("%d/%m/%Y")
    L = []

    # EN-TÊTE
    L.append("☀️ <b>MORNING BRIEFING — " + today + "</b>")
    if b.get("headline"):
        L.append("<i>" + esc(b["headline"]) + "</i>")
    L.append("")

    # MARCHÉS
    markets = b.get("markets", [])
    if markets:
        L.append("📊 <b>MARCHÉS</b>")
        for m in markets:
            change = float(m.get("change", 0))
            arrow  = "▲" if change >= 0 else "▼"
            sign   = "+" if change >= 0 else ""
            L.append(
                "<code>" + esc(m["symbol"]).ljust(7) + "</code> "
                + esc(m["price"]) + "  "
                + arrow + " " + sign + str(change) + "%"
            )
        L.append("")

    # NEWS
    news = b.get("news", [])
    if news:
        L.append("📰 <b>ACTUALITÉS</b>")
        for n in news:
            emoji = CATEGORY_EMOJI.get(n.get("category", ""), "⚪")
            L.append(
                emoji + " <b>" + esc(n.get("title", "")) + "</b>"
                + " — <i>" + esc(n.get("source", "")) + "</i>"
            )
            L.append(esc(n.get("summary", "")))
            L.append("")

    # PODCASTS
    podcasts = b.get("podcasts", [])
    if podcasts:
        L.append("🎙 <b>PODCASTS</b>")
        for p in podcasts:
            dur = " (" + esc(p.get("duration", "")) + ")" if p.get("duration") else ""
            L.append(
                "• <b>" + esc(p.get("name", "")) + "</b>" + dur
                + " — " + esc(p.get("episode", ""))
            )
        L.append("")

    # ARTICLE DU JOUR
    a = b.get("article_du_jour")
    if a:
        L.append("📖 <b>ARTICLE DU JOUR</b>")
        L.append("<b>" + esc(a.get("title", "")) + "</b> — <i>" + esc(a.get("source", "")) + "</i>")
        L.append(esc(a.get("summary", "")))
        L.append("")

    # PHRASE DU JOUR
    phrase = b.get("phrase_du_jour")
    if phrase:
        L.append("💬 <i>" + esc(phrase) + "</i>")

    L.append("")
    L.append("<i>Morning Briefing Bot</i>")
    return "\n".join(L)


# ─────────────────────────────────────────────
# ENVOI TELEGRAM — découpage automatique
# ─────────────────────────────────────────────

def send_one(text):
    url  = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    resp = requests.post(
        url,
        json={
            "chat_id":                  TELEGRAM_CHAT_ID,
            "text":                     text,
            "parse_mode":               "HTML",
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print("Erreur Telegram " + str(resp.status_code) + " : " + resp.text[:300])
        resp.raise_for_status()
    return resp.json().get("ok", False)


def send_telegram(message):
    print("Taille message : " + str(len(message)) + " chars")
    if len(message) <= TELEGRAM_LIMIT:
        return send_one(message)

    # Découpage sur les lignes vides (entre sections)
    parts   = []
    current = ""
    for line in message.split("\n"):
        test = current + line + "\n"
        if len(test) > TELEGRAM_LIMIT and current.strip():
            parts.append(current.strip())
            current = line + "\n"
        else:
            current = test
    if current.strip():
        parts.append(current.strip())

    print("Message decoupé en " + str(len(parts)) + " parties")
    ok = True
    for i, part in enumerate(parts):
        print("Envoi partie " + str(i + 1) + "/" + str(len(parts)))
        ok = send_one(part) and ok
    return ok


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    ts = "[" + datetime.now().strftime("%H:%M:%S") + "] "
    print(ts + "Demarrage Morning Briefing Bot")

    if not ANTHROPIC_API_KEY:
        print("ERREUR : ANTHROPIC_API_KEY manquante")
        return
    if not TELEGRAM_BOT_TOKEN:
        print("ERREUR : TELEGRAM_BOT_TOKEN manquante")
        return

    print(ts + "Variables OK — Appel Claude...")

    try:
        briefing = generate_briefing()
        print(ts + "Briefing genere OK")

        message = format_message(briefing)
        print(ts + "Message formate — " + str(len(message)) + " chars")

        ok = send_telegram(message)
        if ok:
            print(ts + "SUCCES — Telegram OK !")
        else:
            print(ts + "ECHEC — ok=false")

    except requests.exceptions.HTTPError as e:
        print(ts + "Erreur HTTP : " + str(e))
    except requests.exceptions.ConnectionError as e:
        print(ts + "Erreur connexion : " + str(e))
    except requests.exceptions.Timeout:
        print(ts + "Timeout 90s depasse")
    except json.JSONDecodeError as e:
        print(ts + "Erreur JSON : " + str(e))
    except Exception as e:
        print(ts + "Erreur : " + str(e))
        raise


if __name__ == "__main__":
    main()
