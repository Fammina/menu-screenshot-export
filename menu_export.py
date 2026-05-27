#!/usr/bin/env python3
"""
LeggiMenu Renderer - Professional Version

FEATURES
--------
- Render pagina con Playwright
- Screenshot preciso della card menu
- Bordi arrotondati + shadow
- Estrazione logo reale renderizzato
- Header superiore elegante e robusto
- Background uniforme
- Padding laterali professionali
- Cleanup automatico file temporanei

PYTHON 3.11+
"""

import sys
import subprocess
import logging
import time
import os

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from PIL import Image

# ============================================================
# CONFIG
# ============================================================

URL = "https://www.leggimenu.it/menu/79skddaj79s2/201374"

OUTPUT_FILE = "output.jpg"
LOGO_TMP_FILE = "logo_tmp.png"

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
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

# ============================================================
# DEPENDENCIES
# ============================================================

def ensure_python_dependencies():
    import importlib

    required = {
        "playwright": "playwright",
        "PIL": "pillow",
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
# PAGE
# ============================================================

def load_page(page):
    logger.info("Caricamento pagina...")

    page.goto(URL, wait_until="domcontentloaded")

    page.wait_for_timeout(3000)

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except:
        logger.warning("networkidle non raggiunto (ok per SPA)")

    logger.info("Pagina caricata.")

# ============================================================
# STYLE
# ============================================================

def inject_style(page):
    logger.info("Applico stile custom...")

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

    locator.wait_for(
        state="visible",
        timeout=20000
    )

    logger.info("Card trovata.")

    return locator

# ============================================================
# MENU SCREENSHOT
# ============================================================

def take_menu_screenshot(locator):
    logger.info("Creo screenshot menu...")

    locator.scroll_into_view_if_needed()

    time.sleep(1.5)

    locator.screenshot(
        path=OUTPUT_FILE,
        type="jpeg",
        quality=95
    )

# ============================================================
# LOGO SCREENSHOT
# ============================================================

def capture_logo(page):
    logger.info("Cattura logo...")

    try:
        logo = page.locator(LOGO_SELECTOR).first

        logo.wait_for(timeout=10000)

        logo.screenshot(path=LOGO_TMP_FILE)

        logger.info("Logo catturato.")

        return True

    except Exception as e:
        logger.warning(f"Impossibile catturare logo: {e}")
        return False

# ============================================================
# FINAL COMPOSITION
# ============================================================

def compose_final_image():
    logger.info("Composizione immagine finale...")

    base = Image.open(OUTPUT_FILE).convert("RGBA")

    logo_exists = os.path.exists(LOGO_TMP_FILE)

    if logo_exists:
        logo = Image.open(LOGO_TMP_FILE).convert("RGBA")
    else:
        logo = None

    # --------------------------------------------------------
    # Dimensioni finali
    # --------------------------------------------------------

    final_width = base.width + (SIDE_PADDING * 2)

    final_height = (
        base.height
        + TOP_SECTION_HEIGHT
        + BOTTOM_PADDING
    )

    final_img = Image.new(
        "RGBA",
        (final_width, final_height),
        BACKGROUND_COLOR
    )

    # --------------------------------------------------------
    # Inserimento logo
    # --------------------------------------------------------

    if logo:

        max_logo_width = int(final_width * LOGO_MAX_WIDTH_RATIO)

        ratio = logo.height / logo.width

        logo = logo.resize(
            (
                max_logo_width,
                int(max_logo_width * ratio)
            )
        )

        logo_x = (final_width - logo.width) // 2

        # centratura verticale nella top section
        logo_y = (TOP_SECTION_HEIGHT - logo.height) // 2

        final_img.paste(
            logo,
            (logo_x, logo_y),
            logo
        )

    # --------------------------------------------------------
    # Inserimento menu
    # --------------------------------------------------------

    menu_x = SIDE_PADDING
    menu_y = TOP_SECTION_HEIGHT

    final_img.paste(
        base,
        (menu_x, menu_y),
        base
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    final_img.convert("RGB").save(
        OUTPUT_FILE,
        "JPEG",
        quality=95
    )

    logger.info("Immagine finale creata.")

# ============================================================
# CLEANUP
# ============================================================

def cleanup():
    if os.path.exists(LOGO_TMP_FILE):
        try:
            os.remove(LOGO_TMP_FILE)
            logger.info("Cleanup logo_tmp completato.")
        except Exception as e:
            logger.warning(f"Cleanup fallito: {e}")

# ============================================================
# MAIN
# ============================================================

def main():
    try:
        ensure_python_dependencies()
        ensure_playwright()

        with sync_playwright() as p:

            browser = p.chromium.launch(
                headless=True
            )

            page = browser.new_page(
                viewport=VIEWPORT
            )

            load_page(page)

            inject_style(page)

            target = get_target(page)

            take_menu_screenshot(target)

            capture_logo(page)

            compose_final_image()

            browser.close()

        cleanup()

        print(f"Immagine salvata con successo: {OUTPUT_FILE}")

    except PlaywrightTimeoutError as e:
        logger.error("Timeout Playwright")
        logger.error(str(e))
        cleanup()
        sys.exit(1)

    except Exception as e:
        logger.exception("Errore imprevisto")
        cleanup()
        sys.exit(1)

# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    main()