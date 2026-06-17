# Copy this file to config.py and fill in your values
# cp src/config.example.py src/config.py

EOS_IP        = "192.168.1.100"   # IP-адрес пульта ETC EOS (или Nomad на Mac)
EOS_OSC_PORT  = 8000              # UDP RX Port пульта (EOS принимает команды)
EOS_RX_PORT   = 8001              # UDP TX Port пульта (не используется в TCP режиме)
EOS_USER_ID   = 777               # OSC User ID (должен совпадать с настройкой в EOS)
WEB_PORT      = 5002              # Порт веб-интерфейса

ANTHROPIC_API_KEY = "sk-ant-..."  # Ключ Anthropic API (https://console.anthropic.com)
WHISPER_MODEL = "base"            # Модель Whisper: tiny / base / small / medium
