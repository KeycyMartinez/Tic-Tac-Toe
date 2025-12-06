#Cambio 1: Se importan lisbrerías para crear la Aplicación Web
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from fastapi import Body

app = FastAPI()
# CAMBIO 2: Se crea una clase que maneja el estado del juego en el servidor
class ServerTicTac:
    def __init__(self):
        # El servidor mantiene el estado del juego para todos los clientes
        self.last_message = None # Mensaje

        # El tablero ahora es compartido entre todos los clientes
        self.jugadas = [[[0 for _ in range(4)] for _ in range(4)] for _ in range(4)]

        # Turno actual: "player1" o "player2"
        self.turno_actual = "player1"

        # Ganador: None si no hay, "player1" o "player2" si alguien gana
        self.ganador = None

        # Contador de jugadas (para detectar empate)
        self.num_jugadas = 0

        # Combinaciones de direcciones para comprobar victoria (las 13 que ya tienes)
        self.C = [
            [1,1,0], [1,0,1], [0,1,1],
            [1,0,0], [1,-1,0], [0,0,1],
            [-1,0,1], [0,1,0], [0,1,-1],
            [0,-1,-1], [0,-1,0], [0,0,-1],
            [0,0,0]
        ]
        # Estas dos variables menajarán el las conexiones de los jugadores
        # Para que el servidor se  vaya liberando según salgan los jugadores
        self.player1_connected = False
        self.player2_connected = False

    # función del objeto encargado de resetear el juego
    def reset_game(self):
        # Reinicia todas las casillas a 0
        for z in range(4):
            for y in range(4):
                for x in range(4):
                    self.jugadas[z][y][x] = 0

        # Reinicia turno y estado
        self.turno_actual = "player1"
        self.ganador = None
        self.num_jugadas = 0

        return "Juego reiniciado. Turno de player1"
    # Se llamará a este metodo cada vez que un jugador haga un movimiento
    def play_move(self, jugador, x, y, z):
        if self.ganador:  # si ya hay ganador, no aceptar más jugadas
            return f"Juego terminado. Ganador: {self.ganador}"

        if jugador != self.turno_actual: # no es el turno del jugador
            return f"No es tu turno. Le toca a {self.turno_actual}"

        if self.jugadas[z][y][x] != 0: # casilla ocupada
            return "Casilla ocupada. Elige otra."

        # Realizar la jugada, después de las verificaciones ejecutamos la jugada
        valor = -1 if jugador == "player1" else 1
        self.jugadas[z][y][x] = valor
        self.num_jugadas += 1

        # y llamamos a la función que verifica si hay un ganador
        ganador = self.check_victory(jugador)
        if ganador: # si hay un ganador lo indicamos
            self.ganador = ganador
            return f"¡{ganador} ha ganado!"

        if self.num_jugadas == 64: # si se han hecho 64 jugadas y no hay ganador, es empate
            self.ganador = "empate"
            return "Empate. No quedan casillas."

        self.turno_actual = "player2" if jugador == "player1" else "player1"
        return f"Jugada aceptada. Turno de {self.turno_actual}"

    # Verifica si hay un ganador
    def check_victory(self, jugador):
        # Se recorren todas las posibles líneas ganadoras, buscando 4 en línea
        target = -1 if jugador == "player1" else 1
        directions = [
            (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (1, 1, 0), (1, 0, 1), (0, 1, 1),
            (1, -1, 0), (1, 0, -1), (0, 1, -1),
            (1, 1, 1), (1, -1, 1), (1, 1, -1), (1, -1, -1)
        ]
        # Recorremos cada celda del tablero como posible inicio de línea ganadora
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
                                return jugador
        return None # si no hay ganador retornamos None
    # Método para obtener el estado actual del juego
    def get_state(self):
        return {
            "tablero": self.jugadas, # el estado del tablero
            "turno": self.turno_actual, # el turno actual
            "ganador": self.ganador, # el ganador si lo hay
            "linea_ganadora": getattr(self, "linea_ganadora", None) # línea ganadora si la hay
        }

    def is_game_over(self):
        return self.ganador is not None or self.num_jugadas == 64 # juego terminado



# Instancia única del servidor
server = ServerTicTac()
# CCAMBIO 3: Se crean los endpoints para que los clientes puedan interactuar con el servidor
# La clase Move define el formato de los datos que se envían al servidor para hacer una jugada
class Move(BaseModel):
    jugador: str
    x: int
    y: int
    z: int

# Endpoint para realizar una jugada, simplementa llama al método play_move del servidor, pasándole los datos recibidos
@app.post("/play")
def play(move: Move):
    return server.play_move(move.jugador, move.x, move.y, move.z)

# Endpoint para obtener el estado actual del juego
@app.get("/state")
def state():
    return server.get_state()

# Endpoint para reiniciar el juego
@app.post("/reset")
def reset():
    return server.reset_game()

# Endpoint para asignar jugador, devuelve "player1" o "player2" o None si ya hay dos jugadores conectados
#Según se conecten los clientes, se les asigna un jugador
@app.get("/assign")
def assign():
    if not hasattr(server, "player1_connected"):
        server.player1_connected = False
        server.player2_connected = False

    if not server.player1_connected:
        server.player1_connected = True
        return {"jugador": "player1"}
    elif not server.player2_connected:
        server.player2_connected = True
        return {"jugador": "player2"}
    else:
        return {"jugador": None, "error": "Ya hay dos jugadores conectados"}

# Endpoint para desconectar un jugador
# La clase Disconnect define el formato de los datos que se envían al servidor para desconectar un jugador
class Disconnect(BaseModel):
    jugador: str
@app.post("/disconnect")
def disconnect(payload: Disconnect):
    jugador = payload.jugador
    if jugador == "player1":
        server.player1_connected = False
    elif jugador == "player2":
        server.player2_connected = False
    return {"status": "disconnected", "jugador": jugador}