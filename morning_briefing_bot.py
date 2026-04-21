#!/usr/bin/env python3
"""
Morning Briefing Bot
Envoie le briefing par Telegram ET/OU Email (Gmail).
"""

import os
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─────────────────────────────────────────────
# CONFIGURATION — variables Railway
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")

# Telegram (laisser vide pour désactiver)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "6327266038")

# Email Gmail (laisser vide pour désactiver)
GMAIL_USER         = os.environ.get("GMAIL_USER", "")       # ex: monmail@gmail.com
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "") # mot de passe app Gmail
EMAIL_TO           = os.environ.get("EMAIL_TO", "")          # destinataire (peut être le même)

TELEGRAM_LIMIT     = 4000


# ─────────────────────────────────────────────
# GÉNÉRATION VIA CLAUDE — prompt minimal et strict
# ─────────────────────────────────────────────

PROMPT_TEMPLATE = """Tu es un assistant de veille pour un trader crypto francais.
Date : {today}

Reponds UNIQUEMENT avec un objet JSON valide. Rien d autre.
Pas de texte avant, pas de texte apres, pas de backticks.
Chaque champ "summary" : maximum 15 mots.

{{
"headline":"une phrase de 10 mots max",
"markets":[
{{"s":"BTC","p":"$84000","c":1.2}},
{{"s":"ETH","p":"$1600","c":-0.8}},
{{"s":"SP500","p":"5200","c":0.5}},
{{"s":"EUR/USD","p":"1.082","c":-0.1}}
],
"news":[
{{"title":"titre 5 mots","src":"CoinDesk","summary":"une phrase.","cat":"crypto"}},
{{"title":"titre 5 mots","src":"Bloomberg","summary":"une phrase.","cat":"macro"}},
{{"title":"titre 5 mots","src":"Reuters","summary":"une phrase.","cat":"tech"}},
{{"title":"titre 5 mots","src":"TheBlock","summary":"une phrase.","cat":"regulation"}}
],
"podcasts":[
{{"name":"nom","ep":"episode court","dur":"45min"}},
{{"name":"nom","ep":"episode court","dur":"30min"}}
],
"article":{{"title":"titre","src":"source","summary":"deux phrases max."}},
"quote":"citation courte"
}}"""


def extract_json(text):
    """Extrait le premier objet JSON valide trouvé dans le texte."""
    text = text.strip()
    # Nettoyer les balises markdown
    text = text.replace("```json", "").replace("```", "").strip()

    # Tentative 1 : parser directement
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Tentative 2 : trouver { ... } et parser
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start != -1 and end > 0:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    # Tentative 3 : raw_decode (trouve le premier JSON valide)
    decoder = json.JSONDecoder()
    for i in range(len(text)):
        if text[i] == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
                return obj
            except json.JSONDecodeError:
                continue

    raise ValueError("Aucun JSON valide trouve. Reponse brute :\n" + text[:400])


def generate_briefing():
    today  = datetime.now().strftime("%d %B %Y")
    prompt = PROMPT_TEMPLATE.format(today=today)

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        },
        json={
            "model":      "claude-sonnet-4-6",
            "max_tokens": 1000,
            "messages":   [{"role": "user", "content": prompt}],
        },
        timeout=90,
    )

    if resp.status_code != 200:
        print("Erreur API " + str(resp.status_code) + " : " + resp.text[:300])
        resp.raise_for_status()

    raw = ""
    for block in resp.json().get("content", []):
        if block.get("type") == "text":
            raw += block["text"]

    print("Reponse Claude (" + str(len(raw)) + " chars) : " + raw[:100] + "...")
    return extract_json(raw)


# ─────────────────────────────────────────────
# FORMATAGE
# ─────────────────────────────────────────────

CAT_EMOJI = {"crypto": "🟡", "tech": "🔵", "macro": "🟢", "regulation": "🔴"}

