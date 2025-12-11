
# iniciar app
./startup.sh


# comandos habilitados

python manage.py mcp_assist --args '{"question": "que competencias existen?"}'

python manage.py mcp_tool get_competencias

python manage.py mcp_tool get_cortes --args "{\"competencia\": 1}"

## Ejemplo ##

(venv) juanmolina@192 ai-assist-attorney % python manage.py mcp_tool get_tribunales --args "{\"corte\": 1}" 
🚀 Ejecutando tool MCP: get_tribunales
📦 Con argumentos: {"corte": 1}

✅ Tool 'get_tribunales' ejecutada correctamente

{
  "status": "success",
  "data": [
    {
      "id": 1,
      "nombre": "1º Juzgado de Letras de Arica"
    }
  ],
  "count": 1
}

# Get Demanda
python manage.py mcp_tool get_demanda --args "{\"RIT\": \"C-45-2025\", \"Competencia\": 1, \"Corte\": 1, \"Tribunal\": 1}"

python manage.py mcp_tool rag_query --args "{\"demand_id\": 4, \"question\": \"quienes son los litigantes?\"}"

python manage.py mcp_tool rag_search --args "{\"demand_id\": 4, \"question\": \"quienes son los litigantes?\"}"