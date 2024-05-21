import socket
import ssl
import threading

# Definir variables
puerto = 5000
host = "0.0.0.0"  # Escuchar en todas las interfaces de red
subastas_activas = {}  # Diccionario para almacenar subastas activas
lock = threading.Lock()  # Bloqueo para sincronización

# Configurar SSL
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile="cert.pem", keyfile="key.pem")

# Crear socket y enlazarlo
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((host, puerto))
server_socket.listen(5)

clientes_conectados = []

# Clase para representar una subasta
class Subasta:
    def __init__(self, nombre, puja_inicial):
        self.nombre = nombre
        self.puja_actual = puja_inicial
        self.mejor_postor = None
        self.clientes = []
        self.timer = None

    def startTimer(self, durationInSeconds):
        def terminarSubasta():
            # Notificar a los clientes que la subasta ha terminado
            for cliente in self.clientes:
                cliente.enviarMensaje("¡La subasta ha terminado!")

            # Determinar el ganador y enviar el mensaje correspondiente
            ganador = None
            pujaGanadora = 0
            for cliente in self.clientes:
                if cliente.puja_actual > pujaGanadora:
                    ganador = cliente
                    pujaGanadora = cliente.puja_actual

            if ganador:
                mensaje_ganador = f"¡Felicidades! Ganaste la subasta {self.nombre} con una puja de {pujaGanadora}"
                mensaje_perdedor = f"La subasta {self.nombre} ha terminado. El ganador es {ganador.nombre} con una puja de {pujaGanadora}"
                for cliente in self.clientes:
                    if cliente == ganador:
                        cliente.enviarMensaje(mensaje_ganador)
                    else:
                        cliente.enviarMensaje(mensaje_perdedor)
            else:
                mensaje_sin_ganador = f"La subasta {self.nombre} ha terminado sin ganador."
                for cliente in self.clientes:
                    cliente.enviarMensaje(mensaje_sin_ganador)

            # Eliminar la subasta de la lista de subastas activas
            with lock:
                del subastas_activas[self.nombre]

        # Inicia el temporizador
        self.timer = threading.Timer(durationInSeconds, terminarSubasta)
        self.timer.start()

# Clase para representar un cliente
class Cliente:
    def __init__(self, socket, nombre):
        self.socket = socket
        self.nombre = nombre
        self.puja_actual = 0

    def enviarMensaje(self, mensaje):
        self.socket.send(mensaje.encode("utf-8"))

    def recibirMensaje(self):
        return self.socket.recv(1024).decode("utf-8")

