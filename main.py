import logging
import os
from typing import Optional
import re
import ipaddress
import geoip2.database
import uvicorn
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger("uvicorn.error")

try:
    city_db_reader = geoip2.database.Reader('./GeoLite.mmdb/GeoLite2-City.mmdb')
    country_db_reader = geoip2.database.Reader('./GeoLite.mmdb/GeoLite2-Country.mmdb')
except TypeError:
    logger.error('APP: Could not find MaxMind database\n')
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
def lookup_ip(request: Request):
    if PROXY_MODE:
        res = request.headers.get('x-forwarded-for', "").split(',')[0].strip()
        logger.debug(f"APP: In Proxy Mode, resolved IP is {res}")
    else:
        client_info = getattr(request.client, "host", None)
        if client_info is not None:
            res = client_info
            logger.debug(f"APP: In Non-Proxy Mode, resolved IP is {client_info}")
        else:
            logger.warning("APP: Client host information not available; defaulting to 'Unknown'.")
            res = "Unknown"
    return res

import geoip2.errors

def get_geo_info(ip_address, record_type):
    try:
        if record_type == 'city':
            geo_info = city_db_reader.city(ip_address).city.names.get(language, 'City Not Found')
        elif record_type == 'country':
            geo_info = country_db_reader.country(ip_address).country.names.get(language, 'Country Not Found')
        else:
            raise ValueError(f"Unsupported record type: {record_type}")
    except geoip2.errors.AddressNotFoundError:
        logger.warning(f"APP: IP address {ip_address} not found in {record_type} database.")
        return f"信息未找到" # 简化用户看到的错误信息
    except Exception as e:
        logger.error(f"APP: Error looking up {record_type} for IP {ip_address}: {e}")
        return f"获取{record_type}信息失败" # 简化用户看到的错误信息
    return geo_info

def _prepare_context(request: Request, ip_address, city, country, cmd_options):
    plain_res = (f"ip address: {ip_address} \n"
                 f"country: {country} \n"
                 f"city: {city} \n"
                 f"url: https://ifconfig.icu/{ip_address}\n")
    headers_tuple = list(request.headers.items()) + [("city", city), ("country", country), ("ip", ip_address)]
    headers_json = {key: value for key, value in headers_tuple}
    context = {
        "all": headers_json,
        "cmd": is_cli(request),
        "cmd_with_options": mk_cmd(cmd_options),
        "plain_res": plain_res,
        "ip_address": ip_address,
        "headers": headers_tuple,
        "country": country,
        "city": city,
        "request": request
    }
    return context


def is_cli(request: Request):
    user_agent = request.headers.get('user-agent', "")
    cli_patterns = r"(curl|wget|Wget|fetch slibfetch)"
    match = re.search(cli_patterns, user_agent, re.IGNORECASE)
    if match:
        logger.debug(f"APP: Detected CLI: {match.group()}")
        return match.group()
    logger.debug(f"APP: No recognizable CLI detected in User-Agent: {user_agent}")
    return False


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
    country = get_geo_info(ip_address, 'country')
    city = get_geo_info(ip_address, 'city')
    context = _prepare_context(request, ip_address, city, country, cmd)
    if is_cli(request):
        return PlainTextResponse(f"{context['plain_res']}")
    return templates.TemplateResponse("index.html", context)


def is_valid_ip(ip_address: str):
    try:
        ip_obj = ipaddress.ip_address(ip_address)
        return ip_obj.version == 4 or ip_obj.version == 6
    except ValueError:
        return False


@app.head("/")
async def root_head():
    """
    This endpoint is used to respond to Uptime Robot's monitoring checks.
    It returns an empty response with HTTP status code 200 to indicate that the service is up and running.
    """
    return None


@app.get("/{query_type}")
@app.get("/{ip_address}/{query_type}")
async def custom_query(request: Request, query_type: Optional[str] = None, ip_address: Optional[str] = None, cmd: Optional[str] = "curl"):
    if query_type and is_valid_ip(query_type):
        # 处理 /ip_address 单个参数被当成 query_type的情况
        ip_address = query_type
        query_type = None

    if ip_address and is_valid_ip(ip_address):
        # 处理特定IP地址的情况
        country = get_geo_info(ip_address, 'country')
        city = get_geo_info(ip_address, 'city')
        
        if query_type:
            if query_type == "country":
                return PlainTextResponse(f"{country}\n")
            elif query_type == "city":
                return PlainTextResponse(f"{city}\n")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid query type")
        else:
            context = _prepare_context(request, ip_address, city, country, cmd)
            if is_cli(request):
                return PlainTextResponse(f"{context['plain_res']}\n")
            return templates.TemplateResponse("index.html", context)

    # 处理没有特定IP地址的情况
    ip_address = lookup_ip(request)
    country = get_geo_info(ip_address, 'country')
    city = get_geo_info(ip_address, 'city')
    if query_type in ["country", "city", "ip"]:
        if query_type == "country":
            return PlainTextResponse(f"{country}\n")
        elif query_type == "city":
            return PlainTextResponse(f"{city}\n")
        elif query_type == "ip":
            return PlainTextResponse(f"{ip_address}\n")
    elif query_type == "all.json":
        headers_tuple = list(request.headers.items()) + [("city", city), ("country", country)]
        return JSONResponse({key: value for key, value in headers_tuple})
    elif query_type:
        if dict(request.headers).get(query_type):
            return PlainTextResponse(dict(request.headers).get(query_type) + "\n")
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found!", headers={"X-Error": "Error"})
    else: # query_type is None, 返回 index 页面
        context = _prepare_context(request, ip_address, city, country, cmd)
        if is_cli(request):
            return PlainTextResponse(f"{context['plain_res']}\n")
        return templates.TemplateResponse("index.html", context)

if __name__ == "__main__":
    log_level = "info"
    if bool(os.getenv("DEBUG")):
        log_level = "debug"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level=log_level,
        reload=True,
    )
