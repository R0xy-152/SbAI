# Windows Server 2022 部署方案（备选，主推方案仍是换 Linux，见 DEPLOY.md）

> 实测当前服务器 SSH 横幅：SSH-2.0-OpenSSH_for_Windows_9.5（Windows Server 2022 + OpenSSH Server）。
> 本项目的容器镜像全部是 Linux 镜像（python:3.12-slim / nginx:1.27-alpine /
> postgres:16-alpine），Windows 原生容器跑不了，Windows 路径只有下面两条。
> **2核2GiB 内存下优先建议：阿里云控制台一键更换操作系统为 Ubuntu 22.04（免费），
> 然后用 deploy/up.sh 一键部署。** 保留 Windows 请评估下面的内存取舍。

## 方案 W1：WSL2 + Docker Engine（沿用 docker-compose，内存紧）

Windows 底座约占 1.5GB，2GiB 下 WSL2 里再跑三个容器会明显吃紧（换页卡顿）。
如仍要走这条路：

```powershell
# 1. 启用 WSL 与虚拟机平台（管理员 PowerShell，重启生效）
dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
Restart-Computer

# 2. 重启后安装 WSL2 内核更新（微软 wsl_update_x64.msi）并装 Ubuntu
wsl --update
wsl --install -d Ubuntu --web-download
wsl --set-default-version 2

# 3. WSL 内启用 systemd（Ubuntu 内执行）
#    sudo nano /etc/wsl.conf  写入：
#    [boot]
#    systemd=true
#    wsl --shutdown 后重进，再装 Docker Engine（官方 apt 源，同 Linux 步骤）

# 4. 内存上限（Windows 用户目录新建 .wslconfig）
#    [wsl2]
#    memory=1400MB
#    swap=2048MB
```

```powershell
# 5. 端口暴露：WSL2 默认只把端口转发到 Windows 的 127.0.0.1，公网不可达。
#    两条路任选：
#    a) 新版 WSL 镜像网络（.wslconfig 加 networkingMode=mirrored）→ 端口直接绑到宿主网卡；
#    b) 端口代理 + 防火墙：
$wslIp = (wsl hostname -I).Trim().Split(' ')[0]
netsh interface portproxy add v4tov4 listenport=80 listenaddress=0.0.0.0 connectport=80 connectaddress=$wslIp
netsh advfirewall firewall add rule name="gal-http" dir=in action=allow protocol=TCP localport=80
#    注意：WSL2 重启后 IP 会变，需重设 portproxy（或用镜像网络模式）。
```

部署本身同 Linux：仓库放入 WSL 文件系统（/srv/gal）→ docker compose build/up →
deploy/verify.ps1 验收。

## 方案 W2：原生 Windows（无 Docker、无 WSL 开销）

内存最省（省掉 WSL2 虚拟机与容器层），但组件各自安装、没有 compose 编排：

1. **Python 3.12**（python.org 安装包）→ venv → pip install -r backend/requirements.txt；
2. **PostgreSQL 16**（Windows 安装版）→ 建库 gal，GAL_SAVE_BACKEND=postgres、
   GAL_POSTGRES_DSN=postgresql://gal:密码@127.0.0.1:5432/gal；
3. 后端：uvicorn app.main:app --host 127.0.0.1 --port 8000，用 NSSM 或任务计划注册成服务；
4. 前端：本地 npm run build 出 dist，用 **nginx for Windows**（nginx.org）托管 + /api 反代 127.0.0.1:8000；
5. 会话 JSON 落在 backend/data（无需额外配置）。

> 代价：没有容器化，回滚/更新都要手工；且 Windows 上未验证过全链路
>（本仓库所有验证都在 Linux 容器栈上）。

## 结论

- 主推：**换 Ubuntu 22.04**，跑 deploy/up.sh；
- 保留 Windows：能接受内存风险选 W1（改动最小）；想省内存且接受手工运维选 W2。
