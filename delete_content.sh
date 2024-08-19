#!/bin/bash

# Caminho para a pasta que você deseja limpar
PATH="/running"

# Verificar se a pasta existe
if [ -d "$PATH" ]; then
    echo "Cleaning path: $PATH"
    
    # Deletar todo o conteúdo dentro da pasta, incluindo arquivos ocultos
    rm -rf "$PATH"/*
    rm -rf "$PATH"/.*

    echo "Folder content cleaned successfully."
else
    echo "Path don't exists: $PATH"
    exit 1
fi
