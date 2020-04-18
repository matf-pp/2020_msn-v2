import socket
import ssl
import select

HEADERSIZE = 8
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile="cert.pem",keyfile="cert.pem")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0) as sckt:
    with context.wrap_socket(sckt, server_side=True) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('127.0.0.1',8443))
        sock.listen()
        sockets_list = [sock]
        clients = {}
        mapSocketId = {}
        userIdCounter = 1

        def receive_message(client_socket):
            try:
                message_header = client_socket.recv(HEADERSIZE)
                if not len(message_header):
                    return False
                header = message_header.decode('utf-8').strip()
                print(header)
                if header[0] == '1':
                    print('got a command from client')
                    command_lenght = int(header[1:])
                    command = client_socket.recv(command_lenght).decode('utf-8').strip()
                    print(command)
                    if command == 'getOnlineUsers':
                        getOnlineUsers(client_socket)
                    return 1
                elif header[0] == '0':
                    message_lenght = int(header[1:])
                    return {'header': message_header, 'data': client_socket.recv(message_lenght)}
            
            except:
                return False

        def getOnlineUsers(client_socket):
            clientList = 'clientList'
            for key in clients:
                output = f' {mapSocketId[key]},{clients[key]["data"].decode("utf-8")}'
                clientList += output
            responseHeader = f'1{len(clientList):<{HEADERSIZE-1}}'.encode('utf-8')
            response = clientList.encode('utf-8')
            print(response)
            client_socket.send(responseHeader + response)
            
        while True:
            read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)
            for notified_socket in read_sockets:
                if notified_socket == sock:
                    client_socket, client_address = sock.accept()
                    user = receive_message(client_socket)
                    if user is 1:
                        continue
                    elif user is False:
                        continue
                    sockets_list.append(client_socket)
                    clients[client_socket] = user
                    mapSocketId[client_socket] = userIdCounter
                    userIdCounter += 1
                else:
                    message = receive_message(notified_socket)
                    if message is 1:
                        continue
                    elif message is False:
                        sockets_list.remove(notified_socket)
                        del clients[notified_socket]
                        continue
                    user = clients[notified_socket]
                    for client_socket in clients:
                        if client_socket != notified_socket:
                            client_socket.send(user['header'] + user['data'] + message['header'] + message['data'])
            
            for notified_socket in exception_sockets:
                sockets_list.remove(notified_socket)
                del clients[notified_socket]