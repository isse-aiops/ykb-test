# 此代码用selenium进行js注入获取timing信息并收集起来（生成csv手动导入数据库或直接写sql。还可以用dataframe的接口直接存https://www.cnblogs.com/think90/articles/11899070.html）
# 安装webdriver见https://www.selenium.dev/zh-cn/documentation/webdriver/getting_started/install_drivers/
# 如在Linux使用安装Chromium，chromium-browser --version查看版本对应（红帽系列安装epel-release先

# 代码中cookie有时效性需运行前检查（可能数小时）
from time import sleep
import time, json
from datetime import datetime
import logging
logging.basicConfig(level=logging.ERROR)

import pandas as pd
import numpy as np
from pandas.core.indexes.base import Index
import pymysql
from selenium.webdriver.chrome.webdriver import WebDriver
from sqlalchemy import create_engine
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import concurrent.futures # 由于是网络io密集多线程多进程都能用，问题是用多线程共享TestYKB是否更快，可以对比两个方法（并发数用默认值）

class TestYKB:

    def __init__(self) -> None:
        # 也可直接用narr或dataframe保存
        self.times = {'serviceId': [], 'Status': [], 'redirctTime': [], 'dnsTime': [], 'ttfbTime': [], 'appcacheTime': [], 'unloadTime': [], 'tcpTime': [], 'reqTime': [], 'analysisTime': [], 'blankTime': [], 'domReadyTime': [], 'allTime': [], 'Timestamp': []}
        


    def setup(self, chromedriver_path='./driver/chromedriver-90'):
        '''该函数配置webdriver的启动属性'''
        self.opt = webdriver.ChromeOptions() # 可通过DesirdCapablilitites对象实例化options，在通过其实例化driver
        self.opt.add_argument('--headless')
        self.driver = webdriver.Chrome(executable_path=chromedriver_path,options=self.opt)
        self.driver.maximize_window()
        # self.driver.implicitly_wait(5) # 隐式等待 https://www.jianshu.com/p/bf27aad96614
    
    def addCookie(self,JSESSIONID='inspurbb332f8993d84dcca368954a0a4127eb'): #
        """ webdriver保持登录状态（否则无法无法访问办事详情），JSESSIONID字段需访问下面url获取后登录即可 """
        # 添加cookie的域名需要设置对,先访问
        self.driver.get('https://auth.cq.gov.cn:81/sso/login?utype=0') # 解决domain报错，需要https://www.cnblogs.com/deliaries/p/14121204.html
        self.driver.delete_cookie('JSESSIONID') # 需先删除访问初始化的
        self.driver.add_cookie({'name':'JSESSIONID','value':JSESSIONID,'domain':'auth.cq.gov.cn','path':'/'})

    def teardown(self):
        self.driver.quit()

    def get_performance(self,id="00065e9b-407e-49a2-933c-eb82de004c04"):
        """获取页面标题和部分性能数据 -访问url用js获取timing具体数据"""
        try:
            self.driver.get("https://zwykb.cq.gov.cn/ggbf_search/ljbl/?mainKey="+id)
            print(("（如果是登录说明cookie没对）"+self.driver.execute_script("return document.title;"))) 

            # 显式等待加载完毕，直接sleep也可,否则是load状态就获取timing了
            WebDriverWait(self.driver, 10).until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            logging.info(self.driver.execute_script('return document.readyState'))
            js = self.driver.execute_script("return JSON.stringify(performance.timing)")
            idict = json.loads(js) # 字典类型
            logging.info(idict) #21个
            logging.info(len(list(idict.values())))
            #需要用map而非print(list(idict.values())[:]-idict['navigationStart'])
            #print(list(map(lambda x: x-idict['navigationStart'],list(idict.values()))))
            # 计算意义 https://zhuanlan.zhihu.com/p/82981365
            self.times['redirctTime'].append(idict['redirectEnd'] - idict['redirectStart'])
            self.times['dnsTime'].append(idict['domainLookupEnd'] - idict['domainLookupStart'])
            self.times['ttfbTime'].append(idict['responseStart'] - idict['navigationStart'])
            self.times['appcacheTime'].append(idict['domainLookupStart'] - idict['fetchStart'])
            self.times['unloadTime'].append(idict['unloadEventEnd'] - idict['unloadEventStart'])
            self.times['tcpTime'].append(idict['connectEnd'] - idict['connectStart'])
            self.times['reqTime'].append(idict['responseEnd'] - idict['responseStart'])
            self.times['analysisTime'].append(idict['domComplete'] - idict['domInteractive'])
            self.times['blankTime'].append((idict['domInteractive'] or idict['domLoading']) - idict['fetchStart'])
            self.times['domReadyTime'].append(idict['domContentLoadedEventEnd'] - idict['fetchStart'])
            self.times['allTime'].append(idict['loadEventEnd']-idict['navigationStart']) #!不应该用上诉各段求和
            self.times['Status'].append(1)
        except:
            self.times['redirctTime'].append(0)
            self.times['dnsTime'].append(0)
            self.times['ttfbTime'].append(0)
            self.times['appcacheTime'].append(0)
            self.times['unloadTime'].append(0)
            self.times['tcpTime'].append(0)
            self.times['reqTime'].append(0)
            self.times['analysisTime'].append(0)
            self.times['blankTime'].append(0)
            self.times['domReadyTime'].append(0)
            self.times['allTime'].append(0)
            self.times['Status'].append(0)
            
        self.times['serviceId'].append(id)
        self.times['Timestamp'].append(datetime.now())
        logging.info(self.times)


    def save2mysql(self):
        """ 从dataframe保存至mysql(加上后置数据处理) """ 
        engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/performancedb?charset=utf8")
        df = pd.DataFrame(self.times) #dataframe需的字典是包含index信息的 所以times值是列表
        logging.info(df)
        print(df)
        df.to_sql('TB_PERFORMANCE',con=engine,if_exists='append', index=False)

    
    def generate_performance_count(self):
        pass
    
    def generate_performance_status(self):
        pass
        


