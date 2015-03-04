#!/usr/bin/python
#coding:utf-8
import logging
import os.path

import tornado.httpserver
import tornado.web
import tornado.ioloop
import tornado.options
import tornado.httpclient
import tornado.websocket
import tornado.auth
import tornado.websocket

from tornado import gen
from tornado.options import define, options

import simplejson as json
import time
import datetime
import torndb

from auth import AuthLoginHandler,AuthLogoutHandler,BaseHandler 
from wechathandlers import GetDataFromWechat,SendDataToWechat
from settings import DATABASE
import signal

define("mysql_host", default = DATABASE.get("host","localhost") + ":" + str(DATABASE.get("port","3306")), help="blog database host")
define("mysql_database", default= DATABASE.get("database","test") , help="blog database name")
define("mysql_user", default = DATABASE.get("username","test"), help="blog database user")
define("mysql_password", default = DATABASE.get("password","test"), help="blog database password")

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/chatsocket", ChatSocketHandler), 
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
            xsrf_cookies=True,
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            debug=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

        # Have one global connection to the blog DB across all handlers
        self.db = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)

class WechatDataReciever(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r"/wechat",GetDataFromWechat), 
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
#            xsrf_cookies=True, #必须禁用 xsrf 才能正常接受微信过来的消息
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            debug=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

        # Have one global connection to the blog DB across all handlers
        self.db = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)

class IndexHandler(BaseHandler):

    @tornado.web.authenticated
    def get(self):
        print self.get_current_user()
        self.render("index.html")

class ChatSocketHandler(tornado.websocket.WebSocketHandler):

    waiters = set()
    cache =  []

    def get_current_user(self):
        user_json = self.get_secure_cookie("chatdemo_user")
        if not user_json: return None
        return tornado.escape.json_decode(user_json)

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

#    @tornado.web.authenticated
    def open(self):
        if not self.get_current_user():
            return
        self.waiters.add(self)

    def on_close(self):
        pass

    def on_message(self, message):
#        print "got message %r" % message
        self.event_handler(message)

    @classmethod
    def update_cache(cls):
        cls.cache = GetDataFromWechat.cache
        GetDataFromWechat.cache = []
        for msg in cls.cache:
            for waiter in cls.waiters:
                echo_back = {
                    "event":"newMessage",
                    "room":msg.source,
                    "msg":msg.content,
                    "username":msg.source,
                    "type":msg.type,
                    "timestamp":int(time.time()),
                    }

            waiter.write_message(json.dumps(echo_back))

    def event_handler(self,message):
        msg = json.loads(message)
        if msg["event"] == "newMessage":
            newMessage = {
                "content":msg['msg'],
                "username":msg["room"],
                "type":"text",
                }

            SendDataToWechat(newMessage).send_data()

            data_source = 1
            customer_name = msg["room"] 
            content_type = "text"
            create_time =  datetime.datetime.fromtimestamp(int(time.time()))
            content = msg['msg']
            employee = self.get_current_user()
            self.application.db.execute("insert into out_data(data_source,customer_name,content_type,create_time,content,employee) \
values(%s,%s,%s,%s,%s,%s)", data_source,customer_name,content_type,create_time,content,employee)
            echo_back = {
                "event":"newMessage",
                "room":msg['room'],
                "msg":msg['msg'],
                "username":self.get_current_user(),
                "type":"text",
                "timestamp":int(time.time()),
                }

            self.write_message(json.dumps(echo_back)) #回显，表示收到消息

        elif msg["event"] == "queryUnhandled":
            #"send uhandled users "
            max_times = self.application.db.query("select a.customer_name from in_data as a ,out_data as b where a.customer_name = b.customer_name group by a.customer_name, b.customer_name having max(a.insert_time) < max(b.insert_time) ")
            handled = set()
#            print max_times
#            for max_time in max_times: 
#                if max_time.get("max(b.insert_time)") > max_time.get("max(a.insert_time)"):
            if max_time.get("customer_name"):
                handled.add(max_time.get("customer_name"))
            handled_string = ""
            for x in handled:
                handled_string += x + ","
#            print handled_string
            unhandled = self.application.db.query("select distinct(customer_name) from in_data where customer_name not in (%s)",handled_string[:-1])
            users = []
            for user in  unhandled:
                users.append(
                    {
                        "username":user.get("customer_name"),
                        "msg":"11",
                        }
                    )
            newMessage = {
                "event":"queryUnhandled",
                "users":users,
                }
            self.write_message(json.dumps(newMessage))

        elif msg["event"] == "getUnhandledUser":
#            print "send uhandled"
            messages = self.application.db.query("select content,content_type,create_time  from in_data where customer_name = %s",msg["username"])
            message = []
            for msgx in messages:
                message.append(
                    {
                        "msg":msgx.get("content"),
                        "type":msgx.get("content_type"),
                        "timestamp":time.mktime(msgx.get("create_time").timetuple()),
                        "username":msg["username"],
                        }
                    )
            newMessage = {
                "event":"getUnhandledUser",
                "room":msg['username'],
                "message":message,
                }
            self.write_message(json.dumps(newMessage))

        else:
            pass

def echo():
    print "echo called"
##MAIN
if __name__ == '__main__':

    app = Application()
    app.listen(8888)
    app2 = WechatDataReciever()
    app2.listen(9999) #微信服务器仅支持80端口的post 用wecheat 可以不是80端口
    loop = tornado.ioloop.IOLoop.instance()
    signal.signal(signal.SIGUSR1,lambda a,b:loop.add_callback_from_signal(ChatSocketHandler.update_cache))
    
#    prd = tornado.ioloop.PeriodicCallback(ChatSocketHandler.update_cache, 5000)
#    prd.start()
    loop.start()
