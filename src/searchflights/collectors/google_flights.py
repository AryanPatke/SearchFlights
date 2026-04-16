"""Google Flights fare collector using Playwright with interactive form fill."""

from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import datetime

from playwright.async_api import Browser, Locator, Page, Playwright, async_playwright

from ..config import settings
from ..models import Fare, SearchLeg
from .base import BaseCollector

logger = logging.getLogger(__name__)

_GOOGLE_FLIGHTS_URL = "https://www.google.com/travel/flights"
_LISTITEM_PRICE_RE = re.compile(r"₹([\d,]+)")
_LISTITEM_STOPS_RE = re.compile(r"(\d+)\s+stop|Nonstop", re.IGNORECASE)
_LISTITEM_DURATION_RE = re.compile(
    r"(\d+)\s*hr(?:\s+(\d+)\s*min)?", re.IGNORECASE
)


class GoogleFlightsCollector(BaseCollector):
    """Scrapes Google Flights by filling the search form via Playwright."""

    def __init__(self) -> None:
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None
        self._current_origin: str | None = None
        self._current_dest: str | None = None

    # -- lifecycle ------------------------------------------------------------

    async def setup(self) -> None:
        self._pw = await async_playwright().start()
        launch_kwargs: dict = {"headless": settings.headless}
        if settings.proxy_url:
            launch_kwargs["proxy"] = {"server": settings.proxy_url}
        self._browser = await self._pw.chromium.launch(**launch_kwargs)
        self._page = await self._browser.new_page(
            viewport={"width": 1280, "height": 900},
            locale="en-US",
        )
        await self._page.goto(
            f"{_GOOGLE_FLIGHTS_URL}?hl={settings.hl}&gl={settings.gl}",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        await self._page.wait_for_timeout(3000)
        await self._dismiss_consent(self._page)
        await self._wait_for_form(self._page)

    async def _dismiss_consent(self, page: Page) -> None:
        """Dismiss Google cookie-consent or ToS dialogs if present."""
        for label in [
            "Accept all",
            "Reject all",
            "I agree",
            "Accept",
            "Consent",
        ]:
            btn = page.get_by_role("button", name=label)
            try:
                await btn.wait_for(state="visible", timeout=2000)
                await btn.click()
                logger.info("Dismissed consent dialog via '%s'.", label)
                await page.wait_for_timeout(2000)
                return
            except Exception:
                continue

    async def _wait_for_form(self, page: Page) -> None:
        """Wait until the flights search form is interactive."""
        for label in ["Where from?", "Where to?"]:
            combo = page.get_by_role("combobox", name=label)
            try:
                await combo.wait_for(state="visible", timeout=10_000)
            except Exception:
                logger.warning("Form field '%s' not visible after 10 s.", label)

    async def teardown(self) -> None:
        if self._page:
            await self._page.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    # -- public ---------------------------------------------------------------

    async def collect(self, leg: SearchLeg) -> list[Fare]:
        if not self._page:
            raise RuntimeError("Collector not initialised; use `async with`.")

        try:
            fares = await self._search(leg)
        except Exception:
            logger.exception(
                "Failed to collect fares for %s -> %s on %s",
                leg.origin, leg.destination, leg.departure_date,
            )
            await self._save_debug_screenshot(leg)
            fares = []
            await self._recover()

        await self._random_delay()
        return fares

    async def _save_debug_screenshot(self, leg: SearchLeg) -> None:
        """Save a screenshot for post-mortem debugging."""
        try:
            assert self._page is not None
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = f"debug_{leg.origin}_{leg.destination}_{ts}.png"
            await self._page.screenshot(path=path, full_page=True)
            logger.info("Debug screenshot saved to %s", path)
        except Exception:
            pass

    async def _recover(self) -> None:
        """Navigate back to the flights landing page after a failure."""
        try:
            assert self._page is not None
            self._current_origin = None
            self._current_dest = None
            await self._page.goto(
                f"{_GOOGLE_FLIGHTS_URL}?hl={settings.hl}&gl={settings.gl}",
                wait_until="domcontentloaded",
                timeout=15_000,
            )
            await self._page.wait_for_timeout(2000)
            await self._dismiss_consent(self._page)
            await self._wait_for_form(self._page)
        except Exception:
            logger.warning("Recovery navigation failed.", exc_info=True)

    # -- search flow ----------------------------------------------------------

    async def _search(self, leg: SearchLeg) -> list[Fare]:
        page = self._page
        assert page is not None

        if self._current_origin != leg.origin:
            await self._fill_airport(page, "Where from?", leg.origin)
            self._current_origin = leg.origin

        if self._current_dest != leg.destination:
            await self._fill_airport(page, "Where to?", leg.destination)
            self._current_dest = leg.destination

        # Close any lingering popups/dropdowns before touching the date fields.
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

        await self._fill_dates(page, leg)
        await self._click_search(page)
        await page.wait_for_timeout(5000)

        if await self._detect_captcha(page):
            logger.warning(
                "CAPTCHA detected for %s -> %s; skipping.",
                leg.origin, leg.destination,
            )
            return []

        return await self._extract_fares(page, leg)

    # -- form helpers ---------------------------------------------------------

    async def _fill_airport(self, page: Page, label: str, code: str) -> None:
        """Click the airport combobox, clear it, type the IATA code, and
        select the first suggestion."""
        combo = page.get_by_role("combobox", name=label)
        await combo.wait_for(state="visible", timeout=10_000)
        await combo.click()
        await page.wait_for_timeout(500)

        # Google may open an inner input once the combo is clicked.
        # Try the inner expanded one first, fall back to the original.
        targets = [
            page.locator(f'input[aria-label="{label}"]').last,
            combo,
        ]
        typed = False
        for target in targets:
            try:
                await target.wait_for(state="visible", timeout=2000)
                await target.fill("")
                await page.wait_for_timeout(200)
                await target.type(code, delay=100)
                typed = True
                break
            except Exception:
                continue

        if not typed:
            logger.warning("Could not type into '%s' input; trying keyboard.", label)
            await page.keyboard.type(code, delay=100)

        await page.wait_for_timeout(1500)

        # Pick the first option from the suggestion listbox.
        first_option = page.get_by_role("option").first
        try:
            await first_option.wait_for(state="visible", timeout=3000)
            await first_option.click()
        except Exception:
            logger.debug("No autocomplete options for %s; pressing Enter.", code)
            await page.keyboard.press("Enter")

        await page.wait_for_timeout(500)

    async def _fill_dates(self, page: Page, leg: SearchLeg) -> None:
        dep_str = leg.departure_date.strftime("%b %d").replace(" 0", " ")
        ret_str = leg.return_date.strftime("%b %d").replace(" 0", " ")

        # Try multiple selectors for the departure date input.
        dep_input = await self._find_date_input(page, "Departure")
        await dep_input.click()
        await page.wait_for_timeout(800)

        # After clicking, an inner input may appear inside the date-picker overlay.
        target_dep = await self._find_date_input(page, "Departure", prefer_last=True)
        await target_dep.fill(dep_str)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(800)

        target_ret = await self._find_date_input(page, "Return", prefer_last=True)
        await target_ret.fill(ret_str)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(800)

        # Click the "Done" button if present to close the date picker.
        done_btn = page.get_by_role("button", name=re.compile(r"^Done"))
        try:
            await done_btn.wait_for(state="visible", timeout=3000)
            await done_btn.click()
            await page.wait_for_timeout(500)
        except Exception:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)

    async def _find_date_input(
        self, page: Page, label: str, *, prefer_last: bool = False
    ) -> Locator:
        """Find a visible date input by trying multiple selector strategies."""
        # Strategy 1: get_by_role textbox
        locator = page.get_by_role("textbox", name=label)
        try:
            count = await locator.count()
            if count > 0:
                target = locator.last if (prefer_last and count > 1) else locator.first
                await target.wait_for(state="visible", timeout=5000)
                return target
        except Exception:
            pass

        # Strategy 2: CSS selector by placeholder or aria-label
        for sel in [
            f'input[placeholder="{label}"]',
            f'input[aria-label="{label}"]',
        ]:
            loc = page.locator(sel).first
            try:
                await loc.wait_for(state="visible", timeout=3000)
                return loc
            except Exception:
                continue

        # Strategy 3: label-based
        loc = page.get_by_label(label).first
        try:
            await loc.wait_for(state="visible", timeout=3000)
            return loc
        except Exception:
            pass

        raise RuntimeError(f"Could not find date input for '{label}'")

    async def _click_search(self, page: Page) -> None:
        search_btn = page.get_by_role("button", name="Search")
        try:
            await search_btn.wait_for(state="visible", timeout=3000)
            await search_btn.click()
        except Exception:
            logger.debug("Search button not found; pressing Enter.")
            await page.keyboard.press("Enter")

    # -- captcha detection ----------------------------------------------------

    async def _detect_captcha(self, page: Page) -> bool:
        visible_text = await page.inner_text("body")
        lower = visible_text.lower()
        blocking_phrases = [
            "unusual traffic from your computer",
            "our systems have detected unusual traffic",
            "please show you're not a robot",
            "are you a robot",
            "before you continue to google",
        ]
        if any(phrase in lower for phrase in blocking_phrases):
            return True
        captcha_frame = await page.query_selector(
            'iframe[src*="recaptcha"], iframe[title*="reCAPTCHA"]'
        )
        if captcha_frame and await captcha_frame.is_visible():
            return True
        return False

    # -- result extraction ----------------------------------------------------

    async def _extract_fares(self, page: Page, leg: SearchLeg) -> list[Fare]:
        """Extract fares from the flight result link descriptions.

        Each flight result card is an <a> with an aria-label like:
        "From 69685 Indian rupees round trip total. 1 stop flight with
        Qatar Airways. Leaves ... at 4:10 AM ... arrives ... at 2:25 PM ..."
        """
        search_url = page.url
        fares: list[Fare] = []

        links = await page.query_selector_all("a")
        for link in links:
            try:
                name = await link.get_attribute("aria-label") or ""
                if not name:
                    name = (await link.inner_text()).strip()
            except Exception:
                continue

            if "indian rupees round trip" not in name.lower():
                continue

            fare = self._parse_link_description(name, leg, search_url)
            if fare:
                fares.append(fare)

        if not fares:
            fares = await self._extract_from_listitems(page, leg, search_url)

        # Deduplicate by price (same price on the same leg is the same flight).
        seen: set[float] = set()
        unique: list[Fare] = []
        for fare in fares:
            if fare.price not in seen:
                seen.add(fare.price)
                unique.append(fare)
        fares = unique

        logger.info(
            "Extracted %d fare(s) for %s -> %s on %s.",
            len(fares), leg.origin, leg.destination, leg.departure_date,
        )
        return fares

    async def _extract_from_listitems(
        self, page: Page, leg: SearchLeg, search_url: str
    ) -> list[Fare]:
        """Fallback: parse listitem inner text for basic price/stops info."""
        items = await page.query_selector_all("ul > li")
        fares: list[Fare] = []

        for item in items:
            try:
                text = (await item.inner_text()).strip()
            except Exception:
                continue

            if "round trip" not in text.lower():
                continue

            fare = self._parse_listitem(text, leg, search_url)
            if fare:
                fares.append(fare)

        return fares

    # -- text parsers ---------------------------------------------------------

    def _parse_listitem(
        self, text: str, leg: SearchLeg, search_url: str = ""
    ) -> Fare | None:
        """Parse the compact listitem text format.

        Example: "4:10 AM BOM 2:25 PM CDG ₹69,685 round trip 1 stop 13 hr 45 min Qatar Airways"
        """
        price_m = _LISTITEM_PRICE_RE.search(text)
        if not price_m:
            return None

        try:
            price = float(price_m.group(1).replace(",", ""))
        except ValueError:
            return None

        if price < 500 or price > 10_000_000:
            return None

        stops = self._parse_stops(text)
        duration = self._parse_duration(text)
        airline = self._parse_airline_from_listitem(text)

        return Fare(
            origin=leg.origin,
            destination=leg.destination,
            departure_date=leg.departure_date,
            return_date=leg.return_date,
            airline=airline,
            stops=stops,
            duration_hours=duration,
            price=price,
            currency=leg.currency,
            source="google_flights",
            collected_at=datetime.utcnow(),
            booking_url=search_url,
        )

    def _parse_link_description(
        self, text: str, leg: SearchLeg, search_url: str = ""
    ) -> Fare | None:
        """Parse the verbose link aria-label format.

        Example: "From 69685 Indian rupees round trip total. 1 stop flight
        with Qatar Airways. Leaves Chhatrapati Shivaji ... at 4:10 AM on
        Wednesday, July 1 and arrives at Paris Charles de Gaulle ... at
        2:25 PM on Wednesday, July 1. Total duration 13 hr 45 min."
        """
        price_m = re.search(r"From\s+([\d,]+)\s+Indian rupees", text)
        if not price_m:
            return None

        try:
            price = float(price_m.group(1).replace(",", ""))
        except ValueError:
            return None

        if price < 500 or price > 10_000_000:
            return None

        stops = 0
        stops_m = re.search(r"(\d+)\s+stop", text, re.IGNORECASE)
        if stops_m:
            stops = int(stops_m.group(1))
        elif "nonstop" in text.lower():
            stops = 0

        airline = "N/A"
        airline_m = re.search(r"flight with\s+(.+?)\.", text)
        if airline_m:
            raw = airline_m.group(1).strip()
            airline = raw if self._is_valid_airline(raw) else "N/A"

        duration = 0.0
        dur_m = re.search(r"(?:Total duration|duration)\s+(\d+)\s*hr(?:\s+(\d+)\s*min)?", text, re.IGNORECASE)
        if dur_m:
            duration = round(int(dur_m.group(1)) + (int(dur_m.group(2)) / 60 if dur_m.group(2) else 0), 2)
        else:
            dur_m2 = _LISTITEM_DURATION_RE.search(text)
            if dur_m2:
                duration = round(int(dur_m2.group(1)) + (int(dur_m2.group(2)) / 60 if dur_m2.group(2) else 0), 2)

        return Fare(
            origin=leg.origin,
            destination=leg.destination,
            departure_date=leg.departure_date,
            return_date=leg.return_date,
            airline=airline,
            stops=stops,
            duration_hours=duration,
            price=price,
            currency=leg.currency,
            source="google_flights",
            collected_at=datetime.utcnow(),
            booking_url=search_url,
        )

    # -- field extractors -----------------------------------------------------

    @staticmethod
    def _parse_stops(text: str) -> int:
        lower = text.lower()
        if "nonstop" in lower:
            return 0
        m = re.search(r"(\d+)\s*stop", lower)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _parse_duration(text: str) -> float:
        m = _LISTITEM_DURATION_RE.search(text)
        if not m:
            return 0.0
        hours = int(m.group(1))
        mins = int(m.group(2)) if m.group(2) else 0
        return round(hours + mins / 60, 2)

    @staticmethod
    def _parse_airline_from_listitem(text: str) -> str:
        """Extract the airline name from listitem text.

        The inner_text() is multi-line.  The airline line sits somewhere
        after the flight-time line and before the duration line.  We scan
        all lines in that range and return the first valid airline,
        skipping separators or other non-airline text.
        """
        _TIME_RE = re.compile(
            r"^\d{1,2}:\d{2}\s*(?:AM|PM)", re.IGNORECASE
        )
        _DUR_RE = re.compile(r"^\d+\s*hr", re.IGNORECASE)

        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        found_time = False
        for line in lines:
            if _TIME_RE.match(line):
                found_time = True
                continue
            if found_time:
                if _DUR_RE.match(line):
                    found_time = False
                    continue
                candidate = re.sub(r"\s+", " ", line).strip()
                if GoogleFlightsCollector._is_valid_airline(candidate):
                    result = GoogleFlightsCollector._fix_concatenated_airlines(candidate)
                    return result[:80]

        return "N/A"

    @staticmethod
    def _fix_concatenated_airlines(text: str) -> str:
        """Split airline names that were concatenated without a separator.

        Google Flights renders each airline in its own <span>; inner_text()
        joins them without spaces, e.g. "Air AstanaAir India".  We detect
        the boundary where a lowercase letter is immediately followed by an
        uppercase letter starting a word of 3+ chars (to avoid splitting
        names like "IndiGo").
        """
        return re.sub(r"([a-z])([A-Z][a-z]{2,})", r"\1, \2", text)

    @staticmethod
    def _is_valid_airline(value: str) -> bool:
        """Return True if *value* looks like a real airline name."""
        if not value or len(value) < 3:
            return False
        v = value.strip()
        if re.match(r"^[A-Z]{2,4}$", v):
            return False
        if re.search(r"[A-Z]{3}\s*[\u2013\-–]\s*[A-Z]{3}", v):
            return False
        reject = [
            "international airport", "airport", "kg co2",
            "emissions", "round trip", "nonstop", "stop",
        ]
        lower = v.lower()
        if any(r in lower for r in reject):
            return False
        return True

    @staticmethod
    async def _random_delay() -> None:
        delay = random.uniform(settings.min_delay, settings.max_delay)
        await asyncio.sleep(delay)
