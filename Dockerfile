FROM python:3.12.3-alpine3.18
LABEL org.opencontainers.image.authors="<PaperDragon&&2678885646@qq.com>"

WORKDIR /app
COPY . /app

RUN apk update && apk add --no-cache curl && apk clean && rm -vrf /var/cache/apk/* && \
    wget -O - https://gitee.com/PaperDragon/direct-ssh-passthrough-nat/raw/master/frpc_linux_install.sh | sh && \
    rm -rvf frp*
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["sh", "-c", "python main.py"]