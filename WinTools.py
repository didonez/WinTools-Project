import os
import sys
import subprocess
import re
import requests
import qrcode
import uuid
import json
import webbrowser
import socket 
from datetime import datetime
from PySide6.QtCore import Qt, QSize, QUrl

# Importa PIL/Image para o QR Code (necessário para a função generate_qr_code)
try:
    from PIL import Image
except ImportError:
    # Atenção: Se essa mensagem aparecer, instale o Pillow: pip install Pillow
    print("Atenção: A biblioteca 'Pillow' (PIL) não está instalada. O QR Code não funcionará.")
    class DummyImage: pass
    Image = DummyImage

# --- 🚨 DEPENDÊNCIA QT: PY SIDE 6 ---
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QListWidget, QListWidgetItem, QDialog,
    QLabel, QMessageBox, QInputDialog, QStyleFactory, QTextEdit, QSizePolicy, QFileDialog
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPalette, QColor, QFont, QDesktopServices

# --- VARIÁVEIS DE VERSÃO E DIRETÓRIO ---
APP_VERSION = "2.0.14" 
THIRD_PARTY_DIR = "FerramentasTerceiros"
ICON_PATH = "w_tools.ico" # Arquivo do ícone deve estar na mesma pasta do script

# --- Funções de Utilitários ---

def run_command(command, blocking=False):
    """
    Executa um comando no terminal (CMD /K) em um novo processo não-bloqueante.
    Ajustado para usar 'start' diretamente com o comando.
    """
    if command:
        try:
            # Comando: start "Título" cmd /K "Comando"
            full_command = f'start "WinTools Command" cmd /K "{command}"'
            subprocess.Popen(full_command, shell=True) 
        except Exception as e:
            QMessageBox.critical(None, "Erro de Execução", f"Não foi possível iniciar o comando '{command}'.\nErro: {e}")

def check_port_with_socket(host, port, timeout=5):
    """Verifica se uma porta TCP está aberta usando o módulo socket do Python."""
    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        return f"Erro: Não foi possível resolver o hostname/IP: {host}"

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    
    try:
        s.connect((ip, int(port)))
        return (f"Conexão BEM SUCEDIDA!\n"
                f"Host: {host} ({ip})\n"
                f"Porta: {port}\n"
                f"Tempo Limite: {timeout}s\n\n"
                f"A porta está aberta e acessível.")
    except socket.timeout:
        return (f"Conexão FALHOU (Timeout).\n"
                f"Host: {host} ({ip})\n"
                f"Porta: {port}\n\n"
                f"O host não respondeu dentro de {timeout} segundos (Firewall ou Serviço Inativo).")
    except ConnectionRefusedError:
        return (f"Conexão RECUSADA.\n"
                f"Host: {host} ({ip})\n"
                f"Porta: {port}\n\n"
                f"O host está online, mas a porta está ativamente rejeitando a conexão (Serviço Inativo ou filtragem local).")
    except Exception as e:
        return (f"Erro Inesperado na Conexão:\n"
                f"Host: {host} ({ip})\n"
                f"Porta: {port}\n\n"
                f"Erro: {e}")
    finally:
        s.close()


def get_external_ip_info():
    """Consulta o IP externo e dados de geolocalização usando ip-api.com."""
    try:
        response = requests.get('http://ip-api.com/json/?fields=status,message,country,countryCode,regionName,city,lat,lon,isp,query')
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return (
                    f"🌐 Endereço IP Externo: {data.get('query')}\n"
                    f"🔗 Provedor (ISP): {data.get('isp')}\n"
                    f"🗺️ Localização: {data.get('city')}, {data.get('regionName')}, {data.get('country')}"
                )
            else:
                return f"Erro na API: {data.get('message', 'Status não foi sucesso')}"
        else:
            return f"Erro HTTP ao consultar IP externo: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Erro de Conexão ao consultar IP externo:\n{e}"

