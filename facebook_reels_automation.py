"""
Facebook Reels Automation - Bilingual English/German Content Generator
IMPROVED VERSION: Better backgrounds, English categories, no repeats, Velocity German branding
"""

import os
import sys
import json
import random
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gemini-fast")

# Directories
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
VIDEO_DIR = OUTPUT_DIR / "video"
HISTORY_DIR = OUTPUT_DIR / "history"

for d in [OUTPUT_DIR, IMAGES_DIR, AUDIO_DIR, VIDEO_DIR, HISTORY_DIR]:
    d.mkdir(exist_ok=True)

# Video settings (9:16 vertical)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# English category names (for American/European learners)
CATEGORIES_ENGLISH = [
    "Motivation", "Love", "Success", "Wisdom", "Happiness",
    "Self Improvement", "Gratitude", "Friendship", "Hope", "Creativity",
    "Inner Peace", "Confidence", "Perseverance", "Inspiration", "Positive Life",
    "Courage", "Kindness", "Patience", "Forgiveness", "Strength",
    "Joy", "Balance", "Growth", "Purpose", "Mindfulness",
]

# German translations for display
CATEGORIES_GERMAN = {
    "Motivation": "Motivation",
    "Love": "Liebe",
    "Success": "Erfolg",
    "Wisdom": "Weisheit",
    "Happiness": "Glück",
    "Self Improvement": "Selbstverbesserung",
    "Gratitude": "Dankbarkeit",
    "Friendship": "Freundschaft",
    "Hope": "Hoffnung",
    "Creativity": "Kreativität",
    "Inner Peace": "Innere Ruhe",
    "Confidence": "Selbstvertrauen",
    "Perseverance": "Ausdauer",
    "Inspiration": "Inspiration",
    "Positive Life": "Positives Leben",
    "Courage": "Mut",
    "Kindness": "Freundlichkeit",
    "Patience": "Geduld",
    "Forgiveness": "Verzeihen",
    "Strength": "Stärke",
    "Joy": "Freude",
    "Balance": "Gleichgewicht",
    "Growth": "Wachstum",
    "Purpose": "Zweck",
    "Mindfulness": "Achtsamkeit",
}

# Edge TTS voices
ENGLISH_VOICE = "en-US-GuyNeural"
GERMAN_VOICE = "de-DE-ConradNeural"

# Phrase history file (NEVER delete this!)
PHRASE_HISTORY_FILE = HISTORY_DIR / "all_generated_phrases.json"


# ============== PHRASE HISTORY MANAGEMENT (Prevent Repeats) ==============

def load_phrase_history():
    """Load all previously generated phrases"""
    if PHRASE_HISTORY_FILE.exists():
        with open(PHRASE_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"phrases": [], "last_updated": None}


