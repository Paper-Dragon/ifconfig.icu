"""ifconfig.icu — IP 地址与地理信息查询服务"""
import os
import re
import ipaddress
import logging
from typing import Optional

import geoip2.database
import geoip2.errors
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, JSONResponse, Response
from fastapi.templating import Jinja2Templates

logger = logging.getLogger("uvicorn.error")

DEBUG = bool(os.getenv("DEBUG"))
PROXY = bool(os.getenv("PROXY_MODE"))
TEMPLATES = Jinja2Templates(directory="templates")


class GeoIPService:
    def __init__(self):
        self.city_reader: Optional[geoip2.database.Reader] = None
        self.country_reader: Optional[geoip2.database.Reader] = None

    def initialize(self) -> None:
        try:
            self.city_reader = geoip2.database.Reader("./GeoLite.mmdb/GeoLite2-City.mmdb")
            self.country_reader = geoip2.database.Reader("./GeoLite.mmdb/GeoLite2-Country.mmdb")
        except Exception as e:
            logger.error("地理数据库加载失败: %s", e)
            raise

    def close(self) -> None:
        for r in (self.city_reader, self.country_reader):
            if r:
                r.close()

    def get_geo(self, ip: str, kind: str) -> str:
        try:
            if kind == "city":
                return self.city_reader.city(ip).city.names.get("en", "City Not Found")
            return self.country_reader.country(ip).country.names.get("en", "Country Not Found")
        except geoip2.errors.AddressNotFoundError:
            return "信息未找到"
        except Exception as e:
            logger.error("GeoIP 查询失败 ip=%s kind=%s: %s", ip, kind, e)
            return "获取信息失败"


def is_valid_ip(s: str) -> bool:
    try:
        return ipaddress.ip_address(s).version in (4, 6)
    except ValueError:
        return False


def lookup_ip(req: Request) -> str:
    if PROXY:
        return (req.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    return getattr(req.client, "host", None) or "Unknown"


def is_cli(req: Request) -> bool:
    return bool(re.search(r"curl|wget|fetch", (req.headers.get("user-agent") or ""), re.I))


def plain_query(q: str, country: str, city: str, ip: str) -> Optional[Response]:
    if q == "country":
        return PlainTextResponse(f"{country}\n")
    if q == "city":
        return PlainTextResponse(f"{city}\n")
    if q == "ip":
        return PlainTextResponse(f"{ip}\n")
    return None


def render(req: Request, ip: str, city: str, country: str, cmd: str = "curl") -> Response:
    plain = f"ip address: {ip} \ncountry: {country} \ncity: {city} \nurl: https://ifconfig.icu/{ip}\n"
    if is_cli(req):
        return PlainTextResponse(plain)
    hl = list(req.headers.items()) + [("city", city), ("country", country), ("ip", ip)]
    return TEMPLATES.TemplateResponse("index.html", {
        "all": dict(hl),
        "cmd": cmd,
        "cmd_with_options": "wget -qO -" if cmd == "wget" else "fetch -qo -" if cmd == "fetch" else "curl",
        "plain_res": plain,
        "ip_address": ip,
        "headers": hl,
        "country": country,
        "city": city,
        "request": req,
    })


geo = GeoIPService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    geo.initialize()
    app.state.geo = geo
    yield
    geo.close()


app = FastAPI(title="ifconfig.icu", version="beta 0.2", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(Exception)
async def on_error(_: Request, exc: Exception):
    logger.exception("未处理异常: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


@app.get("/")
def index(req: Request, cmd: Optional[str] = "curl"):
    ip = lookup_ip(req)
    g = req.app.state.geo
    return render(req, ip, g.get_geo(ip, "city"), g.get_geo(ip, "country"), cmd)


@app.head("/")
def head_root():
    return None


@app.get("/{q}")
@app.get("/{ip_or_path}/{q}")
async def query(req: Request, q: Optional[str] = None, ip_or_path: Optional[str] = None, cmd: Optional[str] = "curl"):
    g = req.app.state.geo
    if q and is_valid_ip(q):
        ip_or_path, q = q, None
    if ip_or_path and is_valid_ip(ip_or_path):
        ip = ip_or_path
        country, city = g.get_geo(ip, "country"), g.get_geo(ip, "city")
        if q:
            if q in ("country", "city"):
                return plain_query(q, country, city, ip)
            raise HTTPException(404, detail="无效查询类型")
        return render(req, ip, city, country, cmd)
    ip = lookup_ip(req)
    country, city = g.get_geo(ip, "country"), g.get_geo(ip, "city")
    if q in ("country", "city", "ip"):
        return plain_query(q, country, city, ip)
    if q == "all.json":
        return JSONResponse(dict(list(req.headers.items()) + [("city", city), ("country", country)]))
    if q:
        v = req.headers.get(q)
        if v is not None:
            return PlainTextResponse(f"{v}\n")
        raise HTTPException(404, detail="命令未找到", headers={"X-Error": "错误"})
    return render(req, ip, city, country, cmd)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="debug" if DEBUG else "info", reload=DEBUG)
