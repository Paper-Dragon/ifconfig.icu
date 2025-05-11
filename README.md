# ifconfig.icu

## description

Source code of [ifconfig.icu](ifconfig.icu) website

The function of the item is to display the information of the visitor.

Even location country or city.

Supported ways:

- website (main)  
**command**
- curl  
- wget
- fetch

### New features

- 2024/04/03 migrate web to Koyeb ,Begin support IPv6
- 2024/04/15 add manual check feature
>
  > ```bash
  >  curl ifconfig.icu/101.231.100.xx
  >  curl ifconfig.icu/2400:8902::f03c:94ff:fe42:xxxx
  >  ```
  >
  > <https://ifconfig.icu/xxx.xxx.xxx.xxx>

- 2024/04/15 Beautify command line result
- 2024/04/16 Code refactoring: use build item function delete pretty head, beautify command line, fixed log print error

## How to run ifconfig.icu server?

```bash
  docker run -it \
	-d \
	--restart always \
	-p 8000:8000 \
	jockerdragon/ifconfig.icu:latest
```

## Config Server

`PROXY_MODE`: Default `None`, if set `PROXY_MODE=True` in env, Get the source IP instead of the last IP forwarded as your IP address. (before the first forward ip).

`AGENT_MODE`: Default `None`, DO NOT SET THIS ENV, For the author's personal use only.

## contribute

Rewrite the [ifconfig.top](https://github.com/ngoduykhanh/ifconfig.top.git) project using Python.

