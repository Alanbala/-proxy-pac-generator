from flask import Flask, Response
import requests
import time
from functools import lru_cache

app = Flask(__name__)
IP_LIST_URL = "http://api.tianqiip.com/getip?secret=awkltj28l9j4c6fn&num=10&type=txt&port=1&time=3&mr=1&sign=0788785efdbaac16aadeda2521ef8f98"
CACHE_DURATION = 3 * 60  # 3分钟，单位为秒

# 自定义带时间限制的缓存装饰器
def timed_lru_cache(seconds: int, maxsize: int = 128):
    def wrapper(func):
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = seconds
        func.expiration = time.time() + func.lifetime
        
        def wrapped(*args, **kwargs):
            if time.time() >= func.expiration:
                func.cache_clear()
                func.expiration = time.time() + func.lifetime
            return func(*args, **kwargs)
        return wrapped
    return wrapper

# 使用自定义缓存装饰器
@timed_lru_cache(seconds=CACHE_DURATION)
def get_proxy_list():
    try:
        # 请求IP列表
        response = requests.get(IP_LIST_URL)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch IP list, status code: {response.status_code}")
        
        # 解析IP列表
        ip_lines = response.text.strip().split('\n')
        proxy_list = [line.strip() for line in ip_lines if line.strip()]
        
        if not proxy_list:
            raise Exception("No valid proxies found")
            
        print(f"成功获取代理列表，包含 {len(proxy_list)} 个代理服务器")
        return proxy_list
        
    except Exception as e:
        print(f"获取代理列表时出错: {e}")
        raise

@app.route('/proxy.pac')
def generate_pac_file():
    try:
        # 获取代理列表（可能从缓存中获取）
        proxy_list = get_proxy_list()
        
        # 构建PAC文件内容
        pac_content = f"""
function FindProxyForURL(url, host) {{
    // 从 {IP_LIST_URL} 获取的代理服务器列表
    var proxyList = {str(proxy_list)};
    
    // 简单的轮询机制，根据URL的哈希值选择代理服务器
    var hash = 0;
    for (var i = 0; i < url.length; i++) {{
        hash = ((hash << 5) - hash) + url.charCodeAt(i);
        hash |= 0; // 转换为32位整数
    }}
    
    var selectedProxy = proxyList[Math.abs(hash) % proxyList.length];
    return "PROXY " + selectedProxy;
}}
"""
        
        # 返回PAC文件
        return Response(
            pac_content,
            mimetype='application/x-javascript-config',
            headers={'Content-Disposition': 'inline; filename=proxy.pac'}
        )
        
    except Exception as e:
        return f"Error generating PAC file: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
