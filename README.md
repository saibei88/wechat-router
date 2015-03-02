# wechat-router

现在还只是个框架，没有真实上线使用测试。。。

只是简单的在本地用wecheat 测试了下。。。

主要将用户发送到微信公众号消息的消息进行存储，目前采用mysql来记录数据

如果有web前段作为客服的工作人员在，同时将消息转发到web端进行处理

客服处理发送给用户的消息也会被记录下来

使用方式：
在settings.py 里配置好内容
然后 initdb.py
再运行 main.py

暂时不整理需要啥包了，运行main.py 时提示缺啥包，看看提示缺啥再pip install 吧

使用纯websocket 实现聊天

web服务使用tornado

微信消息解析
https://github.com/messense/wechatpy

web前段借鉴这个工程里的，tornado自带的chat demo ui太渣了。。。
https://github.com/tegioz/chat

shengaofeng@gmail.com
