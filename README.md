# tos-app-ttyd(应用 ID:ttyd-web)

将 [ttyd](https://github.com/tsl0922/ttyd)(网页终端,MIT)打包为 [铁威马 TOS](https://www.terra-master.com) 应用中心 **deb 类应用**(x86_64 + aarch64 双架构)。

**这是什么**:TOS deb 元数据壳 + 可复现构建脚本。上游 musl 静态单二进制(1.3MB,Release 资产即二进制,UPSTREAM 锁定 SHA256)原样打包,本仓只产出 TOS 平台元数据、systemd 单元与凭据种子 —— 不修改任何上游代码。

| 项目 | 值 |
|---|---|
| 应用 ID | `ttyd` |
| 应用形态 | deb 类 · 悬浮窗(`type=iframe`, `exec=false`)· 端口代理模式 |
| 悬浮路由 | `http://<NAS>/ttyd/`(TOS nginx → 127.0.0.1:18231,前缀剥离 + **WebSocket 升级头**) |
| 终端命令 | `/bin/bash --login`(专用系统用户 `ttyd`,家目录 `/var/lib/ttyd`) |
| 凭据 | 首装生成 `admin:<随机密码>` → `/etc/ttyd/ttyd.env`(基本认证,升级保留) |
| 版本 | 1.7.7(见 [UPSTREAM](UPSTREAM) 锁定) |
| 上游许可证 | MIT(全文见 [LICENSE](LICENSE),义务见 [NOTICE](NOTICE)) |

## iframe 内嵌可行性(本仓调研结论)

ttyd 1.7.7 的嵌入页把 **JS/CSS 全部 inline 进 index.html**(webpack inline),无外部资源请求;
WebSocket 与 token URL 从 `window.location.pathname` 相对构造
(`html/src/components/app.tsx`):

```js
const path = window.location.pathname.replace(/[/]+$/, '');
const wsUrl    = [protocol, '//', host, path, '/ws',    search].join('');
const tokenUrl = [protocol, '//', host, path, '/token'].join('');
```

因此 `location /ttyd/ { proxy_pass http://127.0.0.1:18231/; }`(尾斜杠剥前缀)+
`Upgrade/Connection` 升级头即可完整内嵌 —— 见 [nginx/ttyd.conf](nginx/ttyd.conf)。

## 目录结构

```
tos-app-ttyd/
├── config.ini                       # TOS 平台元数据(iframe + exec:false)
├── ttyd.lang                        # 26 种语言(生成:scripts/make_lang.py)
├── packaging-extras/ttyd.env.default# 环境种子(首装生成凭据到 /etc/ttyd/ttyd.env)
├── UPSTREAM                         # 版本锁定(Release 二进制 + SHA256)
├── DEBIAN/                          # control + postinst(生成凭据)/prerm/postrm
├── init.d/ttyd.service              # systemd(--writable --credential,pty 需 PrivateDevices=false)
├── nginx/ttyd.conf                  # ⭐ /ttyd/ → 127.0.0.1:18231/(ws 升级头)
├── images/icons/ttyd.svg            # 原创图标(终端窗口 >_)
├── scripts/                         # fetch/build_deb/unpack_check/validate/make_lang/bump
├── build.sh                         # 一键构建 ./build.sh [x86_64|aarch64]
├── LICENSE                          # 上游 MIT 全文
└── NOTICE                           # 归属与许可义务说明
```

## 本地构建

依赖:bash、curl、python3(任意平台;有 dpkg-deb 时自动优先)。

```bash
./build.sh                # 双架构(下载上游二进制 → 校验 → 打包 → 解包验证)
./scripts/validate.py     # 元数据校验
```

产物:`build/output/ttyd_<platform>.deb` + `.sha256`(约 1.5MB,全场最小)。
`build.sh` 自动执行 `scripts/unpack_check.py`:ar 成员、control 根布局、字段、
ELF 机器类型与可执行位全过才算完成。

## 安全设计

- 基本认证默认开启:`-c admin:<随机密码>`(postinst 生成,写入 `/etc/ttyd/ttyd.env`,
  `chmod 640`;修改后 `systemctl restart ttyd`);
- `--writable` 显式开启(ttyd 默认只读);服务以专用 `ttyd` 系统用户运行,
  `ProtectSystem=strict`,家目录 `/var/lib/ttyd` 白名单;
- 终端不提权:如需 root 操作请自行在终端内配置 sudo 场景,包内不做免密。

## 上架 Checklist(内部奖励计划 · deb 档 60 元)

1. ☐ 推送本仓 GitHub(ericbyz/tos-app-ttyd)+ 打 tag `v1.7.7`;
2. ☐ 提交前**刷新查重**(`ttyd`,2026-11-15 核验空白);
3. ☐ x86_64 与 ARM **分别创建应用**(独立 App ID、同一开发者账号);
4. ☐ 提交 Release 直链 + SHA256 + 上游源码仓 + 本仓构建脚本;
5. ☐ VM 实测:raw dpkg 安装 + 手动接线(runbook AdWall 流程),悬浮窗打开终端、
   输入凭据、执行 `ls -la /` 截图;确认 WebSocket 正常(能敲命令即正常);
6. ☐ 《参与报名表》勾选 deb 档,附仓库链接;
7. ☐ 30 天内维护 Issues 响应。

## 合规声明

- 上游二进制**原样封装**(MIT),未修改任何上游代码,许可证全文随包分发;
- 安装包内容:上游 Release 二进制 + 本仓元数据,无其他二进制;
- 不收集任何用户数据;终端会话不落盘记录。

## ⚠️ 重要教训:应用 ID 不能叫 `ttyd`(v1.7.7 初版返工记录)

TOS 7 的**内置 Web 终端本身就是 ttyd**(官方 deb 包:二进制 `/usr/bin/ttyd`,
服务 `/usr/lib/systemd/system/ttyd.service`,配置 `/etc/default/ttyd`,
`ttyd -b /v2/ttyd -P 1 -i lo -p 7681 bash --login`,由 TOS 主服务反代 `/v2/ttyd`)。
初版应用 ID 取 `ttyd` 导致应用中心安装时把我们的单元覆盖到
`/lib/systemd/system/ttyd.service` + `/etc/ttyd/` 配置冲突 → **TOS 内置终端白屏**。

已返工:应用 ID 改为 **`ttyd-web`**(服务/路径全部错开),内置终端已从
官方 `.ins` rootfs 提取原版 `ttyd.service` + `/etc/default/ttyd` + `/usr/bin/ttyd` 恢复。
**给后续封装者的规则:选应用 ID 前先 `ssh grep /lib/systemd/system` 与 TOS 官方
deb 清单查重,避开系统自带服务名。**
