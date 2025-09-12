===============================================================================
                  SISTEMAS OLIVIUM - SISTEMA DE MONITORAMENTO DE REDE
                                    Versão 2.0
===============================================================================

Este é um sistema profissional de monitoramento de rede em tempo real que 
permite acompanhar o status de todos os dispositivos conectados à sua rede. 
O sistema foi modernizado com interface web responsiva, modo escuro/claro e 
exportação profissional de relatórios.

===============================================================================
                               CARACTERÍSTICAS
===============================================================================

• Monitoramento em tempo real de dispositivos de rede via ICMP e TCP
• Interface web moderna e responsiva com modo escuro/claro
• Dashboard profissional com estatísticas em tempo real
• Pesquisa e filtros avançados de dispositivos
• Exportação de relatórios em PDF e Excel com branding profissional
• Histórico detalhado de status de cada máquina
• Sistema de alertas para dispositivos offline
• Scan otimizado de até 144 dispositivos em menos de 5 segundos
• Compatível com Windows e Linux

===============================================================================
                              REQUISITOS DO SISTEMA
===============================================================================

SOFTWARE OBRIGATÓRIO:
• Python 3.8 ou superior (recomendado Python 3.11)
• Navegador web moderno (Chrome, Firefox, Edge, Safari)
• Acesso à rede local onde os dispositivos serão monitorados
• Privilégios de administrador (para ping ICMP)

DEPENDÊNCIAS PYTHON (instaladas automaticamente):
• Flask - Framework web
• SQLAlchemy - Banco de dados
• Pandas - Manipulação de dados
• OpenPyXL - Exportação Excel  
• ReportLab - Exportação PDF
• PyTZ - Fuso horário brasileiro

===============================================================================
                          INSTALAÇÃO PASSO A PASSO
===============================================================================

PASSO 1: PREPARAR O AMBIENTE
----------------------------

1.1. Instalar Python:
   • Windows: Baixe de https://python.org/downloads/
   • Linux Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip
   • Linux CentOS/RHEL: sudo yum install python3 python3-pip

1.2. Verificar instalação:
   python3 --version
   pip3 --version

PASSO 2: BAIXAR E PREPARAR O SISTEMA
------------------------------------

2.1. Extrair os arquivos do sistema para uma pasta, exemplo:
   Windows: C:\SistemasOlivium\
   Linux: /opt/sistemas-olivium/

2.2. Abrir terminal/prompt na pasta do sistema:
   Windows: Shift + Clique direito na pasta → "Abrir PowerShell aqui"
   Linux: Abrir terminal e navegar: cd /opt/sistemas-olivium/

PASSO 3: INSTALAR DEPENDÊNCIAS
-------------------------------

3.1. Instalar bibliotecas Python:
   Windows: pip install flask sqlalchemy pandas openpyxl reportlab pytz
   Linux: pip3 install flask sqlalchemy pandas openpyxl reportlab pytz

3.2. Verificar instalação (deve mostrar as versões):
   python3 -c "import flask, sqlalchemy, pandas; print('Dependências OK')"

PASSO 4: CONFIGURAR LISTA DE MÁQUINAS
-------------------------------------

4.1. Editar o arquivo "machines.csv" com suas máquinas:
   • Abra com editor de texto (Notepad++, gedit, nano, etc.)
   • Formato: NOME_MAQUINA,ENDERECO_IP
   • Exemplo:
     SERVIDOR-PRINCIPAL,192.168.1.100
     DESKTOP-ADMIN,192.168.1.101
     IMPRESSORA-HP,192.168.1.102

4.2. Salvar o arquivo mantendo a codificação UTF-8

PASSO 5: INICIAR O SISTEMA
--------------------------

5.1. Executar o sistema:
   python3 app.py

5.2. Aguardar as mensagens de inicialização:
   ✓ Carregadas X máquinas do arquivo machines.csv
   ✓ Sistema de monitoramento iniciado com sucesso!
   ✓ Running on http://0.0.0.0:5000

5.3. O sistema estará disponível em:
   • Local: http://localhost:5000
   • Rede: http://SEU_IP:5000 (substitua SEU_IP pelo IP do servidor)

===============================================================================
                            CONFIGURAÇÃO AVANÇADA
===============================================================================

CONFIGURAR FAIXAS DE IP AUTOMÁTICAS:
------------------------------------
Para monitorar faixas inteiras de IP, adicione no machines.csv:
REDE-DHCP-1,192.168.1.50-192.168.1.100
REDE-SERVIDOR,10.0.0.1-10.0.0.50

ALTERAR PORTA DO SISTEMA:
-------------------------
Edite o arquivo app.py na última linha:
app.run(host="0.0.0.0", port=8080, debug=False)

AJUSTAR TIMEOUT DE PING:
------------------------
No arquivo app.py, localize e altere:
PING_TIMEOUT = 1000  # Valor em milissegundos

CONFIGURAR THREADS DE MONITORAMENTO:
-----------------------------------
No arquivo app.py, altere o número de workers:
MAX_WORKERS = 32  # Máximo de verificações simultâneas

===============================================================================
                               USANDO O SISTEMA
===============================================================================

ACESSAR O DASHBOARD:
-------------------
1. Abra seu navegador
2. Digite: http://localhost:5000
3. O dashboard carregará automaticamente

FUNCIONALIDADES PRINCIPAIS:
---------------------------

