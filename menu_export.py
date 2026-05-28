#!/usr/bin/env python3
"""
LeggiMenu Renderer - Professional Version

FEATURES
--------
- Legge lista URL da menus.csv
- Crea cartella temp ad ogni avvio
- Render pagina con Playwright
- Screenshot preciso della card menu
- Bordi arrotondati + shadow
- Estrazione logo reale renderizzato
- Header superiore elegante e robusto
- Background uniforme
- Padding laterali professionali
- Cleanup automatico file temporanei e cartella temp

PYTHON 3.11+
"""

import sys
import csv
import subprocess
import logging
import time
import os
import shutil
import glob

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from PIL import Image

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
# ============================================================

MENUS_FILE = os.environ.get("MENUS_FILE")

if not MENUS_FILE:
    logger.error("Variabile d'ambiente MENUS_FILE non configurata.")
    sys.exit(1)

TEMP_DIR = "temp"
TARGET_SELECTOR = 'div.card.card-style[id^="voce-"]'
LOGO_SELECTOR = "a.header-logo"

VIEWPORT = {
    "width": 1920,
    "height": 1080
}

# ============================================================
# LAYOUT CONFIG
# ============================================================

SIDE_PADDING = 24
BOTTOM_PADDING = 24
TOP_SECTION_HEIGHT = 240
LOGO_MAX_WIDTH_RATIO = 0.28

BACKGROUND_COLOR = (245, 245, 245, 255)

# ============================================================
# DEPENDENCIES
# ============================================================

def ensure_python_dependencies():
    import importlib

    required = {
        "playwright": "playwright",
        "PIL": "pillow",
        "requests": "requests",
    }

    missing = []

    for module, pip_name in required.items():
        try:
            importlib.import_module(module)
        except ImportError:
            missing.append(pip_name)

    if missing:
        logger.info(f"Installazione dipendenze mancanti: {missing}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", *missing],
            check=True
        )

# ============================================================
# PLAYWRIGHT
# ============================================================

def ensure_playwright():
    logger.info("Verifica Playwright browser...")
    subprocess.run(
        [sys.executable, "-m", "playwright", "install"],
        check=True
    )

# ============================================================
# TEMP DIR
# ============================================================

def create_temp_dir():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        logger.info("Cartella temp precedente rimossa.")

    os.makedirs(TEMP_DIR)
    logger.info(f"Cartella temp creata: {TEMP_DIR}/")

def cleanup_temp_dir():
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        logger.info("Cartella temp eliminata.")

# ============================================================
# CSV
# ============================================================

