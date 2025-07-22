# AUTOTG

Telegram 账户数据管理和采集工具

## 功能

- Telegram 账户登录
- 账户数据管理
- 数据采集
- 配置文件支持
- 实时消息监听和存储
- 美观的控制台输出

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置

在运行程序前，需要先配置`config.json`文件：

```json
{
    "api_id": 你的API_ID,
    "api_hash": "你的API_HASH",
    "session_name": "autotg_session",
    "proxy": {
        "enabled": false,
        "type": "socks5",
        "addr": "127.0.0.1",
        "port": 1080,
        "username": "",
        "password": ""
    },
    "log_level": "INFO"
}
```

配置说明：

- `api_id` 和 `api_hash`：Telegram API 凭据，从https://my.telegram.org/apps获取
- `session_name`：会话名称，保存登录状态的文件名
- `proxy`：代理设置，如需使用代理，将`enabled`设为`true`
- `log_level`：日志级别，可选值：`DEBUG`、`INFO`、`WARNING`、`ERROR`、`CRITICAL`

## 使用方法

运行主程序:

```bash
python main.py
```

程序默认会开启消息监听和存储功能。运行后，所有接收到的消息都会以美观的格式显示在控制台中，并自动保存到 SQLite 数据库中。

### 命令行参数

- `-c, --config`：指定配置文件路径，默认为`config.json`
- `-d, --db`：指定数据库文件路径，默认为`data.db`
- `--no-listen`：禁用消息监听功能

例如：

```bash
# 使用自定义配置文件
python main.py -c my_config.json

# 使用自定义数据库文件
python main.py -d my_data.db

# 仅登录，不监听消息
python main.py --no-listen
```

## 数据存储

消息数据将存储在 SQLite 数据库中，包含以下详细信息：

- 消息 ID、聊天 ID
- 聊天标题和类型
- 发送者信息（ID、用户名、姓名）
- 消息文本内容
- 发送时间
- 媒体类型
- 转发信息
- 回复信息
- 原始数据
