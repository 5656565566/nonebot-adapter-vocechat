<p align="center">
  <a href="https://nonebot.dev/"><img src="https://nonebot.dev/logo.png" width="200" height="200" alt="nonebot"></a>
</p>

<div align="center">

# nonebot-adapter-vocechat

_✨ vocechat webhook 协议适配 ✨_

</div>

> [!NOTE]
> 由于时间问题，目前代码尚未完善
> 
> 目前正在进行代码规范处理


## 配置

修改 NoneBot 配置文件 `.env` 或者 `.env.*`。

### Driver

参考 [driver](https://nonebot.dev/docs/appendices/config#driver) 配置项，添加 `HTTPClient` 和 `ASGIServer` 支持。

如：

```dotenv
DRIVER=~httpx+~fastapi
```

### 配置机器人

配置连接配置，如：

```dotenv
vocechat_bots=[
  {"name": "xxx","user_id": "2", "server": "http://vocechat.url", "api_key": ""}
]
```

`name` 是任意的 bot 名称会决定 webhook 地址 如 http://{nonebot_host}:{nonebot_post}/vocechat/webhook?bot={name}

`server` 为 vocechat 服务器的地址。

`api_key` 为 vocechat 为bot生成的 `api_key`。

`user_id` 为 vocechat 生成的 bot 的 `user_id`。

## 相关项目

- [vocechat-web](https://github.com/Privoce/vocechat-web)
