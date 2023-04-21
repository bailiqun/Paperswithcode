import re
import sys
import json
import time

import requests
import os
import datetime
from bs4 import BeautifulSoup
import multiprocessing
import threading
import time


class Timer:
    def __init__(self, interval, callback):
        """
        初始化 Timer 对象
        :param interval: 定时器触发间隔，单位为秒
        :param callback: 定时器触发时执行的回调函数
        """
        self.interval = interval
        self.callback = callback
        self.timer_thread = None
        self.is_running = False
        self.last_time_update = datetime.datetime.now()
        self.start()

    def start(self):
        """
        启动定时器
        """
        self.is_running = True
        self.timer_thread = threading.Thread(target=self.run)
        self.timer_thread.start()

    def stop(self):
        """
        停止定时器
        """
        self.is_running = False
        if self.timer_thread is not None:
            self.timer_thread.join()

    def run(self):
        while self.is_running:
            if (datetime.datetime.now() - self.last_time_update).seconds > self.interval:
                print("start sync.")
                self.callback()
                print(f"cost {(datetime.datetime.now() - self.last_time_update).seconds}")
                self.last_time_update = datetime.datetime.now()
            time.sleep(1)


class PapersWithCode:
    __headers__ = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                 'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}

    def __init__(self):
        self.timer = Timer(3600, self.update)
        self.json_path = os.path.join(os.path.dirname(__file__), "./paper_database.json")

    def request_to_soap(self, url):
        response = requests.get(url, headers=self.__headers__)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup

    @staticmethod
    def download(url, name=None):
        os.makedirs("./static/papers/img", exist_ok=True)
        os.makedirs("./static/papers/pdf", exist_ok=True)
        suffix = url.split('.')[-1].lower()
        filename = url.split('/')[-1] if name is None else f"{name}.{suffix}"
        if filename.split('.')[-1].lower() in ['jpg', 'png', 'bmp', 'gif']:
            file_path = os.path.join("./static/papers/img", filename)
        elif filename.split('.')[-1].lower() in ['pdf']:
            file_path = os.path.join("./static/papers/pdf", filename)
        if os.path.exists(file_path):
            return 0

        try:
            response = requests.get(url, stream=True)
            file_size = int(response.headers.get('Content-Length', 0))
            file_size_mb = file_size / (1024 * 1024)
            with open(file_path, 'wb') as f:
                downloaded_size = 0
                for data in response.iter_content(512):
                    downloaded_size += len(data)
                    downloaded_size_mb = downloaded_size / (1024 * 1024)
                    progress = downloaded_size * 100 // file_size
                    progress_bar = '[' + '=' * progress + ' ' * (100 - progress) + ']'
                    progress_str = f'{progress_bar} {downloaded_size_mb:.2f}MB / {file_size_mb:.2f}MB {filename}'
                    sys.stdout.write(f'\r{progress_str}')
                    sys.stdout.flush()
                    f.write(data)
            print(f'\nDownload {filename} completed. ({downloaded_size_mb:.2f}MB)')
        except Exception as e:
            print(f"raise except, {e}")
            return -1

    def get_papers(self, page):
        papers_list = []
        for i in range(1, page):
            main_url = f"https://paperswithcode.com/?page={i}"
            main_page = self.request_to_soap(main_url)
            infinite_container = main_page.find('div', {'class': 'infinite-container text-center home-page'})
            list_container = infinite_container.find_all('div', {'class': 'row infinite-item item paper-card'})
            for item in list_container:
                div_item_image = item.find('div', {'class': 'col-lg-3 item-image-col'})
                page_url = div_item_image.find('a')['href']
                paper_img = div_item_image.find('div', {'class': 'item-image'})['style']
                match = re.search(r'url\((.*?)\)', paper_img)
                cover_img_url = match.group(1).strip("'\"") if match else ""
                strip_abstract = item.find('div', {'class': 'col-lg-9 item-content'}).find('p', {
                    'class': "item-strip-abstract"}).text.strip()

                github_link = item.find('span', {'class': 'item-github-link'}).find('a').text.strip()
                div_item_interact = item.find('div', {'class': 'col-lg-3 item-interact text-center'})
                entity_stars = div_item_interact.find('span', {"class": "badge badge-secondary"}).text.strip()
                stars_accumulated = div_item_interact.find('div', {"class": "stars-accumulated text-center"}).text.strip()

                detail_page = self.request_to_soap("https://paperswithcode.com" + page_url)
                paper_info = detail_page.find("div", {'class': 'paper-title'})
                paper_date = detail_page.find('div', {'class': 'authors'}).find('span',
                                                                                {'class': 'author-span'}).text.strip()
                paper_authors = detail_page.find('div', {'class': 'authors'}).find_all('a')
                paper_authors = ", ".join([x.text.strip() for x in paper_authors])

                paper_title = paper_info.find("h1").text.strip()
                paper_abstract = detail_page.find('div', {'class': 'paper-abstract'}).find('p').text.strip()
                paper_url = detail_page.find('div', {'class': 'paper-abstract'}).find_all('a')
                paper_url = [add['href'] for add in paper_url][0]
                paper_task = detail_page.find('div', {'class': 'paper-tasks'}).find_all('a')
                paper_task = [x.text.strip() for x in paper_task]

                paper_code_short_list = detail_page.find('div', {'id': 'implementations-short-list'})
                paper_code = paper_code_short_list.find_all('a', {'class': 'code-table-link'})
                paper_code = [x['href'] for x in paper_code]

                self.download(paper_url, paper_title)
                self.download(cover_img_url, paper_title)
                paper = {
                    'title': paper_title,
                    'authors': paper_authors,
                    'gitlab': github_link,
                    'date': paper_date,
                    'cover_img': cover_img_url,
                    'abstract': paper_abstract,
                    'strip_abstract': strip_abstract,
                    'arxiv_url': paper_url,
                    'entity_stars': entity_stars,
                    'stars_accumulated': stars_accumulated,
                    'paper_task': paper_task,
                    'code': paper_code
                }
                papers_list.append(paper)
        return papers_list

    def update(self):
        papers_list = self.get_papers(page=5)
        with open(self.json_path, 'w') as f:
            json.dump(papers_list, f, indent=4)

    def get(self):
        if os.path.exists(self.json_path):
            with open(self.json_path, 'r') as f:
                data = json.load(f)
            return data
        else:
            return []


if __name__ == "__main__":
    p = PapersWithCode()
    p.update()
    p.update()


