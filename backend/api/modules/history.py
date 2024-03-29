from ctypes import sizeof
from flask import Blueprint,request,jsonify,url_for,redirect,render_template,session
from datetime import datetime
import datetime
import pymysql
import yaml
import re
import traceback
import hashlib
import pandas as pd
import random
import string
import time
import datetime
from flask_cors import CORS

#for user register

with open('config.yml', 'r') as f:
    cfg = yaml.safe_load(f)


history=Blueprint("history",__name__) 
CORS(history,resources={r"/*": {"origins": "*"}},supports_credentials=True)


#for cut path
@history.route('/')
def index():
    return "history route"

@history.route('/checkLendClassroom',methods=['POST'])
def checkLendClassroom():
    connection = pymysql.connect(host=cfg['db']['host'],user=cfg['db']['user'],password=cfg['db']['password'],db=cfg['db']['database'])
    info = dict()
    cursor = connection.cursor()
    #ApplicationForms's PK = classroomID lendTime weekDay
    info['schoolName'] = request.json['schoolName']
    info['classroomID'] = request.json['classroomID']
    info['lendTime'] = request.json['lendTime']
    info['weekDay'] = request.json['weekDay']
    info['confirmType'] = request.json['confirmType']
    info['errors'] = []
    print(info)
    if info['confirmType']=='1':
        cursor.execute("SELECT status from Classrooms WHERE classroomID=(%(classroomID)s)",{'classroomID':info['classroomID']})
        rows = cursor.fetchall()
        connection.commit()
        if len(rows)==0:
            info['errors'] = 'Classroom has been deleted!'
        elif rows[0][0]==1:
            info['errors'] = 'Classroom has been lent!'
        elif rows[0][0]==2:
            info['errors'] = 'Classroom has been banned!'
        if len(info['errors'])!=0:
            insertString = 'DELETE from ApplicationForms WHERE classroomID=(%(classroomID)s) AND lendTime=(%(lendTime)s) AND weekDay=(%(weekDay)s);'
            cursor.execute(insertString,{'classroomID':info['classroomID'],'lendTime':info['lendTime'],'weekDay':info['weekDay']})
            connection.commit() #submit the data to database 
        else:
            try:
                cursor.execute("SELECT status from Users WHERE schoolName=(%(schoolName)s)",{'schoolName':info['schoolName']})
                rows = cursor.fetchall()
                connection.commit()
                if rows[0][0]==1:
                    info['errors'] = 'User has not return key!'
                elif rows[0][0]==2:
                    info['errors'] = 'User can not borrow key!(user has been banned!)'
                else:
                    #update user state first
                    if info['confirmType'] == '1':
                        insertString = 'UPDATE Users SET status = 1 WHERE schoolName=(%(schoolName)s);'
                    cursor.execute(insertString, {'schoolName':info['schoolName']})
                    connection.commit() #submit the data to database 
                    #search the reason from ApplicationForms
                    insertString = 'SELECT courseName,userName,reason from ApplicationForms WHERE classroomID=(%(classroomID)s) AND lendTime=(%(lendTime)s) AND weekDay=(%(weekDay)s);'
                    cursor.execute(insertString,{'classroomID':info['classroomID'],'lendTime':info['lendTime'],'weekDay':info['weekDay']})
                    rows = cursor.fetchall()
                    connection.commit()
                    if len(rows)==0:
                        info['errors'] = 'invalid select from ApplicationForms'
                    else :
                        #print(rows)
                        insertString = 'DELETE from ApplicationForms WHERE classroomID=(%(classroomID)s) AND lendTime=(%(lendTime)s) AND weekDay=(%(weekDay)s);'
                        cursor.execute(insertString,{'classroomID':info['classroomID'],'lendTime':info['lendTime'],'weekDay':info['weekDay']})
                        #rows = cursor.fetchall()
                        connection.commit()
                        info['lendTime'] = datetime.datetime.now()
                        info['courseName'] = rows[0][0]
                        info['userName'] = rows[0][1]
                        info['reason'] = rows[0][2]
                        #insert new data to history
                        if info['confirmType'] == '1':
                            info['lendWeekDay'] = pd.Timestamp(datetime.datetime.strptime(info['weekDay'],"%Y-%m-%d")).dayofweek
                            insertString = 'INSERT INTO History(classroomID,courseName,userName,schoolName,lendTime,returnTime,lendWeekDay,returnWeekDay,reason)values(%(classroomID)s,%(courseName)s,%(userName)s,%(schoolName)s,%(lendTime)s,NULL,%(lendWeekDay)s,NULL,%(reason)s);'
                            cursor.execute(insertString,{'classroomID':info['classroomID'],'courseName':info['courseName'],'userName':info['userName'],'schoolName':info['schoolName'],'lendTime':info['lendTime'],'reason':info['reason'],'lendWeekDay':info['lendWeekDay']})
                            connection.commit()
            except Exception: #get exception if there's still occured something wrong
                    traceback.print_exc()
                    connection.rollback()
                    info['errors'] = 'checkLendClassroom fail'
    else:
        insertString = 'DELETE from ApplicationForms WHERE classroomID=(%(classroomID)s) AND lendTime=(%(lendTime)s) AND weekDay=(%(weekDay)s);'
        cursor.execute(insertString,{'classroomID':info['classroomID'],'lendTime':info['lendTime'],'weekDay':info['weekDay']})
        connection.commit() #submit the data to database 
    return jsonify(info)