def esc(v):
    s = str(v) if v else ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def build_telegram(b):
    today = datetime.now().strftime("%d/%m/%Y")
    L = []
    L.append("☀️ <b>BRIEFING — " + today + "</b>")
    if b.get("headline"):
        L.append("<i>" + esc(b["headline"]) + "</i>")
    L.append("")

    for m in b.get("markets", []):
        c = float(m.get("c", 0))
        arrow = "▲" if c >= 0 else "▼"
        s = "+" if c >= 0 else ""
        L.append("<code>" + esc(m.get("s","")).ljust(7) + "</code> " + esc(m.get("p","")) + "  " + arrow + " " + s + str(c) + "%")
    L.append("")

    news = b.get("news", [])
    if news:
        L.append("📰 <b>NEWS</b>")
        for n in news:
            e = CAT_EMOJI.get(n.get("cat",""), "⚪")
            L.append(e + " <b>" + esc(n.get("title","")) + "</b> — <i>" + esc(n.get("src","")) + "</i>")
            L.append(esc(n.get("summary","")))
        L.append("")

    pods = b.get("podcasts", [])
    if pods:
        L.append("🎙 <b>PODCASTS</b>")
        for p in pods:
            L.append("• <b>" + esc(p.get("name","")) + "</b> (" + esc(p.get("dur","")) + ") — " + esc(p.get("ep","")))
        L.append("")

    a = b.get("article")
    if a:
        L.append("📖 <b>ARTICLE</b>")
        L.append("<b>" + esc(a.get("title","")) + "</b> — <i>" + esc(a.get("src","")) + "</i>")
        L.append(esc(a.get("summary","")))
        L.append("")

    if b.get("quote"):
        L.append("💬 <i>" + esc(b["quote"]) + "</i>")

    L.append("")
    L.append("<i>Morning Briefing Bot</i>")
    return "\n".join(L)


def build_email_html(b):
    today = datetime.now().strftime("%d %B %Y")
    html  = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
