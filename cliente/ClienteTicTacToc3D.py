import httpx
from tkinter import *
from tkinter import messagebox
# Servidor URL, este debe coincidir con el del servidor
# A traves de esta URL el cliente se comunica con el servidor
SERVER_URL = "https://tic-tac-toe-0l0o.onrender.com"

# Asignar jugador al conectarse, accede al endpoint /assign
r = httpx.get(f"{SERVER_URL}/assign")
data = r.json() # Los json es el formato de intercambio de datos entre cliente y servidor
PLAYER_NAME = data["jugador"] # player1 o player2


# lista de botones, uno por cada casilla del tablero 4x4x4
botones = []
tablero = Tk()
tablero.title(f"Tic Tac Toe 3D - {PLAYER_NAME}")
tablero.resizable(0, 0)

# 🔹 Aquí ya existe tablero, ahora sí puedes crear el Label
label_estado = Label(tablero, text="", font='arial, 20')
label_estado.place(x=300, y=5)

# El messagebox es una ventana emergente para mostrar mensajes
# Si no se pudo asignar un jugador, significa que ya hay dos conectados
if PLAYER_NAME is None:
    messagebox.showerror("Error", "Ya hay dos jugadores conectados")
    exit()
# Al cerrar la ventana, desconectar del servidor
# Accede al endpoint /disconnect
def on_close():
    try:
        httpx.post(f"{SERVER_URL}/disconnect", json={"jugador": PLAYER_NAME})
    except Exception as e:
        print("Error al desconectar:", e)
    tablero.destroy()

# Asociar la función on_close al evento de cerrar la ventana
tablero.protocol("WM_DELETE_WINDOW", on_close)


def get_button_index(z, y, x):
    return (3 - z) * 16 + y * 4 + x
# Crear un botón para el tablero, igual que el código de base
def crearBoton(valor, i):
    return Button(tablero, text=valor, width=5, height=1, font=("Helvetica", 15),
                  command=lambda: botonClick(i))

# El principal cambio de está funcion es que ahora envía la jugada al servidor
# Ya el servidor se encarga de validar la jugada y actualizar el estado del juego
# La lógica del juego está en l servidor
def botonClick(i):
    z = 3 - (i // 16)
    y = (i % 16) // 4
    x = (i % 16) % 4

    # Enviar jugada al servidor
    r = httpx.post(f"{SERVER_URL}/play", json={
        "jugador": PLAYER_NAME,
        "x": x,
        "y": y,
        "z": z
    })

    print("Servidor:", r.text)

    # Actualizar tablero con el estado
    actualizar_tablero()

# Actualizar el tablero según el estado recibido del servidor
# Accede al endpoint /state, que devuelve el estado actual del juego
# El array "tablero" contiene las jugadas realizadas
def actualizar_tablero():
    r = httpx.get(f"{SERVER_URL}/state")
    state = r.json()

    jugadas = state["tablero"]
    turno = state["turno"]
    ganador = state["ganador"]
    linea = state.get("linea_ganadora")
    # Actualizar botones según jugadas, para que se visualice correctamente
    contador = 0
    for z in range(3, -1, -1):
        for y in range(4):
            for x in range(4):
                val = jugadas[z][y][x]
                if val == -1:
                    botones[contador].config(text="X", fg="blue", bg="white")
                elif val == 1:
                    botones[contador].config(text="O", fg="red", bg="white")
                else:
                    botones[contador].config(text=" ", bg="white")
                contador += 1
    # Comprobamos si la variable ganador tiene un valor
    # En ese caso mostramos el ganador y resaltamos la línea ganadora
    if ganador:
        label_estado.config(text=f"Ganador: {ganador}", fg="blue")
        if linea:
            for (z,y,x) in linea: # Se recorren las coordenadas de la línea ganadora
                idx = get_button_index(z, y, x)
                botones[idx].config(bg="red", fg="yellow") # resaltar línea ganadora, igual que en el código de base
    else:
        # Si no hay ganador, mostrar el turno actual
        label_estado.config(text=f"Turno: {turno}", fg="green")

# Función para preguntar si se quiere continuar o finalizar
# Accede al endpoint /reset o /disconnect según la elección
def seguir_o_finalizar():
    resp = messagebox.askyesno("FINALIZAR", "¿Quieres continuar?")
    if resp:
        httpx.post(f"{SERVER_URL}/reset")
        actualizar_tablero()
    else:
        try:
            httpx.post(f"{SERVER_URL}/disconnect", json={"jugador": PLAYER_NAME})
        except Exception as e:
            print("Error al desconectar:", e)
        tablero.destroy()
    return resp

# Está funcion refresca el tablero cada segundo, si no se usa está función
# el cliente no verá las jugadas del otro jugador hasta que él haga una jugada
def refrescar_periodicamente():
    actualizar_tablero() # actualizar el tablero
    tablero.after(1000, refrescar_periodicamente)  # cada 1 segundo



# --- Interfaz ---
# Generamos la interfaz gráfica igual que en el código de base
for b in range(64):
    botones.append(crearBoton(' ', b))
# El juego empieza cuando el se conecta y hace la primera jugada
contador = 0
for z in range(3, -1, -1):
    for y in range(4):
        for x in range(4):
            botones[contador].grid(row=y+z*4, column=x+(3-z)*4)
            contador += 1

botonexit = Button(tablero, text='Exit', width=5, height=1, font=("Helvetica", 15),
                   command=seguir_o_finalizar)
botonexit.grid(row=0, column=10)

# Inicializar tablero desde servidor
actualizar_tablero()

refrescar_periodicamente() # iniciar refresco periódico

tablero.mainloop()

