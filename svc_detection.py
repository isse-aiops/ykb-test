# -*- encoding: utf-8 -*-
import pymysql
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

# 远程数据库配置
DB_ADDR = "10.236.101.14"
DB_PORT = 3306
DB_USER = "root"
DB_PWD = "123456"
DB_SCHEMA = "performancedb"

# 页面及数据数据需求
# 登录页面
LOGIN_URL = "https://auth.cq.gov.cn:81/sso/login?utype=0"
# 登录SESSION
JSESSIONID = "inspurbb332f8993d84dcca368954a0a4127eb"

# SQL语句
# 查询服务名称，所属部门，ID
QUERY_SVC_ITEM_ID_SQL = """
    select
        ITEM_ID, DEPT_NAME, task_name
    FROM
        audit_item
    LIMIT 0,1000
"""

def getMysqlConn():
    """获取数据库连接"""
    conn = pymysql.connect(
        host=DB_ADDR,
        port=DB_PORT,
        user=DB_USER,
        passwd=DB_PWD,
        db=DB_SCHEMA
    )
    return conn

def getServiceList():
    """获取所有的服务"""
    try:
        db = getMysqlConn()
        cursor = db.cursor()
        
    except Exception as e:
        print(e)
    finally:
        db.close()


class WebSvcAnalyzer:

    def __init__(self, webdriver_path):
        self.webdriver_path = webdriver_path
        self._setupWebdriver(self.webdriver_path)

    def _setupWebdriver(self, webdriver_path):
        self.opt = webdriver.ChromeOptions()
        self.opt.add_argument('--headless')
        self.driver = webdriver.Chrome(executable_path=webdriver_path,options=self.opt)
        self.driver.maximize_window()

    def getSvcStatus(self, service_id):
        """获取单个服务状态
        """
    
    def generateAnomalousSvcData():
        """生成数据并写入数据库
        """
    
    def _writeSvcStatusToDb(data:tuple):
        """写入数据到数据库
        """

if __name__ == "__main__":
    webdriver_path = ""
    analyzer = WebSvcAnalyzer(webdriver_path)
    analyzer.generateAnomalousSvcData()