def load_menus():
    logger.info(f"Lettura {MENUS_FILE}...")

    menus = []

    with open(MENUS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            menus.append({
                "id": row["id"].strip(),
                "url": row["url"].strip(),
                "descrizione": row["descrizione"].strip(),
            })

    logger.info(f"Trovate {len(menus)} voci.")
    return menus

# ============================================================
# PAGE
# ============================================================

def load_page(page, url):
    logger.info(f"Caricamento pagina: {url}")

    page.goto(url, wait_until="domcontentloaded")

    page.wait_for_timeout(3000)

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        logger.warning("networkidle non raggiunto (ok per SPA)")

    logger.info("Pagina caricata.")

# ============================================================
# STYLE
# ============================================================

def inject_style(page):
    page.add_style_tag(content="""
        .card.card-style {
            border-radius: 18px !important;
            overflow: hidden !important;
            box-shadow: 0 12px 30px rgba(0,0,0,0.18) !important;
        }
    """)

# ============================================================
# TARGET
# ============================================================

def get_target(page):
    logger.info("Cerco card menu...")

    page.wait_for_function(
        """() => document.querySelectorAll('div.card.card-style[id^="voce-"]').length > 0""",
        timeout=20000
    )

    locator = page.locator(TARGET_SELECTOR).first
    locator.wait_for(state="visible", timeout=20000)

    logger.info("Card trovata.")
    return locator

# ============================================================
# MENU SCREENSHOT
# ============================================================

def take_menu_screenshot(locator, output_file):
    logger.info("Creo screenshot menu...")

    locator.scroll_into_view_if_needed()
    time.sleep(1.5)

    locator.screenshot(
        path=output_file,
        type="png"
    )

# ============================================================
# LOGO SCREENSHOT
# ============================================================

def capture_logo(page, logo_tmp_file):
    logger.info("Cattura logo...")

    try:
        logo = page.locator(LOGO_SELECTOR).first
        logo.wait_for(timeout=10000)
        logo.screenshot(path=logo_tmp_file)
        logger.info("Logo catturato.")
        return True
    except Exception as e:
        logger.warning(f"Impossibile catturare logo: {e}")
        return False

# ============================================================
# FINAL COMPOSITION
# ============================================================

def compose_final_image(output_file, logo_tmp_file):
    logger.info("Composizione immagine finale...")

    base = Image.open(output_file).convert("RGBA")

    logo = None
    if os.path.exists(logo_tmp_file):
        logo = Image.open(logo_tmp_file).convert("RGBA")

    final_width = base.width + (SIDE_PADDING * 2)
    final_height = base.height + TOP_SECTION_HEIGHT + BOTTOM_PADDING

    final_img = Image.new("RGBA", (final_width, final_height), BACKGROUND_COLOR)

    if logo:
        max_logo_width = int(final_width * LOGO_MAX_WIDTH_RATIO)
        ratio = logo.height / logo.width
        logo = logo.resize((max_logo_width, int(max_logo_width * ratio)))
        logo_x = (final_width - logo.width) // 2
        logo_y = (TOP_SECTION_HEIGHT - logo.height) // 2
        final_img.paste(logo, (logo_x, logo_y), logo)

    final_img.paste(base, (SIDE_PADDING, TOP_SECTION_HEIGHT), base)

    final_img.save(output_file, "PNG")

    logger.info("Immagine finale creata.")

# ============================================================
# CLEANUP LOGO TMP
# ============================================================

def cleanup_logo_tmp(logo_tmp_file):
    if os.path.exists(logo_tmp_file):
        try:
            os.remove(logo_tmp_file)
        except Exception as e:
            logger.warning(f"Cleanup logo_tmp fallito: {e}")

# ============================================================
# UPLOAD SUPABASE
# ============================================================

def upload_to_supabase(completed):
    import requests

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        logger.error("SUPABASE_URL o SUPABASE_KEY non configurati.")
        sys.exit(1)

    if not completed:
        logger.warning("Nessun file da uploadare.")
        return False

    edge_fn_url = f"{supabase_url}/functions/v1/upload-menu"

    headers = {
        "apikey": supabase_key,
    }

    errors = 0

    for filepath, restaurant_id in completed:
        filename = os.path.basename(filepath)

        try:
            with open(filepath, "rb") as f:
                response = requests.post(
                    edge_fn_url,
                    headers=headers,
                    files={"file": (filename, f, "image/png")},
                    data={
                        "restaurantId": restaurant_id,
                        "menuType": "daily",
                    },
                )

            try:
                body = response.json()
            except Exception:
                body = {"error": "Invalid JSON response"}

            logger.info(f"Edge Function response [{response.status_code}]: {body}")

            if response.ok and body.get("success"):
                logger.info(f"Upload OK: {filename} → {body.get('publicUrl')}")
            else:
                logger.error(f"Upload fallito per {filename}: {body}")
                errors += 1

        except Exception as e:
            logger.error(f"Errore upload {filename}: {e}")
            errors += 1

    if errors == 0:
        logger.info(f"Tutti i {len(completed)} file caricati con successo.")
        return True

    logger.error(f"Upload completato con {errors} errori.")
    return False

# ============================================================
# PROCESS SINGLE MENU
# ============================================================

def process_menu(browser, menu):
    menu_id = menu["id"]
    url = menu["url"]
    descrizione = menu["descrizione"]

    logger.info(f"Inizio elaborazione: {descrizione}")

    timestamp = int(time.time() * 1000)
    output_folder = menu_id
    output_file = os.path.join(TEMP_DIR, f"{menu_id}_{timestamp}.png")
    logo_tmp_file = os.path.join(TEMP_DIR, f"{menu_id}_logo_tmp.png")

    page = browser.new_page(viewport=VIEWPORT)

    try:
        load_page(page, url)
        inject_style(page)
        target = get_target(page)
        take_menu_screenshot(target, output_file)
        capture_logo(page, logo_tmp_file)
        compose_final_image(output_file, logo_tmp_file)

        logger.info(f"Completato: {descrizione} → {output_file}")

        return {
            "ok": True,
            "file": output_file,
            "folder": output_folder,
        }

    except PlaywrightTimeoutError:
        logger.error(f"ho ottenuto un errore leggendo {descrizione} (timeout)")
        return {"ok": False}

    except Exception as e:
        logger.error(f"ho ottenuto un errore leggendo {descrizione}: {e}")
        return {"ok": False}

    finally:
        page.close()
        cleanup_logo_tmp(logo_tmp_file)

# ============================================================
# MAIN
# ============================================================

def main():
    ensure_python_dependencies()
    ensure_playwright()

    menus = load_menus()

    # Crea cartella temp (ricrea se esiste già)
    create_temp_dir()

    errors = 0
    successes = 0
    completed = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for menu in menus:
            result = process_menu(browser, menu)
            if result["ok"]:
                successes += 1
                completed.append((result["file"], result["folder"]))
            else:
                errors += 1

        browser.close()

    print(f"\nScreenshot: {successes} ok, {errors} errori su {len(menus)} totali.")

    # Upload su Supabase e cleanup temp solo se tutto ok
    if successes > 0:
        upload_ok = upload_to_supabase(completed)
        if upload_ok:
            cleanup_temp_dir()
        else:
            logger.warning("Cartella temp NON eliminata a causa di errori nell'upload.")
    else:
        logger.warning("Nessun file generato, upload saltato.")

# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    main()