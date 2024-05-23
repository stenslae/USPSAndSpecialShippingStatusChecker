# Import Statements
import pandas as pd
import numpy as np
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Load arrays onto csv file to flag undelivered rows, and add row of info describing
def infoupdate(filename, statuses, undelivered):
    # Reads original csv file
    df = pd.read_csv(filename)

    # Format arrays to add to DataFrame
    formatstatus = [''] * len(df)
    formatundeliv = [''] * len(df)
    for i in range(len(statuses)):
        if formatstatus[int(statuses[i][0])-2] != '':
            formatstatus[int(statuses[i][0])-2] = formatstatus[int(statuses[i][0])-2] + " and " + statuses[i][1]
        else:
            formatstatus[int(statuses[i][0])-2] = statuses[i][1]
    for i in range(len(undelivered)):
        formatundeliv[int(undelivered[i])-2] = "Yes"

    df['Shipping Status'] = formatstatus
    df['Undelivered?'] = formatundeliv

    # Write updated DataFrame to a new CSV file
    df.to_csv(f'updated_{filename}', index=False)

# DEP
def checkstatus(carrier_name, tracking_number, row, file, custompath, chromedriverpath):
    if 'AMZN' in carrier_name or 'Amazon' in carrier_name:
        delivered = 'Unknown'
    else:
        url = f'https://www.aftership.com/track/{tracking_number}'

        # Set up Selenium
        chrome_options = Options()
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--incognito")  # Open Chrome in incognito mode
        chrome_options.add_argument(f"--user-data-dir={custompath}")  # Specify a custom user data directory

        service = Service(rf'{chromedriverpath}')
        driver = webdriver.Chrome(service=service, options=chrome_options)

        try:
            # Load the page
            driver.get(url)

            # Wait for the shadow host element to be present
            shadow_host = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div#tracking"))
            )

            # Define a function to get the shadow root element using JavaScript
            def expand_shadow_element(element):
                shadow_root = driver.execute_script('return arguments[0].shadowRoot', element)
                return shadow_root

            # Get the shadow root
            shadow_root = expand_shadow_element(shadow_host)

            # Check to see if package was found
            carrier_info_element = WebDriverWait(shadow_root, 20).until(
                lambda d: d.find_element(By.CSS_SELECTOR, ".text-blue-600.cursor-pointer.inline-block")
            )

            if 'Select carrier' in carrier_info_element.text:
                js_code = """
                    const shadowHost = document.querySelector('div#tracking');
                    const shadowRoot = shadowHost.shadowRoot;
                    const clickableElement = shadowRoot.querySelector('.text-blue-600.cursor-pointer.inline-block');
                    const childElement = clickableElement.querySelector('.font-semibold');
                    if (childElement && childElement.innerText.includes('Select carrier')) {
                        childElement.click();  // Click the element
                        return true;  // Indicate the click was performed
                    } else {
                        return false;  // Indicate the element was not found
                    }
                """

                # Execute the JavaScript to click the element
                clicked = driver.execute_script(js_code)

                if clicked:
                    time.sleep(2)  # Adjust sleep time as necessary

                    search_bar = WebDriverWait(driver, 20).until(
                        lambda d: expand_shadow_element(d.find_element(By.CSS_SELECTOR, "div#tracking")).find_element(
                            By.CSS_SELECTOR,
                            ".appearance-none.bg-gray-100.rounded-md.focus\\:outline-none.focus\\:shadow-cool-gray-outline.block.w-full.pl-10.pr-12.transition.ease-in-out.duration-150.py-2")
                    )

                    # Clear the search bar if needed
                    search_bar.clear()
                    search_bar.send_keys(searchNames(carrier_name))

                    # Wait for the search results to load
                    time.sleep(2)
                    search_result = WebDriverWait(driver, 20).until(
                        lambda d: expand_shadow_element(d.find_element(By.CSS_SELECTOR, "div#tracking")).find_element(
                            By.CSS_SELECTOR, ".p-3.hover\\:bg-gray-100.rounded.cursor-pointer.w-1\\/4")
                    )
                    search_result.click()
                    time.sleep(5)  # Adjust sleep time as necessary

            # Locate the tracking info element inside the shadow root
            tracking_info_element = WebDriverWait(shadow_root, 20).until(
                lambda d: d.find_element(By.CSS_SELECTOR, ".ml-3.flex-1.flex-shrink-0")
            )

            # Extract the text from the element
            temp = tracking_info_element.text

        except Exception as e:
            file.write(f"Error for row {row}: {str(e)}\n")
            driver.quit()
            return 'Unknown'

        # Clear browsing data (history, cookies, cache, etc.)
        driver.execute_script("window.localStorage.clear();")
        driver.execute_script("window.sessionStorage.clear();")
        driver.delete_all_cookies()
        driver.quit()

        # Determine if the package was delivered or not
        if 'Unknown' in temp:
            delivered = 'Unknown'
        elif 'Delivered' in temp:
            delivered = 'Delivered'
        elif 'Shipped' in temp:
            delivered = 'Shipped'
        elif 'Not Shipped' in temp:
            delivered = 'Not Shipped'
        else:
            delivered = 'Unknown'
    return delivered

