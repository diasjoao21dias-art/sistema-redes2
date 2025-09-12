# Sistemas Olivium - Painel de Monitoramento de Rede

## 📋 Visão Geral

O Sistema de Monitoramento de Rede da Sistemas Olivium é uma solução profissional e moderna para monitoramento em tempo real de dispositivos de rede. O sistema oferece uma interface web elegante e responsiva, com capacidade de monitorar centenas de máquinas simultaneamente através de verificações ICMP ping e TCP.

### ✨ Principais Recursos

- **Monitoramento em Tempo Real**: Verificação automática do status online/offline de todas as máquinas
- **Interface Moderna**: Dashboard profissional com modo escuro/claro alternável
- **Exportação de Relatórios**: Geração de relatórios PDF profissionais com header e footer personalizados
- **Histórico Completo**: Rastreamento de mudanças de status com timestamps em horário de Brasília
- **Alertas Inteligentes**: Notificações para máquinas offline por mais de 5 minutos
- **Performance Otimizada**: Sistema otimizado para lidar com dezenas de máquinas eficientemente
- **Busca e Filtros**: Pesquisa por nome ou IP com filtros de status
- **Responsivo**: Interface adaptável para diferentes tamanhos de tela

## 🚀 Instalação

### Pré-requisitos

- Python 3.11 ou superior
- Sistema operacional: Windows ou Linux
- Acesso de rede para as máquinas que serão monitoradas

### Passo 1: Clonar ou baixar o projeto

```bash
# Se usando git
git clone [url-do-repositorio]
cd sistema-monitoramento-rede

# Ou simplesmente extrair os arquivos para uma pasta
```

### Passo 2: Instalar dependências

O projeto usa uv para gerenciamento de dependências (recomendado) ou pip tradicional:

**Usando uv (recomendado):**
```bash
# O uv será instalado automaticamente se necessário
uv add flask sqlalchemy pytz reportlab openpyxl pandas
```

**Usando pip:**
```bash
pip install flask sqlalchemy pytz reportlab openpyxl pandas
```

### Passo 3: Configurar o arquivo de máquinas

Edite o arquivo `machines.csv` com suas máquinas:

```csv
Nome,IP
SERVIDOR-01,192.168.0.10
FINANCEIRO-PC,192.168.0.15
RECEPCAO-01,192.168.0.20
CME-04,192.168.0.25
```

**Formato do arquivo:**
- Primeira linha deve ser o cabeçalho: `Nome,IP`
- Cada linha seguinte deve ter: `Nome da Máquina,Endereço IP`
- IPs inválidos (com "/" ou "?") serão automaticamente ignorados
- Linhas vazias são ignoradas

## ▶️ Como Executar

### Iniciar o sistema

```bash
python app.py
```

### Acessar o dashboard

Abra seu navegador e acesse:
```
http://localhost:5000
```

O sistema estará disponível imediatamente e começará a monitorar as máquinas automaticamente.

## 📊 Funcionalidades Detalhadas

### Dashboard Principal

O dashboard moderno oferece:

**📈 Estatísticas em Tempo Real:**
- Total de máquinas monitoradas
- Número de máquinas online/offline
- Latência média da rede
- Última atualização

**🔍 Pesquisa e Filtros:**
- Pesquisa por nome da máquina ou endereço IP
- Filtro por status (Online/Offline/Todos)
- Resultados em tempo real

**📋 Tabela de Máquinas:**
- Status visual com cores (verde=online, vermelho=offline)
- Latência em millisegundos
- Data/hora da última verificação
- Histórico individual de cada máquina

### ⚡ Modo Escuro/Claro

**Como usar:**
1. Clique no ícone de lua/sol no canto superior direito
2. A preferência é salva automaticamente no navegador
3. O sistema detecta automaticamente a preferência do sistema operacional

### 📄 Exportação de Relatórios PDF

**Como gerar:**
1. Clique no botão "Exportar PDF" no header
2. O arquivo será baixado automaticamente

**Conteúdo do relatório:**
- Header profissional com logo "Sistemas Olivium"
- Data e hora de geração
- Resumo executivo com estatísticas
- Tabela completa de todas as máquinas
- Footer com direitos autorais e ano atual
- Styling profissional com cores modernas

### 📈 Histórico de Máquinas

**Como visualizar:**
1. Na tabela principal, clique em "Histórico" na linha da máquina desejada
2. Modal será aberto com os últimos 50 registros de mudança de status
3. Mostra timestamps precisos e latência quando disponível

## ⚙️ Configuração Avançada

### Parâmetros do Sistema

No arquivo `app.py`, você pode ajustar:

```python
CHECK_INTERVAL = 10          # Intervalo entre varreduras (segundos)
PING_TIMEOUT_MS = 800        # Timeout do ping (millisegundos)
MAX_WORKERS = 32             # Número máximo de threads paralelas
PORTAS_TCP_TESTE = [3389, 445, 80]  # Portas para teste TCP
MAX_RETRIES = 2              # Tentativas de ping antes de considerar offline
```

