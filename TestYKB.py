# 此代码用selenium进行js注入获取timing信息并收集起来（生成csv手动导入数据库或直接写sql。还可以用dataframe的接口直接存https://www.cnblogs.com/think90/articles/11899070.html）
# 安装webdriver见https://www.selenium.dev/zh-cn/documentation/webdriver/getting_started/install_drivers/
# 如在Linux使用安装Chromium，chromium-browser --version查看版本对应（红帽系列安装epel-release先

from time import sleep
import time, json
from datetime import datetime
import logging
logging.basicConfig(level=logging.ERROR)

import pandas as pd
import numpy as np
import pymysql
from sqlalchemy import create_engine
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
import concurrent.futures 
class TestYKB:

    def __init__(self,serviceLists,testTime=datetime.now()) -> None:
        self.TestYKB_TIME = testTime # 使用测试开启的时间而非添加数据当前的时间
        self.serviceLists = serviceLists

        # 也可直接用narr或dataframe保存
        self.times = {'serviceId': [], 'Status': [], 'redirctTime': [], 'dnsTime': [], 'ttfbTime': [], 'appcacheTime': [], 'unloadTime': [], 'tcpTime': [], 'reqTime': [], 'analysisTime': [], 'blankTime': [], 'domReadyTime': [], 'allTime': [], 'Timestamp': []}
        # performance-status表结构
        self.dataframe = {'SERVICE_ID': [],'SERVICE_NAME':[],'CURRENT_RESTIME':[],'CURRENT_STATUS':[],'LAST_RESTIME':[],'LAST_STATUS':[],'CHANGE_TIME':[],'LAST_DURATION':[],'CRT_TIME':[]}


    def setup(self, chromedriver_path='./driver/chromedriver-90'):
        '''该函数配置webdriver的启动属性'''
        self.opt = webdriver.ChromeOptions() # 可通过DesirdCapablilitites对象实例化options，在通过其实例化driver
        self.opt.add_argument('--headless')
        self.driver = webdriver.Chrome(executable_path=chromedriver_path,options=self.opt)
        self.driver.maximize_window()
        # self.driver.implicitly_wait(5) # 隐式等待 https://www.jianshu.com/p/bf27aad96614
    
    def addCookie(self,JSESSIONID='inspurbb332f8993d84dcca368954a0a4127eb'): #
        """ webdriver保持登录状态（否则无法无法访问办事详情） ， JSESSIONID字段需访问下面url获取后登录即可 """
        # 添加cookie的域名需要设置对,先访问
        self.driver.get('https://auth.cq.gov.cn:81/sso/login?utype=0') # 解决domain报错，需要https://www.cnblogs.com/deliaries/p/14121204.html
        self.driver.delete_cookie('JSESSIONID') # 需先删除访问初始化的
        self.driver.add_cookie({'name':'JSESSIONID','value':JSESSIONID,'domain':'auth.cq.gov.cn','path':'/'})

    def teardown(self):
        self.driver.quit()


        
    def get_performance(self,id="00065e9b-407e-49a2-933c-eb82de004c04"):
        """获取页面标题和部分性能数据 -访问url用js获取timing具体数据"""
        try:
            self.driver.get("https://zwykb.cq.gov.cn/grbs/bszn/?itemid="+id)


            # 显式等待加载完毕，直接sleep也可,否则是load状态就获取timing了
            WebDriverWait(self.driver, 10).until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            logging.info(self.driver.execute_script('return document.readyState'))
            js = self.driver.execute_script("return JSON.stringify(performance.timing)")
            idict = json.loads(js) # 字典类型


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
            if self.driver.execute_script("return getComputedStyle(document.querySelector(' a.w-cur')).backgroundColor")=='rgb(39, 137, 238)':
                self.times['Status'].append(7) #状态设置7不可用

            elif idict['loadEventEnd']-idict['navigationStart'] < 1000: 
                self.times['Status'].append(1)
            elif idict['loadEventEnd']-idict['navigationStart'] < 2000:
                self.times['Status'].append(2)
            elif idict['loadEventEnd']-idict['navigationStart'] < 3000:
                self.times['Status'].append(3)
            elif idict['loadEventEnd']-idict['navigationStart'] < 5000:
                self.times['Status'].append(4)
            else :
                self.times['Status'].append(5)
        except:
            print("!!!!!!返回报错!!!!!!!!") #状态设置为6访问异常
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
            self.times['Status'].append(6)
            
        self.times['serviceId'].append(id)
        self.times['Timestamp'].append(self.TestYKB_TIME)
        logging.info(self.times)

