import httpx  # NUEVO: Librería para peticiones HTTP (no existía en el original)
from tkinter import *
from tkinter import messagebox, simpledialog  # NUEVO: simpledialog para entrada de IP
import time
import threading  # NUEVO: Para ejecutar servidor en segundo plano
import socket  # NUEVO: Para obtener IP local
import json  # NUEVO: Para comunicación JSON con servidor
from enum import Enum  # NUEVO: Para definir modos de juego
import sys


# ============================================
# MODOS DE FUNCIONAMIENTO - COMPLETAMENTE NUEVO
# ============================================
class GameMode(Enum):
    HOST = 1  # NUEVO: Crea partida y sirve como servidor
    CLIENT = 2  # NUEVO: Se conecta a un servidor remoto
    STANDALONE = 3  # NUEVO: No se usa en esta versión (reservado para futuro)


# ============================================
# SERVIDOR EMBEBIDO (para modo HOST) - COMPLETAMENTE NUEVO
# ============================================
class EmbeddedServer:
    def __init__(self):
        # CAMBIO: Estado del juego centralizado en servidor (antes eran variables globales)
        self.jugadas = [[[0 for _ in range(4)] for _ in range(4)] for _ in range(4)]
        self.turno_actual = "player1"  # CAMBIO: Nombres en inglés en lugar de "Jugador 1"
        self.ganador = None
        self.num_jugadas = 0  # NUEVO: Contador para detectar empates
        self.linea_ganadora = None  # NUEVO: Almacena coordenadas de la línea ganadora
        self.player1_connected = False  # NUEVO: Control de conexiones
        self.player2_connected = False  # NUEVO: Control de conexiones
        self.server_socket = None
        self.running = False

    def start_server(self, port=8000):
        """Inicia un servidor HTTP simple en un hilo - COMPLETAMENTE NUEVO"""
        import http.server
        import socketserver
        import urllib.parse

        class GameHTTPHandler(http.server.BaseHTTPRequestHandler):
            # NUEVO: Maneja peticiones GET del cliente
            def do_GET(self):
                if self.path == '/assign':  # NUEVO: Asigna jugador al conectarse
                    self.handle_assign()
                elif self.path == '/state':  # NUEVO: Obtiene estado del juego
                    self.handle_state()
                else:
                    self.send_error(404)

            # NUEVO: Maneja peticiones POST del cliente
            def do_POST(self):
                if self.path == '/play':  # NUEVO: Envía jugada
                    self.handle_play()
                elif self.path == '/reset':  # NUEVO: Reinicia juego
                    self.handle_reset()
                elif self.path == '/disconnect':  # NUEVO: Desconecta jugador
                    self.handle_disconnect()
                else:
                    self.send_error(404)

            def handle_assign(self):  # NUEVO: Asigna player1 o player2 al conectarse
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                if not self.server.game_server.player1_connected:
                    self.server.game_server.player1_connected = True
                    response = {"jugador": "player1"}
                elif not self.server.game_server.player2_connected:
                    self.server.game_server.player2_connected = True
                    response = {"jugador": "player2"}
                else:
                    response = {"jugador": None, "error": "Ya hay dos jugadores conectados"}

                self.wfile.write(json.dumps(response).encode())

            def handle_state(self):  # NUEVO: Devuelve estado completo del juego
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                state = {
                    "tablero": self.server.game_server.jugadas,
                    "turno": self.server.game_server.turno_actual,
                    "ganador": self.server.game_server.ganador,
                    "linea_ganadora": self.server.game_server.linea_ganadora
                }
                self.wfile.write(json.dumps(state).encode())

            def handle_play(self):  # NUEVO: Procesa una jugada
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)

                response_text = self.server.game_server.play_move(
                    data["jugador"], data["x"], data["y"], data["z"]
                )

                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response_text.encode())

            def handle_reset(self):  # NUEVO: Reinicia el juego
                self.server.game_server.reset_game()
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

            def handle_disconnect(self):  # NUEVO: Maneja desconexión de jugador
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)

                jugador = data["jugador"]
                if jugador == "player1":
                    self.server.game_server.player1_connected = False
                elif jugador == "player2":
                    self.server.game_server.player2_connected = False

                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

            def log_message(self, format, *args):
                pass  # Silenciar logs - NUEVO: No mostrar logs en consola

        class ThreadingHTTPServer(http.server.ThreadingHTTPServer):
            def __init__(self, server_address, RequestHandlerClass, game_server):
                super().__init__(server_address, RequestHandlerClass)
                self.game_server = game_server  # NUEVO: Pasa referencia al servidor del juego

        try:
            self.running = True
            server = ThreadingHTTPServer(('0.0.0.0', port), GameHTTPHandler, self)
            self.server_socket = server

            # NUEVO: Obtener y mostrar la IP local para compartir
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            print(f"Servidor iniciado en http://{local_ip}:{port}")
            print(f"Comparte esta IP con el otro jugador: {local_ip}")

            server.serve_forever()
        except Exception as e:
            print(f"Error en servidor: {e}")
        finally:
            self.running = False

    def stop_server(self):  # NUEVO: Detiene el servidor
        if self.server_socket:
            self.server_socket.shutdown()
            self.server_socket.server_close()

    def play_move(self, jugador, x, y, z):  # CAMBIO: Lógica centralizada en servidor
        if self.ganador:
            return f"Juego terminado. Ganador: {self.ganador}"

        if jugador != self.turno_actual:
            return f"No es tu turno. Le toca a {self.turno_actual}"

        if self.jugadas[z][y][x] != 0:
            return "Casilla ocupada. Elige otra."

        valor = -1 if jugador == "player1" else 1
        self.jugadas[z][y][x] = valor
        self.num_jugadas += 1

        if self.check_victory(jugador):
            return f"¡{jugador} ha ganado!"

        # NUEVO: Detección de empate
        if self.num_jugadas == 64:
            self.ganador = "empate"
            return "Empate. No quedan casillas."

        self.turno_actual = "player2" if jugador == "player1" else "player1"
        return f"Jugada aceptada. Turno de {self.turno_actual}"

    def check_victory(self, jugador):
        # CAMBIO COMPLETO: Reemplaza la matriz C de 13 patrones por algoritmo genérico
        target = -1 if jugador == "player1" else 1
        # NUEVO: 13 direcciones posibles (antes eran 13 patrones en matriz C)
        directions = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1),  # Ejes X, Y, Z
            (1, 1, 0), (1, 0, 1), (0, 1, 1),  # Diagonales en planos
            (1, -1, 0), (1, 0, -1), (0, 1, -1),  # Diagonales inversas
            (1, 1, 1), (1, -1, 1), (1, 1, -1), (1, -1, -1)  # Diagonales 3D
        ]

        for z in range(4):
            for y in range(4):
                for x in range(4):
                    if self.jugadas[z][y][x] == target:
                        for dz, dy, dx in directions:
                            coords = []
                            for i in range(4):
                                nz, ny, nx = z + dz * i, y + dy * i, x + dx * i
                                if 0 <= nz < 4 and 0 <= ny < 4 and 0 <= nx < 4:
                                    coords.append((nz, ny, nx))
                                else:
                                    break
                            if len(coords) == 4 and all(self.jugadas[nz][ny][nx] == target for nz, ny, nx in coords):
                                self.ganador = jugador
                                self.linea_ganadora = coords  # NUEVO: Guarda línea ganadora
                                return True
        return False

    def reset_game(self):  # Similar al inicio() original pero en servidor
        for z in range(4):
            for y in range(4):
                for x in range(4):
                    self.jugadas[z][y][x] = 0
        self.turno_actual = "player1"
        self.ganador = None
        self.num_jugadas = 0
        self.linea_ganadora = None
        return "Juego reiniciado. Turno de player1"


