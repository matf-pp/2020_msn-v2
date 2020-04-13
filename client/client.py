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

HEADERSIZE = 7

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
        usernameHeader = f'{len(encUsername):<{HEADERSIZE}}'.encode('utf-8')
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

        try:
            sock = socket.create_connection((hostname, 8443))
            try:
                ssock = context.wrap_socket(sock, server_hostname=hostname)
                mainApp.serverSocket = ssock
                ssock.setblocking(False)
                ssock.send(usernameHeader + encUsername)
                mainApp.mainLoopSchedule = Clock.schedule_interval(AppScreen.appLoop, 0.5)
                mainApp.screenManager.current = 'App'

            except:
                print('ssock failed')
                mainApp.screenManager.current = 'Login'                
        except:
            print('create connection failed')
            mainApp.screenManager.current = 'Login'
            

class AppScreen(GridLayout, Screen):
    label_wid = ObjectProperty()

    def __init__(self, **kwargs):
        super(AppScreen, self).__init__(**kwargs)
        mainApp.label = self.label_wid

    def appLoop(time):
        try:
            usernameHeader = mainApp.serverSocket.recv(HEADERSIZE)
            if not usernameHeader:
                print('fatal error, server closed')
            username_lenght = int(usernameHeader.decode('utf-8').strip())
            username = mainApp.serverSocket.recv(username_lenght).decode('utf-8')
            messageHeader = mainApp.serverSocket.recv(HEADERSIZE)
            messageLenght = int(messageHeader.decode('utf-8').strip())
            msg = mainApp.serverSocket.recv(messageLenght).decode('utf-8')
            mainApp.label.text += '\n'
            mainApp.label.text += username + ': ' + msg
        except:
            pass
        
    def disconnect(self):
        mainApp.serverSocket.close()
        del mainApp.serverSocket
        Clock.unschedule(mainApp.mainLoopSchedule)
        mainApp.label.text = ''
        mainApp.screenManager.current = 'Login'

    def send_message(self, message, chat):
        Clock.schedule_once(lambda dt: AppScreen.set_focus(message))
        if not (message.text.strip()):
            return
        chat.text += '\n'
        chat.text += mainApp.username + ': ' + message.text
        encMessage = message.text.encode('utf-8')
        messageHeader = f'{len(message.text):<{HEADERSIZE}}'.encode('utf-8')
        mainApp.serverSocket.send(messageHeader + encMessage)

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
