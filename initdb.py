#!/usr/bin/python
#coding:utf8
import MySQLdb
from settings import DATABASE
try:
    conn = MySQLdb.connect(host='localhost',
                         user=DATABASE.get("username", "test"),
                         passwd=DATABASE.get("password", "test"),
                         db=DATABASE.get("database", "test"),
                         port=DATABASE.get("port", 3306))
    cur = conn.cursor()
    cur.execute('create table in_data(\
id int(11) AUTO_INCREMENT PRIMARY KEY, \
insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\
data_source int(11), \
customer_name varchar(100),\
content_type varchar(30),\
create_time TIMESTAMP,\
content varchar(2000),\
msg_id bigint(11)\
)\
')

    cur.execute('create table out_data( \
id int(11) AUTO_INCREMENT PRIMARY KEY,\
insert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\
data_source int(11),\
customer_name varchar(100),\
content_type varchar(30),\
create_time TIMESTAMP,\
content varchar(2000),\
employee varchar(200)\
)\
')

    conn.commit()
    #data_source = models.IntegerField() #1:微信 2:易信 3: 微博
    cur.close()
    conn.close()
except MySQLdb.Error, e:
    print "Mysql Error %d: %s" % (e.args[0], e.args[1])
