# Wrapper del acceso directo de escritorio: existe solo para que el TargetPath
# del .lnk pueda ser "powershell -WindowStyle Hidden" (que sí oculta consolas
# de forma confiable) en vez de apuntar directo a Iniciar-R2Hub.bat (que
# mostraría su propia consola negra al abrirse desde el ícono).
#
# Iniciar-R2Hub.bat ya lanza Hub y frontend con -WindowStyle Hidden por su
# cuenta -- este wrapper solo le falta ocultar la consola del .bat en sí.
& (Join-Path $PSScriptRoot "Iniciar-R2Hub.bat")
