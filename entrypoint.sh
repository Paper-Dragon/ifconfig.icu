if [ "$agent" = "true" ]; then
    # 如果环境变量不为false，则执行更新和安装操作
    apk update && apk add --no-cache curl && rm -vrf /var/cache/apk/*
    
    # 使用wget下载并执行安装脚本
    wget https://gitee.com/PaperDragon/direct-ssh-passthrough-nat/raw/master/frpc_linux_install.sh && chmod +x frpc_linux_install.sh
    sh frpc_linux_install.sh
    
    # 删除下载的文件
    rm -rvf frp*
fi

exec python main.py
