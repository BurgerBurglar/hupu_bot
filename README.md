# hupu_bot

从虎扑论坛读取贴子，遇到关键词自动回复。
可以设置：

- 读取专区
- 关键词
- 运行间隔

目前功能：

- 无厘头自动回复
- 比较英雄联盟对位胜率和击杀率
  - \[WIP\]调用 op.gg API
- 比较球员赛季数据
  - \[WIP\]调用足球数据 API

TBD:

- 优化速度: 目前使用 multiprocessing, 将切换成 async
- 使用 cron 自动运行
- 自动读取 Chrome Cookie
- logging
- 重构面条代码，重命名变量
