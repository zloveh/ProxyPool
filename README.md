# 代理池搭建    
&ensp;&ensp;&ensp;&ensp;当使用爬虫进行大规模爬取时，就需要防止IP被封， 解决办法就是使用代理IP。但不管是付费代理还是免费代理都会面临代理失效，特别是网上公布的免费代理，很少有可用的，这就需要爬取大量IP进行检测，留下可用的，去掉不可用的。所以建一个有效的IP代理池是很有必要的。    

代理池搭建主要分为四个模块：  
&ensp;&ensp;&ensp;&ensp;* 存储模块  
&ensp;&ensp;&ensp;&ensp;* 抓取模块  
&ensp;&ensp;&ensp;&ensp;* 检测模块  
&ensp;&ensp;&ensp;&ensp;* api模块    
抓取模块负责在代理网站上抓取IP，存储模块负责存储抓到的IP，检测模块负责检测IP是否有效，若无效则把IP删除，api模块则负责为外界调用代理IP提供接口。  

1.存储模块：  
&ensp;&ensp;&ensp;&ensp;存储模块使用Redis数据库中的有序集合，用来做代理的去重和状态标识。  
&ensp;&ensp;&ensp;&ensp;有序集合中的分数字段score由于排序和表示代理IP的状态，对于刚抓取的IP把分数设置为10分，检测代理是有有效时，若有效则把IP的score设置为100， 若无效分数减1。之后会每隔一段时间就检测一次，有效设置100， 无效减1，当分数为0时就将IP删除。当我们取用IP时会先选用分数最高的，这样可以保证我们的IP尽量是有效的。  

Redis数据库模块接口设计代码：  
```
    def add(self, proxy, score=INITIAL_SCORE):
        """
        添加代理，分数设置为10
        :param proxy: 代理
        :param score: 分数
        :return: 添加结果
        """
        # 如果没有返回proxy对应的分数，则认为REDIS_KEY没有这个proxy,应添加
        if not self.db.zscore(REDIS_KEY, proxy):
            return self.db.zadd(REDIS_KEY, score, proxy)

    def random(self):
        """
        随机获取有效代理， 首先尝试最高分代理，如果最高分代理不存在，则按照排名获取，
        否则异常
        :return:随机代理
        """
        result = self.db.zrangebyscore(REDIS_KEY, MAX_SCORE, MAX_SCORE)
        if len(result):
            return choice(result)
        else:
            result = self.db.zrevrange(REDIS_KEY, 0, 100)
            if len(result):
                return choice(result)
            else:
                raise "PoolEmptyError"

    def decrease(self, proxy):
        """
        代理值减一分，分数小于最小值，则代理删除
        :param proxy: 代理
        :return: 修改后的参数
        """
        score = self.db.zscore(REDIS_KEY, proxy)
        if score and score > MIN_SCORE:
            print("代理:" + proxy + " ,当前分数:" + str(score) + " ,减1")
            return self.db.zincrby(REDIS_KEY, proxy, -1)
        else:
            print("代理:" + proxy + "移除")
            return self.db.zrem(REDIS_KEY, proxy)

    def exists(self, proxy):
        """
        判断代理是否存在
        :param proxy: 代理
        :return: 是否存在
        """
        return not self.db.zscore(REDIS_KEY, proxy) == None

    def max(self, proxy):
        """
        将代理设置为MAX_SCORE
        :param proxy: 代理
        :return: 设置结果
        """
        print("代理:" + proxy + "可用，设置为：", MAX_SCORE)
        return self.db.zadd(REDIS_KEY, MAX_SCORE, proxy)

    def count(self):
        """
        获取数量
        :return:数量
        """
        return self.db.zcard(REDIS_KEY)

    def all(self):
        """
        获取全部代理
        :return: 全部代理列表
        """
        return self.db.zrangebyscore(REDIS_KEY, MIN_SCORE, MAX_SCORE)
```  
详细代码见：db.py  

