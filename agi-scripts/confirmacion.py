
#!/usr/bin/env python3
"""
confirmacion.py - AGI Script para Sistema de Confirmación de Citas
Clínica Regional "Salud Integral" - CUY5132 EFT 2025
Autor: Cristopher Lopez
Descripción: Gestiona el flujo de llamadas automáticas de confirmación,
             captura respuestas DTMF y actualiza la BD (Google Sheets).
"""

import sys
import os
import requests
import logging
from datetime import datetime

# ─── Configuración de logging ───────────────────────────────────────────────
logging.basicConfig(
    filename='/var/log/asterisk/confirmacion.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# ─── Configuración Google Sheets ────────────────────────────────────────────
SHEETS_API_URL = "https://script.google.com/macros/s/AKfycbwzNSF6IkAu4mguGURAnpNxSOK5xJL-UoobH_KfZoXwhjSLd15tN4b8PU-bj4zK8ICY/exec"

# ─── Configuración ElevenLabs TTS ───────────────────────────────────────────
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Voz gratuita
AUDIO_PATH = "/var/lib/asterisk/sounds/custom/mensaje_tts.wav"

# ─── Funciones AGI ──────────────────────────────────────────────────────────

def agi_send(command):
    """Envía un comando AGI a Asterisk y retorna la respuesta."""
    sys.stdout.write(command + "\n")
    sys.stdout.flush()
    return sys.stdin.readline().strip()

def agi_answer():
    """Contesta la llamada."""
    return agi_send("ANSWER")

def agi_hangup():
    """Cuelga la llamada."""
    return agi_send("HANGUP")

def agi_playback(filename):
    """Reproduce un archivo de audio."""
    return agi_send(f"EXEC Playback {filename}")

def agi_wait_dtmf(timeout=10):
    """Espera una tecla DTMF del usuario."""
    response = agi_send(f"WAIT FOR DIGIT {timeout * 1000}")
    if response.startswith("200"):
        parts = response.split("=")
        if len(parts) > 1:
            code = int(parts[1].strip().split()[0])
            if code > 0:
                return chr(code)
    return None

def agi_read_vars():
    """Lee variables del entorno AGI al inicio."""
    variables = {}
    while True:
        line = sys.stdin.readline().strip()
        if not line:
            break
        if ":" in line:
            key, value = line.split(":", 1)
            variables[key.strip()] = value.strip()
    return variables

# ─── Funciones de negocio ────────────────────────────────────────────────────

def obtener_cita(extension):
    """
    Consulta Google Sheets para obtener datos de la cita
    asociada a la extensión que recibe la llamada.
    """
    try:
        response = requests.get(
            SHEETS_API_URL,
            params={"action": "getCita", "extension": extension},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(f"Error consultando cita: {e}")
    return None

def actualizar_estado(cita_id, estado):
    """
    Actualiza el estado de la cita en Google Sheets.
    Estados: CONFIRMADA, CANCELADA, REPROGRAMAR
    """
    try:
        response = requests.post(
            SHEETS_API_URL,
            json={"action": "updateCita", "id": cita_id, "estado": estado},
            timeout=10
        )
        return response.status_code == 200
    except Exception as e:
        logging.error(f"Error actualizando cita {cita_id}: {e}")
        return False

def generar_audio_tts(texto):
    """
    Genera audio personalizado con ElevenLabs TTS.
    Convierte MP3 a WAV 8kHz mono para compatibilidad con Asterisk.
    """
    try:
        # Llamada a ElevenLabs API
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": texto,
                "model_id": "eleven_turbo_v2_5",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            # Guardar MP3 temporal
            mp3_path = "/var/lib/asterisk/sounds/custom/mensaje_tts.mp3"
            with open(mp3_path, "wb") as f:
                f.write(response.content)

            # Convertir a WAV 8kHz mono (requerido por Asterisk)
            os.system(
                f"ffmpeg -i {mp3_path} -ar 8000 -ac 1 "
                f"-acodec pcm_s16le {AUDIO_PATH} -y -loglevel quiet"
            )
            logging.info("Audio TTS generado correctamente")
            return True
    except Exception as e:
        logging.error(f"Error generando TTS: {e}")
    return False

# ─── Flujo principal ─────────────────────────────────────────────────────────

def main():
    """
    Flujo principal del AGI:
    1. Lee variables de entorno AGI
    2. Obtiene datos de la cita desde Google Sheets
    3. Genera mensaje personalizado con TTS ElevenLabs
    4. Reproduce el mensaje y captura respuesta DTMF
    5. Actualiza el estado en Google Sheets
    6. Registra el resultado en log
    """
    # Leer variables AGI
    agi_vars = agi_read_vars()
    extension = agi_vars.get("agi_callerid", "1001")

    logging.info(f"Llamada entrante desde extensión: {extension}")

    # Contestar llamada
    agi_answer()

    # Obtener datos de la cita
    cita = obtener_cita(extension)

    if not cita:
        logging.warning(f"No se encontró cita para extensión {extension}")
        agi_playback("custom/error_cita")
        agi_hangup()
        return

    cita_id = cita.get("id", "N/A")
    paciente = cita.get("paciente", "Paciente")
    especialidad = cita.get("especialidad", "Medicina General")
    fecha = cita.get("fecha", "sin fecha")
    hora = cita.get("hora", "sin hora")

    logging.info(f"Cita encontrada: ID={cita_id}, Paciente={paciente}")

    # Generar mensaje TTS personalizado
    mensaje = (
        f"Hola {paciente}. Le llamamos de la Clínica Salud Integral "
        f"para recordarle su cita de {especialidad} "
        f"el día {fecha} a las {hora}. "
        f"Presione 1 para confirmar su asistencia, "
        f"2 para cancelar la cita, "
        f"o 3 para solicitar reprogramación."
    )

    if generar_audio_tts(mensaje):
        agi_playback("custom/mensaje_tts")
    else:
        # Fallback a audio estático si TTS falla
        logging.warning("TTS falló, usando audio de respaldo")
        agi_playback("custom/mensaje_generico")

    # Capturar respuesta DTMF
    digito = agi_wait_dtmf(timeout=15)

    if digito == "1":
        estado = "CONFIRMADA"
        agi_playback("beep")
    elif digito == "2":
        estado = "CANCELADA"
        agi_playback("beep")
    elif digito == "3":
        estado = "REPROGRAMAR"
        agi_playback("beep")
    else:
        estado = "SIN_RESPUESTA"
        logging.warning(f"Sin respuesta DTMF para cita {cita_id}")

    # Actualizar estado en Google Sheets
    if actualizar_estado(cita_id, estado):
        logging.info(f"Cita {cita_id} actualizada: {estado}")
    else:
        logging.error(f"No se pudo actualizar cita {cita_id}")

    # Registrar resultado completo
    logging.info(
        f"RESULTADO | ID:{cita_id} | Paciente:{paciente} | "
        f"Estado:{estado} | Fecha:{datetime.now().isoformat()}"
    )

    agi_hangup()

if __name__ == "__main__":
    main()
