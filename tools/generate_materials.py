"""Start the real application, validate UI, capture evidence, and generate its PDF."""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from capture import capture
from build_manual import build


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8876)
    args=parser.parse_args()
    out=ROOT/'deliverables';out.mkdir(exist_ok=True)
    # Refuse to touch an existing service. This script owns only its new process.
    url=f'http://127.0.0.1:{args.port}'
    try:
        urllib.request.urlopen(url+'/api/overview',timeout=1)
    except Exception:
        pass
    else:
        raise RuntimeError(f'端口 {args.port} 已存在服务，请用 --port 指定另一个端口')
    log=(out/'capture-server.log').open('w')
    proc=subprocess.Popen([sys.executable,str(ROOT/'server.py'),'--port',str(args.port)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    try:
        for _ in range(180):
            if proc.poll() is not None:
                raise RuntimeError('服务启动失败，详情见 deliverables/capture-server.log')
            try:
                with urllib.request.urlopen(url+'/api/overview',timeout=1) as r:
                    data=json.load(r)
                if sum(s['rows'] for s in data['sources'])!=27385:
                    raise RuntimeError('源数据数量已变化，请先更新采集断言并核对材料')
                break
            except OSError:
                time.sleep(1)
        else:
            raise RuntimeError('服务启动超时')
        capture(url)
        build()
        print('已完成：deliverables/化合物数据与可解释筛选系统V1.0_软件操作说明书.pdf')
    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
        log.close()

if __name__=='__main__':main()