#TODO 去掉查表
    def generate_performance_status(self,df_one,serviceId):
        """ 生成times后，查performance_status信息，生成id为i的新状态保存在列表中最后再存
        df_one,是只有一行的dataframe，这里可以转化为dict改改下面的访问也许性能好些
        """
        # TODO 类型转换问题（df取出类型）-.values.tolist()[0]解决(结果不用tolist直接切否则时间列会变时间戳还无法直接转回datetime) ，+代替append，线程不安全
        '''相比获取performance中最新的记录，直接查performce-status表，SELECT serviceId,Status,allTime,Timestamp FROM TB_PERFORMANCE WHERE serviceId = "%s"ORDER BY Timestamp DESC LIMIT 1'''
        # print(datetime.fromtimestamp(1641933374799277000)) # 太长了
        # print((df_one['Timestamp'].values[0])) #.values就变成时间戳了
        selectSql = '''
            SELECT
                SERVICE_NAME,CURRENT_STATUS,CURRENT_RESTIME,CRT_TIME, LAST_DURATION
            FROM
                TB_SERVICE_STATUS
            WHERE
                SERVICE_ID = "%s"
            ORDER BY CRT_TIME DESC LIMIT 1
        '''%(serviceId)   # 如何一次性查出来用df读入。
        conn = pymysql.connect(host='127.0.0.1', port=3306, user='root' ,passwd='123456',db='performancedb')
        cursor = conn.cursor()
        cursor.execute(selectSql)
        data = (cursor.fetchone()) # 元组如(0, 5, datetime.datetime(2022, 1, 11, 17, 53, 12))
        if data == None :
            '''当performance-status表空，需要初始化'''
            # print([1,2,3].append([5])) 打印None(+需要返回append不需要，原列表变为[[5],1,2..]
            # print((df_one['Status'].values.tolist())+[1,2]) #没有tolist，narr+list会数值加
            self.dataframe['SERVICE_ID'].append(serviceId)
            cursor.execute("SELECT service_name FROM TB_SERVICES WHERE id='%s'"%serviceId)
            self.dataframe['SERVICE_NAME'].append(cursor.fetchone()[0])  # 初始化表没有信息，df也没有只能查services（或join
            self.dataframe['LAST_STATUS'].append(df_one['Status'].values.tolist()[0]) # 数据表为空，初始化方式（起初设上一状态为0，现认为上一状态和当前一样）
            self.dataframe['LAST_RESTIME'].append(df_one['allTime'].values.tolist()[0])
            self.dataframe['CURRENT_RESTIME'].append(df_one['allTime'].values.tolist()[0])
            self.dataframe['CURRENT_STATUS'].append(df_one['Status'].values.tolist()[0])
            self.dataframe['CRT_TIME'].append(df_one['Timestamp'].values[0])
            self.dataframe['CHANGE_TIME'].append(df_one['Timestamp'].values[0])
            self.dataframe['LAST_DURATION'].append(0)
        else:
            self.dataframe['SERVICE_ID'].append(serviceId)
            self.dataframe['SERVICE_NAME'].append(data[0])  # 不需查performance
            self.dataframe['LAST_STATUS'].append(data[1])
            self.dataframe['LAST_RESTIME'].append(data[2])
            LastTime = data[3]
            self.dataframe['CURRENT_RESTIME'].append(df_one['allTime'].values.tolist()[0])
            self.dataframe['CURRENT_STATUS'].append(df_one['Status'].values.tolist()[0])
            # CRT_TIME = 不现获取，而是通过df获取测试当时的时刻
            CRT_TIME = (df_one['Timestamp'].values[0])
            # print(type(CRT_TIME),type(LastTime)) #找不到法子把这个ns的datetime64转化datetime，直接时间戳转
            self.dataframe['CRT_TIME'].append(CRT_TIME)
            # 仅此两个计算属性（逻辑，当前测试状态改变改变时间定为现在，状态持续时间也不从上一状态计而是变为0
            self.dataframe['CHANGE_TIME'].append(LastTime if data[1] == df_one['Status'].values[0] else CRT_TIME)
            delta = CRT_TIME.astype(datetime)/1000000 - LastTime.timestamp()*1000 #注意单位化为ms
            # print(delta,CRT_TIME.astype(datetime)/1000000,LastTime.timestamp()*1000)
            self.dataframe['LAST_DURATION'].append((delta + data[4]) if data[1] == df_one['Status'].values[0] else 0)
        conn.close()

    def save2mysql(self):
        for id in self.serviceLists:
            self.get_performance(id[0])
        """ 从dataframe保存至mysql(加上后置数据处理) """ 
        engine = create_engine("mysql+pymysql://root:123456@127.0.0.1:3306/performancedb?charset=utf8")
        df = pd.DataFrame(self.times) #dataframe需的字典是包含index信息的 所以times值是列表
        logging.info(df)
        df.to_sql('TB_PERFORMANCE',con=engine,if_exists='append', index=False) #是否用索引
        # 存入status计数（比较简单就不单独作为类变量
        dataframe_count = {'STATUS':df['Status'].value_counts().index.tolist(),'NUMBER':df['Status'].value_counts().values.tolist(),'RECORD_TIME':[self.TestYKB_TIME]*len(df['Status'].value_counts())}
        # 给各个状态填充默认值
        for i in [1,2,3,4,5,6]:
            if i not in df['Status'].value_counts().index:
                dataframe_count['STATUS'].append(i)
                dataframe_count['NUMBER'].append(0)
                dataframe_count['RECORD_TIME'].append(self.TestYKB_TIME)
        pd.DataFrame(dataframe_count).to_sql('TB_PERFORMANCE_COUNT',con=engine,if_exists='append', index=False)
        # 存入服务状态变迁统计(流程：根据id列表查上次状态表和这次times对比)
        for id in self.serviceLists:
            self.generate_performance_status(pd.DataFrame(self.times)[df['serviceId']==id[0]],id[0]) #传入times的df类型比times好操作点
        
        print((self.dataframe))
        pd.DataFrame(self.dataframe).to_sql('TB_SERVICE_STATUS',con=engine,if_exists='append', index=False)

    
          