# Función para manejar cada cliente conectado
def manejar_cliente(cliente):
    comandos_disponibles = """
Comandos disponibles:
- UNIRSE: Unirse a una subasta activa
- PUJAR: Pujar en la subasta actual (ej. PUJAR:100)
- LISTAR: Listar subastas activas
- CREAR: Crear una nueva subasta
- TERMINAR: Terminar una subasta existente
- SALIR: Salir de la subasta y desconectarse
"""
    cliente.enviarMensaje(comandos_disponibles)
    subasta_actual = None  # Almacenar la subasta actual a la que el cliente se ha unido
    while True:
        try:
            mensaje = cliente.recibirMensaje().strip()
            if not mensaje:
                continue

            partes_mensaje = mensaje.split(":")
            comando = partes_mensaje[0].strip().upper()
            argumento = partes_mensaje[1].strip() if len(partes_mensaje) > 1 else None

            if comando == "UNIRSE":
                if not subastas_activas:
                    cliente.enviarMensaje("No hay subastas activas para unirse")
                else:
                    mensaje_subastas = "Subastas activas:\n"
                    for nombre_subasta in subastas_activas:
                        mensaje_subastas += f"- {nombre_subasta}\n"
                    cliente.enviarMensaje(mensaje_subastas)
                    cliente.enviarMensaje("Elige a qué subasta deseas unirte: ")
                    subasta_elegida = cliente.recibirMensaje().strip()
                    if subasta_elegida in subastas_activas:
                        subasta_actual = subastas_activas[subasta_elegida]  # Actualizar la subasta actual del cliente
                        with lock:
                            subasta_actual.clientes.append(cliente)
                        cliente.enviarMensaje(f"Te has unido a la subasta {subasta_elegida}")
                    else:
                        cliente.enviarMensaje(f"La subasta '{subasta_elegida}' no existe")

            elif comando == "PUJAR":
                if subasta_actual:
                    if argumento:
                        puja = int(argumento)
                        if puja > subasta_actual.puja_actual:
                            with lock:
                                subasta_actual.puja_actual = puja
                                subasta_actual.mejor_postor = cliente
                            mensaje_puja = f"{cliente.nombre} ha pujado {puja} en la subasta {subasta_actual.nombre}"
                            for otro_cliente in subasta_actual.clientes:
                                if otro_cliente != cliente:
                                    otro_cliente.enviarMensaje(mensaje_puja)
                        else:
                            cliente.enviarMensaje("La puja debe ser mayor que la puja actual")
                    else:
                        cliente.enviarMensaje("Debe ingresar un valor de puja")
                else:
                    cliente.enviarMensaje("Debes unirte a una subasta antes de pujar")

            elif comando == "LISTAR":
                if subastas_activas:
                    mensaje_listar = "Subastas activas:\n"
                    for nombre_subasta, subasta in subastas_activas.items():
                        mensaje_listar += f"- {nombre_subasta}: Puja actual: {subasta.puja_actual}\n"
                    cliente.enviarMensaje(mensaje_listar)
                else:
                    cliente.enviarMensaje("No hay subastas activas")

            elif comando == "CREAR":
                cliente.enviarMensaje("Nombre de la subasta: ")
                nombre_subasta = cliente.recibirMensaje().strip()
                if nombre_subasta:
                    if nombre_subasta not in subastas_activas:
                        with lock:
                            subastas_activas[nombre_subasta] = Subasta(nombre_subasta, 0)
                        cliente.enviarMensaje(f"Se ha creado la subasta de {nombre_subasta}")
                    else:
                        cliente.enviarMensaje(f"Ya existe una subasta con el nombre '{nombre_subasta}'")
                else:
                    cliente.enviarMensaje("Nombre de la subasta no válido")

            elif comando == "TERMINAR":
                if argumento in subastas_activas:
                    subastas_activas[argumento].timer.cancel()
                    cliente.enviarMensaje(f"La subasta '{argumento}' ha sido terminada")
                else:
                    cliente.enviarMensaje(f"La subasta '{argumento}' no existe")

            elif comando == "SALIR":
                cliente.enviarMensaje("DESCONEXIÓN")
                cliente.socket.close()
                clientes_conectados.remove(cliente)
                print(f"[DESCONEXIÓN] Cliente {cliente.nombre} desconectado")
                break

            else:
                cliente.enviarMensaje(f"Comando desconocido: {comando}")

        except Exception as e:
            print(f"[ERROR] {e}")
            cliente.socket.close()
            clientes_conectados.remove(cliente)
            break

# Bucle principal para aceptar nuevos clientes
while True:
    try:
        cliente_socket, address = server_socket.accept()
        cliente_socket_ssl = context.wrap_socket(cliente_socket, server_side=True)
        nombre_usuario = cliente_socket_ssl.recv(1024).decode("utf-8")
        nuevo_cliente = Cliente(cliente_socket_ssl, nombre_usuario)
        clientes_conectados.append(nuevo_cliente)

        hilo_cliente = threading.Thread(target=manejar_cliente, args=(nuevo_cliente,))
        hilo_cliente.start()
        print(f"[CONECTADO] Cliente {nombre_usuario} conectado desde {address}")
    except Exception as e:
        print(f"[ERROR] {e}")

# Cerrar el socket del servidor al final
server_socket.close()
