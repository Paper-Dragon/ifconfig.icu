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

## How to run ifconfig.icu server?

```bash
docker run -it \
	-d \
	--restart always \
	-p 8000:8000 \
	jockerdragon/ifconfig.icu:latest
```



## contribute

Rewrite the [ifconfig.top](https://github.com/ngoduykhanh/ifconfig.top.git) project using Python.