def getMainKeyList(): # 是否作为实例函数耦合
#itemid列表
    return key_list




def process_job():

    print((time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())))
    def process2(servies,datetime):
        print(datetime)
        testykb = TestYKB(servies,datetime)
        testykb.setup()
        testykb.save2mysql()
        print('此次测试的已请求数量:',len(testykb.times['serviceId'])) #应该是852条全跑完了
        testykb.teardown()

    start_time_process = time.time()
    record_time = datetime.now()
    print(len(getMainKeyList()))
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process2,getMainKeyList()[x*36:x*36+36],record_time) for x in range(24)]
        # concurrent.futures.as_completed(futures) # 应该不需要这个就complete了
    print ("Process pool execution in " + str(time.time() - start_time_process), "seconds")
    
    # testykb.save2mysql()



def testjob():
    # 多线程为什么没有效果呢，仅个get也是。process包含Test对象创建会报错。
    testykb2 = TestYKB()
    testykb2.setup()
    def process():
        '''因为上面的getperformance没有效果，就一个请求看多线程对比，结果仍没有提升是说明非网络io任务'''
        testykb2.driver.get("http://www.tieba.com")
        WebDriverWait(testykb2.driver, 10).until(lambda driver: driver.execute_script('return document.readyState') == 'complete')

    start_time_thread = time.time()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(process()) for item in range(200)]
        # concurrent.futures.as_completed(futures) # 应该不需要这个就complete了
    print ("Thread pool execution in " + str(time.time() - start_time_thread), "seconds")
    start_time_order = time.time()  
    [process() for id in range(200)]
    print ("Order execution in " + str(time.time() - start_time_order), "seconds")
    testykb2.teardown()


    
if __name__ == '__main__':
    import sys
    import schedule
    #顺序执行一遍
    testykb = TestYKB(getMainKeyList(),datetime.now())
    testykb.setup()
    testykb.save2mysql()
    print('此次测试的已请求数量:',len(testykb.times['serviceId'])) 
    testykb.teardown()    

    #定时并发执行
#    while True:
#        process_job()
        #schedule.run_pending()   # 运行所有可以运行的任务
        #time.sleep(1)