• CARDS DE STATUS: Visualize total, online, offline e latência média
• PESQUISAR: Digite nome ou IP na caixa de busca
• FILTRAR: Use o dropdown para filtrar por status (Online/Offline)
• HISTÓRICO: Clique em "Histórico" ao lado de qualquer máquina
• MODO ESCURO: Clique no ícone da lua no cabeçalho
• EXPORTAR PDF: Clique no botão "PDF" para relatório completo
• EXPORTAR EXCEL: Clique no botão "Excel" para planilha detalhada

INTERPRETAR STATUS:
------------------
• Verde (Online): Máquina respondendo normalmente
• Vermelho (Offline): Máquina não responde a ping/TCP
• Cinza (Desconhecido): Primeira verificação ou erro temporário

LATÊNCIA:
---------
• Valores baixos (< 50ms): Rede excelente
• Valores médios (50-200ms): Rede boa
• Valores altos (> 200ms): Possível congestionamento

===============================================================================
                            SOLUÇÃO DE PROBLEMAS
===============================================================================

PROBLEMA: "Comando não encontrado" ou "Python not found"
SOLUÇÃO: Certifique-se que Python está instalado e no PATH do sistema

PROBLEMA: Erro de permissão para ping
SOLUÇÃO Windows: Execute como Administrador
SOLUÇÃO Linux: sudo python3 app.py

PROBLEMA: "ModuleNotFoundError"
SOLUÇÃO: Reinstale as dependências: pip3 install -r requirements.txt

PROBLEMA: Site não carrega
SOLUÇÃO: Verifique se a porta 5000 não está bloqueada pelo firewall

PROBLEMA: Máquinas não aparecem
SOLUÇÃO: Verifique o formato do arquivo machines.csv (sem espaços extras)

PROBLEMA: Performance lenta
SOLUÇÃO: Reduza o número de máquinas ou aumente MAX_WORKERS

PROBLEMA: Exportação PDF/Excel não funciona
SOLUÇÃO: Instale: pip3 install reportlab openpyxl

===============================================================================
                          CONFIGURAÇÃO DE FIREWALL
===============================================================================

WINDOWS:
--------
1. Painel de Controle → Sistema e Segurança → Firewall do Windows
2. Configurações Avançadas → Regras de Entrada → Nova Regra
3. Tipo: Porta → TCP → Porta 5000 → Permitir
4. Aplicar para todos os perfis

LINUX (UFW):
------------
sudo ufw allow 5000/tcp
sudo ufw reload

LINUX (iptables):
-----------------
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
sudo service iptables save

===============================================================================
                            EXECUTAR COMO SERVIÇO
===============================================================================

WINDOWS (como Serviço):
-----------------------
1. Instale: pip install pywin32
2. Crie um arquivo de serviço usando o módulo win32serviceutil

LINUX (systemd):
----------------
1. Crie o arquivo: /etc/systemd/system/olivium-monitor.service

   [Unit]
   Description=Sistemas Olivium Network Monitor
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/sistemas-olivium
   ExecStart=/usr/bin/python3 app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target

2. Ative o serviço:
   sudo systemctl daemon-reload
   sudo systemctl enable olivium-monitor
   sudo systemctl start olivium-monitor

3. Verificar status:
   sudo systemctl status olivium-monitor

===============================================================================
                              BACKUP E MANUTENÇÃO
===============================================================================

ARQUIVOS IMPORTANTES PARA BACKUP:
---------------------------------
• machines.csv - Lista de máquinas
• status.db - Histórico de monitoramento
• app.py - Configurações do sistema

LIMPEZA DE HISTÓRICO:
--------------------
Para limpar dados antigos, delete o arquivo status.db
O sistema criará um novo banco automaticamente

ATUALIZAÇÃO:
-----------
1. Pare o sistema (Ctrl+C)
2. Faça backup dos arquivos importantes
3. Substitua os arquivos do sistema
4. Reinicie: python3 app.py

===============================================================================
                               SUPORTE TÉCNICO
===============================================================================

LOGS DO SISTEMA:
---------------
Os logs aparecem no terminal onde o sistema foi iniciado
Para salvar logs: python3 app.py > sistema.log 2>&1

INFORMAÇÕES DE DEBUG:
--------------------
• Versão Python: python3 --version
• Dependências: pip3 list
• Porta em uso: netstat -an | grep 5000
• Conectividade: ping 192.168.1.1

PERFORMANCE:
-----------
• Verifique CPU/memória com top ou Task Manager
• Monitore rede com iftop ou Resource Monitor
• Ajuste MAX_WORKERS conforme capacidade do servidor

===============================================================================
                              ESPECIFICAÇÕES
===============================================================================

CAPACIDADES:
• Máximo testado: 500+ dispositivos
• Scan típico: 144 dispositivos em 4-5 segundos
• Protocolos: ICMP ping + TCP (portas 80, 443, 3389, 445)
• Banco de dados: SQLite (local)
• Concurrent checks: 32 threads padrão

COMPATIBILIDADE:
• Python: 3.8, 3.9, 3.10, 3.11+
• Navegadores: Chrome 90+, Firefox 88+, Edge 90+, Safari 14+
• OS: Windows 10/11, Ubuntu 18.04+, CentOS 7+, Debian 9+

===============================================================================
                                 LICENÇA
===============================================================================

Copyright © 2025 Sistemas Olivium
Todos os direitos reservados.

Este software é fornecido "como está", sem garantias de qualquer tipo.
O uso é permitido para fins internos da organização.

===============================================================================
                               VERSÃO E DATA
===============================================================================

Versão: 2.0.0
Data: Setembro 2025
Última atualização: 06/09/2025

Para mais informações e suporte, consulte a documentação técnica ou
entre em contato com o administrador do sistema.

===============================================================================