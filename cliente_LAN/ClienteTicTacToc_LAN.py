import httpx
from tkinter import *
from tkinter import messagebox, simpledialog
import time
import threading
import socket
import json
from enum import Enum
import sys


# ============================================
# MODOS DE FUNCIONAMIENTO
# ============================================
class GameMode(Enum):
    HOST = 1
    CLIENT = 2
    STANDALONE = 3


# ============================================
# SERVIDOR EMBEBIDO (para modo HOST)
# ============================================
class EmbeddedServer:
    def __init__(self):
        self.jugadas = [[[0 for _ in range(4)] for _ in range(4)] for _ in range(4)]
        self.turno_actual = "player1"
        self.ganador = None
        self.num_jugadas = 0
        self.linea_ganadora = None
        self.player1_connected = False
        self.player2_connected = False
        self.server_socket = None
        self.running = False

    def start_server(self, port=8000):
        """Inicia un servidor HTTP simple en un hilo"""
        import http.server
        import socketserver
        import urllib.parse

        class GameHTTPHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/assign':
                    self.handle_assign()
                elif self.path == '/state':
                    self.handle_state()
                else:
                    self.send_error(404)

            def do_POST(self):
                if self.path == '/play':
                    self.handle_play()
                elif self.path == '/reset':
                    self.handle_reset()
                elif self.path == '/disconnect':
                    self.handle_disconnect()
                else:
                    self.send_error(404)

            def handle_assign(self):
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

            def handle_state(self):
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

            def handle_play(self):
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

            def handle_reset(self):
                self.server.game_server.reset_game()
                self.send_response(200)
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

            def handle_disconnect(self):
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
                pass  # Silenciar logs

        class ThreadingHTTPServer(http.server.ThreadingHTTPServer):
            def __init__(self, server_address, RequestHandlerClass, game_server):
                super().__init__(server_address, RequestHandlerClass)
                self.game_server = game_server

        try:
            self.running = True
            server = ThreadingHTTPServer(('0.0.0.0', port), GameHTTPHandler, self)
            self.server_socket = server

            # Obtener y mostrar la IP local
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            print(f"Servidor iniciado en http://{local_ip}:{port}")
            print(f"Comparte esta IP con el otro jugador: {local_ip}")

            server.serve_forever()
        except Exception as e:
            print(f"Error en servidor: {e}")
        finally:
            self.running = False

    def stop_server(self):
        if self.server_socket:
            self.server_socket.shutdown()
            self.server_socket.server_close()

    def play_move(self, jugador, x, y, z):
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

        if self.num_jugadas == 64:
            self.ganador = "empate"
            return "Empate. No quedan casillas."

        self.turno_actual = "player2" if jugador == "player1" else "player1"
        return f"Jugada aceptada. Turno de {self.turno_actual}"

    def check_victory(self, jugador):
        target = -1 if jugador == "player1" else 1
        directions = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, 0, 1), (0, 1, 1),
            (1, -1, 0), (1, 0, -1), (0, 1, -1),
            (1, 1, 1), (1, -1, 1), (1, 1, -1), (1, -1, -1)
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
                                self.linea_ganadora = coords
                                return True
        return False

    def reset_game(self):
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
# INTERFAZ DE USUARIO (Común para todos los modos)
# ============================================
class TicTacToeGUI:
    def __init__(self, mode, server_url=None):
        self.mode = mode
        self.server_url = server_url
        self.embedded_server = None
        self.server_thread = None

        if mode == GameMode.HOST:
            self.start_embedded_server()
            self.server_url = "http://localhost:8000"

        self.conectar_al_juego()
        self.crear_interfaz()

    def start_embedded_server(self):
        """Inicia el servidor embebido en un hilo separado"""
        self.embedded_server = EmbeddedServer()
        self.server_thread = threading.Thread(
            target=self.embedded_server.start_server,
            daemon=True
        )
        self.server_thread.start()
        time.sleep(1)  # Esperar a que el servidor se inicie

    def conectar_al_juego(self):
        """Conecta al servidor (local o remoto)"""
        for intento in range(5):
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

        messagebox.showerror("Error", "No se pudo conectar al servidor")
        exit()

    def crear_interfaz(self):
        """Crea la interfaz gráfica"""
        self.botones = []
        self.tablero = Tk()
        self.tablero.title(f"Tic Tac Toe 3D - {self.PLAYER_NAME} ({self.mode.name})")
        self.tablero.resizable(0, 0)

        # Label de estado
        self.label_estado = Label(self.tablero, text="", font='arial, 20')
        self.label_estado.place(x=300, y=5)

        # Botón de salida
        self.botonexit = Button(self.tablero, text='Exit', width=5, height=1,
                                font=("Helvetica", 15), command=self.seguir_o_finalizar)
        self.botonexit.grid(row=0, column=10)

        # Crear botones del tablero
        for b in range(64):
            self.botones.append(self.crearBoton(' ', b))

        # Posicionar botones
        contador = 0
        for z in range(3, -1, -1):
            for y in range(4):
                for x in range(4):
                    self.botones[contador].grid(row=y + z * 4, column=x + (3 - z) * 4)
                    contador += 1

        # Configurar cierre
        self.tablero.protocol("WM_DELETE_WINDOW", self.on_close)

        # Inicializar y refrescar
        self.actualizar_tablero()
        self.refrescar_periodicamente()

    def crearBoton(self, valor, i):
        return Button(self.tablero, text=valor, width=5, height=1,
                      font=("Helvetica", 15), command=lambda: self.botonClick(i))

    def get_button_index(self, z, y, x):
        return (3 - z) * 16 + y * 4 + x

    def botonClick(self, i):
        z = 3 - (i // 16)
        y = (i % 16) // 4
        x = (i % 16) % 4

        try:
            r = httpx.post(f"{self.server_url}/play", json={
                "jugador": self.PLAYER_NAME,
                "x": x,
                "y": y,
                "z": z
            }, timeout=2.0)
            print("Servidor:", r.text)
        except Exception as e:
            print(f"Error al enviar jugada: {e}")

        self.actualizar_tablero()

    def actualizar_tablero(self):
        try:
            r = httpx.get(f"{self.server_url}/state", timeout=2.0)
            state = r.json()

            jugadas = state["tablero"]
            turno = state["turno"]
            ganador = state["ganador"]
            linea = state.get("linea_ganadora")

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
                    for (z, y, x) in linea:
                        idx = self.get_button_index(z, y, x)
                        self.botones[idx].config(bg="red", fg="yellow")
            else:
                self.label_estado.config(text=f"Turno: {turno}", fg="green")

        except Exception as e:
            print(f"Error al actualizar tablero: {e}")

    def seguir_o_finalizar(self):
        resp = messagebox.askyesno("FINALIZAR", "¿Quieres continuar?")
        if resp:
            try:
                httpx.post(f"{self.server_url}/reset")
                self.actualizar_tablero()
            except:
                pass
        else:
            self.on_close()

    def on_close(self):
        try:
            httpx.post(f"{self.server_url}/disconnect",
                       json={"jugador": self.PLAYER_NAME})
        except:
            pass

        if self.embedded_server:
            self.embedded_server.stop_server()

        self.tablero.destroy()

    def refrescar_periodicamente(self):
        self.actualizar_tablero()
        self.tablero.after(1000, self.refrescar_periodicamente)

    def run(self):
        self.tablero.mainloop()


# ============================================
# FUNCIÓN PRINCIPAL
# ============================================
def main():
    # Crear ventana de selección de modo
    root = Tk()
    root.withdraw()  # Ocultar ventana principal temporalmente

    # Preguntar modo de juego
    choice = messagebox.askquestion("Modo de Juego",
                                    "¿Quieres HOSTEAR una partida?\n\n"
                                    "Sí = Crear partida (otros se conectan a ti)\n"
                                    "No = Unirse a partida existente")

    mode = None
    server_url = None

    if choice == 'yes':  # Modo HOST
        mode = GameMode.HOST
        # Mostrar información de conexión
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        messagebox.showinfo("Información del Host",
                            f"Tu IP es: {local_ip}\n\n"
                            f"Comparte esta IP con el otro jugador.\n"
                            f"El juego se iniciará automáticamente.")
        server_url = f"http://{local_ip}:8000"
    else:  # Modo CLIENTE
        mode = GameMode.CLIENT
        # Pedir IP del host
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