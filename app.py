import csv
import os
import platform
import socket
import subprocess
import threading
import time
import queue
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
import pytz

from flask import Flask, jsonify, render_template, send_file, request
from sqlalchemy import Column, DateTime, Integer, String, create_engine, func
from sqlalchemy.orm import declarative_base, sessionmaker
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

# ===================== CONFIGURAÇÃO =====================
# Configuração do fuso horário de Brasília
BRASILIA_TZ = pytz.timezone('America/Sao_Paulo')
DB_FILE = "status.db"
MACHINES_FILE = "machines.csv"
CHECK_INTERVAL = 10          # segundos entre varreduras
PING_TIMEOUT_MS = 800        # Reduzido para melhor performance
MAX_WORKERS = 32             # Otimizado para eficiência
NETWORK_RANGE = "192.168.0."  # base para varredura (0-254)
PORTAS_TCP_TESTE = [3389, 445, 80]
MAX_RETRIES = 2              # Tentativas de ping
CACHE_TIMEOUT = 300          # Cache timeout em segundos
# ==================================================

app = Flask(__name__, template_folder="templates")
Base = declarative_base()

class HostHistory(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    ip = Column(String)
    status = Column(String)
    latency_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(BRASILIA_TZ))

# Configuração otimizada do banco
engine = create_engine(
    f"sqlite:///{DB_FILE}", 
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
    connect_args={"check_same_thread": False}
)
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

status_cache = {}
machines_cache = []  # Cache das máquinas carregadas
last_machines_load = 0  # Timestamp da última carga
monitoring_stats = {
    "last_scan_duration": 0,
    "successful_checks": 0,
    "failed_checks": 0,
    "total_scans": 0
}

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- Funções utilitárias -----------------

def agora_brasilia():
    """Retorna a data/hora atual no fuso horário de Brasília"""
    return datetime.now(BRASILIA_TZ)

def formatar_data_br(dt):
    """Formata uma data/hora para o padrão brasileiro"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Se não tem timezone, assume que é UTC e converte para Brasília
        dt = pytz.UTC.localize(dt).astimezone(BRASILIA_TZ)
    elif dt.tzinfo != BRASILIA_TZ:
        # Se tem timezone diferente, converte para Brasília
        dt = dt.astimezone(BRASILIA_TZ)
    return dt.strftime("%d/%m/%Y %H:%M:%S")

def ping_icmp(ip: str, retries=MAX_RETRIES):
    """Ping ICMP otimizado com retry automático"""
    is_windows = platform.system().lower() == "windows"
    
    for attempt in range(retries):
        cmd = ["ping", "-n", "1", "-w", str(PING_TIMEOUT_MS), ip] if is_windows else \
              ["ping", "-c", "1", "-W", str(int(PING_TIMEOUT_MS/1000) or 1), ip]
        
        t0 = time.perf_counter()
        try:
            out = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=(PING_TIMEOUT_MS/1000 + 1),
                creationflags=subprocess.CREATE_NO_WINDOW if is_windows else 0
            )
            if out.returncode == 0:
                latency = (time.perf_counter() - t0) * 1000.0
                return True, round(latency, 1)
        except (subprocess.TimeoutExpired, Exception) as e:
            if attempt == retries - 1:
                logger.debug(f"Ping failed for {ip}: {e}")
                continue
    
    return False, None

def tcp_ping(ip: str, port: int, timeout=0.3) -> bool:
    """TCP ping otimizado com timeout menor"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def checar_um_host(host: dict):
    """Verifica status de um host com otimizações de performance"""
    ip = host["ip"]
    name = host["name"]
    
    # Verifica se IP é válido
    if not ip or ip == "?" or "/" in ip:
        return None
    
    try:
        # Primeiro tenta ICMP ping
        online, latency = ping_icmp(ip)
        
        # Se ICMP falhou, tenta TCP nas portas comuns
        if not online:
            for port in PORTAS_TCP_TESTE:
                if tcp_ping(ip, port):
                    online = True
                    latency = None  # TCP ping não mede latência precisa
                    break

        now = agora_brasilia()
        existing = status_cache.get(ip, {})
        old_status = existing.get("status")
        new_status = "Online" if online else "Offline"

        data = {
            "name": name,
            "ip": ip,
            "status": new_status,
            "last_checked": now,
            "latency_ms": latency
        }
        
        # Atualiza cache de forma thread-safe
        status_cache[ip] = data

        # Se mudou de status, grava no banco
        if old_status and old_status != new_status:
            try:
                with SessionLocal() as db:
                    db.add(HostHistory(
                        name=name, 
                        ip=ip, 
                        status=new_status, 
                        latency_ms=latency, 
                        timestamp=now
                    ))
                    db.commit()
            except Exception as e:
                logger.error(f"Erro ao salvar histórico para {ip}: {e}")
        
        # Atualiza estatísticas
        monitoring_stats["successful_checks"] += 1
        return data
        
    except Exception as e:
        logger.error(f"Erro ao verificar host {ip}: {e}")
        monitoring_stats["failed_checks"] += 1
        return None

