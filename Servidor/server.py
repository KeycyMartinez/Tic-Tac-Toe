from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from fastapi import Body

app = FastAPI()

class ServerTicTac:
    def __init__(self):
        self.last_message = None # Mensaje

        # Estado del tablero: 4x4x4, 0 = vacío, -1 = jugador1, 1 = jugador2
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
        # 🔹 Añadir estas líneas:
        self.player1_connected = False
        self.player2_connected = False

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

    def play_move(self, jugador, x, y, z):
        if self.ganador:  # si ya hay ganador, no aceptar más jugadas
            return f"Juego terminado. Ganador: {self.ganador}"

        if jugador != self.turno_actual:
            return f"No es tu turno. Le toca a {self.turno_actual}"

        if self.jugadas[z][y][x] != 0:
            return "Casilla ocupada. Elige otra."

        valor = -1 if jugador == "player1" else 1
        self.jugadas[z][y][x] = valor
        self.num_jugadas += 1

        ganador = self.check_victory(jugador)
        if ganador:
            self.ganador = ganador
            return f"¡{ganador} ha ganado!"

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
                                return jugador
        return None

    def get_state(self):
        return {
            "tablero": self.jugadas,
            "turno": self.turno_actual,
            "ganador": self.ganador,
            "linea_ganadora": getattr(self, "linea_ganadora", None)
        }

    def is_game_over(self):
        return self.ganador is not None or self.num_jugadas == 64



# Instancia única del servidor
server = ServerTicTac()

class Move(BaseModel):
    jugador: str
    x: int
    y: int
    z: int

@app.post("/play")
def play(move: Move):
    return server.play_move(move.jugador, move.x, move.y, move.z)

@app.get("/state")
def state():
    return server.get_state()

@app.post("/reset")
def reset():
    return server.reset_game()


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