if __name__ == '__main__':
    testykb = TestYKB()
    testykb.setup()
    testykb.addCookie("填入")
    # testykb只实现访问一个请求保存到变量，访问多个请求多调用几次getperformance再save一次。并发只需要在这里定义个process
    def getMainKeyList(mysqlurl="127.0.0.1/3306/root/123456/performancedb/TB_SERVICES"):
        mysqlurl = mysqlurl.split("/")
        conn = pymysql.connect(host=mysqlurl[0], port=int(mysqlurl[1]), user=mysqlurl[2], passwd=mysqlurl[3],
                               db=mysqlurl[4])
        sqlGetMainKey = 'select id from TB_SERVICES'
        df = pd.read_sql(sqlGetMainKey, con=conn)
        key_list=np.array(df).tolist()
        return key_list

    def process_demo(i):
        print(i)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process_demo,item) for item in [1,2,3,4,5]]
        for future in concurrent.futures.as_completed(futures):
            print(future.result())
    def process(id):
        testykb.get_performance(id)
    start_time_thread = time.time()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process,item[0]) for item in getMainKeyList()]
        # concurrent.futures.as_completed(futures) # 应该不需要这个就complete了
    print ("Thread pool execution in " + str(time.time() - start_time_thread), "seconds")
    print(len(testykb.times['serviceId'])) #应该是852条全跑完了
    testykb.save2mysql()

    # start_time_order = time.time()  #测试得知线程池快了百分之五十以上 但也要用900秒还实名认证拦截
    # testykb.times = {'serviceId': [], 'Status': [], 'redirctTime': [], 'dnsTime': [], 'ttfbTime': [], 'appcacheTime': [], 'unloadTime': [], 'tcpTime': [], 'reqTime': [], 'analysisTime': [], 'blankTime': [], 'domReadyTime': [], 'allTime': [], 'Timestamp': []}
    # [process(id[0]) for id in getMainKeyList()]
    # print(len(testykb.times['serviceId'])) #应该是852条全跑完了
    # print ("Order execution in " + str(time.time() - start_time_thread), "seconds")


    # testykb.performance2dataframe("f4943a42-961d-47db-a86c-b1ada64370ab")
    testykb.teardown()