@history.route('/returnClassroom',methods=['GET'])
def returnClassroom():
    info = dict()
    connection = pymysql.connect(host=cfg['db']['host'],user=cfg['db']['user'],password=cfg['db']['password'],db=cfg['db']['database'])
    cursor=connection.cursor()
    try:
        #select history that 'returnTime = NULL'
        insertString = 'SELECT schoolName, userName, classroomID, lendTime, returnTime, lendWeekDay, returnWeekDay from History WHERE returnTime is NULL'
        cursor.execute(insertString)
        rows = cursor.fetchall()
        connection.commit()
        if len(rows)==0:
            info['errors'] = 'invalid select from History' 
        else :
            info['schoolName'] = []
            info['userName'] = []
            info['classroomID'] = []
            info['lendTime'] = []
            info['returnTime'] = []
            info['lendWeekDay'] = []
            info['returnWeekDay'] = []
            for i in rows:
                info['schoolName'].append(i[0])
                info['userName'].append(i[1])
                info['classroomID'].append(i[2])
                info['lendTime'].append(i[3].strftime('%Y/%m/%d %H:%M:%S'))
                info['returnTime'].append(i[4])
                info['lendWeekDay'].append(i[5])
                info['returnWeekDay'].append(i[6])  
            print(info)    
            
                
    except Exception: #get exception if there's still occured something wrong
            traceback.print_exc()
            connection.rollback()
            info['errors'] = 'returnClassroom fail'
    return jsonify(info)


#get all data from history
@history.route('/seeClassroomHistory',methods=['GET'])
def seeClassroomHistory():
    info = dict()
    errors = []
    connection = pymysql.connect(host=cfg['db']['host'],user=cfg['db']['user'],password=cfg['db']['password'],db=cfg['db']['database'])
    cursor=connection.cursor()
    #undo: displayed data <= 100 
    cursor.execute("SELECT * from History ")
    rows = cursor.fetchall()
    connection.commit()
    if len(rows) == 0:
        errors.append("No history exist!")
    else:
        info['history'] = []
        for row in rows:
            tmp = []
            for i in range(7):
                print(type(row[i]))
                if (i == 4 or i == 5) and row[i] != None:
                    tmp.append(row[i].strftime('%Y/%m/%d %H:%M:%S'))
                else :
                    tmp.append(row[i])
            info['history'].append(tmp)
    info['errors'] = errors
    return jsonify(info)

@history.route('/checkReturnClassroom',methods=['POST'])
def checkReturnClassroom():
    connection = pymysql.connect(host=cfg['db']['host'],user=cfg['db']['user'],password=cfg['db']['password'],db=cfg['db']['database'])
    info = dict()
    errors = []
    cursor = connection.cursor()
    #History's PK = classroomID lendTime
    #Users' PK = schoolName
    info['schoolName'] = request.json['schoolName']
    info['classroomID'] = request.json['classroomID']
    info['lendTime'] = request.json['lendTime']
    #info['lendTime'] = datetime.datetime.strftime(info['lendTime'],"%Y/%m/%d %H:%M:%S")
    #info['lendTime'] = datetime.strptime(info['lendTime'],'%Y/%m/%d %H:%M:%S').datetime()
    info['lendTime'] = datetime.datetime.strptime(info['lendTime'],"%Y/%m/%d %H:%M:%S").strftime("%Y/%m/%d %H:%M:%S")
    print(info['lendTime'])
    info['lendWeekDay'] = request.json['weekDay']
    try:
        #update user's status=0
        cursor.execute("SELECT * from ApplicationForms WHERE schoolname=%(schoolname)s ", {'schoolname':info['schoolName']})
        rows = cursor.fetchall()
        connection.commit()
        if len(rows) == 0:
            insertString = 'UPDATE Users SET status=0 WHERE schoolName=(%(schoolName)s);'
            cursor.execute(insertString, {'schoolName':info['schoolName']})
            connection.commit()
        else:
            insertString = 'UPDATE Users SET status=3 WHERE schoolName=(%(schoolName)s);'
            cursor.execute(insertString, {'schoolName':info['schoolName']})
            connection.commit()
        insertString = 'UPDATE Classrooms SET status=0 WHERE classroomID=(%(classroomID)s);'
        cursor.execute(insertString, {'classroomID':info['classroomID']})
        connection.commit()
        #update history: returnTime,returnWeekDay
        info['returnTime'] = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        print(info)
        info['returnWeekDay'] = datetime.datetime.today().weekday() + 1
        print(info)
        insertString = 'UPDATE history SET returnTime=(%(returnTime)s), returnWeekDay=(%(returnWeekDay)s) WHERE classroomID=(%(classroomID)s) AND lendTime=(%(lendTime)s);'
        cursor.execute(insertString, {'returnTime':info['returnTime'],'returnWeekDay':info['returnWeekDay'],'classroomID':info['classroomID'],'lendTime':info['lendTime']})
        connection.commit() #submit the data to database 
    except Exception: #get exception if there's still occured something wrong
            traceback.print_exc()
            connection.rollback()
            errors = 'checkLendClassroom fail'
    info['errors'] = errors
    return jsonify(info)
#   email confirm undo
#   if a user input an error email (but legal), his student's ID fucked up. 

#   html should alert if sign up failed when reload