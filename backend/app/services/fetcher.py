import asyncio
import os
import re
from collections import defaultdict
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.config import get_settings

settings = get_settings()
BASE_URL = "https://eriskip.com"

# Блокировки для предотвращения "гонки" (race condition)
download_locks = defaultdict(asyncio.Lock)


def sanitize_filename(name: str) -> str:
    """Очистка имени файла от недопустимых символов."""
    return re.sub(r'[\\/*?:"<>|]', "_", name)


async def find_and_download_pdf(device_name: str) -> Optional[str]:
    """
    Ищет документацию на сайте и скачивает PDF.
    Возвращает путь к локальному файлу или None.
    """
    if not device_name:
        return None

    async with download_locks[device_name]:
        save_dir = os.path.join(settings.DATA_DIR, "knowledge_base")
        os.makedirs(save_dir, exist_ok=True)

        filename = f"{sanitize_filename(device_name)}.pdf"
        filepath = os.path.join(save_dir, filename)

        # 1. Проверка локального кэша
        if os.path.exists(filepath):
            print(f"Found cached PDF for {device_name}")
            return filepath

        print(f"Searching online for {device_name}...")

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            try:
                # 2. Поиск прибора
                search_url = f"{BASE_URL}/ru/products"
                resp = await client.get(search_url, params={"q": device_name})
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "html.parser")

                # ОБНОВЛЕННЫЙ СЕЛЕКТОР: Ищем ссылку внутри div.item -> h3 -> a
                product_link_tag = soup.select_one("div.item h3 a")

                if not product_link_tag:
                    print(f"Device {device_name} not found in search results.")
                    return None

                product_url = product_link_tag["href"]
                if not product_url.startswith("http"):
                    product_url = BASE_URL + product_url

                # 3. Переход на страницу товара
                prod_resp = await client.get(product_url)
                prod_resp.raise_for_status()
                prod_soup = BeautifulSoup(prod_resp.text, "html.parser")

                # 4. Поиск ссылки на PDF в блоке файлов
                # ОБНОВЛЕННАЯ ЛОГИКА: Ищем в div.files ссылки, оканчивающиеся на .pdf
                pdf_link = None
                files_div = prod_soup.find("div", class_="files")

                if files_div:
                    for a in files_div.find_all("a", href=True):
                        href = a["href"]
                        text = a.get_text().lower()
                        # Ищем именно руководство по эксплуатации
                        if href.endswith(".pdf") and (
                            "руководство" in text or "эксплуатации" in text
                        ):
                            pdf_link = href
                            break

                if not pdf_link:
                    print(f"PDF manual link not found on page {product_url}")
                    return None

                if not pdf_link.startswith("http"):
                    pdf_link = BASE_URL + pdf_link

                # 5. Скачивание файла
                print(f"Downloading PDF from {pdf_link}...")
                pdf_resp = await client.get(pdf_link)
                pdf_resp.raise_for_status()

                with open(filepath, "wb") as f:
                    f.write(pdf_resp.content)

                return filepath

            except Exception as e:
                print(f"Error fetching PDF for {device_name}: {e}")
                return None
