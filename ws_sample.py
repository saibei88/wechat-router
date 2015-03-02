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

define("mysql_host", default="127.0.0.1:3306", help="blog database host")
define("mysql_database", default="test", help="blog database name")
define("mysql_user", default="root", help="blog database user")
define("mysql_password", default="236788", help="blog database password")

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/chatsocket", ChatSocketHandler), 
            (r"/wechat",GetDataFromWechat), 
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
#            xsrf_cookies=True,
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

    cache = []
    cache_size = 200

    def get_current_user(self):
        user_json = self.get_secure_cookie("chatdemo_user")
        if not user_json: return None
        return json.loads(user_json).get("claimed_id")
#        return tornado.escape.json_decode(user_json)

    def get_compression_options(self):
        # Non-None enables compression with default options.
        return {}

#    @tornado.web.authenticated
    def open(self):
#        for row in  self.application.db.iter("show tables"):
#            print row
        print self.get_current_user()

    def on_close(self):
        pass

    def on_message(self, message):
        print "got message %r" % message
        self.event_handler(message)

    def event_handler(self,message):
        msg = json.loads(message)
        print msg
        if msg["event"] == "newMessage":
            newMessage = {
#                "event":"newMessage",
#                "room":msg['room'],
                "content":msg['msg'],
                "username":msg["room"],
                "type":"text",
#                "timestamp":int(time.time()),
                }
            SendDataToWechat(newMessage).send_data()
#            self.write_message(json.dumps(newMessage))
            data_source = 1
            customer_name = msg["room"] 
            content_type = "text"
            create_time =  datetime.datetime.fromtimestamp(int(time.time()))
            content = msg['msg']
            employee = self.get_current_user()
            self.application.db.execute("insert into out_data(data_source,customer_name,content_type,create_time,content,employee) \
values(%s,%s,%s,%s,%s,%s)", data_source,customer_name,content_type,create_time,content,employee)
#            self.application.db.execute("insert into out_data",)

        elif msg["event"] == "queryUnhandled":
            #"send uhandled users "
            max_times = self.application.db.query("select max(a.insert_time),max(b.insert_time),a.customer_name from in_data as a ,out_data as b where a.customer_name = b.customer_name group by a.customer_name, b.customer_name")
            print max_times

            handled = set()
            for max_time in max_times: 
                if max_time.get("max(b.insert_time)") < max_time.get("max(a.insert_time)"):
                    handled.add(max_time.get("a.customer_name"))
            handled_string = ""
            for x in iter(handled):
                handled_string += x + ","
            print handled_string
            unhandled = self.application.db.query("select distinct(customer_name) from in_data where customer_name not in (%s)",handled_string)
            users = []
            [{"username":"user1","msg":"15"},{"username":"user2","msg":"14"},],
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
            print "send uhandled"
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

##MAIN
if __name__ == '__main__':
    newMessage = {
        "file":"/home/shen/IMG_5581.JPG",
        "type":"text",
        }
    send_msg = SendDataToWechat(newMessage)
    send_msg.send_data()
    app = Application()
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
