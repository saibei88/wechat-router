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

from settings import DATABASE
from handlers import IndexHandler, ChatSocketHandler
from handlers import GetDataFromWechat
from handlers import AuthLoginHandler, AuthLogoutHandler

import signal

define("mysql_host",
       default=DATABASE.get("host", "localhost") + ":" +
       str(DATABASE.get("port", "3306")),
       help="blog database host")
define("mysql_database", default=DATABASE.get("database", "test"),
       help="blog database name")
define("mysql_user", default=DATABASE.get("username", "test"),
       help="blog database user")
define("mysql_password",
       default=DATABASE.get("password", "test"),
       help="blog database password")


class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/chatsocket", ChatSocketHandler),
            (r"/wechat", GetDataFromWechat),
        ]
        settings = dict(
            cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
            login_url="/auth/login",
            xsrf_cookies=True,
            template_path=os.path.join(os.path.dirname(__file__),
                                         "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug=True,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

        # Have one global connection to the blog DB across all handlers
        self.db = torndb.Connection(
            host=options.mysql_host,
            database=options.mysql_database,
            user=options.mysql_user,
            password=options.mysql_password,
            )


##MAIN
if __name__ == '__main__':

    app = Application()
    app.listen(8888)
    loop = tornado.ioloop.IOLoop.instance()
    signal.signal(signal.SIGUSR1,
                  lambda a, b: loop.add_callback_from_signal(
                      ChatSocketHandler.update_cache
                      )
                  )

    loop.start()
