# 仅做一个post请求的数据收集无特殊处理。 分析字段时发现：有些服务pcLink需要人脸识别，用mainkey可以访问；有些服务用mainkey服务会显示没有Formid，用pclink发现是另外有个form；
# 生成csv用数据库ui直接导入数据库比sql建表插入快多了


import time
import requests, fake_useragent #官网的提示 很多时候你想要发送的数据并非编码为表单形式的而传递一个 string 
# from parsel import Selector
# from lxml import etree
import json,csv  

class Service_YKBApi:

    def __init__(self) -> None:
        self.payload = {  # 这里指定读最大一万条，一次读出
            "txnCommCom": {
                "txnIttChnlId": "C0071234567890987654321", 
                "txnIttChnlCgyCode": "BC01C101",
                "tRecInPage": "10000", 
                "tPageJump": "1",
                "explain":"此段是添加注释（json不支持注释只能冗余添加）。上面几个参数:有第几页，每页多少个，加密信息等（加密信息js中简单判断是否json返回来决定是否解密这里没解密）。这些是从页面响应js文件可看到request.js中如何封装请求和解析返回的"
            },
            "txnBodyCom": {
                "addrLvlCd": "2",
                "regnCode": "500000",
                "serviceObject": "0",
                "strLevel": "1",
                "type": "30",
                "explain":"此段负载是来自上层api请求的负载，https://zwykb.cq.gov.cn/images/request.js未解释"
            }
        }
        self.apiurl = "https://ykbapp.cq.gov.cn:8082/gml/web10021" # 直接通过api抓数据库信息（相当于拷贝出来）
        self.headers={"User-Agent" : fake_useragent.UserAgent().random}
        self.get_info_lists()


    def get_info_lists(self):
        self.res = requests.post(self.apiurl,json=self.payload,headers=self.headers)  # json参数代替data参数data=json.dumps(payload),
        # res看api测试返回可知有两次json字符串化操作需要反向解析
        pydict = (json.loads(self.res.text)) # 由api状态返回描述和返回内容组成
        pydict_1 =(json.loads(pydict["C-Response-Body"]))
        #print(type(pydict_1["lIST"][0]['basicCode']))
        self.lists = pydict_1['lIST'] #所有数据的json列表 [{'basicCode':str}, ]

    def to_csv(self):
        csv_file = open("origin-data.csv",'w',encoding="utf-8")
        sheet_title = self.lists[0].keys()
        json_value = []
        for dict in self.lists:
            json_value.append(dict.values())
        csv_writer = csv.writer(csv_file)

        #写入表头
        #print(len(json_value),json_value)
        csv_writer.writerow(sheet_title)
        csv_writer.writerows(json_value)
        csv_file.close()
    
    def to_json(self):
        json_file = open("origin-data.json",'w',encoding="utf-8") # 有gbk字符需要指定uft8存
        json.dump(self.lists,json_file,indent=4,ensure_ascii=False) # 指定间隔的禁用ASCII来显示中文
        json_file.close()
    
    
    def to_mysql(self):
        def generate_insert_sql(dicts):
            sql = """INSERT INTO TB_SERVICES(id,service_name,type,basis) VALUES('%s','%s',%s,'%s')""" % (dicts['id'],dicts['name'][:30],dicts['type'],dicts['basis'][:30])
            return sql
        mysqlurl="127.0.0.1/3306/root/123456/performancedb"
        import pymysql
        mysqlurl = mysqlurl.split("/")
        conn = pymysql.connect(host=mysqlurl[0],port=int(mysqlurl[1]),user=mysqlurl[2],passwd=mysqlurl[3],db=mysqlurl[4],charset='utf8')
        cursor = conn.cursor()
        table_sql = '''CREATE TABLE IF NOT EXISTS TB_SERVICES( 
                    id varchar(128) NOT NULL ,
                    service_name varchar(128) DEFAULT NULL ,
                    type int(12) DEFAULT 0 ,
                    basis longtext DEFAULT NULL,
                    PRIMARY KEY(id))
            ''' #这个表先取这几段关键信息
        cursor.execute(table_sql)
        for i in self.lists:
            sql = generate_insert_sql(i)
            #print(sql)
            cursor.execute(sql)
        conn.commit()
        conn.close()
        cursor.close()

if __name__ == "__main__":
    test = Service_YKBApi()
    test.to_csv()
