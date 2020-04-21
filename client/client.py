from kivy import Config
Config.set('graphics', 'width', '600')
Config.set('graphics', 'height', '500')
Config.set('graphics', 'minimum_width', '600')
Config.set('graphics', 'minimum_height', '500')

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.properties import ObjectProperty

import socket
import ssl
import time
import errno

HEADERSIZE = 8

class LoginScreen(GridLayout, Screen):
    def login(self, ip, password, username):
        mainApp.screenManager.current = 'Loading'
        LoadingScreen.connect(ip,password,username)

class LoadingScreen(GridLayout, Screen):
    def go_back(self):
        mainApp.screenManager.current = 'Login'

    def connect(ip, password, username):
        hostname = ip
        encUsername = username.encode('utf-8')
        mainApp.username = username
        usernameHeader = f'0{len(encUsername):<{HEADERSIZE-1}}'.encode('utf-8')
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

        try:
            sock = socket.create_connection((hostname, 8443))
            try:
                ssock = context.wrap_socket(sock, server_hostname=hostname)
                mainApp.serverSocket = ssock
                ssock.setblocking(False)
                ssock.send(usernameHeader + encUsername)
                mainApp.mainLoopSchedule = Clock.schedule_interval(AppScreen.appLoop, 0.5)
                mainApp.getOnlineUsers = Clock.schedule_interval(AppScreen.getOnlineUsers, 10)
                Clock.schedule_once(AppScreen.getOnlineUsers, 2)
                mainApp.screenManager.current = 'App'

            except:
                print('ssock failed')
                mainApp.screenManager.current = 'Login'                
        except:
            print('create connection failed')
            mainApp.screenManager.current = 'Login'
            

class AppScreen(GridLayout, Screen):
    label_wid = ObjectProperty()
    chat_list = ObjectProperty()

    def __init__(self, **kwargs):
        super(AppScreen, self).__init__(**kwargs)
        mainApp.label = self.label_wid
        mainApp.chat_list = self.chat_list
        mainApp.active_users = {}
        mainApp.idChatMap = {}
        mainApp.idNameMap = {}
        mainApp.idChatMap[0] = ''
        mainApp.currentActiveChat = 0

    def appLoop(time):
        try:
            usernameHeader = mainApp.serverSocket.recv(HEADERSIZE)
            header = usernameHeader.decode('utf-8').strip()
            print(header)
            if header[0] == '1':
                messageLenght = int(header[1:])
                message = mainApp.serverSocket.recv(messageLenght).decode('utf-8')
                recieved = message.split(' ')
                if recieved[0] == 'clientList':
                    idList = []
                    for item in recieved[1:]:
                        id, name = item.split(',')
                        id = int(id)
                        idList.append(id)
                        mainApp.idNameMap[id] = name
                        if id not in mainApp.active_users:
                            btn = Button(text = f'{name}', size_hint_y = None, height = 80, on_press = AppScreen.openPrivateChat)
                            btn.__self__.buttonId = id
                            mainApp.idChatMap[id] = ''
                            mainApp.active_users[id] = btn
                            mainApp.chat_list.add_widget(btn)

                    for user in mainApp.active_users:
                        if user not in idList:
                            mainApp.chat_list.remove_widget(mainApp.active_users[user])

            elif header[0] == '2':
                messageLenght = int(header[1:])
                message = mainApp.serverSocket.recv(messageLenght).decode('utf-8').strip()
                senderId = int(message.split(' ',1)[0].strip())
                msg = message[(len(str(senderId))):].strip()
                mainApp.idChatMap[senderId] += '\n'
                mainApp.idChatMap[senderId] += mainApp.idNameMap[senderId] + ': ' + msg
                if mainApp.currentActiveChat == senderId:
                    mainApp.label.text = mainApp.idChatMap[senderId]

            elif not usernameHeader:
                print('fatal error, server closed')
            username_lenght = int(header[1:])
            username = mainApp.serverSocket.recv(username_lenght).decode('utf-8')
            messageHeader = mainApp.serverSocket.recv(HEADERSIZE)
            messageLenght = int(messageHeader[1:].decode('utf-8').strip())
            msg = mainApp.serverSocket.recv(messageLenght).decode('utf-8')
            mainApp.idChatMap[0] += '\n'
            mainApp.idChatMap[0] += username + ': ' + msg
            if mainApp.currentActiveChat == 0:
                mainApp.label.text = mainApp.idChatMap[0]
        except:
            pass
        
    def disconnect(self):
        mainApp.serverSocket.close()
        del mainApp.serverSocket
        Clock.unschedule(mainApp.mainLoopSchedule)
        Clock.unschedule(mainApp.getOnlineUsers)
        mainApp.label.text = ''
        mainApp.screenManager.current = 'Login'

    def send_message(self, message, chat):
        Clock.schedule_once(lambda dt: AppScreen.set_focus(message))
        if not (message.text.strip()):
            return
        mainApp.idChatMap[mainApp.currentActiveChat] += '\n'
        mainApp.idChatMap[mainApp.currentActiveChat] += mainApp.username + ': ' + message.text
        mainApp.label.text = mainApp.idChatMap[mainApp.currentActiveChat]
        if mainApp.currentActiveChat == 0:
            encMessage = message.text.encode('utf-8')
            messageHeader = f'0{len(message.text):<{HEADERSIZE-1}}'.encode('utf-8')
            mainApp.serverSocket.send(messageHeader + encMessage)
        else:
            newMsg = str(mainApp.currentActiveChat) + ' ' + message.text
            encMessage = newMsg.encode('utf-8')
            messageHeader = f'2{len(newMsg):<{HEADERSIZE-1}}'.encode('utf-8')
            mainApp.serverSocket.send(messageHeader + encMessage)

    def getOnlineUsers(time):
        command = 'getOnlineUsers'
        commandHeader = f'1{len(command):<{HEADERSIZE-1}}'.encode('utf-8')
        command = command.encode('utf-8')
        mainApp.serverSocket.send(commandHeader + command)
        print('request sent')

    def openPrivateChat(self):
        print('private chat opened from: ' + str(self.buttonId))
        mainApp.label.text = mainApp.idChatMap[self.buttonId]
        mainApp.currentActiveChat = self.buttonId

    def openGlobalChat(self):
        mainApp.label.text = mainApp.idChatMap[0]
        mainApp.currentActiveChat = 0

    def set_focus(textInput):
        textInput.focus = True

class MainApp(App):
    def build(self):
        self.screenManager = ScreenManager()

        self.loginScreen = LoginScreen()
        screen = Screen(name='Login')
        screen.add_widget(self.loginScreen)
        self.screenManager.add_widget(screen)

        self.loadingScreen = LoadingScreen()
        screen = Screen(name='Loading')
        screen.add_widget(self.loadingScreen)
        self.screenManager.add_widget(screen)

        self.appScreen = AppScreen()
        screen = Screen(name='App')
        screen.add_widget(self.appScreen)
        self.screenManager.add_widget(screen)
        
        return self.screenManager

if __name__ == '__main__':
    mainApp = MainApp()
    mainApp.run()
