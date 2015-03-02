#!/usr/bin/python
#coding:utf8

import wechatpy
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException,InvalidAppIdException
from wechatpy.crypto import WeChatCrypto
from wechatpy.client import WeChatClient
from wechatpy.replies import REPLY_TYPES

from tornado.httpclient import AsyncHTTPClient,HTTPRequest
from tornado import gen

from auth import BaseHandler 
import simplejson as json
import time
import datetime
import os
import urllib,mimetypes
from settings import MEDIA_DIR

config_file = open("./wechat.config")
rawdata = config_file.readline()
configs = json.loads(rawdata)
config_file.close()
EncodingAESKey = configs.get("EncodingAESKey")
SECRET = configs.get("SECRET")
APPID = configs.get("APPID")
EXPIRED_TIME = configs.get("EXPIRED_TIME")
ACCESS_TOKEN = configs.get("ACCESS_TOKEN")
STORAGE_DIR = MEDIA_DIR

def token_check():
    global EXPIRED_TIME
    global ACCESS_TOKEN
    if time.time() - EXPIRED_TIME < 0:
        return 
    else:
        config_file = open("./wechat.config")
        configs = json.loads(config_file.readlines())
        config_file.close()
        EXPIRED_TIME = configs.get("EXPIRED_TIME")
        ACCESS_TOKEN = configs.get("ACCESS_TOKEN")

class GetDataFromWechat(BaseHandler):

    http_client =  AsyncHTTPClient()
    cache = []

    def get(self):
        """完成url输入之后，微信验证url有效性"""
        signature = self.request.arguments.get('signature', '')
        timestamp = self.request.arguments.get('timestamp', '')
        nonce = self.request.arguments.get('nonce', '')
        echo_str = self.request.arguments.get('echostr', '')
        try:
            token_check()
            check_signature(ACCESS_TOKEN, signature, timestamp, nonce)
        except InvalidSignatureException:
            self.set_status(403)
        self.write(echo_str)

    def post(self):
#        print('Raw message: \n%s' % self.request.body)
        token_check()
#        crypto = WeChatCrypto(ACCESS_TOKEN, EncodingAESKey, APPID)
        try:
#            msg = crypto.decrypt_message(
#                self.request.body,
#                msg_signature,
#                timestamp,
#                nonce
#                )
#            print('Descypted message: \n%s' % ms)
#            
#            self.write("success")
            msg = parse_message(self.request.body)
            self.cache.append(msg)
#            print "message time ",msg.time
            data_source = 1
            customer_name = msg.source 
            content_type = msg.type
            create_time = datetime.datetime.fromtimestamp(msg.time)
            msg_id = msg.id
            content = ""
#微信服务器post的数据链接可以直接回写回复信息，xml格式
            if msg.type == 'text':
#                print msg.content
                content = msg.content
                reply = create_reply(msg.content, msg)
                message_class = REPLY_TYPES.get("text")
                reply_msg = message_class(source = msg.source, target = msg.target, content = msg.content)
                self.write(reply_msg.render())
            elif msg.type == 'image':
                content = msg.image
                self.http_client.fetch(msg.image, self.handle_multimedia_file)

            else:
                url = "http://file.api.weixin.qq.com/cgi-bin/media/get?access_token=" + ACCESS_TOKEN + "&media_id=" + msg.media_id 
                self.http_client.fetch(url, self.handle_multimedia_file)
                if msg.type == 'voice':
                    content = msg.format + ":"  + ":" + msg.media_id + recognition
                elif msg.type == 'video':
                    content = msg.media_id
                else:
                    content = "unsupported"

            self.application.db.execute("insert into in_data(data_source,customer_name,content_type,create_time,content,msg_id) \
values(%s,%s,%s,%s,%s,%s)", data_source,customer_name,content_type,create_time,content,msg_id)

        except (InvalidSignatureException, InvalidAppIdException):
            self.set_status(403)

    def handle_multimedia_file(self,response):
        media_id = response.effective_url.split("media_id=")[-1].split("/")[-1]
        filedir = STORAGE_DIR + datetime.datetime.now().strftime("%Y-%m-%d") + "/" 
        if not os.path.exists(filedir):
            os.makedirs(filedir)
        storage_fd = open(filedir + media_id,"w")
        storage_fd.write(response.body)
        storage_fd.flush()
        storage_fd.close()
    
class SendDataToWechat(object):

    def __init__(self,msg):
        self.http_client =  AsyncHTTPClient()
        self.msg = msg

    @gen.coroutine
    def send_data(self):
        url = "https://api.weixin.qq.com/customservice/kfaccount/add?access_token=" + ACCESS_TOKEN
        if self.msg.get("type") != "text":
            new_msg = yield self.upload_multimedia_file(self.msg.get("file"),self.msg.get("type"))
            if new_msg.get("media_id",None):
                #上传成功,voice image currently
                reply = {
                    "touser":self.msg.get("username"),
                    "msgtype":self.msg.get("type"),
                    self.msg.get("type"):{
                        "media_id":new_msg.get("media_id"),
                        },
                    }
                self.http_client.fetch(url, method = "POST", body = json.dumps(reply))
        else:
            reply = {
                "touser":self.msg.get("username"),
                "msgtype":self.msg.get("type"),
                self.msg.get("type"):{
                    "content":self.msg.get("content")
                    },
                }
            self.http_client.fetch(url, method = "POST", body = json.dumps(reply))
    
    @gen.coroutine
    def upload_multimedia_file(self, file_name, typename):
        """supported types image,voice,video,thumb"""

        file_content = open(file_name)
        file_content = "".join(file_content.readlines())
        url = "http://file.api.weixin.qq.com/cgi-bin/media/upload?access_token=" + ACCESS_TOKEN + "&type=" + typename
#        url = "http://localhost:9999"

        content_type, body = encode_multipart_formdata([("myfile","")], [("myfile","temp.txt",file_content)])
        headers = {
            "Content-Type":content_type
            }
        method = "POST"
        req = HTTPRequest(url = url ,method = method , headers = headers, body = body)
        response = yield self.http_client.fetch(req)
        raise gen.Return(self.handle_response(response))
    
    def handle_response(self,response):
        resp = json.loads(response.body)
        if  not resp.get("errcode"):
#----currently for image and voice reply----
            content = {
#                "source":self.msg.get("username"),
#                "target":self.msg.get("room"), 
#                "content":self.msg.get("msg"),
                "media_id":resp.get("MediaId"),
                }
            return content

def encode_multipart_formdata(fields, files):
    """
    fields is a sequence of (name, value) elements for regular form fields.
    files is a sequence of (name, filename, value) elements for data to be uploaded as files
    Return (content_type, body) ready for httplib.HTTP instance
    """
    BOUNDARY = '----------ThIs_Is_tHe_bouNdaRY_$'
    CRLF = '\r\n'
    L = []
    for (key, value) in fields:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"' % key)
        L.append('')
        L.append(value)
    for (key, filename, value) in files:
        L.append('--' + BOUNDARY)
        L.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, filename))
        L.append('Content-Type: %s' % get_content_type(filename))
        L.append('')
        L.append(value)
    L.append('--' + BOUNDARY + '--')
    L.append('')
    body = CRLF.join(L)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

#        self.write(crypto.encrypt_message(
#            reply.render(),
#            nonce,
#            timestamp
#        ))
