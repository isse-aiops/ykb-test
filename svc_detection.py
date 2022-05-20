# -*- encoding: utf-8 -*-
import json
import logging
import pymysql
from selenium.webdriver.support.ui import WebDriverWait
from msedge.selenium_tools import Edge, EdgeOptions

# 远程数据库配置
DB_ADDR = "10.236.101.14"
DB_PORT = 3306
DB_USER = "root"
DB_PWD = "123456"
DB_SCHEMA = "performancedb"

# 页面及数据数据需求
# 登录页面
LOGIN_URL = "https://auth.cq.gov.cn:81/sso/login?utype=0"
# 服务详情页面
SVC_URL = "https://zwykb.cq.gov.cn/grbs/bszn/?itemid={svc_id}"
# 登录SESSION
JSESSIONID = "inspurbb332f8993d84dcca368954a0a4127eb"

# SQL语句
# 查询服务名称，所属部门，ID
QUERY_SVC_SQL = """
    select
        ITEM_ID, DEPT_NAME, task_name
    from
        audit_item
    limit 0,1000
"""

INSERT_SVC_STATUS = """
    insert into
        `t_anomalous_svc_detection`(`id`,`svc_department`,`svc_name`,`svc_status`)
    values
        (%s, %s, %s, %s)
"""

# 日志
logging.basicConfig(
    level=logging.INFO
)

# 服务状态 
SVC_UNAVAILABLE = 0 # 不可用
SVC_ANOMALY = 1     # 访问异常
SVC_TIMEOUT = 2     # 访问超时

TIMEOUT_ST = 5000   # 超时阈值

def getMysqlConn():
    """获取数据库连接"""
    conn = pymysql.connect(
        host=DB_ADDR,
        port=DB_PORT,
        user=DB_USER,
        passwd=DB_PWD,
        database=DB_SCHEMA
    )
    return conn

def getServiceList():
    """获取所有的服务"""
    svc_list = []
    db = getMysqlConn()
    try:
        cursor = db.cursor()
        cursor.execute(QUERY_SVC_SQL)
        svc_data = cursor.fetchall()
        for row in svc_data:
            single_svc_info = {}
            single_svc_info['id'] = row[0]
            single_svc_info['svc_department'] = row[1]
            single_svc_info['svc_name'] = row[2]
            svc_list.append(single_svc_info)
    except Exception as e:
        logging.ERROR(e)
    finally:
        db.close()
    
    return svc_list


class WebSvcAnalyzer:

    def __init__(self, webdriver_path):
        self.webdriver_path = webdriver_path
        self._setupWebdriver(self.webdriver_path)

    def _setupWebdriver(self, webdriver_path):
        options = EdgeOptions()
        options.use_chromium = True
        options.add_argument('headless')
        self.driver = Edge(executable_path=webdriver_path, options=options)

    def shutdown(self):
        self.driver.quit()

    def getAnomalousSvcStatus(self, service_id):
        """获取单个服务状态
        """
        svc_status = -1  # 服务状态

        try:
            self.driver.get(SVC_URL.format(svc_id=service_id))   
            # 显式等待加载完毕，直接sleep也可,否则是load状态就获取timing了
            WebDriverWait(self.driver, 10).until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            logging.info(self.driver.execute_script('return document.readyState'))
            js = self.driver.execute_script("return JSON.stringify(performance.timing)")
            idict = json.loads(js) # 字典类型
            
            # 判定服务状态
            element = self.driver.find_element_by_link_text("立即办理").get_attribute("style")
            if "rgb(239, 239, 239)" in element:
                svc_status = SVC_UNAVAILABLE
            elif idict['loadEventEnd']-idict['navigationStart'] >= TIMEOUT_ST:
                svc_status = SVC_TIMEOUT
        except:
            svc_status = SVC_ANOMALY

        return svc_status

    def generateAnomalousSvcData(self, svc_list):
        """生成数据并写入数据库
        """
        anomolous_svc_list = []
        for svc_item in svc_list:
            svc_status = self.getAnomalousSvcStatus(svc_item['id'])
            if svc_status < 0:
                continue
            svc_item['svc_status'] = svc_status
            anomolous_svc_list.append(svc_item)

        # 按照插入顺序构造tulpe
        rows = list()
        for item in anomolous_svc_list:
            row = list()
            row.append(item['id'])
            row.append(item['svc_department'])
            row.append(item['svc_name'])
            row.append(item['svc_status'])
            rows.append(row)
        
        with open("svc.txt", "w") as f:
            f.writelines(str(rows))
        logging.info("Write to db.")
        self._writeSvcStatusToDb(tuple(rows))
    
    def _writeSvcStatusToDb(self, data:tuple):
        """写入数据到数据库
        """
        db = getMysqlConn()
        try:
            cursor = db.cursor()
            cursor.executemany(INSERT_SVC_STATUS, data)
            db.commit()
        except pymysql.Error as e:
            logging.error(e)
            db.rollback()
        finally:
            db.close()


if __name__ == "__main__":
    webdriver_path = "./tools/msedgedriver47.exe"
    analyzer = WebSvcAnalyzer(webdriver_path)
    # analyzer.getAnomalousSvcStatus("0020ec0f-3531-43d9-a324-fdc206772abc")
    svc_list = getServiceList()
    analyzer.generateAnomalousSvcData(svc_list)