### Algoritmo de Detecção

O sistema usa um algoritmo inteligente em duas etapas:

1. **ICMP Ping**: Primeira tentativa usando ping tradicional
2. **TCP Check**: Se ICMP falhar, testa portas comuns (RDP, SMB, HTTP)
3. **Múltiplas Tentativas**: Até 2 tentativas antes de marcar como offline

### Performance e Otimizações

**Otimizações implementadas:**
- Threading otimizado com pool de 32 workers
- Cache inteligente de máquinas (5 minutos)
- Timeout reduzido para melhor responsividade
- Logging detalhado para monitoramento
- Conexões de banco otimizadas
- Filtros de IP inválidos

## 🔧 Solução de Problemas

### Problema: Máquinas não aparecem

**Solução:**
1. Verifique o formato do arquivo `machines.csv`
2. Certifique-se que não há caracteres especiais nos IPs
3. Verifique os logs no console para erros de carregamento

### Problema: Máquinas sempre offline

**Possíveis causas:**
1. **Firewall**: Máquinas podem estar bloqueando ping
2. **Rede**: Problemas de conectividade de rede
3. **IPs inválidos**: Verifique se os IPs estão corretos

**Solução:**
1. Teste ping manual: `ping 192.168.0.10`
2. Verifique se as portas TCP estão abertas
3. Confirme que a máquina de monitoramento tem acesso à rede

### Problema: Sistema lento

**Solução:**
1. Reduza o número de máquinas monitoradas
2. Aumente o `CHECK_INTERVAL` para 15-30 segundos
3. Reduza `MAX_WORKERS` se tiver limitações de CPU

### Problema: PDF não exporta

**Possíveis causas:**
1. Biblioteca reportlab não instalada corretamente
2. Permissões de escrita no navegador

**Solução:**
```bash
# Reinstalar dependências
pip install --force-reinstall reportlab
# ou
uv add reportlab
```

## 🔧 Manutenção

### Banco de Dados

O sistema usa SQLite (`status.db`) para armazenar o histórico. Para limpeza:

```bash
# Backup do banco
cp status.db status_backup.db

# O banco é automaticamente otimizado pelo sistema
```

### Logs

Os logs são exibidos no console. Para log permanente:

```bash
python app.py > monitoramento.log 2>&1
```

### Atualização de Máquinas

Para adicionar/remover máquinas:
1. Edite o arquivo `machines.csv`
2. O sistema detectará automaticamente as mudanças em até 5 minutos
3. Não é necessário reiniciar o sistema

## 📱 Compatibilidade

### Navegadores Suportados
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Sistemas Operacionais
- **Servidor**: Windows, Linux
- **Cliente**: Qualquer sistema com navegador moderno

### Dispositivos Móveis
- Interface totalmente responsiva
- Funciona em tablets e smartphones
- Modo escuro/claro em todos os dispositivos

## 🚨 Alertas e Notificações

### Alertas Críticos

O sistema automaticamente identifica:
- Máquinas offline por mais de 5 minutos
- Quantidade total de alertas críticos
- Duração do tempo offline

**Como visualizar:**
- Alertas aparecem automaticamente no dashboard
- Seção específica com destaque visual
- Atualização em tempo real

## 🎨 Personalização Visual

### Cores e Temas

**Modo Claro:**
- Background: Tons de branco e cinza claro
- Acentos: Azul profissional (#1e40af)
- Status: Verde (#059669) e vermelho (#dc2626)

**Modo Escuro:**
- Background: Tons de slate/cinza escuro
- Texto: Branco e cinza claro
- Mantém mesmos acentos para consistência

### Header Fixo

- O header "Sistemas Olivium" permanece visível durante scroll
- Gradiente profissional azul/roxo no ícone
- Toggle de modo escuro/claro sempre acessível

### Footer Profissional

- Copyright dinâmico com ano atual
- Adapta automaticamente ao tema ativo
- Posicionamento fixo na parte inferior

## 📞 Suporte

### Para Problemas Técnicos

1. **Verifique os logs** no console do sistema
2. **Teste conectividade** manual com as máquinas
3. **Confirme permissões** de rede e firewall
4. **Valide o arquivo** `machines.csv`

### Contato

Para suporte adicional, consulte a equipe de TI da Sistemas Olivium.

---

## 📝 Changelog

### Versão 2.0 (Atual)
- ✨ Interface completamente modernizada
- 🌙 Modo escuro/claro
- 📊 Dashboard profissional
- ⚡ Performance otimizada
- 📄 PDF export aprimorado
- 🔧 Backend otimizado com threading
- 📱 Design responsivo completo

### Versão 1.0
- Monitoramento básico de rede
- Interface simples
- Exportação CSV

---

**© 2025 Sistemas Olivium - Todos os direitos reservados**