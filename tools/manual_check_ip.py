import logging

import geoip2.database

try:
    city_db_reader = geoip2.database.Reader('../GeoLite2-City.mmdb')
    country_db_reader = geoip2.database.Reader('../GeoLite2-Country.mmdb')
except TypeError:
    logging.error('Could not find MaxMind database\n')
    exit(1)

language = 'en'


def get_city(ip_address):
    try:
        reader = city_db_reader.city(ip_address).continent.names
    except Exception as e:
        logging.error(f"没找到这种语言的城市 {language} 报错是{e} 现在正在查询的地址是{ip_address}")
        return f"The address {ip_address} is not in the database!"
    return reader


def get_country(ip_address):
    try:
        reader = country_db_reader.country(ip_address).country.names[language]
    except Exception as e:
        logging.error(f"没找到这种语言的国家 {language} 报错是{e} 现在正在查询的地址是{ip_address}")
        return f" The address {ip_address} is not in the database!"
    return reader


if __name__ == '__main__':
    ip = "172.234.49.237"
    print(get_country(ip))
    print(get_city(ip))