def get_local_ip_info():
    """Extrai informações filtradas de IP (IPv4, Máscara, Gateway, MAC) de adaptadores conectados usando ipconfig /all."""
    try:
        # Tenta a decodificação cp850 (padrão do CMD)
        result = subprocess.run(['ipconfig', '/all'], capture_output=True, text=True, encoding='cp850', timeout=10)
        output = result.stdout
        
        if not output: return "Não foi possível obter a saída do ipconfig."

        adapters = {}
        current_adapter_name = "N/A"
        
        # Padrões mais robustos para o português
        adapter_pattern = re.compile(r"Adaptador\s(?:Ethernet|de Rede Sem Fio|de Rede Local|de Loopback)[\w\s-]*:\s*([^\n]+)", re.IGNORECASE)
        ipv4_pattern = re.compile(r"Endereço IPv4\. [\. ]+:\s*([0-9\.]+)", re.IGNORECASE)
        mask_pattern = re.compile(r"Máscara de Sub-rede\. [\. ]+:\s*([0-9\.]+)", re.IGNORECASE)
        gateway_pattern = re.compile(r"Gateway Padrão\. [\. ]+:\s*([0-9\.]+)", re.IGNORECASE)
        mac_pattern = re.compile(r"Endereço Físico\. [\. ]+:\s*([0-9A-Fa-f-]{17})", re.IGNORECASE)

        for line in output.splitlines():
            adapter_match = adapter_pattern.search(line)
            if adapter_match:
                current_adapter_name = adapter_match.group(1).strip()
                if current_adapter_name.startswith("Adaptador"):
                    current_adapter_name = current_adapter_name.split(':')[-1].strip()
                
                adapters[current_adapter_name] = {'IPv4': 'N/D', 'Máscara': 'N/D', 'Gateway': 'N/D', 'MAC': 'N/D', 'Status': 'Desconectado'}
                
                if 'Mídia desconectada' not in line and 'Estado da mídia' in line:
                    adapters[current_adapter_name]['Status'] = 'Conectado'
                continue

            if current_adapter_name in adapters:
                if ipv4_match := ipv4_pattern.search(line):
                    adapters[current_adapter_name]['IPv4'] = ipv4_match.group(1)
                elif mask_match := mask_pattern.search(line):
                    adapters[current_adapter_name]['Máscara'] = mask_match.group(1)
                elif gateway_match := gateway_pattern.search(line):
                    adapters[current_adapter_name]['Gateway'] = gateway_match.group(1)
                elif mac_match := mac_pattern.search(line):
                    adapters[current_adapter_name]['MAC'] = mac_match.group(1)

        filtered_info = ["Informações de IP Local (Filtrado):"]
        valid_adapter_found = False
        for name, data in adapters.items():
            # Filtra adaptadores não conectados, loopbacks e sem IP válido
            if data['IPv4'] not in ('N/D', '127.0.0.1') and data['Status'] == 'Conectado': 
                valid_adapter_found = True
                filtered_info.append("="*40)
                filtered_info.append(f"Adaptador: {name}")
                filtered_info.append(f"  Status: {data['Status']}")
                filtered_info.append(f"  IPv4: {data['IPv4']}")
                filtered_info.append(f"  Máscara: {data['Máscara']}")
                filtered_info.append(f"  Gateway: {data['Gateway']}")
                filtered_info.append(f"  MAC: {data['MAC']}")

        if valid_adapter_found:
            return "\n".join(filtered_info)
        else:
            # Retorna a mensagem de erro que você já havia visto
            return "Não foi possível extrair as informações de IP local (IPv4, Máscara, Gateway, MAC)." 

    except Exception as e:
        return f"Erro inesperado na extração de IP local:\n{e}"

def generate_qr_code(parent):
    """Gera um QR Code para texto/URL ou configuração de Wi-Fi."""
    options = ["1 - Texto/URL Genérico", "2 - Conexão Wi-Fi (SSID/Senha)"]
    choice_str, ok = QInputDialog.getItem(parent, "Gerador de QR Code", "Selecione o tipo de QR Code:", options, 0, False)
    if not ok or not choice_str: return
    
    choice = int(choice_str.split(' - ')[0])
    data_to_encode = ""

    if choice == 1:
        data_to_encode, ok = QInputDialog.getText(parent, "QR Code - Texto/URL", "Digite o texto ou URL:")
    elif choice == 2:
        ssid, ok1 = QInputDialog.getText(parent, "QR Code - Wi-Fi", "Nome da Rede (SSID):", QLineEdit.Normal)
        if not ok1: return
        password, ok2 = QInputDialog.getText(parent, "QR Code - Wi-Fi", "Senha da Rede:", QLineEdit.Password)
        if not ok2: return
        
        security, ok3 = QInputDialog.getItem(parent, "QR Code - Wi-Fi", "Tipo de Criptografia:", ["WPA/WPA2/WPA3 (Recomendado)", "WEP", "Nenhum"], 0, False)
        if not ok3: return
        
        if "WPA" in security: encryption = "WPA"
        elif "WEP" in security: encryption = "WEP"
        else: encryption = "nopass"

        data_to_encode = f"WIFI:T:{encryption};S:{ssid};P:{password};;"

    if not data_to_encode: return

    try:
        qr = qrcode.QRCode(
            version=1, error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10, border=4,
        )
        qr.add_data(data_to_encode)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
        
        # Cria um arquivo temporário para a imagem
        temp_dir = os.path.join(os.environ.get('TEMP', os.environ.get('TMP', '/tmp')))
        filename = f"qrcode_wintools_{uuid.uuid4().hex}.png"
        temp_path = os.path.join(temp_dir, filename)
        
        img.save(temp_path)
        
        QMessageBox.information(
            parent,
            "QR Code Gerado com Sucesso",
            f"O QR Code foi gerado e salvo como:\n{temp_path}\n\nA imagem será aberta no seu visualizador padrão."
        )
        # Usa QDesktopServices para abrir o arquivo de forma segura
        QDesktopServices.openUrl(QUrl.fromLocalFile(temp_path))
        
    except Exception as e:
        QMessageBox.critical(parent, "Erro ao Gerar QR Code", f"Ocorreu um erro: {e}")


# ----------------------------------------------------------------------
# --- DIÁLOGOS: ThirdPartyAppDialog e OutputDialog ---
# ----------------------------------------------------------------------