# Read file and return array with carrier name, tracking number, and row number
def inforead(filename):
    # Reads file and takes important info into a DataFrame
    df = pd.read_csv(filename, usecols=['Order ID', 'Carrier Name & Tracking Number'])

    # Initialize lists to store separated values
    carrier_names = []
    tracking_numbers = []

    # Process each row in the DataFrame
    for index, row in df.iterrows():
        carrier_tracking = row['Carrier Name & Tracking Number']

        # Extract carrier name (before the first parenthesis)
        if "(" in carrier_tracking:
            carrier_name = carrier_tracking.split("(")[0].strip()
        else:
            carrier_name = carrier_tracking.strip()
        carrier_names.append(carrier_name)

        # Extract tracking numbers (within parentheses, handling multiple tracking numbers)
        tracking_numbers_list = []
        while "and" in carrier_tracking:
            start = carrier_tracking.find("(") + 1
            end = carrier_tracking.find(")")
            if start < end:
                tracking_number = carrier_tracking[start:end].strip()
                tracking_numbers_list.append(tracking_number)
                carrier_tracking = carrier_tracking[carrier_tracking.find("and") + 3:].strip()
            else:
                break

        # Handle the last or single tracking number
        if "(" in carrier_tracking and ")" in carrier_tracking:
            start = carrier_tracking.find("(") + 1
            end = carrier_tracking.find(")")
            if start < end:
                tracking_number = carrier_tracking[start:end].strip()
                tracking_numbers_list.append(tracking_number)

        tracking_numbers.append(tracking_numbers_list)

    # Prepare the final array
    final_list = []
    for i in range(len(df)):
        order_id = df.loc[i, 'Order ID']
        for tn in tracking_numbers[i]:
            final_list.append([carrier_names[i], tn, i + 2, order_id])

    final = np.array(final_list)

    return final

# Names adjusted for searchbar
def searchNames(carrier_name):
    if 'UPS' in carrier_name or 'ups' in carrier_name:
        return 'UPS'
    if 'DHL' in carrier_name:
        return 'DHL'
    if 'USPS' in carrier_name:
        return 'USPS'
    if 'Yun' in carrier_name:
        return 'YunExpress'
    if 'Tfroce' in carrier_name or 'Tforce' in carrier_name:
        return 'Tforce'
    if 'Ontrac' in carrier_name:
        return 'Ontrac'
    if 'Yanwen' in carrier_name:
        return 'Yanwen'
    if 'EUB' in carrier_name or 'EPacket' in carrier_name:
        return 'China EMS'
    if 'Newgistics' in carrier_name:
        return 'Newgistics'
    if 'Hong Kong' in carrier_name or "HK Post" in carrier_name:
        return 'Hong Kong'
    if 'China' in carrier_name:
        return 'China Post'
    else:
        return 'USPS'
