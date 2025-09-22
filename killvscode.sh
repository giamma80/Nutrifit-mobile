# Prima prova a chiudere VS Code normalmente
osascript -e 'quit app "Visual Studio Code"'

# Se non funziona, forza la chiusura
pkill -f "Visual Studio Code"
pkill -f "\.vscode/extensions"

