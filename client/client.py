from kivy import Config
Config.set('graphics', 'width', '600')
Config.set('graphics', 'height', '500')
Config.set('graphics', 'minimum_width', '600')
Config.set('graphics', 'minimum_height', '500')

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.properties import ObjectProperty
import socket
import ssl
import encryption

HEADERSIZE = 8

class LoginScreen(GridLayout, Screen):
    def login(self, ip, password, username):
        mainApp.screenManager.current = 'Loading'
        LoadingScreen.connect(ip,password,username)

class LoadingScreen(GridLayout, Screen):
    loadingText = ObjectProperty()
    
    def __init__(self, **kwargs):
        super(LoadingScreen, self).__init__(**kwargs)
        mainApp.loadingText = self.loadingText

    def go_back(self):
        mainApp.screenManager.current = 'Login'

    def connect(ip, password, username):
        hostname = ip
        encUsername = username.strip().encode('utf-8')
        mainApp.username = username.strip()
        usernameHeader = f'0{len(encUsername):<{HEADERSIZE-1}}'.encode('utf-8')
        encPassword = password.strip().encode('utf-8')
        passwordHeader = f'9{len(encPassword):<{HEADERSIZE-1}}'.encode('utf-8')
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)

        try:
            sock = socket.create_connection((hostname, 8443))
            try:
                ssock = context.wrap_socket(sock, server_hostname=hostname)
                mainApp.serverSocket = ssock
                ssock.setblocking(False)
                ssock.send(usernameHeader + encUsername)
                ssock.send(passwordHeader + encPassword)
                mainApp.mainLoopSchedule = Clock.schedule_interval(AppScreen.appLoop, 0.1)
                mainApp.getOnlineUsers = Clock.schedule_interval(AppScreen.getOnlineUsers, 5)
                AppScreen.getMyId()
                mainApp.screenManager.current = 'App'

            except Exception:
                print('ssock failed')
                mainApp.screenManager.current = 'Login'
        except Exception:
            print('create connection failed')
            mainApp.screenManager.current = 'Login'

class SmoothButton(Button):
    def __init__(self, **kwargs):
        super(SmoothButton, self).__init__(**kwargs)

