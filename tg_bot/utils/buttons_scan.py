import asyncio
from urllib.parse import urlparse
from playwright.async_api import async_playwright


BLACKLIST_TEXTS = {
    "made on tilda",
}


def _is_external_link(href: str, base_url: str) -> bool:
    if not href or href.startswith("#"):
        return False
    return urlparse(href).netloc not in ("", urlparse(base_url).netloc)


def _is_blacklisted(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return normalized in BLACKLIST_TEXTS


async def scan_buttons(url: str) -> list[str]:
    buttons: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60_000,
        )

        elements = await page.query_selector_all(
            "button, a, input[type=submit], input[type=button], [role=button], [onclick]"
        )

        for el in elements:
            text = (await el.inner_text() or "").strip()
            if not text:
                continue

            if _is_blacklisted(text):
                continue

            # ❌ меню / header / footer
            is_in_layout = await el.evaluate(
                """
                el => {
                    let p = el;
                    while (p) {
                        if (
                            ['NAV', 'HEADER', 'FOOTER'].includes(p.tagName) ||
                            (p.className && typeof p.className === 'string' &&
                             p.className.match(/menu|nav|footer/i))
                        ) return true;
                        p = p.parentElement;
                    }
                    return false;
                }
                """
            )
            if is_in_layout:
                continue

            tag = await el.evaluate("el => el.tagName.toLowerCase()")

            is_visual_button = (
                tag in ("button", "input")
                or await el.evaluate(
                    "el => window.getComputedStyle(el).cursor === 'pointer'"
                )
            )

            is_external = False
            if tag == "a":
                href = await el.get_attribute("href")
                is_external = _is_external_link(href, url)

            if is_visual_button or is_external:
                buttons.append(text)

        await browser.close()

    return list(dict.fromkeys(buttons))


if __name__ == "__main__":
    async def _run():
        site_url = "https://project18058216.tilda.ws/"
        result = await scan_buttons(site_url)

        print("Найденные кнопки:")
        for r in result:
            print("-", r)

    asyncio.run(_run())
