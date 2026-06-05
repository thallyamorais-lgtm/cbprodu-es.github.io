"""
Servidor local para geração de PDF.
Execute: python3 servidor_local.py
Mantém rodando na porta 5000. Deixe aberto enquanto usa o sistema.
"""
import http.server, json, base64, os, sys, tempfile, threading
from urllib.parse import urlparse

PORT = 5000
LOGO_PATH = os.path.join(os.path.dirname(__file__), 'logo_cb.png')

ALLOW_ORIGIN = '*'

def gerar_pdf(data, logo_path, preco_override=None):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as rl_canvas
    import io

    PW, PH = A4
    COL = [19.0,51.8,175.6,205.4,245.1,300.9,330.6,406.4,459.5,514.6,572.2]
    X0,C_LOGO,C_DESC,C_QTY,C_VUNIT,C_VTOT,C_QACUM,C_VACUM,C_QTOT,C_ATOT,C_TPAGO,X1 = \
        COL[0],COL[1],COL[1],COL[2],COL[3],COL[4],COL[5],COL[6],COL[7],COL[8],COL[9],COL[10]
    TW = X1-X0
    R_TOPSTRIP=8.78;R_HEADER=33.82;R_MES=8.76;R_EQUIPE=8.82;R_BLANK=8.76
    R_MEMBER=8.76;R_SEP=8.78;R_THDR_A=8.78;R_THDR_B=24.38
    R_DATA0=14.74;R_DATA=8.88;R_DESCONTO=8.84;R_SP1=8.80;R_SP2=9.14
    R_TOTAL=8.77;R_SP3=8.46;R_PROD=8.93;GAP=16.5
    C_MA=colors.HexColor('#FCE4D6');C_AA=colors.HexColor('#DEEAF1')
    C_AT=colors.HexColor('#E2EFDA');C_TOT=colors.HexColor('#BFBFBF')
    C_LOGO_BG=colors.HexColor('#1A1A1A');BLACK=colors.black

    def brl(v):
        neg=v<0
        s=f"{abs(v):,.2f}".replace(',','_').replace('.',',').replace('_','.')
        return f"-R$ {s}" if neg else f"R$ {s}"
    def n2(v): return f"{float(v):,.2f}".replace(',','_').replace('.',',').replace('_','.')
    def ficha_h(n): return (R_TOPSTRIP+R_HEADER+R_MES+R_EQUIPE+R_BLANK+R_MEMBER*3+R_SEP+
                            R_THDR_A+R_THDR_B+(R_DATA0 if n>0 else 0)+R_DATA*max(0,n-1)+
                            R_DESCONTO+R_SP1+R_SP2+R_TOTAL+R_SP3+R_PROD)
    def box(cv,x,yt,w,h,bg=None):
        cv.saveState();cv.setLineWidth(0.4);cv.setStrokeColor(BLACK)
        if bg: cv.setFillColor(bg);cv.rect(x,yt-h,w,h,fill=1,stroke=1)
        else: cv.rect(x,yt-h,w,h,fill=0,stroke=1)
        cv.restoreState()
    def vline(cv,x,yt,h):
        cv.saveState();cv.setLineWidth(0.3);cv.setStrokeColor(BLACK)
        cv.line(x,yt,x,yt-h);cv.restoreState()
    def tc(cv,t,xl,xr,yt,rh,sz,bold=False):
        cv.saveState();cv.setFont('Helvetica-Bold'if bold else'Helvetica',sz)
        cv.setFillColor(BLACK);cv.drawCentredString((xl+xr)/2,yt-rh*0.5-sz*0.35,str(t));cv.restoreState()
    def tl(cv,t,xl,yt,rh,sz,bold=False,pad=2):
        cv.saveState();cv.setFont('Helvetica-Bold'if bold else'Helvetica',sz)
        cv.setFillColor(BLACK);cv.drawString(xl+pad,yt-rh*0.5-sz*0.35,str(t));cv.restoreState()
    def tr(cv,t,xr,yt,rh,sz,bold=False,pad=2):
        cv.saveState();cv.setFont('Helvetica-Bold'if bold else'Helvetica',sz)
        cv.setFillColor(BLACK);cv.drawRightString(xr-pad,yt-rh*0.5-sz*0.35,str(t));cv.restoreState()
    def cl(cv,bg,xl,xr,y,h,l1,l2=None):
        box(cv,xl,y,xr-xl,h,bg=bg);cv.setFont('Helvetica-Bold',6);cv.setFillColor(BLACK)
        if l2: cv.drawCentredString((xl+xr)/2,y-h*0.32,l1);cv.drawCentredString((xl+xr)/2,y-h*0.65,l2)
        else: cv.drawCentredString((xl+xr)/2,y-h*0.5,l1)
    ALL_DIV=[C_DESC,C_QTY,C_VUNIT,C_VTOT,C_QACUM,C_VACUM,C_QTOT,C_ATOT,C_TPAGO]

    def draw_ficha(cv,top,team,mes,ano):
        nm=len(team['members']);rows=team.get('rows',[]);y=top
        logo_w=C_LOGO-X0
        # top strip
        h=R_TOPSTRIP;box(cv,X0,y,TW,h);tl(cv,'Identificação:',C_TPAGO,y,h,5.5,pad=2);y-=h
        # header
        h=R_HEADER;box(cv,X0,y,TW,h)
        box(cv,X0,y,logo_w,h,bg=C_LOGO_BG)
        if logo_path and os.path.exists(logo_path):
            cv.drawImage(logo_path,X0+1,y-h+1,width=logo_w-2,height=h-2,preserveAspectRatio=True,mask='auto')
        cv.setFont('Helvetica-Bold',6.5);cv.setFillColor(BLACK)
        cv.drawString(C_LOGO+3,y-h*0.32,'Sistema de Gestão da Qualidade')
        cv.drawString(C_LOGO+3,y-h*0.58,'LOTEAMENTO JOSE BERNARDINO I e II')
        title_cx=C_LOGO+3+(C_ATOT-C_LOGO-3)/2
        cv.setFont('Helvetica-Bold',8.5)
        cv.drawCentredString(title_cx,y-h*0.30,'CONTROLE DE PRODUÇÃO')
        cv.drawCentredString(title_cx,y-h*0.58,'PISO E REVESTIMENTO CERÂMICO')
        vline(cv,C_ATOT,y,h)
        mid_y=y-h/2;cv.saveState();cv.setLineWidth(0.4);cv.line(C_ATOT,mid_y,X1,mid_y);cv.restoreState()
        cv.setFont('Helvetica',5.5);cv.setFillColor(BLACK)
        cv.drawString(C_ATOT+2,y-h*0.27,'PQO - Anexo A')
        cv.drawString(C_ATOT+2,y-h*0.68,'Revisão: 02')
        y-=h
        # mes
        h=R_MES;box(cv,X0,y,TW,h)
        tl(cv,'Mês:',X0,y,h,7,bold=True);tl(cv,mes.upper(),X0+22,y,h,7,bold=True)
        tr(cv,f'Ano: {ano}',X1,y,h,7,bold=True);y-=h
        # equipe
        h=R_EQUIPE;box(cv,X0,y,TW,h);tl(cv,'Equipe:',X0,y,h,7,bold=True);y-=h
        # blank
        h=R_BLANK;box(cv,X0,y,TW,h);y-=h
        # members
        for i in range(3):
            h=R_MEMBER;box(cv,X0,y,TW,h);vline(cv,C_LOGO,y,h);vline(cv,C_TPAGO,y,h)
            tc(cv,str(i+1),X0,C_LOGO,y,h,7,bold=True)
            if i<nm:
                m=team['members'][i]
                tl(cv,f"{m['name']} - {m.get('cargo','PEDREIRO')}",C_LOGO,y,h,7,bold=True)
                prod=m.get('prod_liq',0)
                if prod!=0: tr(cv,brl(prod),X1,y,h,7,bold=True)
            y-=h
        # sep
        h=R_SEP;box(cv,X0,y,TW,h);y-=h
        # table header top
        h=R_THDR_A
        box(cv,C_TPAGO,y,X1-C_TPAGO,h+R_THDR_B)
        cv.setFont('Helvetica-Bold',7);cv.setFillColor(BLACK)
        mid_tp=y-(h+R_THDR_B)/2
        cv.drawCentredString((C_TPAGO+X1)/2,mid_tp+3.5,'Total a Ser')
        cv.drawCentredString((C_TPAGO+X1)/2,mid_tp-3.5,'Pago')
        box(cv,X0,y,C_QACUM-X0,h,bg=C_MA);box(cv,C_QACUM,y,C_QTOT-C_QACUM,h,bg=C_AA)
        box(cv,C_QTOT,y,C_TPAGO-C_QTOT,h,bg=C_AT)
        cv.setFillColor(BLACK)
        tc(cv,'Medição Atual',X0,C_QACUM,y,h,7,bold=True)
        tc(cv,'Acumulado Anterior',C_QACUM,C_QTOT,y,h,7,bold=True)
        tc(cv,'Acumulado Total',C_QTOT,C_TPAGO,y,h,7,bold=True)
        y-=h
        # table header bottom
        h=R_THDR_B
        cl(cv,C_MA,X0,C_DESC,y,h,'Quadra')
        cl(cv,C_MA,C_DESC,C_QTY,y,h,'Descrição')
        cl(cv,C_MA,C_QTY,C_VUNIT,y,h,'Quant.','(un)')
        cl(cv,C_MA,C_VUNIT,C_VTOT,y,h,'Valor','unitário (un)')
        cl(cv,C_MA,C_VTOT,C_QACUM,y,h,'Valor total')
        cl(cv,C_AA,C_QACUM,C_VACUM,y,h,'Quant.','(un)')
        cl(cv,C_AA,C_VACUM,C_QTOT,y,h,'Acumulado anterior')
        cl(cv,C_AT,C_QTOT,C_ATOT,y,h,'Quant.','(un)')
        cl(cv,C_AT,C_ATOT,C_TPAGO,y,h,'Acumulado')
        y-=h
        # data rows
        total_qty=0;total_vtot=0;total_aqty=0;total_avt=0
        for ri,dr in enumerate(rows):
            rh=R_DATA0 if ri==0 else R_DATA
            box(cv,X0,y,TW,rh)
            for cx in ALL_DIV: vline(cv,cx,y,rh)
            qty=dr['qty'];vtot=qty*1250;aqty=dr.get('acum_qty',0);avt=dr.get('acum_val',0)
            tqty=aqty+qty;tatot=avt+vtot
            total_qty+=qty;total_vtot+=vtot;total_aqty+=aqty;total_avt+=avt
            tc(cv,dr['quadra'],X0,C_DESC,y,rh,6.5)
            tl(cv,dr['lotes'],C_DESC,y,rh,6,pad=2)
            tc(cv,n2(qty),C_QTY,C_VUNIT,y,rh,6.5)
            tc(cv,brl(1250),C_VUNIT,C_VTOT,y,rh,6.5)
            tc(cv,brl(vtot),C_VTOT,C_QACUM,y,rh,6.5)
            tc(cv,n2(aqty),C_QACUM,C_VACUM,y,rh,6.5)
            tc(cv,brl(avt)if avt else'R$ -',C_VACUM,C_QTOT,y,rh,6.5)
            tc(cv,n2(tqty),C_QTOT,C_ATOT,y,rh,6.5)
            tc(cv,brl(tatot),C_ATOT,C_TPAGO,y,rh,6.5)
            tr(cv,brl(vtot),X1,y,rh,6.5)
            y-=rh
        # desconto
        h=R_DESCONTO;box(cv,X0,y,TW,h)
        for cx in ALL_DIV: vline(cv,cx,y,h)
        total_sal=sum(m.get('sal_liq',0)for m in team['members'])
        tl(cv,'DESCONTO SALÁRIO',C_DESC,y,h,6.5,bold=True)
        tc(cv,'1,00',C_QTY,C_VUNIT,y,h,6.5)
        if total_sal:
            tc(cv,brl(-total_sal),C_VUNIT,C_VTOT,y,h,6.5)
            tc(cv,brl(-total_sal),C_VTOT,C_QACUM,y,h,6.5)
            tc(cv,'1,00',C_QACUM,C_VACUM,y,h,6.5)
            tr(cv,brl(-total_sal),X1,y,h,6.5)
        y-=h
        # spacers
        h=R_SP1;box(cv,X0,y,TW,h);y-=h
        h=R_SP2;box(cv,X0,y,TW,h)
        cv.setFont('Helvetica',6.5);cv.setFillColor(BLACK)
        cv.drawCentredString((C_ATOT+C_TPAGO)/2,y+R_SP2*0.5-2,'-');y-=h
        # total
        h=R_TOTAL;box(cv,X0,y,TW,h,bg=C_TOT)
        for cx in ALL_DIV: vline(cv,cx,y,h)
        cv.setFillColor(BLACK)
        tc(cv,'Total',X0,C_QTY,y,h,7,bold=True)
        tc(cv,n2(total_qty),C_QTY,C_VUNIT,y,h,7,bold=True)
        tc(cv,brl(total_vtot),C_VTOT,C_QACUM,y,h,7,bold=True)
        tc(cv,n2(total_aqty),C_QACUM,C_VACUM,y,h,7,bold=True)
        tc(cv,brl(total_avt)if total_avt else'R$ -',C_VACUM,C_QTOT,y,h,7,bold=True)
        tc(cv,n2(total_aqty+total_qty),C_QTOT,C_ATOT,y,h,7,bold=True)
        tc(cv,brl(total_avt+total_vtot),C_ATOT,C_TPAGO,y,h,7,bold=True)
        y-=h
        # sp3
        h=R_SP3;box(cv,X0,y,TW,h);y-=h
        # producao
        h=R_PROD;box(cv,X0,y,TW,h,bg=C_TOT);vline(cv,C_TPAGO,y,h)
        cv.setFillColor(BLACK)
        tc(cv,f'Produção total do mês de {mes}',X0,C_TPAGO,y,h,7,bold=True)
        tr(cv,brl(total_vtot-total_sal),X1,y,h,7,bold=True)
        y-=h
        return y

    # ── Página de resumo ──────────────────────────────────────────────────────
    def draw_resumo(cv, data, mes, ano):
        from reportlab.lib import colors as rlc
        PW2, PH2 = A4
        TOTAL_UHS = 444
        QUADRA_MAX = {2:15,8:15,9:15,15:13,16:13,17:13}
        def q_max(n):
            return QUADRA_MAX.get(int(n) if str(n).isdigit() else 0, 30)
        quadras = {}
        for team in data['teams']:
            for row in team.get('rows', []):
                q = row['quadra']
                if q not in quadras:
                    quadras[q] = {'feito': 0, 'mes': 0, 'equipes': set()}
                quadras[q]['feito'] += row['qty'] + row.get('acum_qty', 0)
                quadras[q]['mes']   += row['qty']
                quadras[q]['equipes'].add(team['label'])
        total_feito = sum(v['feito'] for v in quadras.values())
        pct_total = total_feito / TOTAL_UHS * 100
        ML=28; MR=PW2-28; MW=MR-ML; y=PH2-28
        # Header
        cv.setFillColor(rlc.HexColor('#1A1A1A'))
        cv.rect(ML, y-52, MW, 52, fill=1, stroke=0)
        if logo_path and os.path.exists(logo_path):
            cv.drawImage(logo_path,ML+6,y-46,width=40,height=40,preserveAspectRatio=True,mask='auto')
        cv.setFillColor(rlc.white)
        cv.setFont('Helvetica-Bold',13)
        cv.drawCentredString(ML+MW/2, y-18, 'PAINEL DE PRODUÇÃO — CERÂMICA')
        cv.setFont('Helvetica',8)
        cv.drawCentredString(ML+MW/2, y-31, f'LOTEAMENTO JOSE BERNARDINO I e II  ·  {mes.upper()} / {ano}')
        cv.setFont('Helvetica',6.5)
        cv.drawRightString(MR-4, y-46, 'Identificação: PQO - Anexo A  |  Revisão: 02')
        y -= 62
        # KPI geral
        kpi_h=64
        cv.setFillColor(rlc.HexColor('#F8F8F8')); cv.setStrokeColor(rlc.HexColor('#CCCCCC'))
        cv.setLineWidth(0.5); cv.rect(ML, y-kpi_h, MW, kpi_h, fill=1, stroke=1)
        cv.setFillColor(rlc.HexColor('#2E7D32')); cv.rect(ML, y-kpi_h, 5, kpi_h, fill=1, stroke=0)
        cv.setFillColor(rlc.HexColor('#1A1A1A')); cv.setFont('Helvetica-Bold',8)
        cv.drawString(ML+14, y-14, 'PROGRESSO GERAL DO LOTEAMENTO')
        cv.setFont('Helvetica-Bold',26); cv.drawString(ML+14, y-42, str(total_feito))
        nw = cv.stringWidth(str(total_feito),'Helvetica-Bold',26)
        cv.setFont('Helvetica',9); cv.setFillColor(rlc.HexColor('#555555'))
        cv.drawString(ML+18+nw, y-36, f'/ {TOTAL_UHS} unidades')
        cv.drawString(ML+18+nw, y-47, f'{TOTAL_UHS-total_feito} restantes')
        bar_x=ML+14; bar_w=MW-110; bar_h=9; bar_y=y-56
        cv.setFillColor(rlc.HexColor('#E0E0E0')); cv.roundRect(bar_x,bar_y,bar_w,bar_h,4,fill=1,stroke=0)
        cv.setFillColor(rlc.HexColor('#2E7D32')); cv.roundRect(bar_x,bar_y,max(bar_w*(pct_total/100),8),bar_h,4,fill=1,stroke=0)
        cv.setFont('Helvetica-Bold',22); cv.setFillColor(rlc.HexColor('#2E7D32'))
        cv.drawRightString(MR-8, y-40, f'{pct_total:.1f}%')
        cv.setFont('Helvetica',7); cv.setFillColor(rlc.HexColor('#888888'))
        cv.drawRightString(MR-8, y-52, 'concluído')
        y -= kpi_h+14
        # Título seção
        cv.setFillColor(rlc.HexColor('#1A1A1A')); cv.setFont('Helvetica-Bold',8)
        cv.drawString(ML, y, 'DETALHAMENTO POR QUADRA')
        cv.setLineWidth(0.4); cv.setStrokeColor(rlc.HexColor('#CCCCCC'))
        cv.line(ML, y-4, MR, y-4); y -= 16
        # Grid 2 colunas
        sorted_q = sorted(quadras.items(), key=lambda x: x[0])
        card_w=(MW-10)/2; card_h=52; col=0
        for q_name, q_data in sorted_q:
            try: num=int(q_name.split('Q')[-1].strip().lstrip('0') or '0')
            except: num=0
            max_l=q_max(num); feito=q_data['feito']; mq=q_data['mes']
            pct_q=feito/max_l*100 if max_l else 0
            pc=(rlc.HexColor('#2E7D32') if pct_q>=75 else rlc.HexColor('#F9A825') if pct_q>=40 else rlc.HexColor('#C62828'))
            cx=ML+col*(card_w+10)
            cv.setFillColor(rlc.HexColor('#FAFAFA')); cv.setStrokeColor(rlc.HexColor('#E0E0E0'))
            cv.setLineWidth(0.4); cv.roundRect(cx,y-card_h,card_w,card_h,4,fill=1,stroke=1)
            cv.setFillColor(pc); cv.roundRect(cx,y-card_h,5,card_h,4,fill=1,stroke=0)
            cv.rect(cx+2,y-card_h,3,card_h,fill=1,stroke=0)
            cv.setFillColor(rlc.HexColor('#1A1A1A')); cv.setFont('Helvetica-Bold',9)
            cv.drawString(cx+12,y-14,q_name)
            eq=', '.join(sorted(q_data['equipes']))
            cv.setFont('Helvetica',6.5); cv.setFillColor(rlc.HexColor('#777777'))
            cv.drawString(cx+12,y-24,eq[:42])
            bx=cx+12; bw=card_w-22; bh=7; by=y-35
            cv.setFillColor(rlc.HexColor('#EBEBEB')); cv.roundRect(bx,by,bw,bh,3,fill=1,stroke=0)
            cv.setFillColor(pc); cv.roundRect(bx,by,max(bw*(pct_q/100),4),bh,3,fill=1,stroke=0)
            cv.setFillColor(rlc.HexColor('#1A1A1A')); cv.setFont('Helvetica-Bold',9)
            cv.drawString(cx+12,y-49,f'{feito}/{max_l}')
            cv.setFont('Helvetica',7); cv.setFillColor(rlc.HexColor('#888888'))
            cv.drawString(cx+42,y-49,f'+{mq} este mês')
            cv.setFont('Helvetica-Bold',10); cv.setFillColor(pc)
            cv.drawRightString(cx+card_w-6,y-49,f'{pct_q:.0f}%')
            col+=1
            if col>=2:
                col=0; y-=card_h+8
                if y<70: cv.showPage(); y=PH2-40
        if col==1: y-=card_h+8
        y-=10
        cv.setLineWidth(0.3); cv.setStrokeColor(rlc.HexColor('#CCCCCC'))
        cv.line(ML,y,MR,y)
        cv.setFont('Helvetica',6.5); cv.setFillColor(rlc.HexColor('#AAAAAA'))
        cv.drawCentredString(ML+MW/2,y-10,f'CB Engenharia  ·  {mes}/{ano}  ·  444 unidades totais  ·  Verde ≥75%  ·  Amarelo ≥40%  ·  Vermelho <40%')

        # ── Gerar PDF ─────────────────────────────────────────────────────────────
    mes   = data.get('mes','Junho')
    ano   = data.get('ano','2026')
    teams = data['teams']

    buf = io.BytesIO()
    cv  = rl_canvas.Canvas(buf, pagesize=A4)

    # Página de resumo primeiro
    draw_resumo(cv, data, mes, ano)
    cv.showPage()

    # Fichas por equipe
    page_y = PH - 10
    on_page = 0
    for team in teams:
        nr = len(team.get('rows',[]))
        fh = ficha_h(nr)
        if on_page >= 3 or (page_y - fh) < 10:
            if on_page > 0: cv.showPage()
            page_y = PH - 10; on_page = 0
        page_y = draw_ficha(cv, page_y, team, mes, ano) - GAP
        on_page += 1

    cv.save()
    buf.seek(0)
    return buf.read()


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # silencia logs

    def send_cors(self):
        self.send_header('Access-Control-Allow-Origin', ALLOW_ORIGIN)
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors()
        self.end_headers()

    def do_GET(self):
        base = os.path.dirname(os.path.abspath(__file__))

        # Serve o HTML principal
        if self.path in ('/', '/index', '/ceramica'):
            html_path = os.path.join(base, 'ceramica_junho.html')
            if os.path.exists(html_path):
                with open(html_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_cors()
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_response(404); self.send_cors(); self.end_headers()
            return

        # Endpoint de status (ping)
        if self.path == '/ping':
            resp = json.dumps({'ok': True}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.send_header('Content-Length', str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
            return

        # Carregar estado
        if self.path == '/carregar-estado':
            state_path = os.path.join(base, 'estado_ceramica.json')
            if not os.path.exists(state_path):
                # Retorna objeto vazio com CORS — não 404 cru
                resp = json.dumps({}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors()
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
                return
            try:
                with open(state_path, 'r', encoding='utf-8') as f:
                    content = f.read().encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors()
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except Exception as e:
                resp = json.dumps({'error': str(e)}).encode()
                self.send_response(500)
                self.send_cors()
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            return

        self.send_response(404)
        self.send_cors()
        self.end_headers()

    def do_POST(self):
        if self.path not in ('/gerar-pdf', '/salvar-estado'):
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        # ── Salvar estado ─────────────────────────────────────────────────────
        if self.path == '/salvar-estado':
            try:
                estado = json.loads(body)
                state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'estado_ceramica.json')
                with open(state_path, 'w', encoding='utf-8') as f:
                    json.dump(estado, f, ensure_ascii=False, indent=2)
                resp = json.dumps({'ok': True}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_cors()
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                resp = json.dumps({'ok': False, 'error': str(e)}).encode()
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_cors()
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            return

        try:
            data = json.loads(body)
            logo = LOGO_PATH if os.path.exists(LOGO_PATH) else None
            # Support per-payload UH price
            preco = data.get('preco', 1250)
            pdf_bytes = gerar_pdf(data, logo, preco)
            b64 = base64.b64encode(pdf_bytes).decode()
            resp = json.dumps({'ok': True, 'pdf': b64}).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.send_header('Content-Length', str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            resp = json.dumps({'ok': False, 'error': str(e), 'trace': err}).encode()
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.send_header('Content-Length', str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

if __name__ == '__main__':
    import webbrowser, threading
    print('╔══════════════════════════════════════════╗')
    print('║  CB Engenharia — Servidor de Produção     ║')
    print(f'║  Acesse: http://localhost:{PORT}            ║')
    print('║  Deixe esta janela aberta.                ║')
    print('║  Pressione Ctrl+C para parar.             ║')
    print('╚══════════════════════════════════════════╝')
    server = http.server.HTTPServer(('localhost', PORT), Handler)
    # Abre o browser automaticamente após 1 segundo
    threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{PORT}/')).start()
    server.serve_forever()
