from flask import Flask, render_template, request,redirect,url_for,session
from flask_socketio import SocketIO
from threading import Lock
from datetime import datetime
from paho.mqtt import client as mqtt_client
from email.message import EmailMessage
import random
import json
import pymysql
import pymysql.cursors
import re
import ssl
import smtplib
import time as tm
user=''
'''
    EMAIL PARAMETERS
'''
email_sender='carlosarzez25@gmail.com'
email_password='ohkkhnkblfckdmhn'
email_receiver=''
subject="Envio contraseña y password"
body=""
"""
    MQTT BROKER PARAMETERS
"""
broker = 'ec2-44-204-178-128.compute-1.amazonaws.com'
port = 1883
topic = "WSNPIIData"
client_id = f'python-mqtt-{random.randint(0, 100)}'
username = 'carlos'
password = 'carlos123'
usernameDisplay=''
"""Store data to database"""
def storedata(data):
    connection = pymysql.connect(host='localhost',user='root',password='Carlos123#',database='WSNProjectII')
    with connection:
        with connection.cursor() as cursor:
            sql = "INSERT INTO `devices` (`value`, `description`,`node`) VALUES (%s,%s,%s)"
            cursor.execute(sql,(str(data["humidity"]), 'Dato enviado del sensor de humedad',str(1)))
            cursor.execute(sql,(str(data["temperature"]), 'Dato enviado del sensor de temperatura',str(2)))
            cursor.execute(sql,(str(data["co2"]), 'Dato enviado del sensor de dioxido de carbono',str(3)))
            cursor.execute(sql,(str(data["uv"]), 'Dato enviado del sensor de radiación uv',str(4)))
        connection.commit()
"""Get data from database"""
def Getdata(name,password):
    connection = pymysql.connect(host='localhost',user='root',password='Carlos123#',database='WSNProjectII')
    with connection:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `user` WHERE name=%s AND password = SHA1(%s)"
            cursor.execute(sql, (name,password))
            result = cursor.fetchone()
            return result
    
"""
Connect MQTT broker
"""
def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client
"""
Subscribe MQTT broker
"""
def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        x=msg.payload.decode()
        y=json.loads(x)
        print(y)
        storedata(y)
        socketio.emit('updateSensorData', {'value':y["humidity"], "date": get_current_datetime()})
        socketio.emit('updateSensorData2', {'value':y["temperature"], "date": get_current_datetime()})
        socketio.emit('updateSensorData3', {'value':y["co2"], "date": get_current_datetime()})
        socketio.emit('updateSensorData4', {'value':y["uv"], "date": get_current_datetime()})
        socketio.emit('updateSensorState', {'value':y["nodeuv"], "date": get_current_datetime()})
        socketio.emit('updateSensorState2', {'value':y["nodehumidity"], "date": get_current_datetime()})
        socketio.emit('updateSensorState3', {'value':y["nodetemperature"], "date": get_current_datetime()})
        socketio.emit('updateSensorState4', {'value':y["nodeco2"], "date": get_current_datetime()})
        socketio.sleep(0.2)
    client.subscribe(topic)
    client.on_message = on_message
    print (client.on_message)
   
"""
Background Thread
"""
thread = None
thread_lock = Lock()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'donsky!'
socketio = SocketIO(app, cors_allowed_origins='*')

"""
Get current date time
"""
def get_current_datetime():
    now = datetime.now()
    return now.strftime("%m/%d/%Y %H:%M:%S")

def background_thread():
    client = connect_mqtt()
    subscribe(client)
    client.loop_start()
    tm.sleep(0.5)
    client.loop_stop()

