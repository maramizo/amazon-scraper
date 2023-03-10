import contextlib
from typing import TypedDict
from bs4 import BeautifulSoup
from selenium import webdriver
import pandas as pd
import chromedriver_binary  # noqa
from urllib.parse import urlsplit
import re


driver = webdriver.Chrome()


class Product(TypedDict):
    asin: str
    name: str
    price: float
    brand: str
    images: list[str]
    description: str
    additional_info: list[dict]


Products = list[Product]


def get_product_info(url: str) -> Product:
    """ Get product info from a given amazon url """
    driver.get(url)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    name = soup.find("span", {"id": "productTitle"}).text.strip()
    price = soup.find("span", {"class": "a-price-whole"})
    price = float(price.text.strip().replace(",", "")) if price else None
    if not price:
        price = soup.find("span", {"class": "a-price a-text-price a-size-medium apexPriceToPay"})
        price = price.find("span", {"class": "a-offscreen"}).text.strip() if price else None
        price = re.sub(r"[^\d.]", "", price)
    images = [image["src"] for image in soup.find_all("img", {"class": "a-dynamic-image"})]
    description = soup.find("div", {"id": "productDescription"}).find("p")
    description = description.text.strip() if description else ""
    brand = soup.find("a", {"id": "bylineInfo"})
    brand = brand.text.strip().replace("Brand: ", "") if brand else ""
    asin = soup.find("input", {"id": "ASIN"})["value"]
    additional_info = []
    for info in soup.find_all("div", {"class": "a-section a-spacing-small a-spacing-top-small"}):
        info_name = info.find("span", {"class": "a-size-base a-text-bold"}).text.strip()
        info_value = info.find("span", {"class": "a-size-base po-break-word"}).text.strip()
        additional_info.append({info_name: info_value})
    return {
        "name": name,
        "asin": asin,
        "price": price,
        "brand": brand,
        "images": images,
        "description": description,
        "additional_info": additional_info
    }


def get_all_products(url: str) -> Products:
    """ Get all products from a given amazon url """
    products = []
    driver.get(url)
    current_url = driver.current_url
    scheme, netloc = urlsplit(current_url).scheme, urlsplit(current_url).netloc
    base_url = f"{scheme}://{netloc}"
    next_page = True
    while next_page:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        next_page = None
        with contextlib.suppress(Exception):
            next_page = driver.find_element("xpath", "//li[@class='a-last']/a")
        for product in soup.find_all("div", {"data-component-type": "s-search-result"}):
            if isinstance(product, dict):
                continue
            product_url = base_url + product.find("span", {"data-component-type": "s-product-image"}).find("a")["href"]
            product_info = get_product_info(product_url)
            products.append(product_info)
        next_page and next_page.click()
    driver.close()
    return products


def change_images_to_columns(df: pd.DataFrame) -> pd.DataFrame:
    """ Change images column to multiple columns """

    images = df["images"].apply(pd.Series)
    images.columns = ["IMAGE " + str(x) for x in images.columns]
    df = pd.concat([df, images], axis=1)
    df.drop("images", axis=1, inplace=True)
    return df


def main():
    url = input("Enter the url: ")
    products = get_all_products(url)
    df = pd.DataFrame(products)
    df = change_images_to_columns(df)
    df.to_csv("products.csv", index=False)


if __name__ == '__main__':
    main()
