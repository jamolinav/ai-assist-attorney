import json
import importlib
import asyncio
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Ejecuta una tool MCP (async) sin MCP ni agente. Ejemplo: python manage.py mcp_tool get_organizations_names --args '{\"search\":\"bank\"}'"

    def add_arguments(self, parser):
        parser.add_argument(
            "tool",
            type=str,
            help="Nombre de la tool (módulo dentro de mcp_app.tools)"
        )
        parser.add_argument(
            "--args",
            dest="args_json",
            type=str,
            default="{}",
            help="JSON con los argumentos a pasar a la tool"
        )
        parser.add_argument(
            "--module-base",
            dest="module_base",
            type=str,
            default="mcp_app.tools",
            help="Paquete base donde están las tools"
        )
        parser.add_argument(
            "--raw",
            action="store_true",
            help="Muestra solo el texto plano del resultado (sin formato)"
        )

    def handle(self, *args, **options):
        tool = options["tool"]

        print(f"🚀 Ejecutando tool MCP: {tool}")
        print(f"📦 Con argumentos: {options.get('args_json', '{}')}")
        
        args_json = options.get("args_json", "{}")
        module_base = options.get("module_base", "mcp_app.tools")

        # 🟦 Intenta parsear el JSON recibido
        try:
            arguments = json.loads(args_json)
        except json.JSONDecodeError as e:
            raise CommandError(f"--args no es un JSON válido: {e}")

        module_name = f"{module_base}.{tool}"

        try:
            mod = importlib.import_module(module_name)
        except ModuleNotFoundError:
            raise CommandError(f"No se encontró la tool: {module_name}")

        if not hasattr(mod, "execute"):
            raise CommandError(f"La tool '{tool}' no define función async 'execute(arguments)'")

        #async def run():
        #    return await mod.execute(arguments)
        #result = asyncio.run(run())
        
        # add user_id to arguments if not present
        if "user_id" not in arguments:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            admin_user = User.objects.filter(is_superuser=True).first()
            if admin_user:
                arguments["user_id"] = admin_user.id
            else:
                raise CommandError("No se encontró un usuario administrador para asignar user_id automáticamente.")

        result = mod.execute(arguments)

        # 📦 Muestra el resultado
        if options.get("raw"):
            try:
                print(result["content"][0]["text"])
            except Exception:
                print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"\n✅ Tool '{tool}' ejecutada correctamente\n")
            print(json.dumps(result, ensure_ascii=False, indent=2))