def carregar_maquinas():
    """Carrega máquinas do CSV com cache inteligente"""
    global machines_cache, last_machines_load
    
    # Verifica se precisa recarregar (cache de 5 minutos)
    now = time.time()
    if machines_cache and (now - last_machines_load) < CACHE_TIMEOUT:
        return machines_cache
    
    maquinas = []
    if os.path.exists(MACHINES_FILE):
        try:
            with open(MACHINES_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)  # Pula o cabeçalho
                for row_num, row in enumerate(reader, 2):  # Começa do 2 por causa do header
                    if len(row) >= 2:
                        name = row[0].strip()
                        ip = row[1].strip()
                        
                        # Filtra IPs inválidos
                        if name and ip and ip != "?" and "/" not in ip:
                            maquinas.append({"name": name, "ip": ip})
                        elif ip and ip != "?":
                            logger.warning(f"IP inválido na linha {row_num}: {ip}")
            
            logger.info(f"Carregadas {len(maquinas)} máquinas do arquivo {MACHINES_FILE}")
            
        except Exception as e:
            logger.error(f"Erro ao carregar máquinas: {e}")
    else:
        logger.warning(f"Arquivo {MACHINES_FILE} não encontrado. Criando varredura automática.")
        # se não existir CSV, tenta varrer rede (ping em range limitado)
        for i in range(1, 51):  # Limita a varredura para performance
            maquinas.append({"name": f"Host-{i}", "ip": f"{NETWORK_RANGE}{i}"})
    
    # Atualiza cache
    machines_cache = maquinas
    last_machines_load = now
    
    return maquinas

def worker_loop():
    """Loop principal de monitoramento otimizado"""
    logger.info("Iniciando worker de monitoramento...")
    
    while True:
        try:
            start_time = time.perf_counter()
            maquinas = carregar_maquinas()
            
            if not maquinas:
                logger.warning("Nenhuma máquina para monitorar")
                time.sleep(CHECK_INTERVAL)
                continue
            
            logger.info(f"Iniciando varredura de {len(maquinas)} máquinas...")
            
            # Reset dos contadores para esta varredura
            monitoring_stats["successful_checks"] = 0
            monitoring_stats["failed_checks"] = 0
            
            # Executa verificações em paralelo
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                futures = [pool.submit(checar_um_host, m) for m in maquinas]
                
                # Processa resultados conforme completam
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=5)
                        if result is None:
                            monitoring_stats["failed_checks"] += 1
                    except Exception as e:
                        logger.error(f"Erro no worker: {e}")
                        monitoring_stats["failed_checks"] += 1
            
            # Calcula tempo da varredura
            scan_duration = time.perf_counter() - start_time
            monitoring_stats["last_scan_duration"] = round(scan_duration, 2)
            monitoring_stats["total_scans"] += 1
            
            logger.info(
                f"Varredura concluída em {scan_duration:.2f}s. "
                f"Sucessos: {monitoring_stats['successful_checks']}, "
                f"Falhas: {monitoring_stats['failed_checks']}"
            )
            
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Erro crítico no worker loop: {e}")
            time.sleep(CHECK_INTERVAL)

# ----------------- Rotas Flask -----------------

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/status")
def status():
    items = list(status_cache.values())
    items.sort(key=lambda x: (x["status"] != "Online", x["name"].lower()))
    resp = []
    for it in items:
        resp.append({
            "name": it["name"],
            "ip": it["ip"],
            "status": it["status"],
            "time_last_checked": formatar_data_br(it["last_checked"]) if it["last_checked"] else None,
            "latency_ms": it["latency_ms"]
        })
    return jsonify(resp)

@app.route("/history/<ip>")
def history(ip):
    with SessionLocal() as db:
        rows = db.query(HostHistory).filter(HostHistory.ip == ip).order_by(HostHistory.timestamp.desc()).limit(50).all()
        data = [
            {
                "status": r.status,
                "latency_ms": r.latency_ms,
                "time": formatar_data_br(r.timestamp)
            }
            for r in rows
        ]
    return jsonify(data)

