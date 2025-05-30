from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import random
import pygetwindow as gw

MAX_WAIT = 10
MAX_RETRY = 5
MAX_SCROLLS = 40
REVIEW_PER_LOAD = 20


class GoogleMapsScraper:
    def __init__(self, debug=True, loadmore_fullxpath=None, newest_fullxpath=None):
        self.debug = debug
        self.loadmore_fullxpath = loadmore_fullxpath
        self.newest_fullxpath = newest_fullxpath
        self.driver = self.__get_driver()

    def __get_driver(self):
        # "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --remote-debugging-port=9222 --user-data-dir="C:\edge-dev-profile"
        edge_options = Options()
        if not self.debug:
            edge_options.add_argument("--headless")
        else:
            edge_options.add_argument("--window-size=1366,768")

        edge_options.add_argument("--accept-lang=id-ID")

        edge_options.add_experimental_option(
            "debuggerAddress", "localhost:9222")
        input_driver = webdriver.Edge(options=edge_options)

        return input_driver

    def start(self, url):
        self.driver.get(url)
        wait = WebDriverWait(self.driver, MAX_WAIT)
        time.sleep(5)
        # open dropdown menu
        clicked = False
        tries = 0
        while not clicked and tries < MAX_RETRY:
            try:
                # Activate the Edge window
                # win = gw.getWindowsWithTitle('Edge')[0]
                # win.activate()
                # time.sleep(1) 
                
                # wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'GmP9w')))
                menu_bt = wait.until(EC.element_to_be_clickable(
                    (By.XPATH, self.newest_fullxpath)))
                time.sleep(1)
                menu_bt.click()
                
                clicked = True
                time.sleep(3)
            except Exception as e:
                tries += 1
                # Optionally print the exception for debugging
                print(f"Click failed: {e}")
            if tries == MAX_RETRY:
                return -1
        time.sleep(5)
        return 0

    def expand_review(self):
        # Click all visible "Selengkapnya" buttons to expand full captions
        try:
            buttons = self.driver.find_elements(
                By.XPATH, '//a[contains(@class, "MtCSLb") and contains(text(), "Selengkapnya")]')
            for btn in buttons:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                    time.sleep(0.2)  # slight delay between clicks
                except Exception:
                    continue
        except Exception:
            pass

    def load_until_count(self, target_count):
        """Load more reviews until at least target_count review items are present."""
        response = BeautifulSoup(self.driver.page_source, 'html.parser')
        rblock = response.find_all('div', class_='bwb7ce')
        total_review_html = len(rblock)

        total_load_iteration = (
            target_count - total_review_html) / REVIEW_PER_LOAD
        current_load_iteration = 0
        while current_load_iteration < total_load_iteration:
            try:
                print(
                    f"[DEBUG] Loading more reviews: iteration {total_review_html + current_load_iteration*20}")
                self.load_more()
                current_load_iteration += 1
                delay = random.uniform(0, 1)
                time.sleep(delay)
            except Exception:
                break  # stop if cannot load more

    def load_more(self):
        start_time = time.time()
        load_more_bt = WebDriverWait(self.driver, 100).until(
            EC.element_to_be_clickable((By.XPATH, self.loadmore_fullxpath)))
        load_more_bt.click()
        elapsed = time.time() - start_time
        print(f"[DEBUG] took {elapsed:.2f} seconds")
        # Scroll a bit to keep the page 'alive'
        try:
            self.driver.execute_script("window.scrollBy(0, 200);")
            time.sleep(0.2)
            self.driver.execute_script("window.scrollBy(0, -200);")
            time.sleep(0.2)
        except Exception:
            pass

    def __parse(self, review):
        # reviewer name
        name = review.find('div', class_='Vpc5Fe')
        name = name.get_text(strip=True) if name else ''

        # username (profile link)
        user_link = review.find('a', class_='yC3ZMb')
        username = ''
        if user_link and user_link.has_attr('href'):
            username = user_link['href']

        # user photo profile
        photo_div = review.find('div', class_='wSokxc')
        user_photo = ''
        if photo_div and photo_div.has_attr('style'):
            # style="background-image: url('...');"
            import re
            m = re.search(r'url\([\'"]?([^\'")]+)', photo_div['style'])
            if m:
                user_photo = m.group(1)

        # rating (count only filled stars)
        rating_div = review.find('div', class_='dHX2k')
        rating = ''
        if rating_div:
            stars = rating_div.find_all('svg', class_='ePMStd')
            rating = 0
            for star in stars:
                path = star.find('path')
                if path and path.get('fill') == '#fabb05':
                    rating += 1

        # review timestamp
        time_tag = review.find('span', class_='y3Ibjb')
        timestamp = time_tag.get_text(strip=True) if time_tag else ''

        # caption
        caption_div = review.find('div', class_='OA1nbd')
        caption = caption_div.get_text(
            separator=' ', strip=True) if caption_div else ''

        # Extract special sections from <div class="zMjRQd">
        waktu_kunjungan = ''
        waktu_antrean = ''
        reservasi = ''
        if caption_div:
            special_div = caption_div.find('div', class_='zMjRQd')
            if special_div:
                special_items = special_div.find_all('div', recursive=False)
                # The structure is: label, value, <br>, label, value, <br>, label, value
                labels = [div.get_text(strip=True).lower() for div in special_items if div.get(
                    'style') == 'font-weight: 500;']
                values = [div.get('aria-label', div.get_text(strip=True)) for div in special_items if div.get(
                    'aria-label') or div.get('style') != 'font-weight: 500;']
                # Map labels to values
                for i, label in enumerate(labels):
                    if 'waktu kunjungan' in label and i < len(values):
                        waktu_kunjungan = values[i]
                    elif 'waktu antrean' in label and i < len(values):
                        waktu_antrean = values[i]
                    elif 'reservasi' in label or 'sebaiknya buat reservasi' in label and i < len(values):
                        reservasi = values[i]
                # Remove the special section from caption
                special_div.extract()
                caption = caption_div.get_text(separator=' ', strip=True)

        # review id (from parent div with class 'bwb7ce')
        review_id = review.get('data-id', '')

        return {
            'name': name,
            'username': username,
            'user_photo': user_photo,
            'rating': rating,
            'timestamp': timestamp,
            'caption': caption,
            'review_id': review_id,
            'waktu_kunjungan': waktu_kunjungan,
            'waktu_antrean': waktu_antrean,
            'reservasi': reservasi
        }

    def expand_and_parse_batch(self, start, end):
        """Expand and parse reviews from index start to end (exclusive)."""
        self.expand_review()
        time.sleep(1)
        response = BeautifulSoup(self.driver.page_source, 'html.parser')
        rblock = response.find_all('div', class_='bwb7ce')
        parsed_reviews = []
        for index, review in enumerate(rblock):
            if start <= index < end:
                r = self.__parse(review)
                parsed_reviews.append(r)
        return parsed_reviews
