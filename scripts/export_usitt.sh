#!/bin/bash
# Автоматический экспорт USITT ASCII из EOS Nomad через osascript
# Сохраняет файл в /Users/ts/eos-assistant/exports/

EXPORT_DIR="/Users/ts/eos-assistant/exports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
EXPORT_FILE="$EXPORT_DIR/usitt_$TIMESTAMP.txt"

mkdir -p "$EXPORT_DIR"

osascript <<EOF
-- Активируем EOS
tell application "Eos Family Welcome Screen" to activate
delay 1.5

tell application "System Events"
    tell process "Eos Family Welcome Screen"
        -- File меню
        click menu item "File" of menu bar 1
        delay 0.5

        -- Export подменю
        tell menu item "Export" of menu "File" of menu bar 1
            click
        end tell
        delay 0.5

        -- USITT ASCII пункт
        click menu item "USITT ASCII..." of menu "Export" of menu item "Export" of menu "File" of menu bar 1
        delay 1.5

        -- В диалоге сохранения — вводим путь
        -- Используем Cmd+Shift+G для перехода к папке
        keystroke "g" using {command down, shift down}
        delay 0.5
        keystroke "$EXPORT_FILE"
        delay 0.3
        keystroke return
        delay 0.3
        keystroke return
        delay 1.0
    end tell
end tell
EOF

if [ -f "$EXPORT_FILE" ]; then
    echo "SUCCESS:$EXPORT_FILE"
else
    # Попробуем найти последний созданный файл в папке
    LAST=$(ls -t "$EXPORT_DIR"/*.txt 2>/dev/null | head -1)
    if [ -n "$LAST" ]; then
        echo "SUCCESS:$LAST"
    else
        echo "ERROR: файл не найден"
    fi
fi
