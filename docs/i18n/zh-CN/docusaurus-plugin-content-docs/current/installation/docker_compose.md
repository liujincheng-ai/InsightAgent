# Docker Compose 部署

## 使用 Docker Compose 运行

此示例要求你提供可用的 SiliconFlow API Key。你可以在 [SiliconFlow](https://siliconflow.cn/) 注册，并在 [API Key 页面](https://cloud.siliconflow.cn/account/ak) 创建。
你也可以通过设置 `AIMLAPI_API_KEY` 使用 [AI/ML API](https://aimlapi.com/)。


```bash
SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY} docker compose up -d
```
或者使用 AI/ML API：
```bash
AIMLAPI_API_KEY=${AIMLAPI_API_KEY} docker compose up -d
```

如果部署成功，你会看到类似下面的输出：
```bash
[+] Running 3/3
 ✔ Network dbgptnet              Created                                            0.0s 
 ✔ Container db-gpt-db-1         Started                                            0.2s 
 ✔ Container db-gpt-webserver-1  Started                                            0.2s 
```


## 查看日志
```bash
docker logs db-gpt-webserver-1 -f
```

:::info note

更多配置内容可以直接查看 `docker-compose.yml` 文件。
:::


## 访问
打开浏览器访问 [http://localhost:5670](http://localhost:5670)
