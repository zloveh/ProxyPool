# -*- coding: utf-8 -*-
import json
import requests
from pyquery import PyQuery as pq


header = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/"
    "64.0.3282.119 Safari/537.36"
}


class ProxyMetaclass(type):

    # 创建元类，把属性名中包含‘crawl_’的属性名加入列表
    def __new__(cls, name, bases, attrs):
        count = 0
        attrs["__CrawlFunc__"] = []
        for k, v in attrs.items():
            if "crawl_" in k:
                attrs["__CrawlFunc__"].append(k)
                count += 1
        attrs["__CrawlFuncCount__"] = count
        return type.__new__(cls, name, bases, attrs)


class Crawler(object, metaclass=ProxyMetaclass):

    def get_proxies(self, callback):
        """
        运行以'crawl_'开头的方法
        :param callback: 方法名称
        :return: 代理列表
        """
        proxies = []
        for proxie in eval("self.{}()".format(callback)):
            print("成功获取到代理", proxie)
            proxies.append(proxie)
        return proxies

    def crawl_daili66(self, page_count=4):
        """
        获取代理66
        :param page_count: 页码
        :return: 代理
        """
        start_url = "http://www.66ip.cn/{}.html"
        urls = [start_url.format(page) for page in range(1, page_count + 1)]
        for url in urls:
            print("Crawling", url)
            html = requests.get(url, headers=header)
            html.encoding = "gb2312"
            if html:
                doc = pq(html.text)
                trs = doc(".containerbox table tr:gt(0)").items()
                for tr in trs:
                    ip = tr.find("td:nth-child(1)").text()
                    port = tr.find("td:nth-child(2)").text()
                    yield ":".join([ip, port])

    def crawl_xici(self, page_count=4):
        """
        获取Goubanjia
        :return: 代理
        """
        start_url = "http://www.xicidaili.com/nn/{}"
        urls = [start_url.format(page) for page in range(1, page_count + 1)]
        for url in urls:
            print("Crawling", url)
            html = requests.get(url, headers=header)
            html.encoding = "utf-8"
            if html:
                doc = pq(html.text)
                trs = doc("#ip_list tr:gt(0)").items()
                for tr in trs:
                    ip = tr.find("td:nth-child(2)").text()
                    port = tr.find("td:nth-child(3)").text()
                    yield ":".join([ip, port])
