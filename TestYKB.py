# 此代码用selenium进行js注入获取timing信息并收集起来（生成csv手动导入数据库或直接写sql。还可以用dataframe的接口直接存https://www.cnblogs.com/think90/articles/11899070.html）
# 安装webdriver见https://www.selenium.dev/zh-cn/documentation/webdriver/getting_started/install_drivers/
# 如在Linux使用安装Chromium，chromium-browser --version查看版本对应（红帽系列安装epel-release先

# 代码中cookie有时效性需运行前检查（可能数小时）
from time import sleep
import time
from datetime import datetime
import json, csv

import pandas as pd
import numpy as np
from pandas.core.indexes.base import Index
import pymysql
from selenium.webdriver.chrome.webdriver import WebDriver
from sqlalchemy import create_engine
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

import logging
# 并发处在哪，如果是不是一条一条存，就在获取performce并发，返回全部的数据。如果是包含存数据并发就不需返回
import concurrent.futures # 由于是网络io密集多线程多进程都能用，问题是用多线程共享TestYKB是否更快，对比两个方法（并发数用默认值）
logging.basicConfig(level=logging.INFO)

class TestYKB:

    def __init__(self) -> None:
        self.times = {'serviceId': [], 'Status': [], 'redirctTime': [], 'dnsTime': [], 'ttfbTime': [], 'appcacheTime': [], 'unloadTime': [], 'tcpTime': [], 'reqTime': [], 'analysisTime': [], 'blankTime': [], 'domReadyTime': [], 'allTime': [], 'Timestamp': []}
        self.performance_count = {'COUNT_ID':[], 'STATUS':[], 'NUMBER': [], 'RECORD_TIME': []} 


    def setup(self, chromedriver_path='./chromedriver'):
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

    def createTableBySql(self,mysqlurl="127.0.0.1/3306/root/123456/performancedb"):
        '''此函数用来创建表,需创建performancedb数据库'''
        import pymysql
        mysqlurl = mysqlurl.split("/")
        conn = pymysql.connect(host=mysqlurl[0],port=int(mysqlurl[1]),user=mysqlurl[2],passwd=mysqlurl[3],db=mysqlurl[4],charset='utf8')
        cursor = conn.cursor()
        tb1_sql = '''CREATE TABLE IF NOT EXISTS TB_PERFORMANCE(
                   redirctTime int(11) DEFAULT NULL ,
                   dnsTime int(11) DEFAULT NULL ,
                   ttfbTime int(11) DEFAULT NULL ,
                   unloadTime int(11) DEFAULT NULL ,
                   appcacheTime int(11) DEFAULT NULL ,
                   domReadyTime int(11) DEFAULT NULL ,
                   reqTime int(11) DEFAULT NULL ,
                   tcpTime int(11) DEFAULT NULL ,   
                   blankTime int(11) DEFAULT NULL , 
                   analysisTime int(11) DEFAULT NULL ,
                   allTime int(11) DEFAULT NULL,
                   service_url longtext DEFAULT NULL,
                   TestingTime datetime DEFAULT CURRENT_TIMESTAMP, 
                   updateTime datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                   id INT NOT NULL AUTO_INCREMENT,
                   PRIMARY KEY(id)) ''' #还可以加datatime字段
        
        
        cursor.execute(tb1_sql) #哪个没有建哪个
        conn.commit()
        conn.close()
        cursor.close()

    def performance2mysql(self,url="",mysqlurl="127.0.0.1/3306/root/123456/performancedb/TB_PERFORMANCE"):
        def generate_insert_sql(tbname,dicts):
            cols = ",".join('{}'.format(k) for k in dicts.keys())
            val_cols = ','.join('{}'.format(k) for k in dicts.values())
            sql = """INSERT INTO %s(%s) VALUES(%s)""" % (tbname, cols, val_cols)
            return sql
        times = self.get_performance(url)
        times['service_url'] = "'"+url+"'" # 需要嵌套否则后面生成sql无引号
        mysqlurl = mysqlurl.split("/")
        conn = pymysql.connect(host=mysqlurl[0],port=int(mysqlurl[1]),user=mysqlurl[2],passwd=mysqlurl[3],db=mysqlurl[4])
        cursor = conn.cursor()
        sql = (generate_insert_sql(mysqlurl[5],times))
        cursor.execute(sql)
        conn.commit()
        conn.close()
        cursor.close()
        # 可插入多条
        
    def get_performance(self,url):
        """获取页面标题和部分性能数据：访问url用js获取timing具体数据"""

        self.driver.get(url)
        print(("（如果是登录说明cookie没对）"+self.driver.execute_script("return document.title;"))) 
        # 显式等待加载完毕，直接sleep也可,否则是load状态就获取timing了
        WebDriverWait(self.driver, 10).until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
        logging.info(self.driver.execute_script('return document.readyState'))
        js = self.driver.execute_script("return JSON.stringify(performance.timing)")
        idict = json.loads(js) # 字典类型
        logging.info(idict) #21个
        logging.info(len(list(idict.values())))
        #需要用map而非print(list(idict.values())[:]-idict['navigationStart'])
        #print(list(map(lambda x: x-idict['navigationStart'],list(idict.values())))) 发现有些时间戳为零，现在先计算再存而非直接
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
        self.times['allTime'].append(idict['loadEventEnd']-idict['navigationStart'])
        logging.info(self.times)

        #with open("timing2.json",'w',encoding="utf-8") as f:
        #    json.dump(js,f,indent=4,ensure_ascii=False)

    def performance2dataframe(self,id="00065e9b-407e-49a2-933c-eb82de004c04"):
        try:
            self.get_performance("https://zwykb.cq.gov.cn/ggbf_search/ljbl/?mainKey="+id)
            self.times['Status'].append(1)
        except:
            self.times['Status'].append(0)
        self.times['serviceId'].append(id)
        self.times['Timestamp'].append(datetime.now())
        # print(self.times)
        logging.info(pd.DataFrame(self.times))
        engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/performancedb?charset=utf8")
        pd.DataFrame(self.times).to_sql('TB_PERFORMANCE',con=engine,if_exists='append', index=False)
    
    """ 多进程的话times不易同步需要借数据库，每个进程需要读出来涉及事务。多线程共享times不需读（线程同步？） """
    def generate_performance_count(self):
        pass
    
    def generate_performance_status(self):
        pass
        
    def getMainKey(self,mysqlurl="127.0.0.1/3306/root/123456/performancedb/TB_SERVICES"):
        mysqlurl = mysqlurl.split("/")
        conn = pymysql.connect(host=mysqlurl[0], port=int(mysqlurl[1]), user=mysqlurl[2], passwd=mysqlurl[3],
                               db=mysqlurl[4])
        sqlGetMainKey = 'select id from TB_SERVICES'
        df = pd.read_sql(sqlGetMainKey, con=conn)
        key_list=np.array(df).tolist()
        return key_list

    def getPerformanceWithPixedTime(self,mainKey_to_list):   #可定义脚本抓取性能数据的时间
        mainKey_to_list=mainKey_to_list
        count = 0
        i = 0
        period = 7200  # 定时7200s(两小时)
        start_time = time.time()
        while time.time() - start_time <= period:
            try:
                self.performance2mysql(
                    url='https://zwykb.cq.gov.cn/ggbf_search/ljbl/?mainKey=' + ",".join(mainKey_to_list[i]) + '&type=01&parentPage=1')
            except:
                count += 1
                print("err")
            i = (i + 1) % 851
        print(count)

if __name__ == '__main__':
    testykb = TestYKB()
    testykb.setup()
    testykb.addCookie("inspur0f9b877ffecd43969605496c89c2324d")
    # dataframe需的字典是包含index信息的
    testykb.performance2dataframe("f4943a42-961d-47db-a86c-b1ada64370ab")

    testykb.teardown()
