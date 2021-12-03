# 此脚本爬特定一个api接口并输出json


# 根据审查元素和在线测试发现：
# 办事指南页面固定参数是businessid且无需登录状态和认证
# 在线办理页面都需要登录状态才能访问，但有些页面只能app刷脸认证进入（不知是否可解决暂做个标注），另一些页面的在线办理不可用是个无信息元素不纳入数据收集

import time
import requests, fake_useragent
from parsel import Selector
from lxml import etree
UA_mobile = "Mozilla/5.0 (Linux; Android 6.0.1; Moto G (4)) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Mobile Safari/537.36"
ua = fake_useragent.UserAgent()
headers={"User-Agent" : ua.random}
def test():
    res = requests.get("https://zwykb.cq.gov.cn/grbs/",headers=headers) # verify使得ssl错误变成proxy错误
    # print(res.headers,res.request.headers)
    res.encoding = 'utf8'
    # print(res.text)
    sl = Selector(res.text) 
    #/html/body/div[5]/div/div[2]/div[5]/ul/li[1]/div[2]/ul/li[1]/a ==》 //div[@class='table']/ul/li[1]/div[2]/ul/li[1]/a  办事指南是li[2]
    print(sl.xpath("/html/body/div[5]/div/div[2]/div[3]/div[1]/span").get())  # 为您匹配到  个项目（说明是动态页面

apiurl = "https://ykbapp.cq.gov.cn:8082/gml/web10021" # 直接通过api抓数据库信息（相当于拷贝出来）

payload = {  # 先指定读个一万条
  "txnCommCom": {
    "txnIttChnlId": "C0071234567890987654321", 
    "txnIttChnlCgyCode": "BC01C101",
    "tRecInPage": "10000", 
    "tPageJump": "1",
    "explain":"此段是添加注释（json不支持注释只能冗余添加）。上面几个参数有第几页，每页多少个，加密信息等（加密信息js中简单判断是否json返回来决定是否解密这里没解密）。这些是从页面响应js文件可看到request.js中如何封装请求和解析返回的"
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
import json,csv  #看到官网的提示很多时候你想要发送的数据并非编码为表单形式的而传递一个 string 
res = requests.post("https://ykbapp.cq.gov.cn:8082/gml/web10021",data=json.dumps(payload),headers={"User-Agent" :ua.random})
res = requests.post("https://ykbapp.cq.gov.cn:8082/gml/web10021",json=payload,headers={"User-Agent" :ua.random})
#res = r = requests.post("http://httpbin.org/post", data=payload)
# print(res.text) # 查找和浏览器差别太麻烦了，直接看postman等的header进行测试（虽然结果是没有从request角度发现问题是以为其做了其他header处理）
pydict = (json.loads(res.text)) # 由api状态返回描述和返回内容组成
pydict_1 =(json.loads(pydict["C-Response-Body"]))
#print(type(pydict_1["lIST"][0]['basicCode']))
lists = pydict_1['lIST'] #所有数据的json列表

def to_csv():
    csv_file = open("data.csv",'w',encoding="utf-8")
    sheet_title = lists[0].keys()
    json_value = []
    for dict in lists:
        json_value.append(dict.values())
    csv_writer = csv.writer(csv_file)

    #写入表头
    #print(len(json_value),json_value)
    csv_writer.writerow(sheet_title)
    csv_writer.writerows(json_value)
    csv_file.close()
    
def to_json():
    json_file = open("data.json",'w',encoding="utf-8") # 有gbk字符需要指定uft8存
    json.dump(lists,json_file,indent=4,ensure_ascii=False) # 指定间隔的禁用ASCII来显示中文
    json_file.close()
   
   
def to_mysql():
    def generate_insert_sql(dicts):
        sql = """INSERT INTO TB_service(id,service_name,type,basis) VALUES('%s','%s',%s,'%s')""" % (dicts['id'],dicts['name'][:30],dicts['type'],dicts['basis'][:30])
        return sql
    mysqlurl="10.236.101.17/3306/root/123456/performancedb"
    import pymysql
    mysqlurl = mysqlurl.split("/")
    conn = pymysql.connect(host=mysqlurl[0],port=int(mysqlurl[1]),user=mysqlurl[2],passwd=mysqlurl[3],db=mysqlurl[4],charset='utf8')
    cursor = conn.cursor()
    table_sql = '''CREATE TABLE IF NOT EXISTS TB_service( 
                   id varchar(100) NOT NULL ,
                   service_name varchar(36) DEFAULT NULL ,
                   type int(11) DEFAULT 0 ,
                   basis longtext DEFAULT NULL,
                   PRIMARY KEY(id))
        ''' #暂时来三个字段
    cursor.execute(table_sql)
    for i in lists:
        sql = generate_insert_sql(i)
        #print(sql)
        cursor.execute(sql)
    conn.commit()
    conn.close()
    cursor.close()
print(len(lists)) #852
to_mysql() 