import argparse
import copy
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime
from typing import Dict, List, Tuple, Union

import coloredlogs
from dotenv import load_dotenv
from flask import Flask, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# Last output of the monitor (aka data-layer, lol)
OUTPUT = {}


class GhiseulMonitor:

    # Pages required by the monitor
    login_page: str = "https://www.ghiseul.ro/ghiseul/public/"
    debit_page: str = "https://www.ghiseul.ro/ghiseul/public/debite"

    # Login elements
    login_username_element: str = "username"
    login_password_element: str = "passwordP"
    login_passwordT_element: str = "passwordT"
    login_form_element: str = "login"

    # Debit elements
    debit_show_element: str = "showDebiteBtn_"
    debit_pay_form: str = "detalii_"

    # Output dict
    output: Dict[str, Union[str, float, bool, dict]] = {
        "flows": {},
        "success": False,
        "error": "",
        "duration": 0.0,
        "date": ""
    }

    # Shortcut variables
    short_delay: float = 0.5
    flows: List[str] = ["login", "debit"]

    def __init__(
            self,
            username: str,
            password: str,
            institution: int,
            persistent_driver: bool,
            render_timeout: int,
            driver_dir: str):

        # Set attributes
        self.username = username
        self.password = password
        self.institution = institution
        self.persistent_driver = persistent_driver
        self.render_timeout = render_timeout
        self.driver_dir = driver_dir

        # Create a long-living driver
        if self.persistent_driver:
            self.__create_driver()

    def run(self, refresh: int) -> None:
        """Method to be executed in a separate thread. It self.execute every refresh minutes"""
        global OUTPUT

        i = 0
        log.info(
            f"Starting ghiseul.ro monitor {"with" if self.persistent_driver else "without"} persistent driver, institution={self.institution}, refresh={refresh}m")
        while True:
            log.info(f"Starting iteration {i}...")

            # Create an ephemeral driver
            if not self.persistent_driver:
                self.__create_driver()

            # Execute the monitor flows and send the ouput to the global OUTPUT
            OUTPUT = self.execute()
            log.info(f"Finished iteration {i}, sleeping for {refresh} minutes. Current output={OUTPUT}")

            # Sleep for refresh time
            time.sleep(refresh*60)
            i += 1

            # Close the ephemeral driver
            if not self.persistent_driver:
                self.driver.quit()

    def execute(self) -> Dict[str, Union[str, float, bool]]:
        """Method to run the monitor once and return the output"""

        # Clone the output dict
        output = copy.deepcopy(self.output)
        output["date"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Run flows
        for flow in self.flows:
            log.info(f"Starting '{flow}' flow.")
            flow_timer = time.time()
            flow_output, flow_err = getattr(self, f"_{flow}")()
            flow_timer = time.time() - flow_timer
            log.info(
                f"Flow '{flow}' finished: "
                f"status={"success" if flow_output else "fail"}, "
                f"duration={round(flow_timer, 2)}s"
            )
            output["flows"][flow] = flow_output
            output["error"] = f"{output["error"]}{flow.upper()}: {flow_err}; " if flow_err else output["error"]
            output["duration"] = round(output["duration"] + flow_timer, 2)

        # Final log output
        output["success"] = False not in [output["flows"][f] for f in self.flows]
        log.info(f"Main flow finished: success={output["success"]}, duration={output["duration"]}s, output={output}")

        return output

    def quit(self) -> None:
        self.driver.quit()

    def _login(self) -> Tuple[bool, str]:
        """
        Visits the login page and login with username and password. The procedure goes like this:

        1. Visit self.login_page
        2. Get all required elements from DOM
        3. Wait for the form to be rendered in the driver, with self.render_timeout as timeout in seconds
        4. Click the username field and fill in self.username, wait self.short_delay
        5. Click on the passwordT element to make the actual password field interactable
        6. Click on the password field and fill in self.password, wait self.short_delay
        7. Submit the form
        """

        # Visit the login page
        self.driver.get(self.login_page)

        # Check if we are already logged in and skip the execution
        if not self.driver.current_url == self.login_page:
            log.warning(
                f"Redirected to {self.driver.current_url}, marking 'login' flow sucessfull and skipping execution.")
            return True, ""

        # Find form, username and password input fields
        try:
            login_form = self.wait.until(EC.visibility_of_element_located(
                (By.ID, self.login_form_element)
            ))
            username_field = self.driver.find_element(By.ID, self.login_username_element)
            password_field = self.driver.find_element(By.ID, self.login_password_element)
            passwordT_field = self.driver.find_element(By.ID, self.login_passwordT_element)
        except Exception:
            err = "Could not find login for or input fields"
            print(traceback.format_exc())
            return False, err
        log.debug("Found login form and input fields")

        # Enter username and password with short delays
        try:
            username_field.click()
            username_field.send_keys(self.username)
            time.sleep(self.short_delay)

            passwordT_field.click()
            password_field.click()
            password_field.send_keys(self.password)
            time.sleep(self.short_delay)
        except Exception:
            err = "Could not fill in login form"
            print(traceback.format_exc())
            return False, err
        log.debug("Filled in login form")

        # Submit the form
        try:
            login_form.submit()
        except Exception:
            err = "Could not submit login form"
            print(traceback.format_exc())
            return False, err
        log.debug("Submitted login form")

        # Everything went as expected
        return True, ""

    def _debit(self) -> Tuple[bool, str]:
        """
        Visits the debit page after login and checks if the payment button is active. The procedure goes like this:

        1. Visit self.debit_page
        2. Wait for the institution element (acordion) to be visible
        3. Wait for the "Sume de plata" (show_element) to be visible and click it
        4. Wait for the "Plateste" button (pay_element) to be visible.

        If the pay_element is visible, the communication with PCC server works correctly.
        """

        # Visit the debit page if we are not already there
        if not self.driver.current_url == self.debit_page:
            self.driver.get(self.debit_page)

        # Find the institution acordion and wait for it to be rendered
        try:
            inst_element = self.wait.until(EC.visibility_of_element_located(
                (By.ID, str(self.institution))
            ))
        except Exception:
            err = "Could not find institution element"
            print(traceback.format_exc())
            return False, err
        log.debug("Found institution element")

        # Wait until the show element is present and click it
        try:
            show_element = self.wait.until(EC.visibility_of_element_located(
                (By.ID, f"{self.debit_show_element}{self.institution}")
            ))
            show_element.click()
        except Exception:
            err = "Could not find show button for instituion"
            print(traceback.format_exc())
            return False, err
        log.debug("Submitted institution show button")

        # Wait for the pay form to be rendered
        try:
            pay_element = self.wait.until(EC.visibility_of_element_located(
                (By.ID, f"{self.debit_pay_form}{self.institution}")
            ))
        except Exception:
            err = "Could not find pay button for instituion"
            print(traceback.format_exc())
            return False, err
        log.debug("Found institution pay button")

        # Everything went as expected
        return True, ""

    def __create_driver(self):
        """
        Instantiate the Chrome driver with user-data dir to save cookies
        """

        driver_options = Options()
        driver_options.add_argument("--user-data-dir=/tmp/chrome")
        driver_options.add_argument("--headless")
        driver_options.add_argument("--no-sandbox")
        driver_options.add_argument("--window-size=1920,1080")
        driver_options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(options=driver_options)
        self.wait = WebDriverWait(self.driver, timeout=self.render_timeout)


if __name__ == "__main__":

    # Load .env file
    load_dotenv()

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="ghiseul.ro monitor")
    parser.add_argument(
        "--username",
        type=str,
        default=os.environ.get("GHISEUL_USERNAME", ""),
        help="Username to be used for logging in. Environment variable: GHISEUL_USERNAME.",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=os.environ.get("GHISEUL_PASSWORD", ""),
        help="Password to be used for logging in. Environment variable: GHISEUL_PASSWORD.",
    )
    parser.add_argument(
        "--institution",
        type=str,
        default=os.environ.get("GHISEUL_INSTITUTION", ""),
        help="Institution ID to monitor. Environment variable: GHISEUL_INSTITUTION.",
    )
    parser.add_argument(
        "--refresh",
        type=int,
        default=int(os.environ.get("GHISEUL_REFRESH", "10")),
        help="How often to refresh the monitor, in minutes. Environment variable: GHISEUL_REFRESH.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("GHISEUL_TIMEOUT", "30")),
        help="How much time will the browser wait for elements to be rendered. Environment variable: GHISEUL_TIMEOUT.",
    )
    parser.add_argument(
        "--persistent-driver",
        action=argparse.BooleanOptionalAction,
        default=os.environ.get("GHISEUL_PERSISTENT_DRIVER", "true").lower() in ("true", "1", "t", "yes"),
        help="Keep the same browser window open for each check or create a new one each time. Environment variable: GHISEUL_PERSISTENT_DRIVER.",
    )
    parser.add_argument(
        "--driver-dir",
        type=str,
        default=os.environ.get("GHISEUL_DRIVER_DIR", "/tmp/chrome"),
        help="Where to store driver data. Environment variable: GHISEUL_DRIVER_DIR.",
    )
    parser.add_argument(
        "--web-host",
        type=str,
        default=os.environ.get("GHISEUL_WEB_HOST", "0.0.0.0"),
        help="Host to listen for web traffic. Environment variable: GHISEUL_WEB_HOST.",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=int(os.environ.get("GHISEUL_WEB_PORT", "8080")),
        help="Port to listen for web traffic. Environment variable: GHISEUL_WEB_PORT.",
    )
    parser.add_argument(
        "--web-endpoint",
        type=str,
        default=os.environ.get("GHISEUL_WEB_ENDPOINT", "/monitor"),
        help="Endpoint to expose the monitor output. Environment variable: GHISEUL_WEB_ENDPOINT.",
    )
    parser.add_argument(
        "--log-level",
        choices=["INFO", "WARN", "DEBUG"],
        default=os.environ.get("GHISEUL_LOG_LEVEL", "INFO"),
        help="Log level. Environment variable: GHISEUL_LOG_LEVEL.",
    )
    args = parser.parse_args()

    # Logger
    log = logging.getLogger("monitor")
    coloredlogs.install(level=args.log_level)

    # Instantiate monitor
    monitor = GhiseulMonitor(
        username=args.username,
        password=args.password,
        institution=args.institution,
        persistent_driver=args.persistent_driver,
        render_timeout=args.timeout,
        driver_dir=args.driver_dir
    )

    # Threads list
    threads = []

    # Run the monitor in a "thread", every args.refresh minutes
    monitor_thread = threading.Thread(target=monitor.run, kwargs={"refresh": args.refresh})
    threads.append(monitor_thread)

    # Create the flask app and define the monitor route
    webapp = Flask("ghiseul.ro monitor")

    @webapp.route(args.web_endpoint)
    def monitor_route():
        global OUTPUT
        return jsonify(OUTPUT)

    # Run the webserver in a "thread"
    webapp_thread = threading.Thread(target=lambda: webapp.run(
        host=args.web_host,
        port=args.web_port,
        use_reloader=False,
        debug=args.log_level == "DEBUG")
    )
    threads.append(webapp_thread)

    # Start threads
    for t in threads:
        t.start()

    # Endless loop
    try:
        while True:
            pass
    except KeyboardInterrupt:
        monitor.quit()
        for t in threads:
            t.join()
        log.error("Quiting...")
        sys.exit(1)
