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
    city_db_reader = geoip2.database.Reader('./GeoLite2-City.mmdb')
    country_db_reader = geoip2.database.Reader('./GeoLite2-Country.mmdb')
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

def get_geo_info(ip_address, record_type):
    try:
        if record_type == 'city':
            geo_info = city_db_reader.city(ip_address).city.names[language]
        elif record_type == 'country':
            geo_info = country_db_reader.country(ip_address).country.names[language]
        else:
            raise ValueError(f"Unsupported record type: {record_type}")
    except geoip2.errors.AddressNotFoundError:
        logger.error(f"{record_type.capitalize()} information not found for IP {ip_address}, language {language}")
        return f"The address {ip_address} is not in the {record_type} database."
    except KeyError as ke:
        logger.error(f"Language key error for {record_type} lookup: {ke}, IP {ip_address}, language {language}")
        return f"Language key error during {record_type} lookup for IP {ip_address}."
    except Exception as e:
        logger.exception(f"Unexpected error during {record_type} lookup for IP {ip_address}, error: {e}")
        return f"An unexpected error occurred while looking up the {record_type} for IP {ip_address}."
    return geo_info


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
    plain_res = (f"\nip address: {ip_address} \n"
                 f"country: {country} \n"
                 f"city: {city} \n"
                 f"url: https://ifconfig.icu/{ip_address} \n")
    if is_cli(request):
        return PlainTextResponse(f"{plain_res}\n")
    headers_tuple = request.headers.items(
    ) + [("city", city), ("country", country), ("ip", ip_address)]
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
            country = get_geo_info(ip_address, 'country')
            city = get_geo_info(ip_address, 'city')
            plain_res = (f"\nip address: {ip_address} \n"
                         f"country: {country} \n"
                         f"city: {city} \n"
                         f"url: https://ifconfig.icu/{ip_address}\n")
            if is_cli(request):
                return PlainTextResponse(f"{plain_res}\n")
            headers_tuple = request.headers.items(
            ) + [("city", city), ("country", country), ("ip", ip_address)]
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
    country = get_geo_info(ip_address, 'country')
    city = get_geo_info(ip_address, 'city')
    match name:
        case "country":
            return PlainTextResponse(f"{country}\n")
        case "city":
            return PlainTextResponse(f"{city}\n")
        case "ip":
            return PlainTextResponse(f"{ip_address}\n")
        case "all.json":
            headers_tuple = request.headers.items(
            ) + [("city", city), ("country", country)]
            return JSONResponse({key: value for key, value in headers_tuple})
        case _:
            if dict(request.headers).get(f"{name}"):
                return dict(request.headers).get(f"{name}")
            else:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Command not found!",
                                    headers={"X-Error": "Error"})


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