class AppScreen(GridLayout, Screen):
    label_wid = ObjectProperty()
    chat_list = ObjectProperty()
    global_chat_btn = ObjectProperty()

    def __init__(self, **kwargs):
        super(AppScreen, self).__init__(**kwargs)
        mainApp.label = self.label_wid
        mainApp.chat_list = self.chat_list
        mainApp.active_users = {}
        mainApp.idChatMap = {}
        mainApp.idNameMap = {}
        mainApp.idSharedsecretMap = {}
        mainApp.idChatMap[0] = ''
        mainApp.currentActiveChat = 0
        mainApp.myId = -1
        mainApp.sendMessageQueue = []
        mainApp.recieveMessageQueue = []
        mainApp.globalChatBtn = self.global_chat_btn


    def appLoop(time):
        try:
            for message in mainApp.sendMessageQueue:
                print('there should be message here for sending')
                recieverId = int(message.split(' ',1)[0].strip())
                print('sending message to:' + str(recieverId))
                if recieverId not in mainApp.idSharedsecretMap:
                    AppScreen.getSharedSecret(recieverId)
                    print('reciever not in idshrMap')
                else:
                    print('reciever is in map')
                    if 'shared' in mainApp.idSharedsecretMap[recieverId]:
                        try:
                            print('there is shared key')
                            msg = message[(len(str(recieverId))):].strip()
                            sharedSecret = mainApp.idSharedsecretMap[recieverId]['shared']
                            AESmsg = encryption.encrypt(msg, str(sharedSecret))
                            msg = str(recieverId) + ' ' + AESmsg
                            encMessage = msg.encode('utf-8')
                            header = f'2{len(msg):<{HEADERSIZE-1}}'.encode('utf-8')
                            mainApp.serverSocket.send(header + encMessage)
                            mainApp.sendMessageQueue.remove(message)
                            print('all should be good')
                        except Exception as e:
                            print(e)
                    else:
                        AppScreen.getSharedSecret(recieverId)
                        print('no shared key')

            for message in mainApp.recieveMessageQueue:
                print('there should be message here for recieveing')
                recieverId = int(message.split(' ',1)[0].strip())
                if recieverId not in mainApp.idSharedsecretMap:
                    AppScreen.getSharedSecret(recieverId)
                else:
                    if 'shared' in mainApp.idSharedsecretMap[recieverId]:
                        try:
                            msg = message[(len(str(recieverId))):].strip()
                            sharedSecret = mainApp.idSharedsecretMap[recieverId]['shared']
                            AESmsg = encryption.decrypt(msg, str(sharedSecret))
                            mainApp.idChatMap[recieverId] += '\n'
                            mainApp.idChatMap[recieverId] += mainApp.idNameMap[recieverId] + ': ' + AESmsg.decode('utf-8')
                            mainApp.recieveMessageQueue.remove(message)
                            if mainApp.currentActiveChat == recieverId:
                                mainApp.label.text = mainApp.idChatMap[recieverId]
                            else:
                                mainApp.active_users[recieverId].back_color = (1,0,0,1)
                        except Exception as e:
                            print(e)
                    else:
                        AppScreen.getSharedSecret(recieverId)

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
                            btn = SmoothButton(text = f'{name}', size_hint_y = None, height = 80, on_press = AppScreen.openPrivateChat)
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
                mainApp.recieveMessageQueue.append(message)

            elif header[0] == '3' or header[0] == '4':
                messageLenght = int(header[1:])
                message = mainApp.serverSocket.recv(messageLenght).decode('utf-8').strip()
                senderId = int(message.split(' ',1)[0].strip())
                key = message[(len(str(senderId))):].strip()
                if senderId not in mainApp.idSharedsecretMap:
                    mainApp.idSharedsecretMap[senderId] = {'public': int(key)}
                else:
                    mainApp.idSharedsecretMap[senderId]['public'] = int(key)
                AppScreen.getSharedSecret(senderId)

            elif header[0] == '5':
                messageLenght = int(header[1:])
                message = mainApp.serverSocket.recv(messageLenght).decode('utf-8').strip()
                mainApp.myId = int(message)
                print('my id is: ' + message)
                return

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
            else:
                mainApp.globalChatBtn.back_color = (1,0,0,1)

        except Exception as e:
            if type(e) is ConnectionResetError:
                AppScreen.connectionAborted(e)
            elif type(e) is ssl.SSLWantReadError:
                return

    def connectionAborted(e):
        mainApp.screenManager.current = 'Loading'
        mainApp.loadingText.text = 'Connection aborted by server'
        AppScreen.removeLocalInfo(e)

    def removeLocalInfo(e):
        mainApp.serverSocket.close()
        del mainApp.serverSocket
        Clock.unschedule(mainApp.mainLoopSchedule)
        Clock.unschedule(mainApp.getOnlineUsers)
        mainApp.label.text = ''

    def disconnect(self):
        AppScreen.removeLocalInfo(self)
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
            mainApp.sendMessageQueue.append(newMsg)
            print(mainApp.sendMessageQueue)


    def getOnlineUsers(time):
        command = 'getOnlineUsers'
        commandHeader = f'1{len(command):<{HEADERSIZE-1}}'.encode('utf-8')
        command = command.encode('utf-8')
        mainApp.serverSocket.send(commandHeader + command)
        print('request sent')

    @staticmethod
    def getMyId():
        header = f'50000000'.encode('utf-8')
        mainApp.serverSocket.send(header)

    def openPrivateChat(self):
        print('private chat opened from: ' + str(self.buttonId))
        self.back_color = (0.55,0.89,0.95,1)
        mainApp.label.text = mainApp.idChatMap[self.buttonId]
        mainApp.currentActiveChat = self.buttonId
        AppScreen.getSharedSecret(self.buttonId)

    def getSharedSecret(id):
        if id not in mainApp.idSharedsecretMap:
            myPrivateKey = encryption.genkey()
            mainApp.idSharedsecretMap[id] = {}
            mainApp.idSharedsecretMap[id]['private'] = myPrivateKey
            myPublicKey = encryption.curve25519(myPrivateKey)
            if mainApp.myId < id:
                msg = str(id) + ' ' + str(myPublicKey)
                encMessage = msg.encode('utf-8')
                header = f'3{len(msg):<{HEADERSIZE-1}}'.encode('utf-8')
                mainApp.serverSocket.send(header + encMessage)
            else:
                msg = str(id) + ' ' + str(myPublicKey)
                encMessage = msg.encode('utf-8')
                header = f'4{len(msg):<{HEADERSIZE-1}}'.encode('utf-8')
                mainApp.serverSocket.send(header + encMessage)
        else:
            if 'private' in mainApp.idSharedsecretMap[id]:
                if 'public' in mainApp.idSharedsecretMap[id]:
                    if 'shared' in mainApp.idSharedsecretMap[id]:
                        return
                    else:
                        myPrivate = mainApp.idSharedsecretMap[id]['private']
                        public = mainApp.idSharedsecretMap[id]['public']
                        mainApp.idSharedsecretMap[id]['shared'] = encryption.curve25519(myPrivate, public)
                        print('i got the shared key1:' + str(mainApp.idSharedsecretMap[id]['shared']))

            elif 'public' in mainApp.idSharedsecretMap[id]:
                myPrivateKey = encryption.genkey()
                publicKey = mainApp.idSharedsecretMap[id]['public']
                mainApp.idSharedsecretMap[id]['private'] = myPrivateKey
                mainApp.idSharedsecretMap[id]['shared'] = encryption.curve25519(myPrivateKey,publicKey)
                print('i got the shared key2:' + str(mainApp.idSharedsecretMap[id]['shared']))
                myPublicKey = encryption.curve25519(myPrivateKey)
                if mainApp.myId < id:
                    msg = str(id) + ' ' + str(myPublicKey)
                    encMessage = msg.encode('utf-8')
                    header = f'3{len(msg):<{HEADERSIZE-1}}'.encode('utf-8')
                    mainApp.serverSocket.send(header + encMessage)
                else:
                    msg = str(id) + ' ' + str(myPublicKey)
                    encMessage = msg.encode('utf-8')
                    header = f'4{len(msg):<{HEADERSIZE-1}}'.encode('utf-8')
                    mainApp.serverSocket.send(header + encMessage)

    def openGlobalChat(self):
        mainApp.label.text = mainApp.idChatMap[0]
        mainApp.globalChatBtn.back_color = (0.55,0.89,0.95,1)
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
