@echo off
chcp 65001 >nul
echo ====================================================================
echo    SISTEMA DE ANALISIS ESTRATEGICO Y DESERCION - USMP
echo    Actualizador y Publicador Automatico de Metricas Mensuales
echo ====================================================================
echo.
echo [1/3] Activando entorno Python...
call venv\Scripts\activate.bat

echo.
echo [2/3] Procesando bases de datos y recalculando cuadros de mando...
python etl_processor.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Ocurrio un problema al procesar los datos. Revisa la consola arriba.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/3] Desplegando metricas actualizadas a Google Cloud Run...
gcloud run deploy sistema-analisis-estrategico-desercion-usmp ^
    --source . ^
    --project sistemas-usmp ^
    --region europe-west1 ^
    --allow-unauthenticated ^
    --cpu 1 ^
    --memory 1.5Gi ^
    --min-instances 0 ^
    --max-instances 2 ^
    --timeout 600 ^
    --quiet

echo.
echo ====================================================================
echo   PROCESO COMPLETADO CON EXITO
echo   El dashboard en la nube ya esta actualizado con los nuevos datos:
echo   https://sistema-analisis-estrategico-desercion-usmp-960324457000.europe-west1.run.app
echo ====================================================================
echo.
pause