body{font-family:Georgia,serif;max-width:600px;margin:0 auto;background:#f9f9f7;color:#1a1a1a}
.wrap{background:#fff;padding:32px;border-radius:8px;margin:20px auto}
h1{font-size:22px;margin:0 0 4px}
.date{color:#888;font-size:13px;margin-bottom:20px}
.section{margin:20px 0}
.section-title{font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#999;border-bottom:1px solid #eee;padding-bottom:4px;margin-bottom:12px}
.market-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin:8px 0}
.market-card{background:#f5f5f3;border-radius:6px;padding:10px;text-align:center}
.market-sym{font-size:11px;color:#999;margin-bottom:2px}
.market-price{font-size:14px;font-weight:bold}
.market-change{font-size:12px}
.up{color:#16a34a}.down{color:#dc2626}
.news-item{margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #f0f0f0}
.news-title{font-weight:bold;font-size:15px;margin-bottom:2px}
.news-src{font-size:11px;color:#999;margin-bottom:4px}
.news-summary{font-size:14px;line-height:1.5;color:#444}
.podcast{padding:8px 0;border-bottom:1px solid #f5f5f5}
.podcast-name{font-weight:bold}
.podcast-ep{font-size:13px;color:#666}
.article-title{font-weight:bold;font-size:16px}
.article-src{font-size:12px;color:#999;margin:2px 0 6px}
.article-sum{font-size:14px;color:#444;line-height:1.5}
.quote{font-style:italic;color:#666;border-left:3px solid #e0e0e0;padding-left:12px;margin:16px 0}
.footer{text-align:center;font-size:11px;color:#bbb;margin-top:24px}
</style></head><body><div class="wrap">"""

    html += "<h1>☀️ Morning Briefing</h1>"
    html += '<div class="date">' + today + "</div>"
    if b.get("headline"):
        html += "<p><i>" + esc(b["headline"]) + "</i></p>"

    # Marchés
    markets = b.get("markets", [])
    if markets:
        html += '<div class="section"><div class="section-title">Marchés</div><div class="market-grid">'
        for m in markets:
            c = float(m.get("c", 0))
            cls = "up" if c >= 0 else "down"
            sign = "+" if c >= 0 else ""
            html += ('<div class="market-card">'
                     '<div class="market-sym">' + esc(m.get("s","")) + '</div>'
                     '<div class="market-price">' + esc(m.get("p","")) + '</div>'
                     '<div class="market-change ' + cls + '">' + sign + str(c) + '%</div>'
                     '</div>')
        html += "</div></div>"

    # News
    news = b.get("news", [])
    if news:
        html += '<div class="section"><div class="section-title">Actualités</div>'
        emoji_map = {"crypto":"🟡","tech":"🔵","macro":"🟢","regulation":"🔴"}
        for n in news:
            e = emoji_map.get(n.get("cat",""), "⚪")
            html += ('<div class="news-item">'
                     '<div class="news-title">' + e + " " + esc(n.get("title","")) + '</div>'
                     '<div class="news-src">' + esc(n.get("src","")) + '</div>'
                     '<div class="news-summary">' + esc(n.get("summary","")) + '</div>'
                     '</div>')
        html += "</div>"

    # Podcasts
    pods = b.get("podcasts", [])
    if pods:
        html += '<div class="section"><div class="section-title">🎙 Podcasts</div>'
        for p in pods:
            html += ('<div class="podcast">'
                     '<span class="podcast-name">' + esc(p.get("name","")) + '</span>'
                     ' <span style="color:#bbb">(' + esc(p.get("dur","")) + ')</span>'
                     '<div class="podcast-ep">' + esc(p.get("ep","")) + '</div>'
                     '</div>')
        html += "</div>"

    # Article
    a = b.get("article")
    if a:
        html += ('<div class="section"><div class="section-title">📖 Article du jour</div>'
                 '<div class="article-title">' + esc(a.get("title","")) + '</div>'
                 '<div class="article-src">' + esc(a.get("src","")) + '</div>'
                 '<div class="article-sum">' + esc(a.get("summary","")) + '</div>'
                 '</div>')

    # Quote
    if b.get("quote"):
        html += '<div class="quote">' + esc(b["quote"]) + "</div>"

    html += '<div class="footer">Morning Briefing Bot — généré automatiquement</div>'
    html += "</div></body></html>"
    return html


# ─────────────────────────────────────────────
# ENVOI TELEGRAM
# ─────────────────────────────────────────────

def tg_send_one(text):
    url  = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN + "/sendMessage"
    resp = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID, "text": text,
        "parse_mode": "HTML", "disable_web_page_preview": True,
    }, timeout=30)
    if resp.status_code != 200:
        print("Erreur Telegram " + str(resp.status_code) + " : " + resp.text[:200])
        resp.raise_for_status()
    return resp.json().get("ok", False)


def send_telegram(message):
    if len(message) <= TELEGRAM_LIMIT:
        return tg_send_one(message)
    # Découpage sur lignes vides
    parts, cur = [], ""
    for line in message.split("\n"):
        test = cur + line + "\n"
        if len(test) > TELEGRAM_LIMIT and cur.strip():
            parts.append(cur.strip())
            cur = line + "\n"
        else:
            cur = test
    if cur.strip():
        parts.append(cur.strip())
    print("Message découpé en " + str(len(parts)) + " parties")
    return all(tg_send_one(p) for p in parts)


# ─────────────────────────────────────────────
# ENVOI EMAIL
# ─────────────────────────────────────────────

def send_email(html_body):
    today   = datetime.now().strftime("%d/%m/%Y")
    msg     = MIMEMultipart("alternative")
    msg["Subject"] = "☀️ Morning Briefing — " + today
    msg["From"]    = GMAIL_USER
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, EMAIL_TO, msg.as_string())
    return True


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    ts = "[" + datetime.now().strftime("%H:%M:%S") + "] "
    print(ts + "Demarrage Morning Briefing Bot")

    if not ANTHROPIC_API_KEY:
        print("ERREUR : ANTHROPIC_API_KEY manquante")
        return

    use_telegram = bool(TELEGRAM_BOT_TOKEN)
    use_email    = bool(GMAIL_USER and GMAIL_APP_PASSWORD and EMAIL_TO)

    if not use_telegram and not use_email:
        print("ERREUR : aucun canal configuré (Telegram ou Email)")
        return

    print(ts + "Canal(aux) : " + ("Telegram " if use_telegram else "") + ("Email" if use_email else ""))
    print(ts + "Appel Claude...")

    try:
        briefing = generate_briefing()
        print(ts + "Briefing OK")

        if use_telegram:
            msg = build_telegram(briefing)
            print(ts + "Telegram : message " + str(len(msg)) + " chars")
            ok  = send_telegram(msg)
            print(ts + ("✓ Telegram envoyé" if ok else "✗ Telegram echec"))

        if use_email:
            html = build_email_html(briefing)
            print(ts + "Email : envoi vers " + EMAIL_TO + "...")
            send_email(html)
            print(ts + "✓ Email envoyé")

    except requests.exceptions.HTTPError as e:
        print(ts + "Erreur HTTP : " + str(e))
    except requests.exceptions.Timeout:
        print(ts + "Timeout 90s")
    except json.JSONDecodeError as e:
        print(ts + "Erreur JSON : " + str(e))
    except Exception as e:
        print(ts + "Erreur : " + str(e))
        raise


if __name__ == "__main__":
    main()
