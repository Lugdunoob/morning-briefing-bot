#!/usr/bin/env python3
"""
Morning Briefing Bot — Telegram
Génère un briefing quotidien via Claude API (avec web search)
et l'envoie automatiquement sur Telegram.
"""

import os
import json
import requests
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIGURATION — à remplir avec tes clés
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "sk-ant-XXXX")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "XXXX:XXXX")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "6327266038")

# Sujets à inclure dans le briefing (active/désactive à ton goût)
TOPICS = [
    "Crypto & Bitcoin & Altcoins",
    "Marchés financiers & indices boursiers",
    "Tech & Intelligence Artificielle",
    "Macro-économie & Fed & BCE",
    "Podcasts recommandés pour traders",
]

# ─────────────────────────────────────────────
# GÉNÉRATION DU BRIEFING VIA CLAUDE
# ─────────────────────────────────────────────

def generate_briefing() -> dict:
    """Appelle l'API Claude avec web search pour générer le briefing du jour."""
    today = datetime.now().strftime("%A %d %B %Y")
    topics_str = ", ".join(TOPICS)

    prompt = f"""Tu es un assistant de veille pour un trader crypto français.
Aujourd'hui nous sommes le {today}.

Utilise la recherche web pour trouver les vraies actualités du jour.
Génère un briefing matinal couvrant : {topics_str}.

Réponds UNIQUEMENT en JSON valide (sans markdown, sans backticks) avec cette structure :
{{
  "headline": "Titre accrocheur résumant le thème dominant du jour en une phrase",
  "markets": [
    {{ "symbol": "BTC", "price": "$XX,XXX", "change": 2.3, "note": "observation courte" }},
    {{ "symbol": "ETH", "price": "$X,XXX", "change": -0.5, "note": "..." }},
    {{ "symbol": "S&P500", "price": "X,XXX", "change": 0.8, "note": "..." }},
    {{ "symbol": "EUR/USD", "price": "X.XXXX", "change": -0.1, "note": "..." }}
  ],
  "news": [
    {{
      "title": "Titre de l'article",
      "source": "Nom de la source",
      "summary": "Résumé 2-3 phrases. Pourquoi c'est important pour un trader ?",
      "category": "crypto|tech|macro|regulation",
      "url": "url ou null"
    }}
  ],
  "podcasts": [
    {{
      "name": "Nom du podcast",
      "episode": "Titre ou description de l'épisode récent",
      "duration": "~45 min",
      "why": "Pourquoi écouter ça aujourd'hui ?"
    }}
  ],
  "article_du_jour": {{
    "title": "Titre",
    "source": "Source",
    "summary": "Résumé 3-4 phrases de l'article de fond recommandé.",
    "url": "url ou null"
  }},
  "phrase_du_jour": "Une citation ou insight de marché percutant pour commencer la journée."
}}

Inclure 4-5 news, 2 podcasts. Les prix marchés doivent être les plus proches possible du moment actuel."""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "interleaved-thinking-2025-05-14",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2500,
            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()

    # Extraire le texte JSON de la réponse
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block["text"]

    text = text.strip().replace("```json", "").replace("```", "").strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


# ─────────────────────────────────────────────
# FORMATAGE DU MESSAGE TELEGRAM
# ─────────────────────────────────────────────

CATEGORY_EMOJI = {
    "crypto": "🟡",
    "tech": "🔵",
    "macro": "🟢",
    "regulation": "🔴",
}

def format_telegram_message(briefing: dict) -> str:
    """Convertit le JSON briefing en message Telegram formaté (MarkdownV2)."""
    today = datetime.now().strftime("%d/%m/%Y")
    lines = []

    # En-tête
    lines.append(f"☀️ *MORNING BRIEFING — {today}*")
    if briefing.get("headline"):
        lines.append(f"_{escape_md(briefing['headline'])}_")
    lines.append("")

    # Marchés
    if briefing.get("markets"):
        lines.append("📊 *MARCHÉS*")
        for m in briefing["markets"]:
            change = m.get("change", 0)
            arrow = "▲" if change >= 0 else "▼"
            sign = "+" if change >= 0 else ""
            note = f" — {m['note']}" if m.get("note") else ""
            lines.append(
                f"`{m['symbol']:<8}` {escape_md(m['price'])}  "
                f"{arrow} {escape_md(f'{sign}{change}%')}{escape_md(note)}"
            )
        lines.append("")

    # News
    if briefing.get("news"):
        lines.append("📰 *ACTUALITÉS CLÉS*")
        for n in briefing["news"]:
            emoji = CATEGORY_EMOJI.get(n.get("category", ""), "⚪")
            lines.append(f"{emoji} *{escape_md(n['title'])}*")
            lines.append(f"   {escape_md(n['source'])}")
            lines.append(f"   {escape_md(n['summary'])}")
            if n.get("url"):
                lines.append(f"   [Lire l'article]({n['url']})")
            lines.append("")

    # Podcasts
    if briefing.get("podcasts"):
        lines.append("🎙 *PODCASTS DU JOUR*")
        for p in briefing["podcasts"]:
            dur = f" \\({escape_md(p['duration'])}\\)" if p.get("duration") else ""
            lines.append(f"*{escape_md(p['name'])}*{dur}")
            lines.append(f"   {escape_md(p['episode'])}")
            if p.get("why"):
                lines.append(f"   💡 {escape_md(p['why'])}")
            lines.append("")

    # Article du jour
    if briefing.get("article_du_jour"):
        a = briefing["article_du_jour"]
        lines.append("📖 *ARTICLE DU JOUR*")
        lines.append(f"*{escape_md(a['title'])}*")
        lines.append(f"_{escape_md(a['source'])}_")
        lines.append(escape_md(a["summary"]))
        if a.get("url"):
            lines.append(f"[Lire →]({a['url']})")
        lines.append("")

    # Citation
    if briefing.get("phrase_du_jour"):
        lines.append(f"💬 _{escape_md(briefing['phrase_du_jour'])}_")

    lines.append("")
    lines.append("—")
    lines.append("_Généré automatiquement par ton Morning Briefing Bot_")

    return "\n".join(lines)


def escape_md(text: str) -> str:
    """Échappe les caractères spéciaux Telegram MarkdownV2."""
    if not text:
        return ""
    text = str(text)
    special = r"\_*[]()~`>#+-=|{}.!"
    for ch in special:
        text = text.replace(ch, f"\\{ch}")
    return text


# ─────────────────────────────────────────────
# ENVOI SUR TELEGRAM
# ─────────────────────────────────────────────

def send_telegram(message: str) -> bool:
    """Envoie le message sur Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": False,
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()
    return result.get("ok", False)


# ─────────────────────────────────────────────
# POINT D'ENTRÉE
# ─────────────────────────────────────────────

def main():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Génération du briefing...")
    try:
        briefing = generate_briefing()
        print("✓ Briefing généré")

        message = format_telegram_message(briefing)
        ok = send_telegram(message)

        if ok:
            print("✓ Message envoyé sur Telegram avec succès")
        else:
            print("✗ Erreur lors de l'envoi Telegram")

    except requests.exceptions.RequestException as e:
        print(f"✗ Erreur réseau : {e}")
    except json.JSONDecodeError as e:
        print(f"✗ Erreur parsing JSON : {e}")
    except Exception as e:
        print(f"✗ Erreur inattendue : {e}")
        raise


if __name__ == "__main__":
    main()
