# Sistema de Confirmación Automática de Citas Médicas

Evaluación Final Transversal — **CUY5132 Comunicaciones Unificadas**
Duoc UC — Ingeniería en Conectividad y Redes

## Contexto

La Clínica Regional "Salud Integral" enfrenta un 30% de ausencias en sus citas programadas (no-show), producto de un proceso de confirmación manual, ineficiente y sin registro automatizado. Este proyecto implementa un sistema que llama automáticamente al paciente, le informa los datos de su cita mediante una voz generada por IA, captura su respuesta (confirmar / cancelar / reprogramar) vía DTMF, y deja registro en una base de datos — todo con soluciones open-source y capa gratuita de servicios cloud.

Adicionalmente, se implementó un agente conversacional (Slack + n8n + IA) que permite consultar el estado de una cita por chat, reutilizando la misma base de datos.

## Arquitectura

```
Paciente / Softphone
        │  SIP/TLS (5061)
        ▼
   SBC — Kamailio  ───────────────┐
   (IP pública, único expuesto)   │  también aloja:
        │  SIP/UDP (5060,          │  - rtpengine (relay RTP)
        │   interno, SG-restricted)│  - n8n + nginx + Certbot
        ▼                         │
   PBX — Asterisk (Docker)        │
   (sin IP pública)               │
        │                         │
        ├── Script AGI (Python) ──┼── Google Sheets API (BD de citas)
        └── Script AGI (Python) ──┴── ElevenLabs API (TTS dinámico)

Slack ──── webhook HTTPS ──── n8n (Code → HTTP Request → AI Agent/OpenRouter → Send message)
                                        │
                                        └── misma API de Google Sheets
```

Dos instancias EC2 (AWS, capa gratuita), misma VPC:
- **vm-pbx**: Asterisk dockerizado, sin IP pública — solo accesible desde el SBC.
- **vm-sbc**: Kamailio (SBC + TLS + enrutamiento), rtpengine (relay de medios) y n8n (agente conversacional), con IP pública fija (Elastic IP).

## Stack técnico

| Componente | Tecnología |
|---|---|
| Central telefónica | Asterisk 22 (Docker) |
| Session Border Controller | Kamailio 5.7 |
| Relay de medios (RTP) | rtpengine |
| Base de datos de citas | Google Sheets + Apps Script (API REST) |
| Text-to-Speech | ElevenLabs API (`eleven_turbo_v2_5`) |
| Automatización / agente IA | n8n + Slack API + OpenRouter |
| Infraestructura | AWS EC2 (Ubuntu 24.04), Security Groups, Elastic IP |

## Estructura del repositorio

```
├── asterisk/
│   ├── extensions.conf      # Dialplan: contexto confirmacion-citas
│   └── pjsip.conf           # Extensiones SIP (contraseñas censuradas)
├── kamailio/
│   ├── kamailio.cfg         # Enrutamiento SIP, TLS, htable, rtpengine
│   └── rtpengine.conf       # Relay de medios
├── agi-scripts/
│   └── confirmacion.py      # Script AGI: BD, TTS, DTMF, logs
├── google-apps-script/
│   └── Code.gs              # API REST sobre Google Sheets (BD de citas)
├── n8n/
│   └── workflow.json        # Flujo exportado: Slack → IA → Slack
└── docs/
    └── diagrama-arquitectura.png
```

## Variables de entorno requeridas

El script AGI y el contenedor de Asterisk requieren:

```bash
ELEVENLABS_API_KEY=<tu_api_key_de_elevenlabs>
```

Nunca se debe hardcodear esta clave en el código fuente.

## Despliegue resumido

1. Aprovisionar 2 instancias EC2 con los Security Groups descritos en el informe técnico.
2. Desplegar Asterisk en Docker sobre `vm-pbx`, aplicar `asterisk/*.conf`.
3. Copiar `agi-scripts/confirmacion.py` a `/var/lib/asterisk/agi-bin/`, dar permisos de ejecución.
4. Instalar Kamailio + rtpengine en `vm-sbc`, aplicar `kamailio/*.conf` y `kamailio/rtpengine.conf`, generar certificado TLS.
5. Publicar `google-apps-script/Code.gs` como Web App en Google Sheets.
6. Desplegar n8n (Docker + nginx + Certbot) sobre `vm-sbc`, importar `n8n/workflow.json`, configurar credenciales de Slack y OpenRouter.

Instrucciones detalladas paso a paso en el informe técnico entregado junto a este repositorio.

## Autor

Cristopher López — Ingeniería en Conectividad y Redes, Duoc UC

## Declaración de uso de IA

Este proyecto fue desarrollado con apoyo de Claude (Anthropic) como asistente técnico para configuración, diagnóstico de errores y documentación. Todas las implementaciones y pruebas fueron ejecutadas por el autor sobre su propia infraestructura.