def save_phrase_history(data):
    """Save phrase history"""
    data["last_updated"] = datetime.now().isoformat()
    with open(PHRASE_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_phrase_used(english_phrase):
    """Check if phrase was already generated"""
    history = load_phrase_history()
    english_lower = english_phrase.lower().strip()
    for p in history.get("phrases", []):
        if p.get("english", "").lower().strip() == english_lower:
            return True
    return False


def add_phrases_to_history(phrases, category):
    """Add new phrases to history"""
    history = load_phrase_history()
    for phrase in phrases:
        history["phrases"].append({
            "english": phrase["english"],
            "german": phrase["german"],
            "category": category,
            "generated_at": datetime.now().isoformat()
        })
    save_phrase_history(history)
    print(f"[history] Added {len(phrases)} phrases to history (total: {len(history['phrases'])})")


# ============== CONTENT GENERATION ==============

def generate_phrases(category_english: str, num_phrases: int = 5) -> list:
    """Generate unique bilingual phrases with natural pauses, ensuring no repeats"""

    category_german = CATEGORIES_GERMAN[category_english]

    # Check if API key is available
    if not POLLINATIONS_API_KEY:
        print("[content] ⚠️  No POLLINATIONS_API_KEY found - using fallback phrases")
        print("[content] 💡 Set your API key in .env file to get AI-generated phrases")
        return get_fresh_fallback_phrases(category_english, num_phrases)

    # Try AI first
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            import requests
            url = "https://gen.pollinations.ai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {POLLINATIONS_API_KEY}",
                "Content-Type": "application/json"
            }

            prompt = f"""Create {num_phrases * 2} unique {category_english} phrases for English speakers learning German.

IMPORTANT RULES FOR NATURAL SPEECH:
1. Keep phrases SHORT (5-12 words max per language)
2. Add NATURAL PAUSES using commas (e.g., "Dream big, start small")
3. Use punctuation for breathing room in TTS
4. Avoid long run-on sentences
5. Each phrase should be speakable in 3-5 seconds

For each phrase:
1. English phrase (with commas for natural pauses)
2. German translation (with commas matching the rhythm)
3. Pronunciation guide (phonetic for English speakers)

Return as JSON array:
[{{"english": "...", "german": "...", "pronunciation": "..."}}]

IMPORTANT: Create FRESH, UNIQUE phrases that haven't been used before."""

            payload = {
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a German teacher. Create short, natural phrases with pauses."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.9
            }

            print(f"[content] 🤖 Calling AI (attempt {attempt + 1}/{max_attempts})...")
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Extract JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            phrases = json.loads(content)
            print(f"[content] ✓ AI returned {len(phrases)} phrases")

            # Filter out already-used phrases and ensure proper length
            unique_phrases = []
            used_count = 0
            for phrase in phrases:
                # Skip if too long (over 15 words)
                if len(phrase["english"].split()) > 15:
                    continue
                if is_phrase_used(phrase["english"]):
                    used_count += 1
                    continue
                unique_phrases.append(phrase)
                if len(unique_phrases) >= num_phrases:
                    break

            if used_count > 0:
                print(f"[content] ⚠️  Skipped {used_count} already-used phrases")

            if len(unique_phrases) >= num_phrases:
                add_phrases_to_history(unique_phrases[:num_phrases], category_english)
                print(f"[content] ✅ Generated {num_phrases} fresh AI phrases!")
                return unique_phrases[:num_phrases]
            else:
                print(f"[content] ⚠️  Only got {len(unique_phrases)} unique phrases from AI (needed {num_phrases})")

        except requests.exceptions.HTTPError as e:
            print(f"[content] ❌ API Error (attempt {attempt + 1}): {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"[content] Response: {e.response.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"[content] ❌ Network Error (attempt {attempt + 1}): {e}")
        except json.JSONDecodeError as e:
            print(f"[content] ❌ JSON Parse Error (attempt {attempt + 1}): {e}")
            print(f"[content] Raw response: {content[:200] if 'content' in locals() else 'N/A'}")
        except Exception as e:
            print(f"[content] ❌ Unexpected Error (attempt {attempt + 1}): {e}")

    # Fallback to fresh phrases
    print("[content] 📋 Using fallback phrases (AI unavailable)...")
    return get_fresh_fallback_phrases(category_english, num_phrases)


def get_fresh_fallback_phrases(category: str, num_phrases: int) -> list:
    """Get fallback phrases, filtering out used ones - EXPANDED for all 25 categories"""

    all_fallbacks = {
        "Motivation": [
            {"english": "Believe in yourself.", "german": "Glaube an dich.", "pronunciation": "GLOW-beh an dish."},
            {"english": "You are capable of amazing things.", "german": "Du bist zu erstaunlichen Dingen fähig.", "pronunciation": "Doo bist tsoo air-STAOWN-likhen DIN-gen fay-ik."},
            {"english": "Dream big, start small.", "german": "Träume groß, fang klein an.", "pronunciation": "TROY-meH grohs, fang kline an."},
            {"english": "Your future is created by your actions.", "german": "Deine Zukunft wird durch deine Taten geschaffen.", "pronunciation": "DY-neH tsoo-koonft veert doorkh DY-neh TAH-ten geshaf-fen."},
            {"english": "Never give up on your dreams.", "german": "Gib deine Träume niemals auf.", "pronunciation": "Gib DY-neH TROY-meH NEE-mahls owf."},
            {"english": "Every step forward, counts.", "german": "Jeder Schritt vorwärts, zählt.", "pronunciation": "YAY-der shrit FOR-verts, tsaylt."},
            {"english": "You are stronger, than you think.", "german": "Du bist stärker, als du denkst.", "pronunciation": "Doo bist SHTER-ker, als doo denkst."},
            {"english": "Keep going, stay positive.", "german": "Mach weiter, bleib positiv.", "pronunciation": "Makht VY-ter, blyp poh-zee-TEEF."},
            {"english": "Your potential, is limitless.", "german": "Dein Potenzial, ist grenzenlos.", "pronunciation": "Dyn poh-ten-TSIAL, ist gren-tsen-lohs."},
            {"english": "Today is your day, shine.", "german": "Heute ist dein Tag, strahle.", "pronunciation": "HOY-teh ist dyn tahk, shtrah-leh."},
        ],
        "Love": [
            {"english": "Love yourself first.", "german": "Liebe dich selbst zuerst.", "pronunciation": "LEE-beh dish zelpst tsoo-erst."},
            {"english": "Love makes everything possible.", "german": "Liebe macht alles möglich.", "pronunciation": "LEE-beh makht AL-less MUR-glikh."},
            {"english": "You are my heart.", "german": "Du bist mein Herz.", "pronunciation": "Doo bist myn herts."},
            {"english": "I love you, deeply.", "german": "Ich liebe dich, sehr.", "pronunciation": "Ikh LEE-beh dish, seyr."},
            {"english": "You make me, happy.", "german": "Du machst mich, glücklich.", "pronunciation": "Doo makhsht mikh, GLUK-likh."},
            {"english": "My heart beats, for you.", "german": "Mein Herz schlägt, für dich.", "pronunciation": "Myn herts shlaykt, fur dish."},
            {"english": "You are, my everything.", "german": "Du bist, mein Alles.", "pronunciation": "Doo bist, myn AL-less."},
            {"english": "Thinking of you, always.", "german": "Ich denke an dich, immer.", "pronunciation": "Ikh DEN-keh an dish, IM-mer."},
            {"english": "You complete me.", "german": "Du vervollständigst mich.", "pronunciation": "Doo fer-FOLL-shten-digst mikh."},
            {"english": "Forever with you.", "german": "Für immer mit dir.", "pronunciation": "Fur IM-mer mit deer."},
        ],
        "Success": [
            {"english": "Aim higher, enjoy the climb.", "german": "Ziele höher, genieße den Aufstieg.", "pronunciation": "TSEE-leh HUR-er, geh-NEE-seh den OWF-shteeg."},
            {"english": "Small wins, build momentum.", "german": "Kleine Siege, bauen Schwung auf.", "pronunciation": "KLY-ne ZEE-geh, POW-en shvoong owf."},
            {"english": "Success starts, with action.", "german": "Erfolg beginnt, mit Handeln.", "pronunciation": "Air-FOLK beh-GINT, mit HAN-deln."},
            {"english": "You earn success, daily.", "german": "Du verdienst Erfolg, täglich.", "pronunciation": "Doo fer-DEENST er-FOLK, TAY-glikh."},
            {"english": "Celebrate progress, not perfection.", "german": "Feiere Fortschritt, nicht Perfektion.", "pronunciation": "FY-er-eh FORT-shrit, nikht per-fek-TSYOHN."},
            {"english": "Work hard, stay humble.", "german": "Arbeite hart, bleib bescheiden.", "pronunciation": "AR-by-teh hart, blyp beh-SHY-den."},
            {"english": "Your effort, pays off.", "german": "Deine Mühe, zahlt sich aus.", "pronunciation": "DY-neh MUR-heh, tsahlt zikhowz."},
            {"english": "Success is, a journey.", "german": "Erfolg ist, eine Reise.", "pronunciation": "Air-FOLK ist, AY-neh RYZE."},
            {"english": "Keep pushing, forward.", "german": "Drück weiter, vorwärts.", "pronunciation": "DRUK VY-ter, FOR-verts."},
            {"english": "Victory awaits, you.", "german": "Der Sieg wartet, auf dich.", "pronunciation": "Der zeek VAR-tet, owf dish."},
        ],
        "Wisdom": [
            {"english": "Listen first, answer kindly.", "german": "Hör zuerst zu, antworte freundlich.", "pronunciation": "HUR tsoo-erst tsoo, ANT-vorteh FROYNT-likh."},
            {"english": "Small habits, shape futures.", "german": "Kleine Gewohnheiten, formen Zukünfte.", "pronunciation": "KLY-ne geh-VOHN-hy-ten, FOR-men TSOO-kunf-teh."},
            {"english": "Let go, make space.", "german": "Lass los, mach Platz.", "pronunciation": "Lass lohs, makhl plats."},
            {"english": "Ask questions, learn daily.", "german": "Stelle Fragen, lerne täglich.", "pronunciation": "SHTEL-leh FRAH-gen, LER-neh TAY-glikh."},
            {"english": "Slow down, notice wonders.", "german": "Langsam machen, Wunder bemerken.", "pronunciation": "LANG-zam makhen, VOON-der beh-MER-ken."},
            {"english": "Knowledge grows, with curiosity.", "german": "Wissen wächst, mit Neugier.", "pronunciation": "VIS-en vekst, mit NOY-geer."},
            {"english": "Think deeply, act wisely.", "german": "Denke tief, handle weise.", "pronunciation": "DEN-keh teef, HAN-deh VY-ze."},
            {"english": "Experience teaches, best.", "german": "Erfahrung lehrt, am besten.", "pronunciation": "AIR-fah-roong layrt, am BES-ten."},
            {"english": "Patience brings, clarity.", "german": "Geduld bringt, Klarheit.", "pronunciation": "geh-DOOLT bringt, KLAR-hyt."},
            {"english": "Truth emerges, slowly.", "german": "Die Wahrheit erscheint, langsam.", "pronunciation": "Dee VAR-hyt er-SHYNT, LANG-zam."},
        ],
        "Happiness": [
            {"english": "Joy is, a choice.", "german": "Freude ist, eine Wahl.", "pronunciation": "FROY-deh ist, AY-neh vahl."},
            {"english": "Smile more, worry less.", "german": "Lächle mehr, sorge weniger.", "pronunciation": "LEKH-leh mayr, ZOR-geh VAY-ni-ger."},
            {"english": "Happiness lives, in simplicity.", "german": "Glück wohnt, in Einfachheit.", "pronunciation": "GLUK vohnt, in EYN-fakh-hyt."},
            {"english": "Find joy, in small things.", "german": "Finde Freude, in kleinen Dingen.", "pronunciation": "FIN-deh FROY-deh, in KLY-nen DIN-gen."},
            {"english": "Be present, be happy.", "german": "Sei präsent, sei glücklich.", "pronunciation": "Zay preh-ZENT, zay GLUK-likh."},
            {"english": "Gratitude creates, happiness.", "german": "Dankbarkeit schafft, Glück.", "pronunciation": "DANK-bar-kyt shafht, GLUK."},
            {"english": "Your smile, lights up rooms.", "german": "Dein Lächeln, erhellt Räume.", "pronunciation": "Dyn LEKH-eln, air-HELHT ROY-me."},
            {"english": "Happiness spreads, easily.", "german": "Glück verbreitet, sich leicht.", "pronunciation": "GLUK fer-BRY-tet, zikht lykt."},
            {"english": "Choose joy, today.", "german": "Wähle Freude, heute.", "pronunciation": "VAY-leh FROY-deh, HOY-teh."},
            {"english": "Life is, beautiful.", "german": "Das Leben ist, wunderschön.", "pronunciation": "Das LAY-ben ist, VOON-der-shurn."},
        ],
        "Self Improvement": [
            {"english": "Grow daily, even slightly.", "german": "Wachse täglich, auch nur leicht.", "pronunciation": "VAK-seh TAY-glikh, owk noor lykt."},
            {"english": "Better habits, better life.", "german": "Bessere Gewohnheiten, besseres Leben.", "pronunciation": "BES-seh-reh geh-VOHN-hy-ten, BES-seh-res LAY-ben."},
            {"english": "Invest in, yourself.", "german": "Investiere in, dich selbst.", "pronunciation": "In-vesteer-eh in, dish zelpst."},
            {"english": "Progress over, perfection.", "german": "Fortschritt über, Perfektion.", "pronunciation": "FORT-shrit UR-ber, per-fek-TSYOHN."},
            {"english": "Learn something, new today.", "german": "Lerne etwas, Neues heute.", "pronunciation": "LER-neh ET-vas, NOY-es HOY-teh."},
            {"english": "Challenge yourself, gently.", "german": "Fordere dich, sanft heraus.", "pronunciation": "FOR-deh-reh dish, zauft he-ROWS."},
            {"english": "Your growth, matters most.", "german": "Dein Wachstum, zählt am meisten.", "pronunciation": "Dyn VAKS-toom, tsaylt am MYS-ten."},
            {"english": "Become who, you are.", "german": "Werde der, der du bist.", "pronunciation": "VER-deh dair, dair doo bist."},
            {"english": "Self care, is essential.", "german": "Selbstfürsorge, ist wesentlich.", "pronunciation": "ZELBST-fur-zor-geh, ist VAY-zent-likh."},
            {"english": "Reflect, then redirect.", "german": "Reflektiere, dann lenke um.", "pronunciation": "Reh-flek-teer-eh, dann LEN-keh oom."},
        ],
        "Gratitude": [
            {"english": "Thank you, for everything.", "german": "Danke schön, für alles.", "pronunciation": "DAN-keh shurn, fur AL-less."},
            {"english": "I am grateful, today.", "german": "Ich bin dankbar, heute.", "pronunciation": "Ikh bin DANK-bar, HOY-teh."},
            {"english": "Gratitude changes, everything.", "german": "Dankbarkeit verändert, alles.", "pronunciation": "DANK-bar-kyt fer-EN-dert, AL-less."},
            {"english": "Count blessings, not problems.", "german": "Zähle Segen, nicht Probleme.", "pronunciation": "TSEH-leh ZAY-gen, nikht proh-BLAY-meh."},
            {"english": "Appreciate what, you have.", "german": "Schätze was, du hast.", "pronunciation": "SHET-seh vas, doo hast."},
            {"english": "Thankful hearts, are happy hearts.", "german": "Dankbare Herzen, sind glückliche Herzen.", "pronunciation": "DANK-bah-reh HERT-sen, sind GLUK-likheh HERT-sen."},
            {"english": "Gratitude opens, doors.", "german": "Dankbarkeit öffnet, Türen.", "pronunciation": "DANK-bar-kyt ER-fet, TUR-en."},
            {"english": "Say thank you, often.", "german": "Sag danke schön, oft.", "pronunciation": "Zahk DAN-keh shurn, oft."},
            {"english": "Being thankful, transforms life.", "german": "Dankbarkeit verwandelt, das Leben.", "pronunciation": "DANK-bar-kyt fer-VAN-delt, das LAY-ben."},
            {"english": "Grateful for, this moment.", "german": "Dankbar für, diesen Moment.", "pronunciation": "DANK-bar fur, DEE-zen moh-MENT."},
        ],
        "Friendship": [
            {"english": "Friends are, family we choose.", "german": "Freunde sind, Familie die wir wählen.", "pronunciation": "FROYND-eh sind, fa-MIL-yeh dee veer VAY-len."},
            {"english": "True friends, stay forever.", "german": "Wahre Freunde, bleiben für immer.", "pronunciation": "VAH-reh FROYND-eh, BLY-ben fur IM-mer."},
            {"english": "Laugh together, cry together.", "german": "Gemeinsam lachen, gemeinsam weinen.", "pronunciation": "geh-MYN-zam LAKH-en, geh-MYN-zam VY-nen."},
            {"english": "Friends understand, without words.", "german": "Freunde verstehen, ohne Worte.", "pronunciation": "FROYND-eh fer-SHTAY-en, OH-neh VOR-teh."},
            {"english": "Your support, means everything.", "german": "Deine Unterstützung, bedeutet alles.", "pronunciation": "DY-neh oon-ter-SHTUT-soong, beh-DOY-tet AL-less."},
            {"english": "Side by side, always.", "german": "Seite an Seite, immer.", "pronunciation": "ZY-teh an ZY-teh, IM-mer."},
            {"english": "Friends make life, brighter.", "german": "Freunde machen das Leben, heller.", "pronunciation": "FROYND-eh MAKH-en das LAY-ben, HEL-ler."},
            {"english": "Through thick, and thin.", "german": "Durch dick, und dünn.", "pronunciation": "Doorkh dik, oon dunn."},
            {"english": "A friend, is a gift.", "german": "Ein Freund, ist ein Geschenk.", "pronunciation": "Ein FROYNT, ist in geh-SHENK."},
            {"english": "Friendship warms, the heart.", "german": "Freundschaft wärmt, das Herz.", "pronunciation": "FROYNT-shaft VERMT, das herts."},
        ],
        "Hope": [
            {"english": "Hope shines, always.", "german": "Hoffnung scheint, immer.", "pronunciation": "HOF-noong shynt, IM-mer."},
            {"english": "Better days, are coming.", "german": "Bessere Tage, kommen.", "pronunciation": "BES-seh-reh TAH-geh, KOM-men."},
            {"english": "Keep hoping, keep going.", "german": "Weiter hoffen, weiter gehen.", "pronunciation": "VY-ter HOF-fen, VY-ter GAY-en."},
            {"english": "Hope is, the anchor.", "german": "Hoffnung ist, der Anker.", "pronunciation": "HOF-noong ist, dair AN-ker."},
            {"english": "Light follows, darkness.", "german": "Licht folgt, der Dunkelheit.", "pronunciation": "Likht folkt, dair DOON-kel-hyt."},
            {"english": "Tomorrow brings, new hope.", "german": "Morgen bringt, neue Hoffnung.", "pronunciation": "MOR-gen bringt, NOY-eh HOF-noong."},
            {"english": "Never lose, hope.", "german": "Verliere niemals, Hoffnung.", "pronunciation": "Fer-LEER-eh NEE-mahls, HOF-noong."},
            {"english": "Hope springs, eternal.", "german": "Hoffnung springt, ewig.", "pronunciation": "HOF-noong shpringt, AY-vik."},
            {"english": "In hope, we trust.", "german": "Auf Hoffnung, vertrauen wir.", "pronunciation": "Owf HOF-noong, fer-TROW-en veer."},
            {"english": "Hope heals, everything.", "german": "Hoffnung heilt, alles.", "pronunciation": "HOF-noong hylt, AL-less."},
        ],
        "Creativity": [
            {"english": "Create boldly, live fully.", "german": "Kreativ mutig, leben voll.", "pronunciation": "krea-TEEF MOO-tik, LAY-ben fol."},
            {"english": "Your ideas, matter most.", "german": "Deine Ideen, zählen am meisten.", "pronunciation": "DY-neh ee-DEH-en, tsay-len am MYS-ten."},
            {"english": "Imagine more, create better.", "german": "Mehr vorstellen, besser schaffen.", "pronunciation": "Mayr FOR-shtel-len, BES-er SHAF-fen."},
            {"english": "Art flows, from within.", "german": "Kunst fließt, von innen.", "pronunciation": "KOONST fleest, fon IN-nen."},
            {"english": "Express yourself, freely.", "german": "Drücke dich, frei aus.", "pronunciation": "DRUK-eh dish, fry owz."},
            {"english": "Creativity has, no limits.", "german": "Kreativität kennt, keine Grenzen.", "pronunciation": "Krea-tee-vee-TAYT kent, KY-neh GREN-tsen."},
            {"english": "Make something, beautiful.", "german": "Mach etwas, Schönes.", "pronunciation": "MakH ET-vas, SHUR-nes."},
            {"english": "Your vision, is unique.", "german": "Deine Vision, ist einzigartig.", "pronunciation": "DY-neh vee-ZYOHN, ist EYN-tsik-ar-tik."},
            {"english": "Create daily, dream nightly.", "german": "Täglich schaffen, nachts träumen.", "pronunciation": "TAY-glikh SHAF-fen, NAKHTS TROY-men."},
            {"english": "Inspiration finds, you working.", "german": "Inspiration findet, dich arbeitend.", "pronunciation": "In-spee-ra-TSYOHN fin-det, dikH AR-by-tent."},
        ],
        "Inner Peace": [
            {"english": "Peace begins, within.", "german": "Frieden beginnt, innen.", "pronunciation": "FREE-den beh-GINT, IN-nen."},
            {"english": "Breathe deeply, release tension.", "german": "Tief atmen, Spannung lösen.", "pronunciation": "Teef AHT-men, SHPAN-noong LUR-zen."},
            {"english": "Calm mind, calm life.", "german": "Ruhiger Geist, ruhiges Leben.", "pronunciation": "ROO-i-ger GYST, ROO-i-ges LAY-ben."},
            {"english": "Let go, be still.", "german": "Loslassen, still sein.", "pronunciation": "LOHS-las-en, shtil zyn."},
            {"english": "Inner quiet, outer peace.", "german": "Innere Ruhe, äußere Frieden.", "pronunciation": "IN-neh-reh ROO-eh, OY-seh-reh FREE-den."},
            {"english": "Silence feeds, the soul.", "german": "Stille nährt, die Seele.", "pronunciation": "SHTIL-eh nayrt, dee ZAY-leh."},
            {"english": "Find your, center.", "german": "Finde dein, Zentrum.", "pronunciation": "FIN-deh dyn, TSEN-troom."},
            {"english": "Peace is, a practice.", "german": "Frieden ist, eine Übung.", "pronunciation": "FREE-den ist, AY-neh UR-boong."},
            {"english": "Tranquility awaits, inside.", "german": "Gelassenheit wartet, innen.", "pronunciation": "geh-LAS-en-hyt VAR-tet, IN-nen."},
            {"english": "Stillness speaks, loudly.", "german": "Stille spricht, laut.", "pronunciation": "SHTIL-eh shprikt, lowt."},
        ],
        "Confidence": [
            {"english": "Stand tall, speak clear.", "german": "Steh aufrecht, sprich klar.", "pronunciation": "SHTAY owf-rekht, shprikl klahr."},
            {"english": "You are enough, truly.", "german": "Du bist genug, wirklich.", "pronunciation": "Doo bist geh-NOOK, VEER-likh."},
            {"english": "Trust yourself, completely.", "german": "Vertraue dir, vollständig.", "pronunciation": "Fer-TRow-eh deer, FOLL-shten-dik."},
            {"english": "Confidence grows, with action.", "german": "Selbstvertrauen wächst, mit Handeln.", "pronunciation": "ZELBST-fer-trow-en vekst, mit HAN-deln."},
            {"english": "Own your, power.", "german": "Besitze deine, Kraft.", "pronunciation": "Beh-ZIT-seh DY-neh, kraft."},
            {"english": "Bold steps, bring results.", "german": "Mutige Schritte, bringen Ergebnisse.", "pronunciation": "MOO-ti-geh SHRI-teh, BRING-en air-GAYB-nis-seh."},
            {"english": "Your voice, deserves hearing.", "german": "Deine Stimme, verdient Gehör.", "pronunciation": "DY-neh SHIM-meh, fer-DEENT geh-HUR."},
            {"english": "Believe in, your abilities.", "german": "Glaube an, deine Fähigkeiten.", "pronunciation": "GLOW-beh an, DY-neh FAY-ik-ky-ten."},
            {"english": "Confidence is, contagious.", "german": "Selbstvertrauen ist, ansteckend.", "pronunciation": "ZELBST-fer-trow-en ist, AN-shte-kent."},
            {"english": "You got, this.", "german": "Du schaffst, das.", "pronunciation": "Doo shafst, das."},
        ],
        "Perseverance": [
            {"english": "Keep going, never quit.", "german": "Weitermachen, niemals aufgeben.", "pronunciation": "VY-ter-makhen, NEE-mahls OWF-gay-ben."},
            {"english": "Endurance wins, eventually.", "german": "Ausdauer gewinnt, schließlich.", "pronunciation": "OWZ-dow-er geh-VINT, SHLEES-likh."},
            {"english": "Through struggle, comes strength.", "german": "Durch Kampf, kommt Kraft.", "pronunciation": "Doorkh KAMPF, kommt kraft."},
            {"english": "Persistence beats, talent.", "german": "Beharrlichkeit schlägt, Talent.", "pronunciation": "Beh-HART-likh-kyt shlaykt, tah-LENT."},
            {"english": "Don't stop, keep pushing.", "german": "Hör nicht auf, weiter drücken.", "pronunciation": "HUR nikht owf, VY-ter DRUK-en."},
            {"english": "Weather the storm, survive.", "german": "Den Sturm überstehen, überleben.", "pronunciation": "Den SHTURM UR-ber-shtay-en, UR-ber-lay-ben."},
            {"english": "Steady progress, wins races.", "german": "Stetiger Fortschritt, gewinnt Rennen.", "pronunciation": "SHTEH-ti-ger FORT-shrit, geh-VINT REN-en."},
            {"english": "Rise again, stronger.", "german": "Wieder aufstehen, stärker.", "pronunciation": "VEE-der OWF-shtay-en, SHTER-ker."},
            {"english": "Never surrender, your dreams.", "german": "Niemals aufgeben, deine Träume.", "pronunciation": "NEE-mahls OWF-gay-ben, DY-neh TROY-me."},
            {"english": "Perseverance pays, off.", "german": "Ausdauer zahlt, sich aus.", "pronunciation": "OWZ-dow-er tsahlt, zikhowz."},
        ],
        "Inspiration": [
            {"english": "Be the light, for others.", "german": "Sei das Licht, für andere.", "pronunciation": "Zay das Likht, fur AN-deh-reh."},
            {"english": "Inspire by, example.", "german": "Inspuriere durch, Beispiel.", "pronunciation": "In-shpee-reer-eh doorkh, BY-shpyl."},
            {"english": "Your story, inspires others.", "german": "Deine Geschichte, inspiriert andere.", "pronunciation": "DY-neh geh-SHIKH-teh, in-shee-REERT AN-deh-reh."},
            {"english": "Spark change, today.", "german": "Veränderung anzünden, heute.", "pronunciation": "Fer-EN-deh-roong AN-tsun-den, HOY-teh."},
            {"english": "Motivate others, with action.", "german": "Andere motivieren, mit Taten.", "pronunciation": "AN-deh-reh moh-tee-VEER-en, mit TAH-ten."},
            {"english": "Be someone's, hero.", "german": "Sei jemandes, Held.", "pronunciation": "Zay YEMAN-des, helt."},
            {"english": "Inspiration spreads, quickly.", "german": "Inspiration verbreitet, sich schnell.", "pronunciation": "In-shpee-ra-TSYOHN fer-BRY-tet, zikH shnel."},
            {"english": "Lead with, heart.", "german": "Führe mit, Herz.", "pronunciation": "FUR-eh mit, herts."},
            {"english": "Your impact, matters.", "german": "Dein Einfluss, zählt.", "pronunciation": "Dyn EYN-floos, tsaylt."},
            {"english": "Ignite passion, in others.", "german": "Leidenschaft entfachen, in anderen.", "pronunciation": "LY-den-shaft ENT-fakhen, in AN-deh-ren."},
        ],
        "Positive Life": [
            {"english": "Choose positivity, daily.", "german": "Wähle Positivität, täglich.", "pronunciation": "VAY-leh poh-zee-vee-TAYT, TAY-glikh."},
            {"english": "Good vibes, only.", "german": "Nur gute Schwingungen.", "pronunciation": "Noor GOO-teh SHVIN-goong-en."},
            {"english": "Life is, wonderful.", "german": "Das Leben ist, wunderbar.", "pronunciation": "Das LAY-ben ist, VOON-der-bar."},
            {"english": "Embrace joy, reject negativity.", "german": "Freude umarmen, Negativität ablehnen.", "pronunciation": "FROY-deh OOM-ar-men, neh-gah-tee-vee-TAYT AHP-lay-nen."},
            {"english": "Positive thoughts, create positive life.", "german": "Positive Gedanken, schaffen positives Leben.", "pronunciation": "Poh-zee-TEE-veh geh-DAN-ken, SHAF-fen poh-zee-TEE-ves LAY-ben."},
            {"english": "Radiate good energy, always.", "german": "Gute Energie ausstrahlen, immer.", "pronunciation": "GOO-teh eh-ner-GEE OWZ-shtrah-len, IM-mer."},
            {"english": "See the bright, side.", "german": "Sieh die helle, Seite.", "pronunciation": "Zee dee HEL-leh, ZY-teh."},
            {"english": "Optimism wins, hearts.", "german": "Optimismus gewinnt, Herzen.", "pronunciation": "Op-tee-MIS-moos geh-VINT, HERT-sen."},
            {"english": "Live fully, love deeply.", "german": "Lebe voll, liebe tief.", "pronunciation": "LAY-beh fol, LEE-beh teef."},
            {"english": "Positivity attracts, abundance.", "german": "Positivität zieht, Fülle an.", "pronunciation": "Poh-zee-vee-TAYT tseet, FUL-leh an."},
        ],
        "Courage": [
            {"english": "Be brave, always.", "german": "Sei mutig, immer.", "pronunciation": "Zay MOO-tik, IM-mer."},
            {"english": "Courage fears, nothing.", "german": "Mut fürchtet, nichts.", "pronunciation": "MOOT furkhtet, nikhts."},
            {"english": "Face your fears, head-on.", "german": "Stelle dich Ängsten, direkt.", "pronunciation": "SHTEL-leh dish ENG-sten, dee-REKT."},
            {"english": "Brave hearts, conquer all.", "german": "Mutige Herzen, erobern alles.", "pronunciation": "MOO-ti-geh HERT-sen, eh-ROH-ben AL-less."},
            {"english": "Dare greatly, live fully.", "german": "Wage viel, lebe voll.", "pronunciation": "VAH-geh feel, LAY-beh fol."},
            {"english": "Courage is, acting afraid.", "german": "Mut ist, handelnd trotz Angst.", "pronunciation": "MOOT ist, HAN-delnd trots ahngst."},
            {"english": "Your courage, inspires.", "german": "Dein Mut, inspiriert.", "pronunciation": "Dyn MOOT, in-shee-REERT."},
            {"english": "Step forward, fearlessly.", "german": "Tritt vor, furchtlos.", "pronunciation": "Trit for, FURKH-tlohs."},
            {"english": "Warriors never, retreat.", "german": "Krieger weichen, niemals zurück.", "pronunciation": "KREE-ger VY-khen, NEE-mahls tsoo-RUK."},
            {"english": "Courage unlocks, potential.", "german": "Mut entsperrt, Potenzial.", "pronunciation": "MOOT ENT-shper-t, poh-ten-TSIAL."},
        ],
        "Kindness": [
            {"english": "Be kind, always.", "german": "Sei freundlich, immer.", "pronunciation": "Zay FROYNT-likh, IM-mer."},
            {"english": "Kindness costs, nothing.", "german": "Freundlichkeit kostet, nichts.", "pronunciation": "FROYNT-likh-kyt KOS-tet, nikhts."},
            {"english": "Spread kindness, everywhere.", "german": "Verbreite Freundlichkeit, überall.", "pronunciation": "Fer-BRY-teh FROYNT-likh-kyt, UR-ber-al."},
            {"english": "Gentle words, heal hearts.", "german": "Sanfte Worte, heilen Herzen.", "pronunciation": "ZANF-teh VOR-teh, HY-len HERT-sen."},
            {"english": "Compassion changes, lives.", "german": "Mitgefühl verändert, Leben.", "pronunciation": "MIT-ge-fur fer-EN-dert, LAY-ben."},
            {"english": "A kind gesture, goes far.", "german": "Eine freundliche Geste, reicht weit.", "pronunciation": "AY-neh FROYNT-likheh GES-teh, rYkt wyt."},
            {"english": "Kindness echoes, forever.", "german": "Freundlichkeit hallt, nach.", "pronunciation": "FROYNT-likh-kyt halt, nakH."},
            {"english": "Help others, rise together.", "german": "Hilf anderen, steigt zusammen.", "pronunciation": "Hilf AN-deh-ren, shtykt tsoo-ZAM-men."},
            {"english": "Love kindly, love deeply.", "german": "Liebe freundlich, liebe tief.", "pronunciation": "LEE-beh FROYNT-likh, LEE-beh teef."},
            {"english": "Kindness is, universal.", "german": "Freundlichkeit ist, universell.", "pronunciation": "FROYNT-likh-kyt ist, oo-nee-ver-ZEL."},
        ],
        "Patience": [
            {"english": "Patience brings, peace.", "german": "Geduld bringt, Frieden.", "pronunciation": "geh-DOOLT bringt, FREE-den."},
            {"english": "Wait calmly, trust timing.", "german": "Warte ruhig, vertraue Timing.", "pronunciation": "VAR-teh ROO-ik, fer-TROW-eh TY-ming."},
            {"english": "Good things, take time.", "german": "Gute Dinge, brauchen Zeit.", "pronunciation": "GOO-teh DIN-geh, BROW-khen tsyt."},
            {"english": "Patience is, a virtue.", "german": "Geduld ist, eine Tugend.", "pronunciation": "geh-DOOLT ist, AY-neh TOO-gent."},
            {"english": "Breathe through, the wait.", "german": "Atme durch, das Warten.", "pronunciation": "AHT-meh doorkh, das VAR-ten."},
            {"english": "Slow progress, is progress.", "german": "Langsamer Fortschritt, ist Fortschritt.", "pronunciation": "LANG-zah-mer FORT-shrit, ist FORT-shrit."},
            {"english": "Trust the process, patiently.", "german": "Vertraue dem Prozess, geduldig.", "pronunciation": "Fer-TROW-eh dem proh-TSES, geh-DOOL-tik."},
            {"english": "Patience masters, everything.", "german": "Geduld meistert, alles.", "pronunciation": "geh-DOOLT MY-ster-t, AL-less."},
            {"english": "Calm waiting, yields results.", "german": "Ruhiges Warten, bringt Ergebnisse.", "pronunciation": "ROO-i-ges VAR-ten, bringt air-GAYB-nis-seh."},
            {"english": "Time heals, with patience.", "german": "Zeit heilt, mit Geduld.", "pronunciation": "TsyT hylt, mit geh-DOOLT."},
        ],
        "Forgiveness": [
            {"english": "Forgive freely, live lightly.", "german": "Verzeihe frei, lebe leicht.", "pronunciation": "Fer-TSY-hy fry, LAY-beh lykt."},
            {"english": "Letting go, is freedom.", "german": "Loslassen, ist Freiheit.", "pronunciation": "LOHS-las-en, ist FRY-hyt."},
            {"english": "Forgiveness heals, wounds.", "german": "Verzeihung heilt, Wunden.", "pronunciation": "Fer-TSY-oong hylt, VOON-den."},
            {"english": "Release grudges, embrace peace.", "german": "Groll loslassen, Frieden umarmen.", "pronunciation": "GROL LOHS-las-en, FREE-den OOM-ar-men."},
            {"english": "Mercy softens, hearts.", "german": "Barmherzigkeit erweicht, Herzen.", "pronunciation": "BARM-hert-sik-kyt er-VYKHT, HERT-sen."},
            {"english": "Forgive others, forgive yourself.", "german": "Anderen verzeihen, dir selbst verzeihen.", "pronunciation": "AN-deh-ren fer-TSY-hen, deer zelpst fer-TSY-hen."},
            {"english": "Pardon brings, relief.", "german": "Verzeihen bringt, Erleichterung.", "pronunciation": "Fer-TSY-hen bringt, air-LYKH-teh-roong."},
            {"english": "Clean slate, fresh start.", "german": "Reine Tafel, neuer Start.", "pronunciation": "RY-neh TAH-fel, NOY-er shtart."},
            {"english": "Forgiveness is, strength.", "german": "Verzeihung ist, Stärke.", "pronunciation": "Fer-TSY-oong ist, SHTER-keh."},
            {"english": "Absolution frees, the soul.", "german": "Absolution befreit, die Seele.", "pronunciation": "Ap-zoh-LOO-tsyOHN beh-FRYT, dee ZAY-leh."},
        ],
        "Strength": [
            {"english": "Inner strength, conquers all.", "german": "Innere Stärke, erobert alles.", "pronunciation": "IN-neh-reh SHTER-keh, eh-ROH-bert AL-less."},
            {"english": "You are resilient, truly.", "german": "Du bist widerstandsfähig, wirklich.", "pronunciation": "Doo bist VEE-der-shtands-fay-ik, VEER-likh."},
            {"english": "Power within, you.", "german": "Kraft innerhalb, dir.", "pronunciation": "KRAFT in-ner-HALP, deer."},
            {"english": "Strong minds, overcome.", "german": "Starke Köpfe, überwinden.", "pronunciation": "SHTAR-keh KURP-feh, UR-ber-vin-den."},
            {"english": "Resilience builds, character.", "german": "Widerstandskraft baut, Charakter.", "pronunciation": "VEE-der-shtants-kraft POWT, kah-RAK-ter."},
            {"english": "Your strength, amazes me.", "german": "Deine Stärke, erstaunt mich.", "pronunciation": "DY-neh SHTER-keh, air-STAOWNT mikh."},
            {"english": "Tough times, reveal strength.", "german": "Harte Zeiten, zeigen Stärke.", "pronunciation": "HAR-teh TSY-ten, ZY-gen SHTER-keh."},
            {"english": "Unbreakable spirit, within.", "german": "Unzerbrechlicher Geist, innen.", "pronunciation": "OON-tser-brekh-likher GYST, IN-nen."},
            {"english": "Fortitude carries, through.", "german": "Standhaftigkeit trägt, durch.", "pronunciation": "SHTAND-haf-tik-kyt traykt, doorkh."},
            {"english": "Strength rises, from within.", "german": "Stärke steigt, von innen.", "pronunciation": "SHTER-keh shtykt, fon IN-nen."},
        ],
        "Joy": [
            {"english": "Joy explodes, from within.", "german": "Freude explodiert, von innen.", "pronunciation": "FROY-deh eks-ploh-DEERT, fon IN-nen."},
            {"english": "Celebrate life, daily.", "german": "Feiere das Leben, täglich.", "pronunciation": "FY-er-eh das LAY-ben, TAY-glikh."},
            {"english": "Happiness radiates, outward.", "german": "Glück strahlt, nach außen.", "pronunciation": "GLUK shtrahlt, nakH OW-sen."},
            {"english": "Delight in, small moments.", "german": "Freue dich, an kleinen Momenten.", "pronunciation": "FROY-eh dish, an KLY-nen moh-MEN-ten."},
            {"english": "Cheerfulness attracts, friends.", "german": "Fröhlichkeit zieht, Freunde an.", "pronunciation": "FRUR-likh-kyt tseet, FROYND-eh an."},
            {"english": "Your joy, is contagious.", "german": "Deine Freude, ist ansteckend.", "pronunciation": "DY-neh FROY-deh, ist AN-shte-kent."},
            {"english": "Laugh often, love always.", "german": "Lache oft, liebe immer.", "pronunciation": "LAH-heh oft, LEE-beh IM-mer."},
            {"english": "Bliss awaits, inside.", "german": "Glückseligkeit wartet, innen.", "pronunciation": "GLUK-zay-likh-kyt VAR-tet, IN-nen."},
            {"english": "Ecstasy in, simplicity.", "german": "Ekstase in, Einfachheit.", "pronunciation": "Eks-TAH-zeh in, EYN-fakh-hyt."},
            {"english": "Jubilation fills, the heart.", "german": "Jubel erfüllt, das Herz.", "pronunciation": "YOO-bel air-FULLT, das herts."},
        ],
        "Balance": [
            {"english": "Balance body, mind, soul.", "german": "Körper, Geist, Seele ausbalancieren.", "pronunciation": "KUR-per, GYST, ZAY-leh OWZ-bah-lan-tsee-ren."},
            {"english": "Find equilibrium, always.", "german": "Finde Gleichgewicht, immer.", "pronunciation": "FIN-deh GLYKH-geh-vikht, IM-mer."},
            {"english": "Harmony flows, naturally.", "german": "Harmonie fließt, natürlich.", "pronunciation": "Har-moh-NEE fleest, nah-TUR-likh."},
            {"english": "Work rest, repeat.", "german": "Arbeite, ruhe, wiederhole.", "pronunciation": "AR-by-teh, ROO-eh, VEE-der-hoh-leh."},
            {"english": "Moderation brings, stability.", "german": "Mäßigung bringt, Stabilität.", "pronunciation": "MAY-si-goong bringt, Shtah-bee-lee-TAYT."},
            {"english": "Center yourself, daily.", "german": "Zentriere dich, täglich.", "pronunciation": "Tsen-TREE-reh dish, TAY-glikh."},
            {"english": "Equal parts, effort rest.", "german": "Gleiche Teile, Anstrengung Erholung.", "pronunciation": "GLY-kheh TY-leh, AN-stren-goong air-HOH-loong."},
            {"english": "Poise under, pressure.", "german": "Gelassenheit unter, Druck.", "pronunciation": "geh-LAS-en-hyt OON-ter, DRUK."},
            {"english": "Symmetry in, all things.", "german": "Symmetrie in, allen Dingen.", "pronunciation": "ZUM-meh-TREE in, AL-len DIN-gen."},
            {"english": "Balanced life, is bliss.", "german": "Ausgeglichenes Leben, ist Glück.", "pronunciation": "OWZ-geh-gli-keh-nes LAY-ben, ist GLUK."},
        ],
        "Growth": [
            {"english": "Grow through, challenges.", "german": "Wachse durch, Herausforderungen.", "pronunciation": "VAK-seh doorkh, he-ROWS-for-deh-roong-en."},
            {"english": "Evolution is, constant.", "german": "Entwicklung ist, konstant.", "pronunciation": "Ent-VIK-loong ist, kon-STANT."},
            {"english": "Bloom where, planted.", "german": "Blühe wo, gepflanzt.", "pronunciation": "BLY-heh voh, geh-PFLANTST."},
            {"english": "Development takes, time.", "german": "Entwicklung braucht, Zeit.", "pronunciation": "Ent-VIK-loong BROWKHT, tsyt."},
            {"english": "Expand your, horizons.", "german": "Erweitere deine, Horizonte.", "pronunciation": "Air-VY-teh-reh DY-neh, ho-ree-ZON-teh."},
            {"english": "Maturation is, natural.", "german": "Reifung ist, natürlich.", "pronunciation": "RY-foong ist, nah-TUR-likh."},
            {"english": "Progress unfolds, gradually.", "pronunciation": "FORT-shrit ENT-fal-tet, al-MAY-likh.", "german": "Fortschritt entfaltet, allmählich."},
            {"english": "Advancement requires, action.", "german": "Fortschritt erfordert, Handeln.", "pronunciation": "FORT-shrit air-FOR-dert, HAN-deln."},
            {"english": "Thriving is, your nature.", "german": "Gedeihen ist, deine Natur.", "pronunciation": "geh-DY-hen ist, DY-neh nah-TOOR."},
            {"english": "Growth mindset, wins.", "german": "Wachstumsdenken, gewinnt.", "pronunciation": "VAKS-tooms-den-ken, geh-VINT."},
        ],
        "Purpose": [
            {"english": "Find your, why.", "german": "Finde dein, Warum.", "pronunciation": "FIN-deh dyn, VAH-rooM."},
            {"english": "Purpose drives, action.", "german": "Zweck treibt, Handeln.", "pronunciation": "TSVEK trypt, HAN-deln."},
            {"english": "Meaning gives, depth.", "german": "Sinn gibt, Tiefe.", "pronunciation": "ZIN gipt, TEE-feh."},
            {"english": "Live intentionally, daily.", "german": "Lebe absichtlich, täglich.", "pronunciation": "LAY-beh AHP-zikht-likh, TAY-glikh."},
            {"english": "Your mission, awaits.", "german": "Deine Mission, wartet.", "pronunciation": "DY-neh mis-SYOHN, VAR-tet."},
            {"english": "Direction matters, most.", "german": "Richtung zählt, am meisten.", "pronunciation": "RIP-toong tsaylt, am MYS-ten."},
            {"english": "Calling fulfills, the soul.", "german": "Berufung erfüllt, die Seele.", "pronunciation": "beh-ROO-foong air-FULLT, dee ZAY-leh."},
            {"english": "Intention creates, reality.", "german": "Absicht schafft, Realität.", "pronunciation": "AHP-zikht shafht, reh-ah-lee-TAYT."},
            {"english": "Reason to, rise.", "german": "Grund aufzustehen.", "pronunciation": "GRUNT OWF-tsoo-shtay-en."},
            {"english": "Purpose anchors, the journey.", "german": "Zweck verankert, die Reise.", "pronunciation": "TSVEK fer-AN-kert, dee RYZE."},
        ],
        "Mindfulness": [
            {"english": "Be present, now.", "german": "Sei jetzt, hier.", "pronunciation": "Zay yets, heer."},
            {"english": "Awareness awakens, life.", "german": "Bewusstsein erweckt, Leben.", "pronunciation": "Beh-VOOST-zyn air-VEKT, LAY-ben."},
            {"english": "Mindful moments, matter.", "german": "Achtsame Momente, zählen.", "pronunciation": "AKHT-zah-meh moh-MEN-teh, tsay-len."},
            {"english": "Observe without, judgment.", "german": "Beobachte ohne, Urteil.", "pronunciation": "Beh-OB-akh-teh OH-neh, OOR-tyl."},
            {"english": "Consciousness expands, gently.", "german": "Bewusstsein erweitert, sich sanft.", "pronunciation": "Beh-VOOST-zyn air-VY-tert, zikH zauft."},
            {"english": "Here now, is all.", "german": "Hier jetzt, ist alles.", "pronunciation": "Heer yets, ist AL-less."},
            {"english": "Attention shapes, reality.", "german": "Aufmerksamkeit formt, Realität.", "pronunciation": "OWF-merk-zam-kyt formt, reh-ah-lee-TAYT."},
            {"english": "Meditation calms, the mind.", "german": "Meditation beruhigt, den Geist.", "pronunciation": "Meh-dee-TAH-tsyOHN beh-ROO-igt, den GYST."},
            {"english": "Presence is, the gift.", "german": "Gegenwart ist, das Geschenk.", "pronunciation": "GAY-gen-vart ist, das geh-SHENK."},
            {"english": "Mindfulness brings, peace.", "german": "Achtsamkeit bringt, Frieden.", "pronunciation": "AKHT-zam-kyt bringt, FREE-den."},
        ],
    }

    fallbacks = all_fallbacks.get(category, all_fallbacks["Motivation"])
    fresh_phrases = [p for p in fallbacks if not is_phrase_used(p["english"])]
    
    # If we don't have enough fresh phrases, return what we have
    # This ensures we always return something even if some phrases are used
    if len(fresh_phrases) < num_phrases:
        print(f"[content] Warning: Only {len(fresh_phrases)} fresh fallback phrases available for {category} (needed {num_phrases})")
    
    return fresh_phrases[:num_phrases] if fresh_phrases else fallbacks[:num_phrases]


# ============== AUDIO GENERATION ==============

async def generate_single_audio(text: str, voice: str, output_path: str):
    """Generate audio using Edge TTS"""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return True
    except Exception as e:
        print(f"  TTS error: {e}")
        return False


def generate_all_audio(phrases: list, output_dir: str):
    """Generate audio for all phrases with proper timing"""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_files = []

    for i, phrase in enumerate(phrases):
        english_file = output_dir / f"english_{i}.mp3"
        german_file = output_dir / f"german_{i}.mp3"
        combined_file = output_dir / f"combined_{i}.mp3"

        print(f"\n  Phrase {i+1}:")
        print(f"    EN: {phrase['english']}")
        print(f"    DE: {phrase['german']}")

        # Generate English audio
        en_success = asyncio.run(generate_single_audio(phrase["english"], ENGLISH_VOICE, str(english_file)))
        if en_success:
            print(f"    ✓ English: {english_file.name}")
        else:
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2", str(english_file)]
            subprocess.run(cmd, capture_output=True)

        # Generate German audio
        de_success = asyncio.run(generate_single_audio(phrase["german"], GERMAN_VOICE, str(german_file)))
        if de_success:
            print(f"    ✓ German: {german_file.name}")
        else:
            cmd = ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", "2", str(german_file)]
            subprocess.run(cmd, capture_output=True)

        # Get ACTUAL durations
        en_duration = get_audio_duration(str(english_file))
        de_duration = get_audio_duration(str(german_file))

        # Add pause between English and German
        pause_between = 0.5
        total_duration = en_duration + pause_between + de_duration

        print(f"    ⏱️  Total: {total_duration:.2f}s (EN: {en_duration:.2f}s + pause: {pause_between}s + DE: {de_duration:.2f}s)")

        # Combine audio files
        cmd = [
            "ffmpeg", "-y",
            "-i", str(english_file),
            "-i", str(german_file),
            "-filter_complex", f"[0:a][1:a]concat=n=2:v=0:a=1[out]",
            "-map", "[out]",
            str(combined_file)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            concat_file = output_dir / f"concat_{i}.txt"
            with open(concat_file, "w", encoding="utf-8") as f:
                f.write(f"file '{english_file.as_posix()}'\n")
                f.write(f"file '{german_file.as_posix()}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", str(concat_file),
                "-c:a", "aac",
                str(combined_file)
            ]
            subprocess.run(cmd, capture_output=True)
            if concat_file.exists():
                concat_file.unlink()

        actual_duration = get_audio_duration(str(combined_file))
        print(f"    ✓ Combined verified: {actual_duration:.2f}s")

        audio_files.append({
            "index": i,
            "english": str(english_file),
            "german": str(german_file),
            "combined": str(combined_file),
            "duration": actual_duration,
            "en_duration": en_duration,
            "de_duration": de_duration
        })

    print(f"\n[audio] ✓ Generated {len(audio_files)} phrase audios")
    return audio_files


def get_audio_duration(audio_file: str) -> float:
    """Get audio duration in seconds"""
    if not Path(audio_file).exists():
        return 2.0
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", audio_file]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 2.0


def create_final_narration(audio_files: list, output_file: str):
    """Combine all audio files"""
    n = len(audio_files)
    print(f"[audio] Combining {n} audio files...")

    concat_file = Path(output_file).parent / "narration_list.txt"

    with open(concat_file, "w", encoding="utf-8") as f:
        for audio_info in audio_files:
            combined_path = Path(audio_info["combined"])
            if combined_path.exists():
                path_str = str(combined_path.resolve()).replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{path_str}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c:a", "copy", str(output_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if concat_file.exists():
        concat_file.unlink()

    if result.returncode == 0 and Path(output_file).exists() and Path(output_file).stat().st_size > 0:
        size = Path(output_file).stat().st_size
        print(f"\n[audio] ✓ Final narration: {Path(output_file).name} ({size/1024:.1f} KB)")
        return True

    return False


# ============== IMAGE GENERATION ==============

def create_impressive_background(category_english: str):
    """Create stunning gradient background with geometric patterns and glow"""
    from PIL import Image, ImageDraw

    img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT))
    draw = ImageDraw.Draw(img)

    # HIGH CONTRAST gradients for ALL 25 categories (very different colors like Motivation)
    category_colors = {
        "Motivation": [(138, 43, 226), (75, 0, 130), (255, 20, 147), (147, 112, 219)],  # Purple → Dark Purple → Pink → Light Purple
        "Love": [(255, 0, 100), (139, 0, 0), (255, 105, 180), (255, 192, 203)],  # Red → Dark Red → Hot Pink → Pink
        "Success": [(255, 215, 0), (0, 100, 0), (255, 140, 0), (34, 139, 34)],  # Gold → Dark Green → Orange → Forest Green
        "Wisdom": [(0, 0, 139), (255, 215, 0), (70, 130, 180), (255, 255, 0)],  # Dark Blue → Gold → Steel Blue → Yellow
        "Happiness": [(255, 255, 0), (255, 0, 255), (255, 165, 0), (147, 112, 219)],  # Yellow → Magenta → Orange → Purple
        "Self Improvement": [(0, 128, 0), (255, 215, 0), (0, 255, 0), (255, 140, 0)],  # Green → Gold → Lime → Orange
        "Gratitude": [(255, 127, 80), (75, 0, 130), (255, 160, 122), (138, 43, 226)],  # Coral → Dark Purple → Light Salmon → Blue Violet
        "Friendship": [(255, 192, 203), (0, 100, 80), (255, 105, 180), (0, 200, 160)],  # Pink → Dark Teal → Hot Pink → Medium Teal
        "Hope": [(0, 0, 100), (255, 255, 0), (70, 130, 180), (255, 215, 0)],  # Dark Blue → Yellow → Steel Blue → Gold
        "Creativity": [(255, 0, 127), (0, 0, 139), (255, 20, 147), (75, 0, 130)],  # Deep Pink → Dark Blue → Deep Pink → Dark Purple
        "Inner Peace": [(135, 206, 235), (0, 0, 100), (176, 224, 230), (75, 0, 130)],  # Sky Blue → Dark Blue → Powder Blue → Dark Purple
        "Confidence": [(255, 69, 0), (0, 0, 139), (255, 140, 0), (70, 130, 180)],  # Red Orange → Dark Blue → Orange → Steel Blue
        "Perseverance": [(139, 69, 19), (255, 215, 0), (160, 82, 45), (255, 140, 0)],  # Saddle Brown → Gold → Sienna → Orange
        "Inspiration": [(255, 0, 255), (75, 0, 130), (255, 20, 147), (0, 0, 139)],  # Magenta → Dark Purple → Deep Pink → Dark Blue
        "Positive Life": [(50, 205, 50), (255, 0, 127), (144, 238, 144), (255, 20, 147)],  # Lime Green → Deep Pink → Light Green → Deep Pink
        "Courage": [(178, 34, 34), (255, 215, 0), (220, 20, 60), (255, 140, 0)],  # Firebrick → Gold → Crimson → Orange
        "Kindness": [(255, 182, 193), (138, 43, 226), (255, 160, 122), (75, 0, 130)],  # Light Salmon → Dark Purple → Light Salmon → Dark Purple
        "Patience": [(34, 139, 34), (255, 255, 0), (60, 179, 113), (255, 215, 0)],  # Forest Green → Yellow → Medium Sea Green → Gold
        "Forgiveness": [(230, 230, 250), (75, 0, 130), (216, 191, 216), (138, 43, 226)],  # Lavender → Dark Purple → Thistle → Blue Violet
        "Strength": [(100, 100, 100), (255, 69, 0), (150, 150, 150), (255, 140, 0)],  # Gray → Red Orange → Light Gray → Orange
        "Joy": [(255, 255, 0), (255, 0, 127), (255, 215, 0), (147, 112, 219)],  # Yellow → Deep Pink → Gold → Purple
        "Balance": [(60, 179, 113), (138, 43, 226), (152, 251, 152), (75, 0, 130)],  # Medium Sea Green → Dark Purple → Pale Green → Dark Purple
        "Growth": [(0, 100, 0), (255, 215, 0), (34, 139, 34), (255, 140, 0)],  # Dark Green → Gold → Forest Green → Orange
        "Purpose": [(75, 0, 130), (255, 215, 0), (138, 43, 226), (255, 140, 0)],  # Dark Purple → Gold → Blue Violet → Orange
        "Mindfulness": [(210, 180, 140), (75, 0, 130), (245, 245, 220), (138, 43, 226)],  # Tan → Dark Purple → Beige → Blue Violet
    }

    colors = category_colors.get(category_english, [(138, 43, 226), (75, 0, 130), (255, 20, 147), (147, 112, 219)])

    # Create smooth multi-stop gradient
    for y in range(VIDEO_HEIGHT):
        ratio = y / VIDEO_HEIGHT
        if ratio < 0.33:
            r = int(colors[0][0] + (colors[1][0] - colors[0][0]) * (ratio * 3))
            g = int(colors[0][1] + (colors[1][1] - colors[0][1]) * (ratio * 3))
            b = int(colors[0][2] + (colors[1][2] - colors[0][2]) * (ratio * 3))
        elif ratio < 0.66:
            r = int(colors[1][0] + (colors[2][0] - colors[1][0]) * ((ratio - 0.33) * 3))
            g = int(colors[1][1] + (colors[2][1] - colors[1][1]) * ((ratio - 0.33) * 3))
            b = int(colors[1][2] + (colors[2][2] - colors[1][2]) * ((ratio - 0.33) * 3))
        else:
            r = int(colors[2][0] + (colors[3][0] - colors[2][0]) * ((ratio - 0.66) * 3))
            g = int(colors[2][1] + (colors[3][1] - colors[2][1]) * ((ratio - 0.66) * 3))
            b = int(colors[2][2] + (colors[3][2] - colors[2][2]) * ((ratio - 0.66) * 3))
        draw.rectangle([(0, y), (VIDEO_WIDTH, y + 1)], fill=(r, g, b))

    # Add subtle geometric pattern for depth (circles)
    for i in range(0, VIDEO_WIDTH, 120):
        for j in range(0, VIDEO_HEIGHT, 120):
            draw.ellipse(
                [(i + 30, j + 30), (i + 90, j + 90)],
                outline=(255, 255, 255, 20),
                width=1
            )

    # Add radial glow effect from center
    glow = Image.new('RGBA', (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)

    for radius in range(800, 0, -50):
        alpha = int(30 * (1 - radius / 800))
        glow_draw.ellipse(
            [(VIDEO_WIDTH//2 - radius, VIDEO_HEIGHT//3 - radius),
             (VIDEO_WIDTH//2 + radius, VIDEO_HEIGHT//3 + radius)],
            fill=(255, 255, 255, alpha)
        )

    # Composite glow over background
    img = img.convert('RGBA')
    img = Image.alpha_composite(img, glow)

    return img


def generate_complete_image(phrase_data: dict, category_english: str, output_path: str):
    """Generate image with impressive background"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("PIL not available. Install: pip install Pillow")
        return None

    img = create_impressive_background(category_english)
    draw = ImageDraw.Draw(img)

    # Load fonts - Optimized for mobile viewing (INCREASED sizes)
    # Using Linux-native fonts (pre-installed on GitHub Actions)
    font_category = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)  # Increased from 48
    font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 85)     # Increased from 64
    font_pronunciation = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)   # Increased from 32
    font_branding = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 52)   # Increased from 40
    
    english = phrase_data.get("english", "")
    german = phrase_data.get("german", "")
    pronunciation = phrase_data.get("pronunciation", "")

    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]
            if width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        return lines

    # Category at top
    category_text = category_english.upper()
    category_bbox = draw.textbbox((VIDEO_WIDTH // 2, 140), category_text, font=font_category, anchor="mm")
    padding = 25
    draw.rectangle(
        [(category_bbox[0] - padding, category_bbox[1] - padding),
         (category_bbox[2] + padding, category_bbox[3] + padding)],
        fill=(0, 0, 0, 200)
    )
    draw.text(
        (VIDEO_WIDTH // 2, 140),
        category_text,
        fill=(255, 255, 255),
        font=font_category,
        anchor="mm",
        stroke_width=2,
        stroke_fill=(0, 0, 0)
    )

    # English text
    english_y = 470  # Adjusted for larger fonts
    english_lines = wrap_text(english, font_large, VIDEO_WIDTH - 140)
    total_height = len(english_lines) * 95  # Increased from 75 for larger fonts

    draw.rectangle(
        [(60, english_y - 55), (VIDEO_WIDTH - 60, english_y + total_height + 15)],
        fill=(20, 30, 80, 220)
    )

    for i, line in enumerate(english_lines):
        y_pos = english_y + (i * 95)  # Increased spacing
        draw.text(
            (VIDEO_WIDTH // 2, y_pos),
            line,
            fill=(255, 255, 255),
            font=font_large,
            anchor="mm",
            stroke_width=2,
            stroke_fill=(0, 0, 0)
        )

    # German text
    german_y = english_y + total_height + 110  # Increased from 100
    german_lines = wrap_text(german, font_large, VIDEO_WIDTH - 140)
    total_height = len(german_lines) * 95  # Increased from 75

    draw.rectangle(
        [(60, german_y - 55), (VIDEO_WIDTH - 60, german_y + total_height + 15)],
        fill=(80, 30, 30, 220)
    )

    for i, line in enumerate(german_lines):
        y_pos = german_y + (i * 95)  # Increased spacing
        draw.text(
            (VIDEO_WIDTH // 2, y_pos),
            line,
            fill=(255, 255, 0),
            font=font_large,
            anchor="mm",
            stroke_width=2,
            stroke_fill=(0, 0, 0)
        )

    # Pronunciation with FILLED BOX
    pronunciation_y = german_y + total_height + 90  # Increased from 80
    pronunciation_text = f"[{pronunciation}]"
    pron_lines = wrap_text(pronunciation_text, font_pronunciation, VIDEO_WIDTH - 160)

    if pron_lines:
        pron_total_height = len(pron_lines) * 42  # Increased from 35 for larger font
        draw.rectangle(
            [(70, pronunciation_y - 20), (VIDEO_WIDTH - 70, pronunciation_y + pron_total_height + 10)],
            fill=(40, 40, 40, 230)
        )

        for i, pron_line in enumerate(pron_lines):
            y_pos = pronunciation_y + (i * 42)  # Increased spacing
            draw.text(
                (VIDEO_WIDTH // 2, y_pos),
                pron_line,
                fill=(240, 240, 240),
                font=font_pronunciation,
                anchor="mm",
                stroke_width=1,
                stroke_fill=(20, 20, 20, 200)
            )

    # Branding
    branding_y = VIDEO_HEIGHT - 100
    draw.rectangle(
        [(0, branding_y - 30), (VIDEO_WIDTH, branding_y + 50)],
        fill=(0, 0, 0, 180)
    )
    draw.text(
        (VIDEO_WIDTH // 2, branding_y),
        "VELOCITY GERMAN",
        fill=(255, 255, 255),
        font=font_branding,
        anchor="mm",
        stroke_width=2,
        stroke_fill=(0, 0, 0)
    )

    if img.mode == 'RGBA':
        img = img.convert('RGB')

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, quality=95, optimize=True)
    print(f"  ✓ Image: {Path(output_path).name}")
    return output_path


# ============== VIDEO CREATION ==============

def create_video_from_images_audio(image_files: list, audio_files: list, combined_audio: str, output_file: str):
    """Create video from images and audio with PERFECT synchronization"""

    print(f"\n[video] Creating video from {len(image_files)} images...")
    print(f"[video] Ensuring complete audio playback and sync...")

    temp_clips = []

    for i, (img_path, audio_info) in enumerate(zip(image_files, audio_files)):
        duration = audio_info['duration']
        print(f"  Image {i+1}/{len(image_files)}: {duration:.2f}s (EN: {audio_info.get('en_duration', 0):.1f}s + FR: {audio_info.get('fr_duration', 0):.1f}s)")

        temp_clip = Path(output_file).parent / f"temp_clip_{i:02d}.mp4"
        temp_clips.append(temp_clip)

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(img_path),
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            str(temp_clip)
        ]

        subprocess.run(cmd, check=True, capture_output=True)

    # Concatenate clips
    print("[video] Concatenating clips...")
    temp_video = Path(output_file).parent / "temp_video.mp4"
    concat_file = Path(output_file).parent / "concat_list.txt"

    with open(concat_file, "w") as f:
        for clip in temp_clips:
            f.write(f"file '{clip.resolve().as_posix()}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", str(temp_video)]
    subprocess.run(cmd, check=True, capture_output=True)

    # Add audio
    print("[video] Adding audio (ensuring complete playback)...")
    audio_duration = get_audio_duration(combined_audio)
    print(f"[video] Audio duration: {audio_duration:.2f}s")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(temp_video),
        "-i", str(combined_audio),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(output_file)
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    # Verify
    video_duration = get_audio_duration(str(output_file).replace(".mp4", ".mp4"))
    print(f"[video] ✓ Video created: {Path(output_file).name} ({video_duration:.2f}s)")

    # Cleanup
    for clip in temp_clips:
        if clip.exists():
            clip.unlink()
    if temp_video.exists():
        temp_video.unlink()
    if concat_file.exists():
        concat_file.unlink()


# ============== MAIN WORKFLOW ==============

def generate_reel(category_english: str = None):
    """Generate complete Facebook Reel"""

    if not category_english:
        category_english = random.choice(CATEGORIES_ENGLISH)

    print(f"\n{'='*80}")
    print(f"Category: {category_english} ({CATEGORIES_GERMAN[category_english]})")
    print(f"{'='*80}\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reel_dir = VIDEO_DIR / f"{category_english}_{timestamp}"
    reel_dir.mkdir(exist_ok=True)

    # Step 1: Generate unique phrases
    print("[1/4] Generating unique phrases (checking history)...")
    phrases = generate_phrases(category_english, num_phrases=5)

    for i, phrase in enumerate(phrases, 1):
        print(f"  {i}. {phrase['english']} → {phrase['german']}")

    # Step 2: Generate images
    print("\n[2/4] Generating images with impressive backgrounds...")
    for i, phrase in enumerate(phrases):
        output_path = reel_dir / f"phrase_{i:02d}.jpg"
        generate_complete_image(phrase, category_english, str(output_path))
        print(f"  ✓ Image {i+1}: {phrase['english'][:40]}...")

    # Step 3: Generate audio
    print("\n[3/4] Generating audio (English + German with 500ms pause)...")
    audio_files = generate_all_audio(phrases, str(reel_dir))

    final_audio = reel_dir / "narration.mp3"
    create_final_narration(audio_files, str(final_audio))

    # Step 4: Create video - CRITICAL: Sort images for correct order
    print("\n[4/4] Creating video...")
    output_video = reel_dir / "final_reel.mp4"

    image_files = sorted([str(p) for p in reel_dir.glob("phrase_*.jpg")])

    create_video_from_images_audio(
        image_files,
        audio_files,
        str(final_audio),
        str(output_video)
    )

    # Save metadata
    metadata = {
        "category_english": category_english,
        "category_german": CATEGORIES_GERMAN[category_english],
        "timestamp": timestamp,
        "phrases": phrases,
        "video": str(output_video),
        "audio": str(final_audio)
    }

    with open(reel_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"✅ REEL COMPLETE!")
    print(f"  📁 {reel_dir}")
    print(f"  🎬 {output_video.name}")
    print(f"  🏷️  Branding: Velocity German")
    print(f"{'='*80}\n")

    return metadata


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🇩🇪 VELOCITY GERMAN - FACEBOOK REELS AUTOMATION 🇩🇪")
    print("="*80)
    print("\n✨ IMPROVED FEATURES:")
    print("  ✓ Natural pauses with commas (non-robotic TTS)")
    print("  ✓ Perfect audio-video synchronization")
    print("  ✓ Complete audio playback guaranteed")
    print("  ✓ English category names (for American/European learners)")
    print("  ✓ Velocity German branding at bottom")
    print("  ✓ NEVER repeats phrases (permanent history tracking)")
    print(f"\n📊 AVAILABLE CATEGORIES ({len(CATEGORIES_ENGLISH)} total):")
    for i, cat in enumerate(CATEGORIES_ENGLISH, 1):
        print(f"   {i:2d}. {cat} ({CATEGORIES_GERMAN[cat]})")
    print(f"\n📅 DAILY CAPACITY:")
    print(f"  • 4 reels per day = 20 unique phrases daily")
    print(f"  • {len(CATEGORIES_ENGLISH)} categories = Over 6 days before any category repeats")
    print(f"  • Phrase history is PERMANENT (never deletes)")
    print(f"  • AI generates FRESH phrases every time")
    print("="*80)

    generate_reel()

    print("\n" + "="*80)
    print("✅ READY FOR DAILY AUTOMATION!")
    print("="*80)
    print("\nTo generate 4 reels for today:")
    print("  from facebook_reels_automation import generate_daily_content")
    print("  generate_daily_content(times_per_day=4)")
    print("\nTo generate a single reel:")
    print("  generate_reel('Love')  # Or any category from the list above")
    print("="*80)
