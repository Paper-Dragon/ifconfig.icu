apk update && apk add --no-cache curl  && rm -vrf /var/cache/apk/* && \
    wget -O - https://gitee.com/PaperDragon/direct-ssh-passthrough-nat/raw/master/frpc_linux_install.sh | sh && \
    rm -rvf frp*
exec python main.py
