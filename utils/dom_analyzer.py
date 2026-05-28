from selenium.webdriver.common.by import By

def extract_interactive_elements(driver):
    elements = []

    all_elements = driver.find_elements(By.XPATH, "//*")

    for el in all_elements:
        try:
            text = el.text.strip()
            tag = el.tag_name

            if tag in ["button", "a", "input"] or text:
                elements.append({
                    "text": text.lower(),
                    "tag": tag,
                    "element": el
                })
        except:
            continue

    return elements