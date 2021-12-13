# 代码中cookie有时效性运行前检查（数小时）
#  java博客多进程https://blog.csdn.net/zhuyiquan/article/details/80148767   
# 优化：如何在函数中用同一个drive多次get，且少了放cookie的步骤（难点：driver.close()关需切换tab，数据库多条插入但这只是提升此程序性能）
from time import sleep
import time
import json
from selenium import webdriver
from selenium.webdriver.edge.service import Service
import pymysql
import pandas as pd
import numpy as np



class TestJS:  # https://www.jianshu.com/p/7b760e2db555

    def setup(self):
        self.opt = webdriver.EdgeOptions()  # 可通过DesirdCapablilitites对象实例化options，在通过其实例化driver
        self.opt.add_argument('--headless')
        s=Service(r"C:\code\ykb-test\tools\msedgedriver.exe")
        self.driver = webdriver.Edge(service=s, options=self.opt)
        self.driver.maximize_window()
        self.driver.implicitly_wait(5)

        # 添加cookie的域名需要设置对,先访问
        self.driver.get(
            'https://auth.cq.gov.cn:81/sso/login?utype=0&client_id=OCTVFKMB0')  # 解决domain报错https://www.cnblogs.com/deliaries/p/14121204.html
        self.driver.delete_cookie('JSESSIONID')  # 需删除
        self.driver.add_cookie(
            {'name': 'JSESSIONID', 'value': 'inspurdd426acf8d27462a9f1de5fd58cd9cca', 'domain': 'auth.cq.gov.cn',
             'path': '/'})

    def teardown(self):
        self.driver.quit()

    def test_js_scroll(self):
        self.driver.get("http://www.baidu.com")
        self.driver.find_element_by_id('kw').send_keys('selenium测试')
        """使用js脚本进行元素定位，如果要获取返回一定要加入return"""
        element = self.driver.execute_script("return document.getElementById('su')")
        element.click()
        """滑动到页面最底端"""
        self.driver.execute_script("document.documentElement.scrollTop=10000")
        sleep(2)
        """点击下一页按钮"""
        self.driver.find_element_by_xpath("//*[@id='page']/div/a[10]").click()
        sleep(3)

    def get_performance(self, url):
        """获取页面标题和部分性能数据"""

        self.driver.get(url)
        self.driver.execute_script("document.documentElement.scrollTop=10000")
        # print(self.driver.get_log('performance'))

        """方法一：将js命令放在列表中逐个执行"""
        # for code in ['return document.title', 'return JSON.stringify(performance.timing)']:
        #     print(self.driver.execute_script(code))
        """方法二：使用分号隔开js命令，在一条语句中执行，但是这时只返回第一个js命令的返回值"""
        print(self.driver.execute_script("return document.title;"))
        js = self.driver.execute_script("return JSON.stringify(performance.timing)")
        print(js)
        print(type(json.loads(js)))
        idict = json.loads(js)
        print(idict.keys())  # 21个
        print(len(list(idict.values())))
        # 需要用map而非print(list(idict.values())[:]-idict['navigationStart'])
        # print(list(map(lambda x: x-idict['navigationStart'],list(idict.values())))) 发现有些时间戳为零，现在先计算再存而非直接
        times = {}  # https://zhuanlan.zhihu.com/p/82981365
        times['redirctTime'] = idict['redirectEnd'] - idict['redirectStart']
        times['dnsTime'] = idict['domainLookupEnd'] - idict['domainLookupStart']
        times['ttfbTime'] = idict['responseStart'] - idict['navigationStart']
        times['appcacheTime'] = idict['domainLookupStart'] - idict['fetchStart']
        times['unloadTime'] = idict['unloadEventEnd'] - idict['unloadEventStart']
        times['tcpTime'] = idict['connectEnd'] - idict['connectStart']
        times['reqTime'] = idict['responseEnd'] - idict['responseStart']
        times['analysisTime'] = idict['domComplete'] - idict['domInteractive']
        times['blankTime'] = (idict['domInteractive'] or idict['domLoading']) - idict['fetchStart']
        times['domReadyTime'] = idict['domContentLoadedEventEnd'] - idict['fetchStart']

        times['allTime'] = sum(times.values())
        print(times)
        return times
        # with open("timing2.json",'w',encoding="utf-8") as f:
        #    json.dump(js,f,indent=4,ensure_ascii=False)

    def performance2mysql(self, url="https://zwykb.cq.gov.cn/grbs/",
                          mysqlurl="10.236.101.17/3306/root/123456/performancedb/TB_performance2"):
        def generate_insert_sql(tbname, dicts):
            cols = ",".join('{}'.format(k) for k in dicts.keys())
            val_cols = ','.join('{}'.format(k) for k in dicts.values())
            sql = """INSERT INTO %s(%s) VALUES(%s)""" % (tbname, cols, val_cols)
            return sql

        times = self.get_performance(url)
        times['service_url'] = "'" + url + "'"  # 需要嵌套否则后面生成sql无引号
        mysqlurl = mysqlurl.split("/")
        conn = pymysql.connect(host=mysqlurl[0], port=int(mysqlurl[1]), user=mysqlurl[2], passwd=mysqlurl[3],
                               db=mysqlurl[4])
        cursor = conn.cursor()
        sql = (generate_insert_sql(mysqlurl[5], times))
        cursor.execute(sql)
        conn.commit()
        conn.close()
        cursor.close()
        # 可插入多条

    def createTabBySql(self, mysqlurl="10.236.101.17/3306/root/123456/performancedb"):
        '''此函数只运行一次，用来创建表（数据库在连接之前去服务器创建了）'''
        mysqlurl = mysqlurl.split("/")
        conn = pymysql.connect(host=mysqlurl[0], port=int(mysqlurl[1]), user=mysqlurl[2], passwd=mysqlurl[3],
                               db=mysqlurl[4], charset='utf8')
        cursor = conn.cursor()
        tb1_sql = '''CREATE TABLE IF NOT EXISTS TB_performance2(
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
                   PRIMARY KEY(id)) '''  # 还可以加datatime字段

        cursor.execute(tb1_sql)  # 哪个没有建哪个
        conn.commit()
        conn.close()
        cursor.close()

    def getMainKey(self,mysqlurl="10.236.101.17/3306/root/123456/performancedb/TB_service"):
        mysqlurl = mysqlurl.split("/")
        conn = pymysql.connect(host=mysqlurl[0], port=int(mysqlurl[1]), user=mysqlurl[2], passwd=mysqlurl[3],
                               db=mysqlurl[4])
        sqlGetMainKey = 'select id from TB_service'
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
                ts.performance2mysql(
                    url='https://zwykb.cq.gov.cn/ggbf_search/ljbl/?mainKey=' + ",".join(mainKey_to_list[i]) + '&type=01&parentPage=1')
            except:
                count += 1
                print("err")
            i = (i + 1) % 851
        print(count)

if __name__ == "__main__":
    ts = TestJS()
    ts.setup()
    mainKey_list = ts.getMainKey()
    # ts.createTabBySql()  # 第一个链接有字段为负存不了
    ts.getPerformanceWithPixedTime(mainKey_list)


