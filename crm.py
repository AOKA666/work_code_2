import requests
import json
import datetime

from info import get_teacher_dict


class FM:
    """登录crm获取学员列表"""
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.headers = {
        "Referer": "https://eds2.gaodun.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) \
            Chrome/84.0.4147.105 Safari/537.36",        
        }
        # 获取老师列表
        self.teacher_dict = get_teacher_dict()
        self.teachers = list(self.teacher_dict.values())
        self.start_record = 1
        self.need_record = False
        self.teacher2code = dict(zip(self.teacher_dict.values(), self.teacher_dict.keys()))
        
    def get_info(self):
        """获得token"""
        login_session = requests.Session()
        headers = self.headers
        kv = {
        "user": self.username,
        "password": self.password, 
        "appid": 210302
        }
        url = "https://apigateway.gaodun.com/api/v4/vigo/login"
        r = login_session.post(url, data=kv, headers=headers)
        result = json.loads(r.content.decode('utf-8'))
        token = result['refreshToken']
        
        return 'Basic '+token

    def get_list(self):
        """获取学员列表"""
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=30)
        token = self.get_info()
        url = 'https://apigateway.gaodun.com/olaf/api/v1/auth/list'
        kv = {
            "projectId":1000053,
            "statusStage":100118200,
            "status":2012959,
            "teacherIdList":[9485],
            "enterTimeStart":str(start_date),
            "enterTimeEnd":str(end_date),
            "pageNum":1,
            "pageSize":300
        }
        d = {
            "Authentication": token,
            "Content-Type": "application/json; charset=UTF-8",
            "Host": "apigateway.gaodun.com",
        }
        self.headers.update(d)
        r = requests.post(url, json=kv, headers=self.headers)
        res = json.loads(r.content.decode('utf-8'))
        total_size = res['result']['totalSize']
        data_list = res['result']['list']
        if total_size > 1:
            for i in range(1, total_size):
                kv['pageNum'] = i+1
                r = requests.post(url, json=kv, headers=self.headers)
                res = json.loads(r.content.decode('utf-8'))
                data_list.extend(res['result']['list'])
        ls = []
        for i in data_list:
            school = ''
            product = [p['productName'] for p in i['productList']]
            for j in product:
                if '实验班' in j:
                    school = j
            ls.append({'name': i['realName'], 'school': school, 'id': i['id']})
        return ls

    def track_last_teacher(self):
        """读取上次分配轮到谁"""
        with open("track.txt") as f:
            teacher_id = f.read()
        return teacher_id

    def record_last_teacher(self, teacher_id):
        """记录上次分配轮到谁"""
        with open("track.txt", "wt") as f:
            f.write(teacher_id)

    def cal_number(self, stu_list, allocated):
        """计算除去实验班，每个老师还剩几个学员"""
        count = len(stu_list)
        print('\n准备分配FM...')
        print(f"共有{count}个学员")
        average = count // len(self.teachers)
        left = count % len(self.teachers)
        lucky_teacher = []
        if left:
            # 没有整除
            self.need_record = True
            start = int(self.track_last_teacher())       
            for index in range(left):
                number = (start+index) % len(self.teachers)
                if number == 0:
                    number = len(self.teachers)
                lucky_teacher.append(number)
                self.start_record = number
        stu_num_dict = {}
        for i in self.teachers:
            if self.teachers.index(i)+1 in lucky_teacher:
                stu_num_dict[i] = average + 1 
            else:
                stu_num_dict[i] = average       
        for j in allocated:
            stu_num_dict[j] -= len(allocated[j])
        diploy_list = {}
        for t in self.teachers:
            diploy_list[t] = []
            # {'':[], '':[]}

        # 除去实验班之后的订单id列表
        order_id_list = []
        for stu in stu_list:
            # 总的学员列表
            order_id_list.append(stu['id'])
        for values in list(allocated.values()):
            for each in values:
                order_id_list.remove(each)

        index = 0
        # print(order_id_list)
        # stu_num_dict: 每一个老师除去实验班还剩下的同学id,格式{'老师id':7}
        for teacher in stu_num_dict:
            if stu_num_dict[teacher] < 0:
                continue
            for loop in range(stu_num_dict[teacher]):
                # 列表中有多少学员，循环多少次
                diploy_list[teacher].append(order_id_list[index])
                index += 1
        print('不算实验班的数据：', self.transfer(diploy_list))
        for key in diploy_list:
            if allocated.get(key):
                diploy_list[key].extend(allocated[key])
        print('加上实验班的数据：',self.transfer(diploy_list))        
        return diploy_list

    def assign_student(self, data_list):
        """分配认证老师"""
        token = self.get_info()
        url = 'https://apigateway.gaodun.com/olaf/api/v1/auth/auth-teacher/update'        
        d = {
                "Authentication": token,
                "Content-Type": "application/json; charset=UTF-8",
                "Host": "apigateway.gaodun.com",
            }
        self.headers.update(d)
        for teacher_id, school_ids in data_list.items():
            kv = {
                "id": school_ids,
                "teacherId": teacher_id,
                "emailStatus": "false"
            }
            r = requests.post(url, json=kv, headers=self.headers)
        res = json.loads(r.content.decode('utf-8'))
        print("分配完成!")
        if self.need_record:
            self.record_last_teacher(str(self.start_record % 5 + 1))
        return res

    def transfer(self, data):
        """输出中将老师code转为老师名字"""
        result = {}
        for i in data:
            result[self.teacher2code[i]] = data[i]
        return result