2. 抓取模块：  
主要抓取[66免费代理网](http://www.66ip.cn/)和[西刺代理](http://www.xicidaili.com/nn) 中的高匿代理。  
```
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
```  
另外为了便于扩展，使用了元类：  
```
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
```  
这样如果我们想爬其他网站IP时，只需要在方法名上添加‘crawl_’即可，就像爬取这两个网站时的命名方法一样.  

最后设置运行这些方法：  
```
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
```  
调度get_proxies()方法：
```
    def is_over_threshold(self):
        """
        判断是否到达了代理池的xianzhi
        :return:
        """
        if self.redis.count() >= POOL_UPPER_THRESHOLD:
            return True
        else:
            return False

    def run(self):
        print("获取器开始执行")
        if not self.is_over_threshold():
            for callback_label in range(self.crawler.__CrawlFuncCount__):
                callback = self.crawler.__CrawlFunc__[callback_label]
                proxies = self.crawler.get_proxies(callback)
                for proxy in proxies:
                    self.redis.add(proxy)
```  
详细代码见：crawler.py和getter.py  
  
3. 检测模块：  
检测IP就是带着代理IP去访问某个网址看是否可以访问，当写爬虫时最好将这个网址设置为目标网站的网址，这样获得的IP会更加有针对性。这里由于仅仅对IP是否有效进行检测所以选用百度网址：https://www.baidu.com, 对于请求网址如果用requests库的话，由于requests是一个同步请求库，请求一个网址当网页加载完成后才能继续执行，这对于我们要检测大量IP是非常耗时的，所以这里选用aiohttp异步请求库，这样效率会提高很多。
```
 async def test_single_proxy(self, proxy):
        """
        测试单个代理
        :param proxy: 单个代理
        :return: None
        """
        conn = aiohttp.TCPConnector(verify_ssl=False)
        async with aiohttp.ClientSession(connector=conn) as session:
            try:
                if isinstance(proxy, bytes):
                    proxy = proxy.decode("utf-8")
                real_proxy = "http://" + proxy
                print("正在测试", proxy)
                async with session.get(
                    TEST_URL, proxy=real_proxy, timeout=10
                ) as response:
                    if response.status in VALID_STATUS_CODES:
                        self.redis.max(proxy)
                    else:
                        self.redis.decrease(proxy)
                        print("请求响应码不和法", proxy)
            except (
                ClientError,
                ProxyConnectionError,
                ServerConnectionError,
                TimeoutError,
                AttributeError,
            ):
                self.redis.decrease(proxy)
                print("代理请求失败", proxy)
            except Exception as e:
                print(e)
```  
测试多个代理， 一次测试100个：
```
    def run(self):
        """
        测试主函数
        :return:
        """
        print("测试器开始运行")
        try:
            proxies = self.redis.all()
            loop = asyncio.get_event_loop()
            # 批量测试
            for i in range(0, len(proxies), BATCH_TEST_SIZE):
                test_proxies = proxies[i : i + BATCH_TEST_SIZE]
                tasks = [self.test_single_proxy(proxy) for proxy in proxies]
                loop.run_until_complete(asyncio.wait(tasks))
                time.sleep(5)
        except Exception as e:
            print("测试器发生错误", e.args)
```
详细代码见： tester.py  

4. api模块：
设置一个接口模块，以Web API的形式暴露可用代理,使用轻量级的flask库实现，这样可以很方便的使用代理，到时候只需请求网页即可使用代理。如果用连接数据库来使用IP代理的话，当别人使用时就需要知道数据库账户名和密码，这样很不安全。

'''
@app.route("/")
def index():
    return "<h2>Welcome to Proxy Pool System</h2>"


@app.route("/random")
def get_proxy():
    """
    获取随机可用代理
    :return: 返回代理
    """
    conn = get_conn()
    return conn.random()


@app.route("/count")
def get_counts():
    """
    获取代理池总量
    :return: 代理池总量
    """
    conn = get_conn()
    return str(conn.count())
'''  
详细代码见: api.py     

5. 最后增加一个调度模块，用来调度前面的各个模块： 
```
    def schedule_tester(self, cycle=TESTER_CYCLE):
        """
        定时测试代理
        :param cycle:
        :return:
        """
        tester = Tester()
        while True:
            print("测试器开始运行")
            tester.run()
            time.sleep(cycle)

    def schedule_getter(self, cycle=GETTER_CYCLE):
        """
        定时获取代理
        :param cycle:
        :return:
        """
        getter = Getter()
        while True:
            print("开始抓取代理")
            getter.run()
            time.sleep(cycle)

    def schedule_api(self):
        """
        开启api
        :return:
        """
        app.run(API_HOST, API_PORT)

    def run(self):
        print("代理池开始运行")
        if TESTER_ENABLED:
            tester_process = Process(target=self.schedule_tester)
            tester_process.start()

        if GETTER_ENABLED:
            getter_process = Process(target=self.schedule_getter)
            getter_process.start()

        if API_ENABLED:
            api_process = Process(target=self.schedule_api)
            api_process.start()
```  
采用多进程的方法使得各个模块可以同时独立的运行，并且设置了时间，多久获取一个代理， 多久对代理检测一次。
详细代码见： scheduler.py


运行一下：  
![图二](https://github.com/zloveh/ProxyPool/blob/master/image/2.png)


获取代理方法：  
```
获取代理
利用requests获取方法如下

import requests

PROXY_POOL_URL = 'http://localhost:5555/random'

def get_proxy():
    try:
        response = requests.get(PROXY_POOL_URL)
        if response.status_code == 200:
            return response.text
    except ConnectionError:
        return None
```

