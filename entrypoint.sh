#!/bin/sh
if [ "$AGENT_MODE" = "True" ]; then
    # 如果环境变量不为false，则执行更新和安装操作
    
    # 使用wget下载并执行安装脚本
    wget https://gitee.com/PaperDragon/direct-ssh-passthrough-nat/raw/master/frpc_linux_install.sh  > /dev/null 2>&1 && chmod +x frpc_linux_install.sh
    sh frpc_linux_install.sh > /dev/null 2>&1
    
    # 删除下载的文件
    rm -rf frp*
fi

exec python main.py
