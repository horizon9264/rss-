import openpyxl
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import datetime

# --- Configuration ---
EXCEL_FILE_PATH = "C:\\Users\\ym\\Desktop\\3.0\\已签约居民健康档案.xlsx"
LOG_FILE_PATH = "processing_log.txt"
URL = "https://ggws.hnhfpc.gov.cn/FormMain.aspx"

# --- Logging Setup ---
def log_message(message):
    """Logs a message to the console and a file with a timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")

# --- Excel Data Reader ---
def get_id_cards(file_path):
    """Reads ID card numbers from the first column of an Excel file."""
    try:
        workbook = openpyxl.load_workbook(file_path)
        sheet = workbook.active
        id_cards = [sheet.cell(row=i, column=1).value for i in range(1, sheet.max_row + 1)]
        # Filter out empty cells
        id_cards = [str(id_card) for id_card in id_cards if id_card]
        log_message(f"Successfully loaded {len(id_cards)} ID card numbers from {file_path}")
        return id_cards
    except FileNotFoundError:
        log_message(f"Error: The file {file_path} was not found.")
        return []
    except Exception as e:
        log_message(f"An error occurred while reading the Excel file: {e}")
        return []

# --- Main Automation Logic ---
def main():
    id_card_list = get_id_cards(EXCEL_FILE_PATH)
    if not id_card_list:
        log_message("No ID card numbers to process. Exiting.")
        return

    # --- Browser Setup ---
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("window-size=1920x1080")
    chrome_options.add_argument("--start-maximized")

    service = Service(ChromeDriverManager().install())
    driver = None

    try:
        log_message("Starting browser...")
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        log_message(f"Opening URL: {URL}")
        driver.get(URL)

        input("Browser is ready. Press Enter to start the automated processing...")

        wait = WebDriverWait(driver, 10)

        for index, id_card_number in enumerate(id_card_list):
            log_message(f"Processing item {index + 1}/{len(id_card_list)}: {id_card_number}")
            
            try:
                # After a submission, the page should be ready for the next entry without a refresh.
                # The script will now proceed to find the input elements for the next ID.


                # 1. Switch to the first iframe and enter the ID
                log_message("Switching to input iframe (index 1)...")
                driver.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it(1))
                
                id_card_input_selector = (By.NAME, "SFZH")
                id_card_input = wait.until(EC.visibility_of_element_located(id_card_input_selector))
                
                log_message(f"Entering ID: {id_card_number}")
                id_card_input.clear()
                id_card_input.send_keys(id_card_number)
                id_card_input.send_keys(Keys.RETURN)

                # 2. Wait for the result and double-click it
                log_message("Waiting for search result...")
                first_row_selector = (By.CSS_SELECTOR, "tr.ev_dhx_skyblue")
                first_result_row = wait.until(EC.element_to_be_clickable(first_row_selector))
                
                log_message("Found result. Double-clicking it.")
                actions = ActionChains(driver)
                actions.double_click(first_result_row).perform()
                
                # 3. Switch to the second iframe and click Submit
                log_message("Switching to submit iframe (index 2)...")
                driver.switch_to.default_content()
                wait.until(EC.frame_to_be_available_and_switch_to_it(2))

                submit_button_selector = (By.ID, "btnSave")
                submit_button = wait.until(EC.element_to_be_clickable(submit_button_selector))

                log_message("Scrolling to and clicking 'Submit' button.")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                time.sleep(0.5) # Short pause to ensure scrolling is complete
                submit_button.click()

                # 4. Handle the confirmation popup
                log_message("Handling confirmation popup...")
                driver.switch_to.default_content()
                confirm_button_selector = (By.CSS_SELECTOR, "div.dhtmlx_popup_button[result='true']")
                confirm_button = wait.until(EC.element_to_be_clickable(confirm_button_selector))
                
                log_message("Clicking confirmation button.")
                confirm_button.click()
                
                log_message(f"Successfully processed ID: {id_card_number}")
                
                # A short pause before the next iteration
                time.sleep(2)

            except Exception as e:
                log_message(f"An error occurred while processing {id_card_number}: {e}")
                log_message("Skipping to the next ID card number.")
                driver.switch_to.default_content() # Reset context before next attempt
                continue

    except Exception as e:
        log_message(f"A critical error occurred: {e}")
    
    finally:
        if driver:
            log_message("All tasks completed. Closing browser in 5 seconds...")
            time.sleep(5)
            driver.quit()
        log_message("Script finished.")

if __name__ == "__main__":
    main()
