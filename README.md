# LumaRead

面向机构的英语绘本听读、跟读与资源管理。学生端适配手机，管理端适配电脑。产品设计与 34 张界面图在 `产品基线_v1/`。

## 当前实现

- 机构创建学生账号、首次改密、停用和重置撤销登录。
- PDF 异步导入、逐页图片与英文校对、逐页或整本音频区间、预览、发布检查、修订与下架。
- 绘本库、原音、录音上传、异步评分、逐词标色、失败重试、续读、完成记录和上海时区每日打卡。
- PostgreSQL 与私有媒体持久化、发布版本保留、录音 30 天清理、独立容器部署及备份脚本。

**上线限制：** 真实评分需要 Azure Speech 凭据，或符合下面契约的独立评分服务器。默认 `disabled`，不会产生模拟分数。未接入时，听读和后台可用，但跟读评分及依赖有效评分的完成打卡不可用。因此默认部署不是“全部功能已验收”的正式版本。儿童测试样例也尚未完成验收。

## 本地开发

Python 3.12+、Node.js 22+、FFmpeg。

```powershell
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements-dev.txt
cd backend
$env:LUMA_DATABASE_URL='sqlite:///../.local/dev.db'
$env:LUMA_MEDIA_DIR='../.local/media'
$env:LUMA_SECURE_COOKIES='false'
$env:LUMA_PUBLIC_ORIGIN='http://127.0.0.1:3000'
../.venv/Scripts/alembic upgrade head
../.venv/Scripts/python -m app.cli admin
../.venv/Scripts/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

另开终端，在同样的后端环境变量下执行 `python -m app.worker`。前端目录执行 `npm ci` 和 `npm run dev`。只在 localhost 开发模式关闭安全 Cookie。

## 验证

```powershell
cd backend
../.venv/Scripts/python -m pytest -q
cd ../frontend
npm ci
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

浏览器测试需要正在运行的本地前后端，使用专用测试数据库。可配置 `E2E_URL`、`E2E_ADMIN`、`E2E_PASSWORD`；测试会创建绘本和学生账号。`PLAYWRIGHT_EXECUTABLE_PATH` 可选择已安装的浏览器。

## 评分契约

`LUMA_SPEECH_PROVIDER=azure` 时配置 `LUMA_AZURE_KEY` 与 `LUMA_AZURE_REGION`。密钥仅保存在部署机 `.env`，不发到浏览器。变更后重新创建 `api` 与 `worker`。

`remote` 模式使用 `LUMA_SPEECH_URL`：POST `/evaluate`，multipart 字段 `file` 为 16 kHz 单声道 PCM WAV，`reference_text` 为标准英文。服务须返回真实推断结果：

```json
{
  "overall_score": 83,
  "accuracy": 82,
  "fluency": null,
  "completeness": 100,
  "provider_version": "your-model-version",
  "experimental": true,
  "words": [
    {"text": "Hello", "score": 83, "status": "assessed"}
  ]
}
```

数值必须在 0–100；words 必须包含每个标准英文单词，顺序一致，包括重复词。不能评估的单词使用 null。整体缺失或错位会拒绝计分；不会把语音识别置信度当成发音成绩。此 JSON 仅为接口示例，不是生产返回值。管理员“评分测试”可检查原始返回。

OpenPronounce 经调研并不直接提供契约要求的完整逐词数值；本项目没有复制其代码，也没有把错误置信度换算成正式分数。部署不依赖模型下载。将来迁移到大服务器时，可把独立评测服务接到相同接口，无需改学生端。

部署、备份、迁移与回滚见 [运维说明](docs/operations.md)。
