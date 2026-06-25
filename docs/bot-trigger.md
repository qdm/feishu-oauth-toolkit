# 飞书机器人 OAuth 触发 (Bot-trigger)

把 `feishu-oauth-toolkit` 升级成一个**真正能聊的机器人**:用户私聊机器人发
`/auth`(或包含 "授权" / "auth"),机器人**回一张飞书卡片**,卡片里带 OAuth
授权链接,用户在浏览器里点同意 → 跳回 cloudflared tunnel → 你的 `oauth-server`
收 code → 自动换 token → 后续机器人就有 `user_access_token` 可以用了。

**走的是飞书官方 `lark-oapi` SDK 的 `FeishuChannel`** —— WebSocket 长连接,
不占公网端口,不需要 webhook 接收地址。

---

## 1. 后台配置 (3 步)

### 1.1 切换到「长连接接收事件」模式

- 飞书开发者后台 → 你的应用 → **事件与回调**
- **连接方式** → 选 **「使用长连接接收事件」** (不是 webhook)
- 保存

### 1.2 订阅 `im.message.receive_v1`

- 同一页面 → **事件订阅** → 搜索 `im.message.receive_v1`(接收消息 v2.0)
  - 飞书 SDK 的 `FeishuChannel` 默认订阅的就是 `im.message.receive_v1`
  - 还需要在「权限管理」里把 `im:message` 的"用户身份可用"勾上
- 保存

### 1.3 申请 3 个新 scope

机器人要发卡片、回消息,需要(在 **权限管理** 里申请,**用户身份可用**勾上):

| Scope                            | 用途                                  |
|----------------------------------|---------------------------------------|
| `im:message`                     | 以应用身份发消息                      |
| `im:message:send_as_bot`         | 以机器人身份发消息(卡片需要)        |
| `im:message.receive_v1`          | 接收用户发给机器人的消息              |
| `im:message.group_at_msg` (可选) | 群聊里 @ 机器人的消息(如要支持群聊) |

> ⚠️ 申请后必须**发一版**,权限才会生效。

---

## 2. 填 .env

```bash
cp .env.example .env
$EDITOR .env
```

需要的环境变量(仓库**不**提供 FEISHU_REDIRECT_URI 默认值,必须显式填):

```ini
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=your-app-secret
FEISHU_REDIRECT_URI=https://land-rush-readings-plaza.trycloudflare.com/callback
```

`FEISHU_REDIRECT_URI` 必须**已经在飞书后台**的「重定向 URL」里(参见
[feishu-backend-setup.md § 4](feishu-backend-setup.md#4-configure-the-redirect-url))。

---

## 3. 装依赖 + 启动

```bash
# 装 SDK
pip install lark-oapi

# (可选) 装成可编辑模式 — 拿到 feishu-bot console script
pip install -e .

# 直接启动(WS 长连接,会一直跑到你 Ctrl-C)
python -m feishu_oauth.bot
# 或
feishu-bot
```

成功启动你会看到:

```
[bot] feishu-oauth-toolkit-bot v0.1.0 starting
[bot] pid=12345 cwd=/home/...
[bot] connecting WS...
```

**此时不要关这个进程**。切到飞书,私聊机器人,发 `/auth`:

```
[bot] recv msg from=ou_xxx chat=oc_xxx text='/auth'
[bot] send OK ...
```

你的飞书客户端会收到一张卡片,点 "👉 同意并授权" → 浏览器走 OAuth → 跳回
cloudflared tunnel → `oauth-server` 收 code → token 落到
`feishu-user-tokens.json`。

下次再发 `/auth`,机器人会回 **auth_done_card**(绿色),显示 token 还剩多少。

---

## 4. 触发的关键词

`src/feishu_oauth/trigger.py` 里定义:

| 用户消息(任一命中)              | 机器人回复                       |
|----------------------------------|----------------------------------|
| `/auth`                          | 没 token: 授权卡片;有: 状态卡片 |
| 包含"授权"                        | 同上                             |
| 包含 "auth"(不区分大小写)        | 同上                             |
| 其它                              | 沉默,不打扰                     |

**沉默不打扰**是默认行为 —— 机器人不会乱回。

---

## 5. 真要跑起来需要的服务

```
                ┌──────────────────┐
   user ──→ 飞书客户端 ──→ 飞书服务器 ──WS──→ feishu-oauth-toolkit bot
                                              │
                                              ▼
                                  trigger.decide_response()
                                              │
                                              ▼
                                  channel.send(卡片) ──→ 飞书服务器 ──→ 用户
                                              │
                                              ▼  (用户点按钮)
                                  cloudflared tunnel ──→ oauth-server ──→ token 落盘
```

**bot.py 一个进程负责**:
- 维持 WebSocket 长连接
- 收消息 → 触发判断 → 发卡片
- **不**负责收 code(code 仍走你之前跑通的 oauth-server.py + cloudflared tunnel)

---

## 6. 故障排查

| 现象 | 原因 | 修法 |
|------|------|------|
| `ModuleNotFoundError: lark_oapi` | 没装 SDK | `pip install lark-oapi` |
| `❌ 缺少环境变量 FEISHU_REDIRECT_URI` | .env 没填 | 补上 |
| 启动后收不到消息 | 后台没开「长连接接收事件」 | 回到 [§ 1.1](#11-切换到长连接接收事件模式) |
| 启动后收不到消息 | 后台没订阅 `im.message.receive_v1` | 回到 [§ 1.2](#12-订阅-immessagereceive_v1) |
| 启动后收不到消息 | 没发版 | 应用发布 → 创建版本 → 等审核通过 |
| 卡片发出去了但用户看不到 | 卡片 JSON 不合规 | 跑 `python -c "import json; json.load(open('card.json'))"` 验证 |
| 卡片发出去了但用户看不到 | 机器人没被加到用户的"可用范围" | 应用发布 → 可用范围 → 把用户加进去 |

---

## 7. 给开发者:扩展 trigger

`trigger.decide_response()` 是**纯函数**,可以非常容易扩展:

```python
# 加一个 /sync 命令:有 token 时返回"正在同步...",没 token 时返回授权卡片
def decide_response(user_message, has_valid_token, redirect_uri, app_id, state="..."):
    msg = user_message.strip().lower()
    if msg == "/sync":
        # ... 你的业务逻辑
        return some_card
    # 否则走原来的逻辑
    ...
```

`card.py` 也只导出**纯数据**(dict),可以加新卡片模板(比如"权限不足"卡片、
"刷新成功"卡片)而不影响 bot.py 逻辑。

---

## 8. 完整命令清单

| 场景 | 命令 |
|------|------|
| 装 SDK | `pip install lark-oapi` |
| 装工具(3 console scripts) | `pip install -e .` |
| 跑机器人 | `python -m feishu_oauth.bot` |
| 测试 trigger 纯函数(不需要 SDK) | `pytest tests/test_trigger.py` (待补) |
| 跑 OAuth 回调 server(老) | `python -m feishu_oauth.server` (或 systemd) |
| 跑 OAuth 完整验证(老) | `feishu-verify` (或 systemd) |
