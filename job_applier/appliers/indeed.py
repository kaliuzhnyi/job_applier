from typing import NamedTuple

from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync

from job_applier import SETTINGS


class ApiPaths(NamedTuple):
    DOMAIN: str
    LOGIN_PATH: str

    @property
    def LOGIN(self):
        return f"{self.DOMAIN}{self.LOGIN_PATH}"


class Selectors(NamedTuple):
    button_signin: str
    input_jobsearch_title: str
    input_jobsearch_location: str


API_PATHS = ApiPaths(
    DOMAIN="https://ca.indeed.com/",
    # DOMAIN="http://pixelscan.net/",
    LOGIN_PATH="/login"
)

selectors = Selectors(
    button_signin="div[data-gnav-region='Main'] a:has-text('Sign in')",
    input_jobsearch_title="form#jobsearch input#text-input-what",
    input_jobsearch_location=""
)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36"

def apply() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            # executable_path=SETTINGS["appliers"]["properties"]["browser"]["path"],
            # user_data_dir=SETTINGS["appliers"]["properties"]["browser"]["user_data_dir"],
            args=[
                "--disable-blink-features=AutomationControlled",
                f"--user-agent={SETTINGS["appliers"]["properties"]["user_agent"]}",
                "--start-maximized"
            ]
        )

        page = browser.new_page()
        stealth_sync(page)

        page.add_init_script("""
            delete Object.getPrototypeOf(navigator).webdriver;
            window.navigator.chrome = {
                app: {
                    isInstalled: false,
                },
                webstore: {
                    onInstallStageChanged: {},
                    onDownloadProgress: {},
                },
                runtime: {
                    PlatformOs: {
                        MAC: 'mac',
                        WIN: 'win',
                        ANDROID: 'android',
                        CROS: 'cros',
                        LINUX: 'linux',
                        OPENBSD: 'openbsd',
                    },
                    PlatformArch: {
                        ARM: 'arm',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64',
                    },
                    PlatformNaclArch: {
                        ARM: 'arm',
                        X86_32: 'x86-32',
                        X86_64: 'x86-64',
                    },
                    RequestUpdateCheckStatus: {
                        THROTTLED: 'throttled',
                        NO_UPDATE: 'no_update',
                        UPDATE_AVAILABLE: 'update_available',
                    },
                    OnInstalledReason: {
                        INSTALL: 'install',
                        UPDATE: 'update',
                        CHROME_UPDATE: 'chrome_update',
                        SHARED_MODULE_UPDATE: 'shared_module_update',
                    },
                    OnRestartRequiredReason: {
                        APP_UPDATE: 'app_update',
                        OS_UPDATE: 'os_update',
                        PERIODIC: 'periodic',
                    },
                },
            };
        """)

        page.goto("http://pixelscan.net/")

        page.wait_for_load_state("networkidle")

        # context = browser.new_context(
        #     # extra_http_headers={
        #     #     "DNT": "1",  # Do Not Track
        #     #     "Upgrade-Insecure-Requests": "1",
        #     #     "Referer": "https://ca.indeed.com/",
        #     # },
        #
        #     user_agent=SETTINGS["appliers"]["properties"]["user_agent"],
        #     # viewport={
        #     #     "width": int(SETTINGS["appliers"]["properties"]["viewport"]["width"]),
        #     #     "height": int(SETTINGS["appliers"]["properties"]["viewport"]["height"])
        #     # },
        #     # permissions=["geolocation"],
        #     locale=SETTINGS["appliers"]["properties"]["locale"],
        #     timezone_id=SETTINGS["appliers"]["properties"]["timezone"],
        #     bypass_csp=True
        # )
        # page = context.new_page()
        # stealth_sync(page)
        # # page.mouse.move(100, 200, steps=20)
        # page.goto(API_PATHS.DOMAIN)

        input("Please login on the website and then press ENTER ")
