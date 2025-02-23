# -*- coding: utf-8 -*-
import sys
import threading
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QLineEdit, QPushButton, QListWidget, QLabel)
from scrapy import Spider, Request
from scrapy.crawler import CrawlerProcess
from scrapy.utils.log import configure_logging
from elasticsearch import Elasticsearch
from apscheduler.schedulers.background import BackgroundScheduler

# ================== Elasticsearch客户端 ==================
es = Elasticsearch(['http://localhost:9200'])
INDEX_NAME = "web_pages"


# ================== 爬虫模块 ==================
class WebCrawler(Spider):
    name = "single_file_spider"
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'ROBOTSTXT_OBEY': True,
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    def start_requests(self):
        # 示例种子URL（可扩展为从界面输入）
        urls = ['https://baidu.com']
        for url in urls:
            yield Request(url, callback=self.parse)

    def parse(self, response):
        # 提取数据并存入Elasticsearch
        item = {
            'title': response.css('h1::text').get() or "无标题",
            'content': ' '.join(response.css('p::text').getall()),
            'url': response.url,
            'timestamp': datetime.now().isoformat()
        }
        es.index(index=INDEX_NAME, body=item)
        self.log(f"已保存: {item['title']}")


# ================== 用户界面 ==================
class SearchApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("单文件实时搜索工具")
        self.setGeometry(300, 300, 800, 600)

        layout = QVBoxLayout()
        self.keyword_input = QLineEdit(placeholderText="输入搜索关键词...")
        self.search_btn = QPushButton("立即搜索")
        self.result_list = QListWidget()

        layout.addWidget(QLabel("全网实时搜索"))
        layout.addWidget(self.keyword_input)
        layout.addWidget(self.search_btn)
        layout.addWidget(QLabel("搜索结果列表"))
        layout.addWidget(self.result_list)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # 绑定事件
        self.search_btn.clicked.connect(self.perform_search)

    def perform_search(self):
        keyword = self.keyword_input.text()
        if not keyword:
            return

        # 执行Elasticsearch搜索
        query = {
            "query": {
                "multi_match": {
                    "query": keyword,
                    "fields": ["title^2", "content"]
                }
            }
        }
        results = es.search(index=INDEX_NAME, body=query)
        self.result_list.clear()
        for hit in results['hits']['hits']:
            self.result_list.addItem(f"{hit['_source']['title']} - {hit['_source']['url']}")


# ================== 调度模块 ==================
def run_spider():
    """定时执行爬虫任务"""
    configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})
    process = CrawlerProcess()
    process.crawl(WebCrawler)
    process.start()


def start_scheduler():
    """启动定时任务（每小时运行一次）"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_spider, 'interval', hours=1)
    scheduler.start()
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


# ================== 主程序入口 ==================
if __name__ == "__main__":
    # 启动定时爬虫线程
    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    # 启动GUI界面
    app = QApplication(sys.argv)
    window = SearchApp()
    window.show()
    sys.exit(app.exec_())
