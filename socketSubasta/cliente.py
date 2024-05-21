import socket
import ssl
import threading

# Definir variables
puerto = 5000
host = "localhost"  # Cambia esto a la dirección IP del servidor

def recibir_mensajes(cliente_socket):
    while True:
        try:
            # Recibir mensaje del servidor
            mensaje = cliente_socket.recv(1024).decode("utf-8")
            if mensaje:
                print(mensaje)
            else:
                break
        except Exception as e:
            print(f"Se ha perdido la conexión con el servidor: {e}")
            break

def enviar_mensajes(cliente_socket):
    while True:
        try:
            # Leer mensaje del usuario
            mensaje_envio = input("> ").strip()
            if mensaje_envio:
                cliente_socket.send(mensaje_envio.encode("utf-8"))
        except Exception as e:
            print(f"Se ha producido un error: {e}")
            break

def main():
    context = ssl.create_default_context()
    context.check_hostname = False  # Deshabilita la verificación del nombre de host
    context.verify_mode = ssl.CERT_NONE  # No verifica el certificado del servidor (en desarrollo)

    try:
        cliente_socket = socket.create_connection((host, puerto))
        cliente_socket_ssl = context.wrap_socket(cliente_socket, server_hostname=host)
        print("Conexión establecida con el servidor.")

        # Enviar nombre de usuario al servidor
        nombre_usuario = input("Ingrese su nombre de usuario: ")
        cliente_socket_ssl.send(nombre_usuario.encode("utf-8"))

        # Crear hilos para manejar la recepción y el envío de mensajes
        hilo_recepcion = threading.Thread(target=recibir_mensajes, args=(cliente_socket_ssl,))
        hilo_recepcion.daemon = True
        hilo_recepcion.start()

        enviar_mensajes(cliente_socket_ssl)

    except Exception as e:
        print(f"No se pudo conectar al servidor: {e}")
    finally:
        if 'cliente_socket_ssl' in locals():
            cliente_socket_ssl.close()

if __name__ == "__main__":
    main()
