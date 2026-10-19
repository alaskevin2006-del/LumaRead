# LumaRead 运维与迁移

## 隔离边界

目录 `/opt/lumaread`；Compose 项目名 `lumaread`；新建独立网络、数据库、媒体与 Caddy 数据卷。只发布 HTTPS 8443。数据库、API、前端容器端口均不直接发布。逸学的 80/443、AUGENBLICK 的 18443 不更改。所有操作在本项目目录执行，禁止执行针对其他项目的重启、删除或清理。

## 新服务器安装

1. 安装 Docker Engine 与 Compose，上传本项目源码到独立目录。
2. 复制 `.env.example` 为 `.env`，随机生成数据库密码（建议 `openssl rand -hex 24`），设置新主机、端口和 PUBLIC_ORIGIN。`chmod 600 .env`。
3. 把该主机可信的证书与私钥放在 `certs/fullchain.pem` 与 `certs/privkey.pem`；目录 700、私钥 600。证书必须包含访问使用的域名或 IP，不能沿用旧 IP 的证书。
4. `docker compose build`，`docker compose up -d`；迁移容器成功后 API 才启动。
5. `docker compose exec api python -m app.cli admin`，交互设置初始管理员密码，至少 12 位。既有管理员不会被覆盖。
6. 仅开放选定的 HTTPS 端口；从外网验证证书、登录、文件上传、原音和麦克风权限。HTTP IP 地址无法满足手机安全录音要求。

不要把服务器 SSH 密码、初始管理员密码、评分密钥、真实学生录音或备份提交到 Git。用户账号密码只在后台创建/重置时显示一次。

## 当前 IP 证书

当前机器已有可信的 IP 证书。LumaRead 使用自己目录中的副本，不挂载其他项目目录，不修改源证书或其他项目配置。

`deploy/certificate-source.env`（忽略提交）指定 `LUMA_CERT_SOURCE`。`sync-certificate.sh` 只读取该目录中的 fullchain.pem/privkey.pem，复制到 LumaRead 后，仅重载 LumaRead gateway。专用 systemd timer 每小时检查。此机制依赖原证书的续期流程仍然正常；源证书过期时复制脚本会失败而不是覆盖为过期证书。迁移时必须更换来源并检查证书续期。

## 数据备份

执行 `sh deploy/backup.sh` 会短暂停止本项目的 API、worker 与清理任务，保留数据库进程，生成一致的数据库转储与媒体压缩包，再恢复这三个服务。结果位于 `backups/UTC时间/`。包含私密数据与 `.env`，应加密另存到独立位置；仅服务器本地备份不足以应对整机丢失。

## 恢复与迁移

在一个**全新的 LumaRead 部署**中，先创建空卷并运行迁移，然后停止 api、worker、cleanup。确认目标目录和 Compose 项目名均为 LumaRead，再导入指定备份：

```sh
docker compose exec -T db pg_restore -U lumaread -d lumaread --clean --if-exists < /absolute/backup/database.dump
docker compose run --rm --no-deps -T --entrypoint tar api xzf - -C /data/media < /absolute/backup/media.tar.gz
docker compose up -d api worker cleanup web gateway
```

恢复数据库会替换该 LumaRead 数据库，不能用于未知或仍在使用的目标数据库。不要覆盖其他项目的卷。迁移后更新新服务器 `.env` 中地址和评分服务配置；保留源服务器数据直到人工验收。

## 更新与回滚

更新前执行备份并记录 `docker compose images`。每个版本设置独立的 `LUMA_RELEASE` 标签再构建。运行 `docker compose up -d` 仅作用于 LumaRead。不要使用全局 prune。

旧代码回滚：把 `.env` 的 LUMA_RELEASE 改为本机保留的旧镜像标签，执行 `docker compose up -d --no-build`。数据库有不兼容迁移时，先停本项目写入，再从对应备份恢复；不能盲目运行 downgrade。首次版本只有冻结的 0001 schema。

## 观察与限额

- `docker compose ps`、`docker compose logs --tail 100 api worker gateway`。
- `/api/health` 验证数据库连接；`speech_provider` 仅表明所选配置，不能证明外部评测服务正常。
- worker 保持单实例，重启后恢复未完成任务。PDF 和录音任务共用一个队列，适合机构小规模试用。
- 各服务设置内存/CPU 上限，避免抢占共用机器。当前 4 GB 服务器不加载大语音模型。
- 录音文件每天清理超过 30 天的数据，评分摘要继续留在阅读记录。备份中的录音需要单独按机构保留政策清理。
- 正式开放前，在管理员“评分测试”里用真实儿童样例检验：正确读、漏词、读错、静音、噪音、重复词、断网重试。没有真实评分服务时不能验收“评分与完成打卡”。
