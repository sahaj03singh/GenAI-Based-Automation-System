from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import re


def get_dom(url="https://automationexercise.com"):
    options = Options()
    options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    dom = driver.page_source

    driver.quit()
    return dom


def clean_dom(dom):
    """
    Reduce DOM size and remove noise for LLM
    """

    # Remove scripts & styles
    dom = re.sub(r"<script.*?>.*?</script>", "", dom, flags=re.DOTALL)
    dom = re.sub(r"<style.*?>.*?</style>", "", dom, flags=re.DOTALL)

    # Remove extra whitespace
    dom = re.sub(r"\s+", " ", dom)

    # Trim length (VERY IMPORTANT for token limit)
    return dom[:8000]