"""
Serve root index file
"""
@app.route('/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        global usernameDisplay
        name = request.form['username']
        usernameDisplay=name
        password = request.form['password']
        account=Getdata(name,password)
        if account:
            session['loggedin'] = True
            session['id'] = account[0]
            session['username'] = account[7]
            if(session['username'] == 'admin'):
                return redirect(url_for('home'))
            else:
                return redirect(url_for('homeuser'))
        else:
            msg = 'Incorrect username/password!'
    return render_template('pages/login.html', msg=msg)
@app.route('/home')
def home():
    global usernameDisplay
    return render_template('pages/index.html',username=usernameDisplay)
@app.route('/homeuser')
def homeuser():
    global usernameDisplay
    return render_template('pages/homeuser.html',username=usernameDisplay)
@app.route('/logout')
def logout():
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   return redirect(url_for('login'))
@app.route('/create',methods=['GET','POST'])
def create():
    global email_sender
    global email_password
    global email_receiver
    global subject
    global body
    if request.method == 'GET':
        return render_template('pages/userCRUD.html')
    if request.method == 'POST':
        connection = pymysql.connect(host='localhost',user='root',password='Carlos123#',database='WSNProjectII')
        ci = request.form['ci']
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        secondLastname = request.form['secondLastname']
        gender = request.form['gender']
        name = request.form['name']
        password = request.form['password']
        role = request.form['role']
        email = request.form['email']
        with connection:
            with connection.cursor() as cursor:
                sql = "INSERT INTO `user` (`ci`, `firstname`,`lastname`,`secondLastname`,`gender`,`name`,`password`,`role`,`email`,`userID` ) VALUES (%s,%s, %s,%s, %s,%s,SHA1(%s),%s, %s,%s)"
                cursor.execute(sql, (ci, firstname,lastname,secondLastname,gender,name,password,role,email,1))
            connection.commit()
        em=EmailMessage()
        email_receiver=email
        em['From']=email_sender
        em['To']=email_receiver
        em['Subject']=subject
        body='Username: '+name+' Password: '+password
        em.set_content(body)
        context=ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com',465,context=context) as smtp:
            smtp.login(email_sender,email_password)
            smtp.sendmail(email_sender,email_receiver,em.as_string())
        return redirect(url_for('homeuser'))
@app.route('/historic')
def historic():
    global usernameDisplay
    connection = pymysql.connect(host='localhost',user='root',password='Carlos123#',database='WSNProjectII')
    legend = 'Humidity Data'
    legend2 = 'Temperature Data'
    legend3= 'CO2 Data'
    legend4= 'UV Data'
    curs=connection.cursor()
    curs.execute("SELECT * FROM devices WHERE node=1")
    mesParameter=[]
    value=[]
    for row in curs:
        if(row[1]>0):
            mesParameter.append(row[4])
            value.append(row[1])
    labels = mesParameter
    curs.execute("SELECT * FROM devices WHERE node=2")
    mesParameter2=[]
    value2=[]
    for row in curs:
        if(row[1]>0):
            mesParameter2.append(row[4])
            value2.append(row[1])
    labels2 = mesParameter2
    curs.execute("SELECT * FROM devices WHERE node=3")
    mesParameter3=[]
    value3=[]
    for row in curs:
        if(row[1]>0):
            mesParameter3.append(row[4])
            value3.append(row[1])
    labels3 = mesParameter3
    curs.execute("SELECT * FROM devices WHERE node=4")
    mesParameter4=[]
    value4=[]
    for row in curs:
        if(row[1]>0):
            mesParameter4.append(row[4])
            value4.append(row[1])
    labels4 = mesParameter4
    curs.execute("SELECT * FROM devices")
    devices=curs.fetchall()
    return render_template('pages/historic.html',legend4=legend4,legend3=legend3,legend2=legend2,legend=legend,labels=labels,labels2=labels2,labels3=labels3,labels4=labels4,values=value,values2=value2,values3=value3,values4=value4,devices=devices,username=usernameDisplay)
"""
Decorator for connect
"""
@socketio.on('connect')
def connect():
    global thread
    print('Client connected')

    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(background_thread)

"""
Decorator for disconnect
"""
@socketio.on('disconnect')
def disconnect():
    print('Client disconnected',  request.sid)

if __name__ == '__main__':
    socketio.run(app,host='0.0.0.0',port=5000,debug=True)
    
    
