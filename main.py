import logging
import os
from typing import Optional
import re
import ipaddress

import geoip2.database
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates


try:
    city_db_reader = geoip2.database.Reader('./GeoLite2-City.mmdb')
    country_db_reader = geoip2.database.Reader('./GeoLite2-Country.mmdb')
except TypeError:
    logging.error('Could not find MaxMind database\n')
    exit(1)

app = FastAPI(
    title="ifconfig.icu",
    version="beta 0.2"
)

language = 'en'

DEBUG_MODE = bool(os.getenv("DEBUG"))
PROXY_MODE = bool(os.getenv("PROXY_MODE"))


app.mount("/static", app=StaticFiles(directory="./static"), name='static')
templates = Jinja2Templates(directory="templates")


# 若为代理模式需要完善这里
def lookup_ip(request):
    match PROXY_MODE:
        case True:
            res = request.headers['x-forwarded-for'].split(',')[0].strip()
            if DEBUG_MODE:
                print(f"In Proxy Mode, res is {res}")
        case _:
            res = request.client.host
            if DEBUG_MODE:
                print(f"In None Proxy Mode, res is {res}")
    return res


def get_city(ip_address):
    try:
        reader = city_db_reader.city(ip_address).city.names[language]
    except Exception as e:
        logging.error(f"没找到这种语言的城市 {language} 报错是{e} 现在正在查询的地址是{ip_address}")
        return f"The address {ip_address} is not in the database!"
    return reader


def get_country(ip_address):
    try:
        reader = country_db_reader.country(ip_address).country.names[language]
    except Exception as e:
        logging.error(f"没找到这种语言的国家 {language} 报错是{e} 现在正在查询的地址是{ip_address}")
        return f"The address {ip_address} is not in the database!"
    return reader


def is_cli(request: Request):
    res = ""
    user_agent = ""
    try:
        user_agent = dict(request.headers).get('user-agent')
        res = re.findall(r"(curl|wget|Wget|fetch slibfetch)", user_agent)
    except Exception as e:
        logging.debug(f"这吊毛我分析不了，不是字符串。他是 -> {str(user_agent)} 报错信息是 ->{e}")
    if len(res) == 0:
        logging.debug(f"这吊毛是个黑户没有UA，他的信息是 -> {request.headers} 记录在案。")
        return False
    return res[0]


def mk_cmd(cmd):
    match cmd:
        case "curl":
            return "curl"
        case "wget":
            return "wget -qO -"
        case "fetch":
            return "fetch -qo -"
        case _:
            return "curl"


@app.get("/")
def index(request: Request, cmd: Optional[str] = "curl"):
    ip_address = lookup_ip(request)
    country = get_country(ip_address)
    city = get_city(ip_address)
    plain_res = (f"\nip address: {ip_address} \n"
                     f"country: {country} \n"
                     f"city: {city} \n"
                     f"url: https://ifconfig.icu/{ip_address} \n")
    if is_cli(request):
        return PlainTextResponse(f"{plain_res}\n")
    headers_tuple = request.headers.items() + [("city", city), ("country", country), ("ip", ip_address)]
    headers_json = {key: value for key, value in headers_tuple}
    context = {
        "all": headers_json,
        "cmd": is_cli(request),
        "cmd_with_options": mk_cmd(cmd),
        "plain_res": plain_res.replace("\n", "<br>"),
        "ip_address": ip_address,
        "headers": headers_tuple,
        "country": country,
        "city": city,
        "request": request
    }
    return templates.TemplateResponse("index.html", context)


def is_valid_ip(ip_address: str):
    try:
        ip_obj = ipaddress.ip_address(ip_address)
        return ip_obj.version == 4 or ip_obj.version == 6
    except ValueError:
        return False


@app.get("/{name}")
async def custom_query(name: str, request: Request, cmd: Optional[str] = "curl"):
    match name:
        case ip_address if is_valid_ip(ip_address):
            country = get_country(ip_address)
            city = get_city(ip_address)
            plain_res = (f"\nip address: {ip_address} \n"
                             f"country: {country} \n"
                             f"city: {city} \n"
                             f"url: https://ifconfig.icu/{ip_address}\n")
            if is_cli(request):
                return PlainTextResponse(f"{plain_res}\n")
            headers_tuple = request.headers.items() + [("city", city), ("country", country), ("ip", ip_address)]
            headers_json = {key: value for key, value in headers_tuple}
            context = {
                "all": headers_json,
                "cmd": is_cli(request),
                "cmd_with_options": mk_cmd(cmd),
                "plain_res": plain_res.replace("\n", "<br>"),
                "ip_address": ip_address,
                "headers": headers_tuple,
                "country": country,
                "city": city,
                "request": request
            }
            return templates.TemplateResponse("index.html", context)
    ip_address = lookup_ip(request)
    country = get_country(ip_address)
    city = get_city(ip_address)
    match name: 
        case "country":
            return PlainTextResponse(f"{country}\n")
        case "city":
            return PlainTextResponse(f"{city}\n")
        case "ip":
            return PlainTextResponse(f"{ip_address}\n")
        case "all.json":
            headers_tuple = request.headers.items() + [("city", city), ("country", country)]
            return JSONResponse({key: value for key, value in headers_tuple})
        case _:
            if dict(request.headers).get(f"{name}"):
                return dict(request.headers).get(f"{name}")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found!",
                                    headers={"X-Error": "Error"})


# if __name__ == "__main__":
#     uvicorn.run(
#         "main:app",
#         host="0.0.0.0",
#         port=8000,
#         log_level="info",
#         reload=True
#     )
