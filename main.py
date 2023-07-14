import json
import logging
import os

import geoip2.database
import uvicorn
from fastapi import FastAPI, Request, Header
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel
from enum import Enum

logging.basicConfig(
    level=logging.DEBUG,
    # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s-%(funcName)s'
    format='%(levelname)s:     %(name)s - %(message)s-%(funcName)s'
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


@app.get("/{cli}")
async def get_command(cli: str, request: Request):
    match cli:
        case "country":
            ip_address = lookup_ip(request)
            country = get_country(ip_address)
            return country
        case "city":
            ip_address = lookup_ip(request)
            city = get_city(ip_address)
            return city
        case "ip-address":
            return cli
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
            return lookup_ip(request)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=True,
        # workers=8
    )