@app.route("/stats")
def stats():
    items = list(status_cache.values())
    online_count = sum(1 for item in items if item["status"] == "Online")
    offline_count = len(items) - online_count
    
    # Calculate average latency for online machines
    online_latencies = [item["latency_ms"] for item in items if item["status"] == "Online" and item["latency_ms"] is not None]
    avg_latency = round(sum(online_latencies) / len(online_latencies), 2) if online_latencies else 0
    
    return jsonify({
        "total_machines": len(items),
        "online": online_count,
        "offline": offline_count,
        "avg_latency_ms": avg_latency,
        "last_updated": formatar_data_br(agora_brasilia()),
        "monitoring_stats": monitoring_stats
    })

@app.route("/export/excel")
def export_excel():
    items = list(status_cache.values())
    items.sort(key=lambda x: (x["status"] != "Online", x["name"].lower()))
    
    # Create DataFrame
    data = []
    for item in items:
        data.append({
            "Nome da Máquina": item["name"],
            "Endereço IP": item["ip"],
            "Status": item["status"],
            "Latência (ms)": item["latency_ms"] if item["latency_ms"] else "N/A",
            "Última Verificação": formatar_data_br(item["last_checked"]) if item["last_checked"] else "Nunca"
        })
    
    # Create Excel using simpler pandas approach
    import pandas as pd
    
    df = pd.DataFrame(data)
    
    # Create Excel in memory
    buffer = io.BytesIO()
    
    # Add header information
    header_data = []
    agora = agora_brasilia()
    header_data.append(['Sistemas Olivium - Relatório de Status da Rede'])
    header_data.append([f'Gerado em: {formatar_data_br(agora)}'])
    header_data.append([''])
    
    # Add summary
    online_count = sum(1 for item in items if item["status"] == "Online")
    offline_count = len(items) - online_count
    header_data.append([f'Resumo: {len(items)} máquinas | {online_count} Online | {offline_count} Offline'])
    header_data.append([''])
    
    # Create header DataFrame
    header_df = pd.DataFrame(header_data)
    
    # Write to Excel with multiple sheets/sections
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        # Write header
        header_df.to_excel(writer, sheet_name='Status da Rede', index=False, header=False, startrow=0)
        
        # Write main data
        df.to_excel(writer, sheet_name='Status da Rede', index=False, startrow=6)
        
        # Get the workbook and worksheet for styling
        workbook = writer.book
        worksheet = writer.sheets['Status da Rede']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = min(max(max_length + 2, 15), 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'relatorio_rede_{agora.strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route("/export/pdf")
def export_pdf():
    items = list(status_cache.values())
    items.sort(key=lambda x: (x["status"] != "Online", x["name"].lower()))
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4), 
        rightMargin=40, 
        leftMargin=40, 
        topMargin=60, 
        bottomMargin=60
    )
    
    # Define professional styles
    styles = getSampleStyleSheet()
    
    # Custom styles for modern look
    title_style = ParagraphStyle(
        'ModernTitle',
        parent=styles['Heading1'],
        fontSize=20,
        fontName='Helvetica-Bold',
        spaceAfter=30,
        alignment=1,  # Center alignment
        textColor=colors.HexColor('#1e40af')  # Professional blue
    )
    
    subtitle_style = ParagraphStyle(
        'ModernSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        fontName='Helvetica',
        spaceAfter=20,
        alignment=1,
        textColor=colors.HexColor('#64748b')  # Gray
    )
    
    summary_style = ParagraphStyle(
        'ModernSummary',
        parent=styles['Normal'],
        fontSize=11,
        fontName='Helvetica',
        spaceAfter=20,
        leftIndent=20,
        textColor=colors.HexColor('#374151')
    )
    
    # Create content
    story = []
    
    # Professional Header
    agora = agora_brasilia()
    title = Paragraph('Sistemas Olivium', title_style)
    subtitle = Paragraph(f'Relatório de Status da Rede<br/>Gerado em: {formatar_data_br(agora)}', subtitle_style)
    
    story.append(title)
    story.append(subtitle)
    story.append(Spacer(1, 30))
    
    # Summary statistics with modern styling
    online_count = sum(1 for item in items if item["status"] == "Online")
    offline_count = len(items) - online_count
    online_latencies = [item["latency_ms"] for item in items if item["status"] == "Online" and item["latency_ms"] is not None]
    avg_latency = round(sum(online_latencies) / len(online_latencies), 2) if online_latencies else 0
    
    summary_text = f'''
    <b>Resumo Executivo:</b><br/>
    <br/>
    • Total de Máquinas Monitoradas: <b>{len(items)}</b><br/>
    • Máquinas Online: <b style="color: #059669">{online_count}</b><br/>
    • Máquinas Offline: <b style="color: #dc2626">{offline_count}</b><br/>
    • Latência Média: <b>{avg_latency}ms</b><br/>
    • Taxa de Disponibilidade: <b>{round((online_count/len(items)*100), 1) if items else 0}%</b><br/>
    '''
    summary = Paragraph(summary_text, summary_style)
    story.append(summary)
    story.append(Spacer(1, 30))
    
    # Professional table with modern styling
    table_data = [['Nome da Máquina', 'Endereço IP', 'Status', 'Latência (ms)', 'Última Verificação']]
    
    for item in items:
        table_data.append([
            item["name"],
            item["ip"],
            item["status"],
            str(item["latency_ms"]) if item["latency_ms"] else "N/A",
            formatar_data_br(item["last_checked"]) if item["last_checked"] else "Nunca"
        ])
    
    # Create modern table
    table = Table(table_data, colWidths=[2.2*inch, 1.8*inch, 1*inch, 1*inch, 1.8*inch])
    table.setStyle(TableStyle([
        # Modern header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 15),
        ('TOPPADDING', (0, 0), (-1, 0), 15),
        
        # Modern body styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8fafc'), colors.white]),
        
        # Column alignment
        ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Status column center
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Latency column center
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    # Modern status cell colors
    for i, item in enumerate(items, 1):
        if item["status"] == "Online":
            table.setStyle(TableStyle([
                ('BACKGROUND', (2, i), (2, i), colors.HexColor('#dcfce7')),
                ('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#166534'))
            ]))
        else:
            table.setStyle(TableStyle([
                ('BACKGROUND', (2, i), (2, i), colors.HexColor('#fecaca')),
                ('TEXTCOLOR', (2, i), (2, i), colors.HexColor('#991b1b'))
            ]))
    
    story.append(table)
    story.append(Spacer(1, 40))
    
    # Professional Footer
    footer_style = ParagraphStyle(
        'ModernFooter',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        alignment=1,
        textColor=colors.HexColor('#6b7280')
    )
    
    footer_text = f'© {agora.year} Sistemas Olivium - Todos os direitos reservados'
    footer = Paragraph(footer_text, footer_style)
    story.append(footer)
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'relatorio_rede_{agora.strftime("%Y%m%d_%H%M%S")}.pdf'
    )

@app.route("/alerts")
def alerts():
    offline_machines = []
    for item in status_cache.values():
        if item["status"] == "Offline" and item["last_checked"]:
            time_diff = agora_brasilia() - item["last_checked"]
            if time_diff.total_seconds() > 300:  # Offline for more than 5 minutes
                offline_machines.append({
                    "name": item["name"],
                    "ip": item["ip"],
                    "offline_since": formatar_data_br(item["last_checked"]),
                    "offline_duration": str(time_diff).split('.')[0]
                })
    
    return jsonify({
        "critical_alerts": len(offline_machines),
        "offline_machines": offline_machines
    })

@app.route("/search")
def search():
    query = request.args.get('q', '').lower()
    status_filter = request.args.get('status', '')
    
    items = list(status_cache.values())
    
    if query:
        items = [item for item in items if 
                query in item["name"].lower() or 
                query in item["ip"].lower()]
    
    if status_filter:
        items = [item for item in items if item["status"].lower() == status_filter.lower()]
    
    items.sort(key=lambda x: (x["status"] != "Online", x["name"].lower()))
    
    resp = []
    for it in items:
        resp.append({
            "name": it["name"],
            "ip": it["ip"],
            "status": it["status"],
            "time_last_checked": formatar_data_br(it["last_checked"]) if it["last_checked"] else None,
            "latency_ms": it["latency_ms"]
        })
    
    return jsonify(resp)

# ----------------- Inicialização -----------------

def inicializar_cache():
    """Inicializa o cache com todas as máquinas conhecidas"""
    logger.info("Inicializando cache de máquinas...")
    for m in carregar_maquinas():
        status_cache[m["ip"]] = {
            "name": m["name"],
            "ip": m["ip"],
            "status": "Desconhecido",
            "last_checked": None,
            "latency_ms": None
        }
    logger.info(f"Cache inicializado com {len(status_cache)} máquinas")

if __name__ == "__main__":
    # Configure Flask cache headers for better performance
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    inicializar_cache()
    
    # Start monitoring thread
    monitoring_thread = threading.Thread(target=worker_loop, daemon=True)
    monitoring_thread.start()
    
    logger.info("Sistema de monitoramento iniciado com sucesso!")
    
    # Run Flask server with host 0.0.0.0 for Replit compatibility
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)