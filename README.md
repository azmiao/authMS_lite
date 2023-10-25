# authMS_lite

[授权管理](https://github.com/pcrbot/authMS)的自用精简版

注意：因为是纯自用，有什么其他需求请自己改代码

 - 适配：go-cqhttp 1.0.0+
 - 精简：去除web页面
 - 精简：去除卡密相关
 - 精简：去除加好友
 - 精简：去除入群发言
 - 其他：配置文件修改，存储路径调整

## 支持的软件版本

 - hoshino >= 2.0
 - go-cqhttp >= 1.0.0
 
## 简单的逻辑

【插件命令】 --(授权并写入)--> 【插件数据库】 --(写入授权的群)--> 【事件过滤器配置`filter.json`】 --(重载配置)--> go-cqhttp的过滤器

注：每天09:01会自动检查授权

## 指令
**注意, 以下指令中的空格均不可省略**
### 仅限超级管理员私聊的指令

* 【授权列表】查看所有授权群的信息包括到期事件,后跟数字来查看对应页数
* 【快速检查】立刻检查群的授权, 并判断是否有群授权临期或者到期，然后发送通知到对应群
* 【刷新事件过滤器】读取已授权的群列表，并根据群列表刷新事件过滤器配置`filter.json`，再根据该配置刷新go-cqhttp的过滤器
* 【重载事件过滤器】根据事件过滤器配置`filter.json`，去刷新go-cqhttp的过滤器

### 仅限超级管理员的指令(大部分需要@bot，具体自测)

* 【变更授权 123456789+5】为群123456789增加5天授权, 也可以是减，然后会有变更授权的通知发送到对应群
* 【转移授权 123456*987654】将群123456的剩余时间转移至群987654
* 【授权状态】查询已授权的群数量
* 【清除授权 987654】清除群987654的全部授权, 并自动退群(如果配置了AUTO_LEAVE = False的话，就不会退群)
* 【退群 987654】命令退出群聊987654, 但并不清除剩余授权时间
* 【全部白名单】查询全部白名单信息列表

> 注意：下方几个命令不会影响授权状态，即原来没有使用过【变更授权】命令的群，使用下方命令后该群仍然是没有授权的，即使白名单了也和未授权状况一样不回消息，需要手动使用【变更授权】命令添加天数后，再为其设置白名单或不检查之类的
* 【变更所有授权 3】为所有已有授权的群增加3天授权时间，注意：该命令不会影响没有使用过命令【变更授权】的群
* 【不检查人数 987654】不检查群987654的人数是否超标, 直接在群聊中发送则不必附加群号
* 【不检查授权 987654】不检查群987654的授权是否过期, 直接在群聊中发送则不必附加群号
* 【添加白名单 987654】不检查群987654的授权是否过期以及人数是否超标, 直接在群聊中发送则不必附加群号
* 【移除白名单 987654】将群987654从白名单中移出

### 所有人均可用的命令

* 【查询授权】查询本群的授权信息

## 开始使用

1. 在hoshino的modules目录下克隆本项目:
   ```
   git clone https://github.com/azmiao/authMS_lite.git
   ```
2. 安装依赖, 如下载过慢建议清华镜像: 
   ```
   pip install -r requirements.txt
   ```
3. 打开`hoshino/service.py`进行修改，不修改的话未授权的群也会广播消息：
    最顶上加上这行
    ```
    from sqlitedict import SqliteDict
    ```
    然后修改`broadcast()`函数：
    ```
    async def broadcast(self, msgs, TAG='', interval_time=0.5, randomizer=None):
        bot = self.bot
        if isinstance(msgs, (str, MessageSegment, Message)):
            msgs = (msgs, )
        groups = await self.get_enable_groups()
        group_dict = SqliteDict(os.path.join(os.path.dirname(__file__), 'modules/authMS_lite/config/group.sqlite'), flag='r') # 加这行
        for gid, selfids in groups.items():
            if gid not in group_dict: # 加这行
                self.logger.error(f"群{gid} 投递{TAG}失败：该群授权已过期") # 加这行
                continue # 加这行
            try:
                for msg in msgs:
                    await asyncio.sleep(interval_time)
                    msg = randomizer(msg) if randomizer else msg
                    await bot.send_group_msg(self_id=random.choice(selfids), group_id=gid, message=msg)
                l = len(msgs)
                if l:
                    self.logger.info(f"群{gid} 投递{TAG}成功 共{l}条消息")
            except Exception as e:
                self.logger.error(f"群{gid} 投递{TAG}失败：{type(e)}")
                self.logger.exception(e)
    ```

4. 打开配置样例`config/authMS_lite.py.example`, 按照注释修改为您需要的配置，然后将其改名为`authMS_lite.py`并复制到HoshinoBot统一配置目录下`hoshino/config/authMS_lite.py`，
然后在`hoshino/config/__bot__.py`中的`MODULES_ON`里添加本模块`authMS_lite`
   > ！！！重点注意：如果您是初次启动authMS, 请跳到第4步，如果不是，请重启bot并跳到第5步

5. 若为初次使用，请将`authMS_lite.py`中的`ENABLE_AUTH`先暂时保持为`False`，然后重启bot，到群中手动使用命令【变更授权 123456789+5】给每个需要授权的群都增加授权时间, 完成后再修改配置的`ENABLE_AUTH`为`True`，然后重启bot

6. 打开go-cqhttp的根目录，找到`config.yml`，设置里面的中间件锚点里的事件过滤器的路径，文件路径对应到本项目的`/config/filter.json`文件即可
   > 例如：`filter: 'C:/HoshinoBot/hoshino/modules/authMS_lite/config/filter.json'`，注意：路径分割符请务必写单正斜杠，不然授权重载无效，填写完成后然后重启go-cqhttp
   > 参考配置，就改`filter`字段即可，注意要写绝对路径
   ```yml
      # 默认中间件锚点
      default-middlewares: &default
     # 访问密钥, 强烈推荐在公网的服务器设置
     access-token: ''
     # 事件过滤器文件目录
     filter: 'C:/HoshinoBot/hoshino/modules/authMS_lite/config/filter.json'
     # API限速设置
     # 该设置为全局生效
     # 原 cqhttp 虽然启用了 rate_limit 后缀, 但是基本没插件适配
     # 目前该限速设置为令牌桶算法, 请参考:
     # https://baike.baidu.com/item/%E4%BB%A4%E7%89%8C%E6%A1%B6%E7%AE%97%E6%B3%95/6597000?fr=aladdin
     rate-limit:
       enabled: false # 是否启用限速
       frequency: 1  # 令牌回复频率, 单位秒
       bucket: 1     # 令牌桶大小
   ```

7. 开始快乐的玩耍吧

## 贡献

[GitHub@wdvxdr1123](https://github.com/wdvxdr1123)

[GitHub@xhl6699](https://github.com/xhl6666)

[GitHub@var](https://github.com/var-mixer)

[GitHub@AZMIAO](https://github.com/azmiao)