# ============================================
# INTERFAZ DE USUARIO (Común para todos los modos) - REESCRITO COMPLETAMENTE
# ============================================
class TicTacToeGUI:  # NUEVA CLASE: Reemplaza el código procedural original
    def __init__(self, mode, server_url=None):
        self.mode = mode  # NUEVO: Modo de juego (HOST o CLIENT)
        self.server_url = server_url
        self.embedded_server = None  # NUEVO: Referencia al servidor embebido
        self.server_thread = None  # NUEVO: Hilo del servidor

        if mode == GameMode.HOST:
            self.start_embedded_server()  # NUEVO: Inicia servidor si es host
            self.server_url = "http://localhost:8000"

        self.conectar_al_juego()  # NUEVO: Conecta al servidor
        self.crear_interfaz()

    def start_embedded_server(self):
        """Inicia el servidor embebido en un hilo separado - COMPLETAMENTE NUEVO"""
        self.embedded_server = EmbeddedServer()
        self.server_thread = threading.Thread(
            target=self.embedded_server.start_server,
            daemon=True  # NUEVO: Hilo demonio (se cierra con programa)
        )
        self.server_thread.start()
        time.sleep(1)  # Esperar a que el servidor se inicie

    def conectar_al_juego(self):
        """Conecta al servidor (local o remoto) - COMPLETAMENTE NUEVO"""
        for intento in range(5):  # NUEVO: Reintentos de conexión
            try:
                r = httpx.get(f"{self.server_url}/assign", timeout=5.0)
                r.raise_for_status()
                data = r.json()
                self.PLAYER_NAME = data.get("jugador")

                if self.PLAYER_NAME is None:
                    messagebox.showerror("Error", "Ya hay dos jugadores conectados")
                    exit()
                return
            except Exception as e:
                print(f"Intento {intento + 1} fallido: {e}")
                time.sleep(2)

        messagebox.showerror("Error", "No se pudo conectar alđ servidor")
        exit()

    def crear_interfaz(self):
        """Crea la interfaz gráfica - REESCRITO desde el original"""
        self.botones = []
        self.tablero = Tk()
        # CAMBIO: Título dinámico con modo y nombre de jugador
        self.tablero.title(f"Tic Tac Toe 3D - {self.PLAYER_NAME} ({self.mode.name})")
        self.tablero.resizable(0, 0)

        # CAMBIO: Label de estado único (antes había múltiples labels)
        self.label_estado = Label(self.tablero, text="", font='arial, 20')
        self.label_estado.place(x=300, y=5)

        # Botón de salida (similar al original)
        self.botonexit = Button(self.tablero, text='Exit', width=5, height=1,
                                font=("Helvetica", 15), command=self.seguir_o_finalizar)
        self.botonexit.grid(row=0, column=10)

        # Crear botones del tablero (similar al original)
        for b in range(64):
            self.botones.append(self.crearBoton(' ', b))

        # Posicionar botones (similar al original)
        contador = 0
        for z in range(3, -1, -1):
            for y in range(4):
                for x in range(4):
                    self.botones[contador].grid(row=y + z * 4, column=x + (3 - z) * 4)
                    contador += 1

        # NUEVO: Configurar cierre limpio
        self.tablero.protocol("WM_DELETE_WINDOW", self.on_close)

        # NUEVO: Inicializar y refrescar periódicamente
        self.actualizar_tablero()
        self.refrescar_periodicamente()

    def crearBoton(self, valor, i):  # Similar al original
        return Button(self.tablero, text=valor, width=5, height=1,
                      font=("Helvetica", 15), command=lambda: self.botonClick(i))

    def get_button_index(self, z, y, x):  # NUEVO: Calcula índice de botón
        return (3 - z) * 16 + y * 4 + x

    def botonClick(self, i):
        # CAMBIO: Ya no calcula X, Y, Z globales, solo envía jugada al servidor
        z = 3 - (i // 16)
        y = (i % 16) // 4
        x = (i % 16) % 4

        try:
            # NUEVO: Envía jugada al servidor via HTTP POST
            r = httpx.post(f"{self.server_url}/play", json={
                "jugador": self.PLAYER_NAME,
                "x": x,
                "y": y,
                "z": z
            }, timeout=2.0)
            print("Servidor:", r.text)
        except Exception as e:
            print(f"Error al enviar jugada: {e}")

        self.actualizar_tablero()  # Actualiza después de jugar

    def actualizar_tablero(self):  # NUEVO: Obtiene estado del servidor
        try:
            r = httpx.get(f"{self.server_url}/state", timeout=2.0)
            state = r.json()

            jugadas = state["tablero"]
            turno = state["turno"]
            ganador = state["ganador"]
            linea = state.get("linea_ganadora")  # NUEVO: Línea ganadora

            contador = 0
            for z in range(3, -1, -1):
                for y in range(4):
                    for x in range(4):
                        val = jugadas[z][y][x]
                        if val == -1:
                            self.botones[contador].config(text="X", fg="blue", bg="white")
                        elif val == 1:
                            self.botones[contador].config(text="O", fg="red", bg="white")
                        else:
                            self.botones[contador].config(text=" ", bg="white")
                        contador += 1

            if ganador:
                self.label_estado.config(text=f"Ganador: {ganador}", fg="blue")
                if linea:
                    # NUEVO: Resalta línea ganadora
                    for (z, y, x) in linea:
                        idx = self.get_button_index(z, y, x)
                        self.botones[idx].config(bg="red", fg="yellow")
            else:
                self.label_estado.config(text=f"Turno: {turno}", fg="green")

        except Exception as e:
            print(f"Error al actualizar tablero: {e}")

    def seguir_o_finalizar(self):  # Similar al original pero con comunicación HTTP
        resp = messagebox.askyesno("FINALIZAR", "¿Quieres continuar?")
        if resp:
            try:
                httpx.post(f"{self.server_url}/reset")  # NUEVO: Reinicia en servidor
                self.actualizar_tablero()
            except:
                pass
        else:
            self.on_close()

    def on_close(self):  # NUEVO: Maneja cierre limpio
        try:
            httpx.post(f"{self.server_url}/disconnect",
                       json={"jugador": self.PLAYER_NAME})  # NUEVO: Notifica desconexión
        except:
            pass

        if self.embedded_server:
            self.embedded_server.stop_server()  # NUEVO: Detiene servidor si es host

        self.tablero.destroy()

    def refrescar_periodicamente(self):  # NUEVO: Polling para actualizar estado
        self.actualizar_tablero()
        self.tablero.after(1000, self.refrescar_periodicamente)

    def run(self):  # NUEVO: Inicia la interfaz
        self.tablero.mainloop()


# ============================================
# FUNCIÓN PRINCIPAL - COMPLETAMENTE REESCRITA
# ============================================
def main():
    # NUEVO: Ventana de selección de modo
    root = Tk()
    root.withdraw()  # Ocultar ventana principal temporalmente

    # NUEVO: Preguntar modo de juego (antes comenzaba directamente)
    choice = messagebox.askquestion("Modo de Juego",
                                    "¿Quieres HOSTEAR una partida?\n\n"
                                    "Sí = Crear partida (otros se conectan a ti)\n"
                                    "No = Unirse a partida existente")

    mode = None
    server_url = None

    if choice == 'yes':  # Modo HOST
        mode = GameMode.HOST
        # NUEVO: Mostrar información de conexión
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        messagebox.showinfo("Información del Host",
                            f"Tu IP es: {local_ip}\n\n"
                            f"Comparte esta IP con el otro jugador.\n"
                            f"El juego se iniciará automáticamente.")
        server_url = f"http://{local_ip}:8000"
    else:  # Modo CLIENTE
        mode = GameMode.CLIENT
        # NUEVO: Pedir IP del host
        ip = simpledialog.askstring("Conectar a Partida",
                                    "Ingresa la IP del host:")
        if not ip:
            messagebox.showerror("Error", "Debes ingresar una IP")
            sys.exit(1)
        server_url = f"http://{ip}:8000"

    root.destroy()

    # Iniciar juego
    try:
        juego = TicTacToeGUI(mode, server_url)
        juego.run()
    except Exception as e:
        messagebox.showerror("Error", f"No se pudo iniciar el juego: {str(e)}")


# ============================================
# EJECUCIÓN
# ============================================
if __name__ == "__main__":
    main()