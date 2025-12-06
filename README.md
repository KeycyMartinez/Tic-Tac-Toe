# Tic-Tac-Toe
Proyecto Semestral - Tic Tac Toe

## **RESUMEN DE CAMBIOS PRINCIPALES:**

1. **Arquitectura Cliente-Servidor**: El juego original está toda la lógica en un archivo, ahora tiene separación clara entre cliente y servidor.

2. **Estado Compartido**: El servidor mantiene el estado único del juego que todos los clientes ven y modifican.

3. **Comunicación HTTP**: Reemplaza las llamadas a funciones locales por peticiones a una API REST.

4. **Múltiples Jugadores**: Soporta dos jugadores conectados desde diferentes máquinas.

5. **Sincronización**: El cliente actualiza periódicamente el estado desde el servidor.

6. **Gestión de Conexiones**: El servidor controla qué jugadores están conectados y asigna turnos.

7. **Validación en Servidor**: Toda la lógica de validación de jugadas se mueve al servidor para evitar trampas.

8. **Persistencia de Estado**: El juego continúa aunque un cliente se desconecte temporalmente.
