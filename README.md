A# 🛠️ WinTools - Kit de Ferramentas de Rede e Sistema (Windows)

[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/SEU_USUARIO/SEU_REPOSITORIO?style=for-the-badge&sort=semver)](LINK_PARA_SUA_PAGINA_DE_RELEASES) 
[![Licença MIT](https://img.shields.io/badge/Licença-MIT-blue.svg?style=for-the-badge)](LICENSE)

O WinTools é uma ferramenta de diagnóstico e manutenção para Windows que consolida dezenas de comandos e utilitários de sistema (como Netsh, IPConfig, Ping, CHKDSK, Winget, etc.) em uma interface gráfica simples e unificada.

Desenvolvido para **Analistas de Redes/Suporte** que precisam de acesso rápido a diagnósticos complexos.

---

## ✨ Principais Funcionalidades

* **Reset de Rede Completo (Netsh):** Opção crucial para rodar `winsock reset`, `int ip reset`, `tcp reset` e `advfirewall reset` com um único clique (Requer Admin).
* **Diagnóstico de Conexão:** Ping Contínuo, PathPing, Telnet (Verificador de Porta em Python) e Curl para requisições rápidas.
* **Informações de Rede:** Visualização limpa e filtrada de IP, Máscara, Gateway e MAC (sem o lixo do `ipconfig /all`).
* **Utilitários Avançados:** Acesso rápido a comandos como `sfc /scannow`, `tasklist`, `winget` e `chkdsk`.
* **Ferramentas de Terceiros:** Interface com barra de busca para executar qualquer `.exe` ou script dentro da pasta `FerramentasTerceiros`.

## ⬇️ Download e Instalação (Recomendado)

A maneira mais fácil e rápida de usar o WinTools é baixando o executável pré-compilado:

1.  **Vá para a página de [Releases](LINK_PARA_SUA_PAGINA_DE_RELEASES).**
2.  Baixe o arquivo **`WinTools_v2.0.14.zip`** (ou a versão mais recente).
3.  Descompacte o arquivo e execute **`wintools.exe`**.

> **⚠️ Atenção:** Muitos comandos exigem **privilégios de Administrador** para funcionar. Por favor, execute o arquivo como Administrador.

## 👨‍💻 Para Desenvolvedores (Rodando do Código-Fonte)

Se você deseja inspecionar ou modificar o código-fonte:

1.  **Pré-requisitos:** Python 3.11+ e as bibliotecas listadas em `requirements.txt`.
2.  **Instalar dependências:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Executar:**
    ```bash
    python wintools.py
    ```

### Compilação (Usando PyInstaller)

Para gerar seu próprio executável:

```bash

pyinstaller --windowed --onefile --icon=w_tools.ico wintools.py