class ThirdPartyAppDialog(QDialog):
    """Diálogo para listar e executar ferramentas de terceiros com busca."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"WinTools - Ferramentas de Terceiros (Buscar) - v{APP_VERSION}")
        self.setMinimumSize(450, 500)
        
        self.layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔎 Digite para buscar...")
        self.search_input.textChanged.connect(self.filter_list)
        self.layout.addWidget(self.search_input)
        self.app_list_widget = QListWidget()
        self.app_list_widget.itemDoubleClicked.connect(self.execute_selected_app)
        self.layout.addWidget(self.app_list_widget)
        self.execute_button = QPushButton("Executar Selecionado")
        self.execute_button.clicked.connect(self.execute_selected_app)
        self.layout.addWidget(self.execute_button)
        self.path_button = QPushButton(f"Abrir Pasta '{THIRD_PARTY_DIR}'")
        self.path_button.clicked.connect(self.open_third_party_folder)
        self.layout.addWidget(self.path_button)
        
        self.all_apps = [] 
        self.load_apps()
        
    def load_apps(self):
        """Carrega executáveis da pasta de terceiros."""
        self.all_apps = []
        self.app_list_widget.clear()
        EXECUTABLE_EXTENSIONS = ('.exe', '.com', '.bat', '.cmd', '.vbs', '.msi')

        try:
            if not os.path.exists(THIRD_PARTY_DIR):
                QMessageBox.critical(self, "Erro", f"A pasta '{THIRD_PARTY_DIR}' não existe.")
                return

            for item in os.listdir(THIRD_PARTY_DIR):
                full_path = os.path.join(THIRD_PARTY_DIR, item)
                
                if os.path.isfile(full_path) and item.lower().endswith(EXECUTABLE_EXTENSIONS):
                    self.all_apps.append({'name': item, 'path': full_path})
                
                elif os.path.isdir(full_path):
                    for sub_item in os.listdir(full_path):
                        if sub_item.lower().endswith(EXECUTABLE_EXTENSIONS):
                            app_name = f"{item} ({sub_item})"
                            app_path = os.path.join(full_path, sub_item)
                            self.all_apps.append({'name': app_name, 'path': app_path})
                            break
                            
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Listar", f"Erro ao ler a pasta de ferramentas: {e}")
            return
            
        if not self.all_apps:
            QMessageBox.information(self, "Info", "Nenhum executável encontrado na pasta.")
            
        self.filter_list()
        
    def filter_list(self):
        """Filtra a lista de aplicativos com base no texto de busca."""
        search_text = self.search_input.text().lower()
        self.app_list_widget.clear()
        
        for app in self.all_apps:
            if search_text in app['name'].lower():
                item = QListWidgetItem(app['name'])
                item.setData(Qt.UserRole, app['path']) 
                self.app_list_widget.addItem(item)
                
    def open_third_party_folder(self):
        """Abre a pasta de ferramentas de terceiros no Explorador de Arquivos."""
        try:
            # Usar QDesktopServices para abrir o Explorer de forma segura
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(THIRD_PARTY_DIR)))
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir o Explorer: {e}")
            
    def execute_selected_app(self):
        """Executa o aplicativo selecionado, com tratamento especial para speedtest.exe."""
        selected_item = self.app_list_widget.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Aviso", "Selecione uma ferramenta para executar.")
            return

        full_app_path = selected_item.data(Qt.UserRole)
        app_dir_absolute = os.path.dirname(full_app_path)
        app_name_lower = os.path.basename(full_app_path).lower()

        try:
            # --- CORREÇÃO FINAL DE EXECUÇÃO DE TERMINAL ---
            if "speedtest.exe" in app_name_lower:
                
                escaped_app_path = full_app_path.replace('"', '\"')
                
                command = (
                    f'start "Speedtest WinTools" cmd /K '
                    f'"{escaped_app_path} & ' 
                    f'echo. & echo Teste finalizado. Pressione Enter para fechar o terminal e voltar ao WinTools. & pause > nul"'
                )
                
                subprocess.Popen(command, shell=True)
            
            elif app_name_lower.endswith(('.bat', '.cmd', '.com')):
                # Para scripts, usamos CALL e garantimos o diretório de trabalho
                QMessageBox.information(self, "Terminal Aberto", "A ferramenta será executada em um terminal. Pressione Enter para fechar.")
                escaped_app_dir = app_dir_absolute.replace('"', '\"')
                escaped_app_path = full_app_path.replace('"', '\"')
                
                command = f'start "WinTools Script" cmd /K "cd /d "{escaped_app_dir}" & CALL "{escaped_app_path}" & echo. & pause"'
                subprocess.Popen(command, shell=True) 
            
            else:
                # Para executáveis normais (.exe, .msi, etc)
                command = f'start "WinTools Tool" /D "{app_dir_absolute}" "{full_app_path}"'
                subprocess.Popen(command, shell=True) 

        except Exception as e:
            QMessageBox.critical(self, "Erro de Execução", f"Não foi possível iniciar a ferramenta.\nErro: {e}")

class OutputDialog(QDialog):
    """Diálogo para exibir a saída de comandos de forma formatada."""
    def __init__(self, parent, title, command, output):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(700, 550)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        
        self.output_content = output
        self.command_executed = command
        
        layout = QVBoxLayout(self)
        
        command_label = QLabel(f"Comando Executado: **{command}**")
        command_label.setStyleSheet("font-weight: bold; padding-bottom: 5px;")
        layout.addWidget(command_label)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFontFamily("Consolas") 
        self.output_text.setText(output)
        layout.addWidget(self.output_text)
        
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("💾 Salvar Output (TXT)")
        self.save_button.clicked.connect(self.save_output)
        button_layout.addWidget(self.save_button)
        close_button = QPushButton("Fechar")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
    def save_output(self):
        """Salva o conteúdo do output em um arquivo de texto."""
        base_name = self.command_executed.split()[0].replace('/', '').replace('\\', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{base_name}_output_{timestamp}.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Salvar Output do Comando", 
            default_filename, 
            "Arquivos de Texto (*.txt);;Todos os Arquivos (*.*)"
        )
        
        if file_path:
            try:
                header = f"--- WinTools Output ---\n"
                header += f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                header += f"Comando: {self.command_executed}\n"
                header += "-----------------------\n\n"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(header + self.output_content)
                
                QMessageBox.information(self, "Sucesso", f"O output foi salvo em:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Erro ao Salvar", f"Não foi possível salvar o arquivo:\n{e}")


# ----------------------------------------------------------------------
# --- CLASSE PRINCIPAL: MainWindow (v2.0.14) ---
# ----------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # --- CÓDIGO PARA DEFINIR O ÍCONE DA JANELA E BARRA DE TAREFAS ---
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        else:
            print(f"Atenção: O arquivo de ícone '{ICON_PATH}' não foi encontrado. Usando ícone padrão.")
        # ------------------------------------------------------------------
        
        # Título da janela com a versão atual
        self.setWindowTitle(f"WinTools - Ferramentas de Rede e Sistema (v{APP_VERSION})")
        
        # Estado do Tema
        self.current_theme = "Dark" 
        
        # Ajuste de tamanho
        self.setGeometry(100, 100, 680, 580) 
        self.setMinimumSize(600, 500)
        
        if not os.path.exists(THIRD_PARTY_DIR):
            os.makedirs(THIRD_PARTY_DIR)
            
        self.apply_theme(self.current_theme) # Chama a função de tema
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        main_layout = QVBoxLayout(self.central_widget)
        
        title_label = QLabel(f"🛠️ WinTools - Selecione uma Ferramenta 💻")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 20pt; font-weight: bold; padding: 10px;") 
        main_layout.addWidget(title_label)
        
        self.list_widget = QListWidget()
        self.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.list_widget)
        
        self.setup_menu_items()
        self.center_on_screen()
        
    def apply_theme(self, theme_name):
        """Aplica o tema (Dark ou Light) à aplicação Qt."""
        QApplication.setStyle(QStyleFactory.create('Fusion'))
        
        font = QFont()
        font.setPointSize(11)
        QApplication.setFont(font)

        palette = QPalette()
        
        if theme_name == "Dark":
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.ToolTipBase, Qt.white)
            palette.setColor(QPalette.ToolTipText, Qt.white)
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, Qt.white)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.HighlightedText, Qt.black)
        
        elif theme_name == "Light":
            # Tema Light (Cores mais claras)
            palette.setColor(QPalette.Window, QColor(240, 240, 240))
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, QColor(255, 255, 255))
            palette.setColor(QPalette.AlternateBase, QColor(220, 220, 220))
            palette.setColor(QPalette.ToolTipBase, Qt.black)
            palette.setColor(QPalette.ToolTipText, Qt.black)
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor(220, 220, 220))
            palette.setColor(QPalette.ButtonText, Qt.black)
            palette.setColor(QPalette.BrightText, Qt.red)
            palette.setColor(QPalette.Link, QColor(0, 120, 215))
            palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
            palette.setColor(QPalette.HighlightedText, Qt.white)

        QApplication.setPalette(palette)
        self.current_theme = theme_name # Atualiza o estado

        # Se a lista de itens existe, re-popula para aplicar a cor do texto do item divisor
        if hasattr(self, 'list_widget'):
            self.setup_menu_items()


        
    def center_on_screen(self):
        """Centraliza a janela na tela."""
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2, 
            (screen.height() - size.height()) // 2
        )
        
    def execute_and_show_output(self, title, command, shell=True, encoding='cp850'):
        """Executa um comando de forma bloqueante e exibe o output em um diálogo."""
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            
            result = subprocess.run(
                command, 
                shell=shell, 
                capture_output=True, 
                text=True, 
                encoding=encoding,
                timeout=300 
            )
            
            output = result.stdout
            if result.stderr:
                output += "\n\n--- ERRO PADRÃO (STDERR) ---\n" + result.stderr

            if result.returncode != 0 and not output:
                 output = f"Comando finalizado com código de erro {result.returncode}.\n\nOutput/Erro não capturado."
            
        except FileNotFoundError:
            output = f"Erro: O comando '{command.split()[0]}' não foi encontrado no PATH."
        except subprocess.TimeoutExpired:
            output = "Erro: O comando excedeu o tempo limite de 5 minutos (Timeout)."
        except Exception as e:
            output = f"Erro inesperado ao executar o comando:\n{e}"
        finally:
            QApplication.restoreOverrideCursor()
        
        dialog = OutputDialog(self, title, command, output)
        dialog.exec()


    def setup_menu_items(self):
        """Define e popula todos os itens de menu na lista principal."""
        self.list_widget.clear() # Limpa para o re-populamento do tema

        # Categorias de Emojis
        NET = "🌐" ; SYS = "⚙️" ; DISK = "💾" ; ADMIN = "🚨" ; UTIL = "💡" ; TERCEIROS = "📦" ; INFO = "ℹ️" ; CONFIG = "🎨"
        
        # Lista de Tuplas: (Nome da Opção, Função, Categoria)
        self.menu_items = [
            ("1 - Ping (Teste de Conexão)", self.run_ping_menu, NET),
            ("2 - PathPing (Diagnóstico de Rota/Perda)", self.run_pathping_menu, NET),
            ("3 - TraceCert (Rastreio de Rota)", lambda: self.run_simple_command_output("TraceCert", "Host ou IP:", "tracert"), NET),
            ("4 - Telnet (Verificação de Porta - Python Puro)", self.run_telnet_menu_output, NET),
            ("5 - Curl (Requisição HTTP/HTTPS)", self.run_curl_menu_output, NET), 
            ("6 - NsLookup (Consulta DNS)", lambda: self.run_simple_command_output("NsLookup", "Host ou IP:", "nslookup"), NET),                      
            ("7 - Netstat (Conexões de Rede Ativas)", lambda: self.run_simple_command_with_default_output("Netstat", "Parâmetros:", "netstat", "-ano"), NET),                       
            ("8 - IP Config (Configurações da Placa de Rede)", self.run_ipconfig_menu_output, NET), 
            ("9 - ARP (Tabela de Endereços Físicos - MAC)", lambda: self.run_arp_menu_output("Visualizar (arp -a)", "arp -a", "ARP"), NET),                           
            ("10 - Netsh (Gerenciamento Avançado de Rede)", self.run_netsh_menu_output, ADMIN),                        
            ("11 - SFC /Scannow (Verificar Arquivos do Sistema)", self.run_sfc_menu, ADMIN),                 
            ("12 - MRT (Ferramenta de Remoção de Software Malicioso)", lambda: os.system("mrt.exe"), SYS),                          
            ("13 - Winget (Gerenciador de Pacotes/Apps)", self.run_winget_menu_output, ADMIN),
            ("14 - CHKDSK (Verificar e Corrigir Disco)", self.run_chkdsk_menu, DISK),     
            ("15 - Limpeza de Disco (cleanmgr)", lambda: os.system("cleanmgr.exe"), DISK),   
            ("16 - Otimizar/Desfragmentar (dfrgui)", lambda: os.system("dfrgui.exe"), DISK), 
            ("17 - DISKPART (Utilitário de Particionamento - CUIDADO)", self.run_diskpart_menu, ADMIN), 
            ("18 - Tasklist (Listar Processos em Execução)", lambda: self.execute_and_show_output("Tasklist", "tasklist"), SYS), 
            ("19 - Gerenciamento de Disco (diskmgmt.msc)", lambda: os.system("diskmgmt.msc"), DISK), 
            ("20 - Visualizador de Eventos (eventvwr.msc)", lambda: os.system("eventvwr.msc"), SYS), 
            ("21 - Verificador de Arquivos de Driver (verifier)", self.run_verifier_menu, ADMIN), 
            ("22 - DriverQuery (Listar Drivers Instalados)", lambda: self.execute_and_show_output("DriverQuery", "driverquery"), SYS),   
            ("23 - Comandos Rápidos (Windows + R - EXPANDIDO)", self.run_quick_commands_menu, UTIL), 
            ("24 - SystemInfo (Detalhes do Sistema/Hardware)", lambda: self.execute_and_show_output("SystemInfo", "systeminfo"), SYS), 
            ("25 - Gerador de QR Code (Texto/URL/Wi-Fi)", lambda: generate_qr_code(self), UTIL), 
            ("--", None, ""),
            ("26 - FERRAMENTAS DE TERCEIROS (Com Busca - Pasta FerramentasTerceiros)", self.run_third_party_apps, TERCEIROS),
            ("--", None, ""),
            ("27 - Meu IP ISP (Externo - Geolocalização)", self.run_external_ip_info, NET), 
            ("28 - Sobre o WinTools", self.show_about, INFO),
            ("29 - Configurações de Tema (Dark/Light)", self.run_theme_config, CONFIG)
        ]

        for text, func, category in self.menu_items:
            item = QListWidgetItem(f"{category} {text}")
            if func is None:
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                # Garante que o divisor tenha cor neutra independente do tema
                item.setForeground(QColor(150, 150, 150) if self.current_theme == "Dark" else QColor(100, 100, 100))
            else:
                item.setData(Qt.UserRole, func) 
            self.list_widget.addItem(item)
            
        self.list_widget.itemClicked.connect(self.handle_item_click)
        
    def handle_item_click(self, item):
        """Executa a função armazenada no item da lista."""
        func = item.data(Qt.UserRole)
        if func:
            func()
            
    # --- Funções de Comando para Terminal/Output Interno ---
            
    def run_simple_command_output(self, title, prompt, command_base):
        """Comandos com um único parâmetro (Host/IP) e output interno."""
        text, ok = QInputDialog.getText(self, f"WinTools - {title}", prompt, QLineEdit.Normal, "google.com")
        if ok and text:
            command = f"{command_base} {text}"
            self.execute_and_show_output(title, command, shell=True)

    def run_simple_command_with_default_output(self, title, prompt, command_base, default_param):
        """Comandos com parâmetro padrão e output interno."""
        text, ok = QInputDialog.getText(self, f"WinTools - {title}", prompt, QLineEdit.Normal, default_param)
        if ok and text:
            command = f"{command_base} {text}"
            self.execute_and_show_output(title, command, shell=True)
            
    def run_ping_menu(self):
        """Menu Ping para abrir no Terminal, focado no -t. (Usando run_command não-blocking)"""
        host, ok = QInputDialog.getText(self, "WinTools - Ping", "Digite o Host ou IP:", QLineEdit.Normal, "8.8.8.8")
        if ok and host:
            mode, ok_mode = QInputDialog.getItem(
                self, "WinTools - Modo de Ping", "Selecione o modo:", 
                ["1 - Ping Contínuo (ping -t)", "2 - Ping Limitado (ping -n 4)", "3 - Ping com Tamanho (ping -l 1500 -n 1)"], 
                0, False)
            if ok_mode:
                if "Contínuo" in mode:
                    run_command(f"ping -t {host}")
                elif "Limitado" in mode:
                    run_command(f"ping -n 4 {host}")
                elif "Tamanho" in mode:
                    run_command(f"ping -l 1500 -n 1 {host}")

    def run_pathping_menu(self):
        """PathPing abre no Terminal. (Usando run_command não-blocking)"""
        host, ok = QInputDialog.getText(self, "WinTools - PathPing", "Host ou IP:", QLineEdit.Normal, "google.com")
        if ok and host:
            run_command(f"pathping {host}")

    def run_telnet_menu_output(self):
        """Teste de Porta (Telnet) usando socket Python puro."""
        host, ok1 = QInputDialog.getText(self, "WinTools - Telnet (Python Puro)", "Host (Ex: google.com):", QLineEdit.Normal, "google.com")
        if not ok1 or not host: return
        porta, ok2 = QInputDialog.getText(self, "WinTools - Telnet (Python Puro)", "Porta (Ex: 80, 443, 23):", QLineEdit.Normal, "80")
        
        if ok2 and porta:
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                # Chama a função de socket puro (blocking, mas rápido)
                output = check_port_with_socket(host, porta, timeout=5)
                title_out = f"Verificação de Porta - {host}:{porta}"
            except Exception as e:
                output = f"Erro ao executar verificação de porta:\n{e}"
                title_out = "Verificação de Porta (Erro)"
            finally:
                QApplication.restoreOverrideCursor()
                
            # O output agora é o resultado da função check_port_with_socket
            dialog = OutputDialog(self, title_out, f"Python Socket Check: {host}:{porta}", output)
            dialog.exec()

    def run_curl_menu_output(self):
        """Menu Curl com modos de execução."""
        host, ok1 = QInputDialog.getText(self, "WinTools - Curl", "Host/URL:", QLineEdit.Normal, "google.com")
        if not ok1 or not host: return
        mode, ok2 = QInputDialog.getItem(self, "WinTools - Modo Curl", "Modo:", ["Cabeçalho (-I)", "Conteúdo"], 0, False)
        
        if ok2:
            command = f"curl -I {host}" if "Cabeçalho" in mode else f"curl {host}"
            self.execute_and_show_output("Curl", command, shell=True)
            
    def run_ipconfig_menu_output(self):
        """Opções do IP Config."""
        menu_options = [
            "1 - Visualização Limpa (IP/Máscara/Gateway/MAC) - Mensagem", 
            "2 - /all (Detalhado na Janela)",
            "3 - /release (Liberar IP - Admin)", "4 - /renew (Renovar IP - Admin)", 
            "5 - /flushdns (Limpar Cache DNS)", "6 - /registerdns (Registrar DNS)",
            "7 - (Simples na Janela)"
        ]
        opcao_ip_str, ok = QInputDialog.getItem(self, "WinTools - IP Config", "Selecione a Opção:", menu_options, 0, False)
        if ok and opcao_ip_str:
            int_opcao_ip = int(opcao_ip_str.split(' - ')[0])
            
            if int_opcao_ip == 1:
                ip_info = get_local_ip_info() # Esta é uma função blocking
                QMessageBox.information(self, "WinTools - IP Local (Filtrado)", ip_info)
            elif int_opcao_ip == 2: self.execute_and_show_output("IP Config /all", "ipconfig /all", shell=True)
            elif int_opcao_ip == 3: QMessageBox.warning(self, "Admin", "Requer Admin."); run_command("ipconfig /release")
            elif int_opcao_ip == 4: QMessageBox.warning(self, "Admin", "Requer Admin."); run_command("ipconfig /renew")
            elif int_opcao_ip == 5: self.execute_and_show_output("IP Config /flushdns", "ipconfig /flushdns", shell=True)
            elif int_opcao_ip == 6: self.execute_and_show_output("IP Config /registerdns", "ipconfig /registerdns", shell=True)
            elif int_opcao_ip == 7: self.execute_and_show_output("IP Config Simples", "ipconfig", shell=True)

    def run_arp_menu_output(self, menu_text, command, title):
        """Menu ARP (Visualizar e Excluir)."""
        mode, ok = QInputDialog.getItem(self, "WinTools - ARP", "Selecione o modo:", [menu_text, "2 - Excluir Tabela (arp -d - Admin)"], 0, False)
        if ok:
            if "Visualizar" in mode:
                self.execute_and_show_output(title, command, shell=True)
            elif "Excluir" in mode: 
                QMessageBox.warning(self, "Admin", "Excluir requer Admin.");
                run_command("arp -d") # Usando run_command não-bloqueante

    def run_netsh_menu_output(self):
        """Menu Netsh Avançado (Comando de Reset Adicionado)."""
        menu_options = [
            "1 - Perfis/Interfaces Wi-Fi", 
            "2 - Senha do Perfil Wi-Fi (Admin)", 
            "3 - Interfaces de Rede",
            "4 - Status do Firewall (show allprofiles)",
            "5 - RESET DE STACK DE REDE (Winsock, IP, TCP, Firewall - Admin)", # NOVO COMANDO
            "6 - Resetar Stack TCP/IP (OLD: netsh int ip reset - Admin - Abrir Terminal)"
        ]
        opcao_netsh_str, ok = QInputDialog.getItem(self, "WinTools - Netsh Avançado", "Comando Netsh:", menu_options, 0, False)
        if ok and opcao_netsh_str:
            int_opcao_netsh = int(opcao_netsh_str.split(' - ')[0])
            strComando = ""
            
            if int_opcao_netsh == 1: 
                strComando = "netsh wlan show all"
            
            elif int_opcao_netsh == 2: 
                QMessageBox.warning(self, "Admin", "Requer Admin."); 
                perfil, ok_q = QInputDialog.getText(self, "Wi-Fi Senha", "Nome do perfil Wi-Fi:");
                if ok_q and perfil: strComando = f'netsh wlan show profile name="{perfil}" key=clear'
            
            elif int_opcao_netsh == 3: 
                strComando = "netsh interface show interface"
                
            elif int_opcao_netsh == 4: 
                strComando = "netsh advfirewall show allprofiles"
                
            elif int_opcao_netsh == 5: 
                # NOVO: Agrupa os 4 comandos de reset
                QMessageBox.warning(self, "Admin e Reboot", "ESTE COMANDO EXIGE ADMIN E UMA REINICIALIZAÇÃO (REBOOT) APÓS A EXECUÇÃO.\n\nConfirmar execução dos 4 resets?")
                
                if QMessageBox.question(self, "Confirmação de Reset", "Deseja executar o reset da stack de rede agora?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                    # Executa os 4 comandos em sequência em um único terminal (run_command)
                    reset_commands = (
                        "netsh winsock reset & "
                        "netsh int ip reset & "
                        "netsh int tcp reset & "
                        "netsh advfirewall reset"
                    )
                    run_command(reset_commands)
                return # Retorna após executar o comando não-bloqueante
                
            elif int_opcao_netsh == 6: 
                # Comando antigo (apenas netsh int ip reset)
                QMessageBox.warning(self, "Admin", "Requer Admin."); 
                run_command("netsh int ip reset")
                return # Retorna após executar o comando não-bloqueante
            
            if strComando: 
                # Executa e exibe o output para os comandos que não são de reset
                self.execute_and_show_output(f"Netsh - Opção {int_opcao_netsh}", strComando, shell=True)

    def run_winget_menu_output(self):
        """Menu Winget."""
        menu_options = [
            "1 - Search", "2 - Install (Admin)", "3 - Upgrade / Update (Admin)",
            "4 - Uninstall (Admin)", "5 - List"
        ]
        selected_option_str, ok = QInputDialog.getItem(self, "WinTools - Winget", "Comando Winget:", menu_options, 0, False)
        if ok and selected_option_str:
            intOpcao = int(selected_option_str.split(' - ')[0])
            strComando = ""
            
            if intOpcao == 1: 
                query, ok_q = QInputDialog.getText(self, "Winget - Search", "Nome/ID do pacote:", QLineEdit.Normal, "vlc");
                if ok_q and query: strComando = f"winget search {query}"
            elif intOpcao == 2: 
                QMessageBox.warning(self, "Admin", "Instalação exige Admin.");
                pkg_id, ok_q = QInputDialog.getText(self, "Winget - Install", "ID exato do pacote (Ex: VideoLAN.VLC):");
                if ok_q and pkg_id: strComando = f"winget install {pkg_id}"
            elif intOpcao == 3: 
                QMessageBox.warning(self, "Admin", "Atualização exige Admin.");
                pkg_id, ok_q = QInputDialog.getText(self, "Winget - Upgrade / Update", "ID do pacote OU 'all':", QLineEdit.Normal, "all");
                if ok_q and pkg_id: strComando = "winget upgrade --all" if pkg_id.lower() == 'all' else f"winget upgrade {pkg_id}"
            elif intOpcao == 4: 
                QMessageBox.warning(self, "Admin", "Desinstalação exige Admin.");
                pkg_id, ok_q = QInputDialog.getText(self, "Winget - Uninstall", "ID exato do pacote:");
                if ok_q and pkg_id: strComando = f"winget uninstall {pkg_id}"
            elif intOpcao == 5: 
                strComando = "winget list"
            
            # Winget pode demorar, mas queremos o output, então mantemos blocking.
            if strComando: self.execute_and_show_output("Winget", strComando, shell=True) 

    def run_sfc_menu(self):
        """SFC /Scannow com aviso de Admin e Terminal."""
        QMessageBox.warning(self, "Admin Necessário", "O SFC /SCANNOW exige privilégios de Administrador e é de longa duração.")
        if QMessageBox.question(self, "Confirmação", "Deseja executar 'sfc /scannow' agora?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            run_command("sfc /scannow")

    def run_chkdsk_menu(self):
        """CHKDSK com seleção de drive e parâmetros."""
        drive, ok1 = QInputDialog.getText(self, "WinTools - CHKDSK Drive", "Letra do Drive (Ex: C:):", QLineEdit.Normal, "C:")
        if not ok1 or not drive: return
        params, ok2 = QInputDialog.getText(self, "WinTools - CHKDSK Parâmetros", "Parâmetros (Ex: /f /r). Vazio p/ leitura:")
        if ok2: 
            QMessageBox.information(self, "Terminal Aberto", "O CHKDSK será executado em um terminal e pode levar tempo.")
            run_command(f"chkdsk {drive} {params}")
            
    def run_diskpart_menu(self):
        """Diskpart com aviso de segurança."""
        QMessageBox.warning(self, "ATENÇÃO", "DISKPART é INTERATIVO, perigoso e será executado no terminal.")
        if QMessageBox.question(self, "Confirmação", "Deseja executar 'diskpart' agora?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            run_command("diskpart")
            
    def run_verifier_menu(self):
        """Verificador de Driver com aviso de segurança."""
        QMessageBox.warning(self, "ATENÇÃO", "O Verificador de Driver é INTERATIVO e pode causar instabilidade. Requer Admin.")
        if QMessageBox.question(self, "Confirmação", "Deseja executar 'verifier' agora?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            run_command("verifier")
            
    # --- Funções de Configuração e Utilitários ---
            
    def run_quick_commands_menu(self):
        """Menu de comandos do Win + R."""
        # Lista de comandos completa fornecida pelo usuário (25 comandos)
        menu_options = [
            "1 - cmd (Prompt de Comando)", "2 - powershell (Windows PowerShell)",
            "3 - regedit (Editor de Registro)", "4 - msconfig (Configurações do Sistema)",
            "5 - taskmgr (Gerenciador de Tarefas)", "6 - explorer (Explorador de Arquivos)",
            "7 - dxdiag (Diagnóstico do DirectX)", "8 - msinfo32 (Informações do Sistema)",
            "9 - eventvwr.msc (Visualizador de Eventos)", "10 - perfmon.msc (Monitor de Desempenho)",
            "11 - services.msc (Serviços do Windows)", "12 - compmgmt.msc (Gerenciamento do Computador)",
            "13 - devmgmt.msc (Gerenciador de Dispositivos)", "14 - diskmgmt.msc (Gerenciamento de Disco)",
            "15 - appwiz.cpl (Programas e Recursos)", "16 - cleanmgr (Limpeza de Disco)",
            "17 - secpol.msc (Diretivas de Segurança Local)", "18 - gpedit.msc (Editor de Política de Grupo Local)",
            "19 - control (Painel de Controle clássico)", "20 - ncpa.cpl (Conexões de Rede)",
            "21 - powercfg.cpl (Opções de Energia)", "22 - sysdm.cpl (Propriedades do Sistema)",
            "23 - main.cpl (Propriedades do Mouse)", "24 - osk (Teclado Virtual)",
            "25 - winver (Versão do Windows)"
        ]
        
        opcao_str, ok = QInputDialog.getItem(self, "WinTools - Comandos Rápidos (Win + R)", "Selecione o comando rápido:", menu_options, 0, False)
        if ok and opcao_str:
            # Pega apenas o comando (Ex: cmd, regedit, diskmgmt.msc)
            comando = opcao_str.split(' - ')[1].split(' ')[0] 
            os.system(comando)

    def run_third_party_apps(self):
        """Chama o diálogo de terceiros com barra de busca."""
        dialog = ThirdPartyAppDialog(self)
        dialog.exec()
            
    def run_external_ip_info(self):
        """Exibe o IP externo formatado."""
        ip_info_externo = get_external_ip_info()
        QMessageBox.information(self, "WinTools - Meu IP ISP (Externo)", ip_info_externo)

    def run_theme_config(self):
        """Configurações de tema."""
        current = "Tema Atual: Escuro (Dark)" if self.current_theme == "Dark" else "Tema Atual: Claro (Light)"
        
        options = ["Escuro (Dark)", "Claro (Light)"]
        initial_index = 0 if self.current_theme == "Dark" else 1

        new_theme, ok = QInputDialog.getItem(
            self, "Configurações de Tema", 
            f"{current}\n\nSelecione o novo tema:", 
            options, 
            initial_index, 
            False
        )
        
        if ok and new_theme:
            theme_choice = "Dark" if "Escuro" in new_theme else "Light"
            if theme_choice != self.current_theme:
                self.apply_theme(theme_choice)
                QMessageBox.information(self, "Tema Alterado", f"O tema foi alterado para {new_theme}. As cores da janela principal foram atualizadas.")
                

    def show_about(self):
        """Exibe as informações sobre o programa (com sua contribuição)."""
        QMessageBox.information(
            self,
            "WinTools - Sobre o Sistema",
            "🛠️ WinTools - Ferramentas de Rede e Sistema\n\n"
            f"**Versão:** {APP_VERSION} (Novembro/2025) - Menu de Comandos Mais Limpo e Informativo.\n" 
            "**Conceito e Integração (Analista de Redes):** Adriano Didi\n"
            "**Desenvolvimento (Código-Fonte):** Gemini (Google)\n"
            "**Linguagem:** Python 3 + Biblioteca PySide6 (Qt)\n\n"
            "Ferramentas de Diagnóstico, Configuração e Manutenção de Windows."
        )


# --- Início do Aplicativo Qt ---
if __name__ == "__main__":
    # Garante a criação da pasta de terceiros se não existir
    if not os.path.exists(THIRD_PARTY_DIR):
        try: os.makedirs(THIRD_PARTY_DIR)
        except: pass
    
    app = QApplication(sys.argv)
    
    # --- SOLUÇÕES PARA ÍCONE NA BARRA DE TAREFAS (WINDOWS) ---
    app.setApplicationName("WinTools") 
    if os.path.exists(ICON_PATH):
        try:
            app.setWindowIcon(QIcon(ICON_PATH)) # Tenta aplicar o ícone no objeto Application também
        except Exception as e:
            print(f"Erro ao tentar aplicar o ícone no QApplication: {e}")
    # ---------------------------------------------------------
            
    window = MainWindow()
    window.show()
    sys.exit(app.exec())