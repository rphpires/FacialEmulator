# Pasta base onde iremos procurar as subpastas
$baseFolder = "running"

# Função para excluir arquivos chamados "PID" dentro de uma pasta
function DeletePIDFiles {
    param(
        [string]$folderPath
    )
    
    # Verifica se a pasta existe
    if (Test-Path $folderPath) {
        # Obtém todos os arquivos chamados "PID" dentro da pasta
        $files = Get-ChildItem -Path $folderPath -Filter "PID" -File
        
        # Exclui cada arquivo "PID" encontrado
        foreach ($file in $files) {
            Remove-Item $file.FullName -Force
            Write-Host "Arquivo $($file.FullName) excluído."
        }
    } else {
        Write-Host "A pasta $folderPath não existe."
    }
}

# Função para percorrer recursivamente as subpastas e excluir arquivos "PID"
function DeletePIDFilesRecursively {
    param(
        [string]$folderPath
    )
    
    # Exclui arquivos "PID" nesta pasta
    DeletePIDFiles $folderPath
    
    # Obtém todas as subpastas desta pasta
    $subFolders = Get-ChildItem -Path $folderPath -Directory
    
    # Recursivamente chama esta função para cada subpasta encontrada
    foreach ($subFolder in $subFolders) {
        DeletePIDFilesRecursively $subFolder.FullName
    }
}

# Chama a função para percorrer recursivamente a pasta base e excluir arquivos "PID"
DeletePIDFilesRecursively $baseFolder
