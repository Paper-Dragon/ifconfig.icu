import logging
import os

import geoip2.database
import uvicorn
from fastapi import FastAPI, Request, Header, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import PlainTextResponse
import re
from pydantic import BaseModel
from enum import Enum

logging.basicConfig(
    level=logging.DEBUG,
    # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s-%(funcName)s'
    format='%(levelname)s:     %(name)s - %(message)s - %(funcName)s'
)

try:
    city_db_reader = geoip2.database.Reader('./GeoLite2-City.mmdb')
    country_db_reader = geoip2.database.Reader('./GeoLite2-Country.mmdb')
except TypeError:
    logging.error('Could not find MaxMind database\n')
    exit(1)

app = FastAPI(
    title="ifconfig.icu",
    version="beta 0.1"
)

language = 'zh-CN'

app.mount("/static", app=StaticFiles(directory="./static"), name='static')
templates = Jinja2Templates(directory="templates")

# 若为代理模式需要完善这里
def lookup_ip(request):
    match os.getenv("PROXY_MODE"):
        case True:
            res = request.client.host
        case _:
            res = request.client.host
    return res


def get_city(ip_address):
    try:
        reader = city_db_reader.city(ip_address).city.names[language]
    except Exception as e:
        logging.error(e)
        return f"I don't known Your City! The address {ip_address} is not in the database"
    return reader


def get_country(ip_address):
    try:
        reader = country_db_reader.country(ip_address).country.names[language]
    except Exception as e:
        logging.error(e)
        return f"I don't known Your Country! The address {ip_address} is not in the database"
    return reader


def is_cli(request: Request):
    user_agent = dict(request.headers).get('user-agent')
    res = re.findall(r"(curl|wget|Wget|fetch slibfetch)", user_agent)
    if len(res) == 0:
        return False
    return res[0]


def mk_cmd(cmd):
    match cmd:
        case "curl":
            return "curl"
        case ["wget", "Wget"]:
            return "wget -qO -"
        case "fetch slibfetch":
            return "fetch -qo -"
        case _:
            return ""


@app.get("/")
def index(request: Request):
    if is_cli(request):
        return lookup_ip(request)
    headers = dict(request.headers)

    # 删除可在Proxy模式下错误数据。
    del headers['host']

    ip_address = lookup_ip(request)
    headers['ip-address'] = ip_address
    headers['city'] = get_city(ip_address)
    headers['country'] = get_country(ip_address)
    print(headers)
    context = {}
    context["cmd"] = is_cli(request)
    context["cmd_with_options"] = mk_cmd(is_cli(request))
    context["ip_address"] = ip_address
    context["headers"] = headers
    context["country"] = get_country(ip_address)
    context["city"] = get_city(ip_address)
    context["request"] = request
    print(context)
    return templates.TemplateResponse("index.html",context)


@app.get("/{name}")
async def custom_query(name: str, request: Request):
    match name:
        case "country":
            ip_address = lookup_ip(request)
            country = get_country(ip_address)
            return country
        case "city":
            ip_address = lookup_ip(request)
            city = get_city(ip_address)
            return city
        case "ip-address":
            return lookup_ip(request)
        case "all.json":
            res = dict(request.headers)

            # 删除可在Proxy模式下错误数据。
            del res['host']

            ip_address = lookup_ip(request)
            res['ip-address'] = ip_address
            res['city'] = get_city(ip_address)
            res['country'] = get_country(ip_address)
            return res
        case _:
            if dict(request.headers).get(f"{name}"):
                return dict(request.headers).get(f"{name}")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found",
                                    headers={"X-Error": "Error"})


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=True,
        # workers=8
    )
