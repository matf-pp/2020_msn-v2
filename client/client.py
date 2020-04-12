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

import socket
import ssl
import time
import errno

class LoginScreen(GridLayout, Screen):
    def login(self, ip, password, username):
        mainApp.screenManager.current = 'Loading'
        LoadingScreen.connect(ip,password,username)

class LoadingScreen(GridLayout, Screen):
    def go_back(self):
        mainApp.screenManager.current = 'Login'

    def connect(ip, password, username):
        hostname = ip
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

        try:
            sock = socket.create_connection((hostname, 8443))
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                mainApp.serverSocket = ssock
                AppScreen.appLoop(mainApp.serverSocket)
                mainApp.screenManager.current = 'App'
                
        except:
            mainApp.screenManager.current = 'Login'
            

class AppScreen(GridLayout, Screen):
    def appLoop(ssock):
        pass
        
    def disconnect(self):
        mainApp.serverSocket.close()
        del mainApp.serverSocket
        mainApp.screenManager.current = 'Login'

    def send_message(self, message, chat):
        Clock.schedule_once(lambda dt: AppScreen.set_focus(message))
        if not message.text:
            return
        chat.text += '\n'
        chat.text += message.text

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