# 部署用 SSH 驱动脚本（通用工具；密码经命令行参数传入，绝不入库）。
# 用法：
#   python deploy/remote.py --host HOST --user root --password PW --cmd "命令"
#   python deploy/remote.py --host HOST --user root --password PW --put 本地文件 远程路径
#   python deploy/remote.py --host HOST --user root --password PW --script 本地.sh [参数...]
import argparse
import sys

import paramiko

# Windows GBK 控制台下按 UTF-8 输出远端内容（build 进度含 ✓ 等字符）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:  # pragma: no cover - Linux 下无 reconfigure
    pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--user", default="root")
    parser.add_argument("--password", required=True)
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--cmd", default=None, help="在远端执行一条命令并打印输出")
    parser.add_argument("--put", nargs=2, metavar=("LOCAL", "REMOTE"), default=None)
    parser.add_argument("--script", nargs=argparse.REMAINDER, default=None)
    args = parser.parse_args()

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        args.host, port=args.port, username=args.user, password=args.password,
        timeout=20, look_for_keys=False, allow_agent=False,
    )

    try:
        if args.cmd is not None:
            _run(client, args.cmd)
        if args.put is not None:
            local, remote = args.put
            sftp = client.open_sftp()
            sftp.put(local, remote)
            sftp.close()
            print(f"[put] {local} -> {remote}")
        if args.script is not None:
            parts = [p for p in args.script if p != "--script"]
            if parts:
                local = parts[0]
                extra = parts[1:]
                remote = f"/tmp/{local.rsplit('/', 1)[-1]}"
                sftp = client.open_sftp()
                sftp.put(local, remote)
                sftp.close()
                _run(client, f"bash {remote} {' '.join(extra)}")
    finally:
        client.close()
    return 0


def _run(client: paramiko.SSHClient, command: str) -> None:
    stdin, stdout, stderr = client.exec_command(command, timeout=600)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    exit_code = stdout.channel.recv_exit_status()
    sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    print(f"[exit {exit_code}]")


if __name__ == "__main__":
    sys.exit(main())
