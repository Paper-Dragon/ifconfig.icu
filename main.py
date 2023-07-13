import logging
import os

import geoip2.database
import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

# with geoip2.database.Reader('./GeoLite2-City.mmdb') as reader:
#     response = reader.city('101.231.101.116')
#     print(response.country.names['zh-CN'])
#     print(response.city.names['zh-CN'])
#     print(response.raw)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s-%(funcName)s'
)

try:
    city_db_reader = geoip2.database.Reader('./GeoLite2-City.mmdb').city
    country_db_reader = geoip2.database.Reader('./GeoLite2-Country.mmdb').country
except TypeError:
    logging.error('Could not find MaxMind database\n')
    exit(1)

app = FastAPI(
    title="ifconfig.icu",
    version="beta 0.1"
)

app.mount("/static", app=StaticFiles(directory="./static"), name='static')


# 若为代理模式需要完善这里
def lookup_ip(request):
    res = ""
    match os.getenv("PROXY_MODE"):
        case True:
            res = request.client.host
        case _:
            res = request.client.host
    return res


@app.get("/{command}")
async def get_command(command: str, request: Request):
    res = {
        # 客户端连接的 host
        "host": request.client.host,
        # 客户端连接的端口号
        "port": request.client.port,
        # 请求方法
        "method": request.method,
        # 请求路径
        "base_url": request.base_url,
        # request headers
        "headers": request.headers,
        # request cookies
        "cookies": request.cookies,
        # 请求 url
        "url": request.url,
        # 请求组成
        "components": request.url.components,
        # 请求协议
        "scheme": request.url.scheme,
        # 请求 host
        "hostname": request.url.hostname,
        # 请求端口
        "url_port": request.url.port,
        # 请求 path
        "path": request.url.path,
        # 请求查询参数
        "query": request.url.query,
        # 获取路径参数
        "path_params": request.path_params,
        # 获取查询参数
        "query_params": request.query_params
    }

    match command:
        case "country":
            ip_address = lookup_ip(request)
            return ip_address
        case "city":
            ip_address = lookup_ip(request)
            reader = city_db_reader.names
            return reader
        case "ip-address":
            return command
        case "all.json":
            return request.headers
        case _:
            return lookup_ip(request)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=True,
        workers=8
    )
