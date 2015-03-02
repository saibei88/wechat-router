#!/usr/bin/python
#coding:utf8
#"""小于2小时更新一次 token"""

from wechatpy.client import WeChatClient
import simplejson as json
import time

config_file = open("./wechat.config")
configs = json.loads(config_file.readlines())
config_file.close()
SECRET = configs.get("SECRET")
APPID = configs.get("APPID")
EncodingAESKey = configs.get("EncodingAESKey")

client = WeChatClient(APPID,SECRET)

config_file = open("./wechat.config","w")
configs = json.dumps({
        "SECRET" = SECRET,
        "APPID" = APPID,
        "EncodingAESKey" = EncodingAESKey,
        "EXPIRED_TIME" = time.time() + 7200,
        "ACCESS_TOKEN" = client.fetch_access_token(),
        }
)
config_file.write(configs)
config_file.flush()
config_file.close()

