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

    def draw_ficha(cv,top,team,mes,ano,preco_override=None):
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
            uh_price=preco_override or 1250
            qty=dr['qty'];vtot=qty*uh_price;aqty=dr.get('acum_qty',0);avt=dr.get('acum_val',0)
            tqty=aqty+qty;tatot=avt+vtot
            total_qty+=qty;total_vtot+=vtot;total_aqty+=aqty;total_avt+=avt
            tc(cv,dr['quadra'],X0,C_DESC,y,rh,6.5)
            tl(cv,dr['lotes'],C_DESC,y,rh,6,pad=2)
            tc(cv,n2(qty),C_QTY,C_VUNIT,y,rh,6.5)
            tc(cv,brl(uh_price),C_VUNIT,C_VTOT,y,rh,6.5)
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

        # Usa dados globais do painel se disponíveis (enviados pelo HTML)
        # Caso contrário, calcula apenas com os dados do mês atual (fallback)
        painel = data.get('painel')
        TOTAL_UHS = (painel['total_loteamento'] if painel else 444)

        if painel:
            total_feito = painel['total_feito']
            quadras_list = painel['quadras']  # [{label, feito, mes, max, equipes}]
        else:
            # fallback: só dados do mês atual
            QUADRA_MAX = {2:15,8:15,9:15,15:13,16:13,17:13}
            def q_max(n): return QUADRA_MAX.get(int(n) if str(n).isdigit() else 0, 30)
            quadras_dict = {}
            for team in data['teams']:
                for row in team.get('rows', []):
                    q = row['quadra']
                    if q not in quadras_dict:
                        quadras_dict[q] = {'feito':0,'mes':0,'equipes':set()}
                    quadras_dict[q]['feito'] += row['qty'] + row.get('acum_qty',0)
                    quadras_dict[q]['mes']   += row['qty']
                    quadras_dict[q]['equipes'].add(team['label'])
            total_feito = sum(v['feito'] for v in quadras_dict.values())
            quadras_list = [
                {'label':q,'feito':v['feito'],'mes':v['mes'],
                 'max': q_max(int(q.split('Q')[-1].strip().lstrip('0') or '0')),
                 'equipes': ', '.join(sorted(v['equipes']))}
                for q,v in sorted(quadras_dict.items())
            ]

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
        card_w=(MW-10)/2; card_h=52; col=0
        for q in quadras_list:
            label   = q['label']
            feito   = q['feito']
            mq      = q['mes']
            max_l   = q['max']
            equipes = q['equipes'] if isinstance(q['equipes'],str) else ', '.join(sorted(q['equipes']))
            pct_q   = feito/max_l*100 if max_l else 0
            pc = (rlc.HexColor('#2E7D32') if pct_q>=75 else
                  rlc.HexColor('#F9A825') if pct_q>=40 else
                  rlc.HexColor('#C62828'))
            cx=ML+col*(card_w+10)
            cv.setFillColor(rlc.HexColor('#FAFAFA')); cv.setStrokeColor(rlc.HexColor('#E0E0E0'))
            cv.setLineWidth(0.4); cv.roundRect(cx,y-card_h,card_w,card_h,4,fill=1,stroke=1)
            cv.setFillColor(pc); cv.roundRect(cx,y-card_h,5,card_h,4,fill=1,stroke=0)
            cv.rect(cx+2,y-card_h,3,card_h,fill=1,stroke=0)
            cv.setFillColor(rlc.HexColor('#1A1A1A')); cv.setFont('Helvetica-Bold',9)
            cv.drawString(cx+12,y-14,label)
            cv.setFont('Helvetica',6.5); cv.setFillColor(rlc.HexColor('#777777'))
            cv.drawString(cx+12,y-24,equipes[:42])
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

        # ── Gráfico de barras: produção mensal ────────────────────────────────
        historico = data.get('historico', [])
        if historico:
            y -= 14
            # Verifica se há espaço; se não, nova página
            chart_h = 100
            if y - chart_h < 40:
                cv.showPage(); y = PH2 - 28

            cv.setFont('Helvetica-Bold', 8)
            cv.setFillColor(rlc.HexColor('#1A1A1A'))
            cv.drawString(ML, y, 'PRODUÇÃO MENSAL (UHs por mês)')
            cv.setLineWidth(0.4); cv.setStrokeColor(rlc.HexColor('#CCCCCC'))
            cv.line(ML, y-4, MR, y-4)
            y -= 16

            max_uhs = max((d['uhs'] for d in historico), default=1) or 1
            bar_area_h = 72   # altura máxima das barras
            bar_w      = min(30, (MW - 8) / max(len(historico), 1) - 6)
            gap        = max(4, (MW - len(historico) * bar_w) / max(len(historico), 1))
            cx_bar     = ML

            for d in historico:
                uhs   = d['uhs']
                label = d['label']
                atual = d.get('atual', False)
                bh    = max(int((uhs / max_uhs) * bar_area_h), 2) if uhs else 2

                bar_color = rlc.HexColor('#C8F135') if atual else rlc.HexColor('#5A8A2A')

                # Barra
                cv.setFillColor(bar_color)
                cv.roundRect(cx_bar, y - bar_area_h - 2, bar_w, bh, 2, fill=1, stroke=0)

                # Valor acima da barra
                if uhs > 0:
                    cv.setFont('Helvetica-Bold' if atual else 'Helvetica', 6.5)
                    cv.setFillColor(rlc.HexColor('#1A1A1A'))
                    val_str = str(uhs)
                    vw = cv.stringWidth(val_str, 'Helvetica-Bold' if atual else 'Helvetica', 6.5)
                    cv.drawString(cx_bar + (bar_w - vw)/2,
                                  y - bar_area_h - 2 + bh + 2, val_str)

                # Label abaixo
                cv.setFont('Helvetica', 5.5)
                cv.setFillColor(rlc.HexColor('#888888'))
                lw = cv.stringWidth(label, 'Helvetica', 5.5)
                cv.drawString(cx_bar + (bar_w - lw)/2,
                              y - bar_area_h - 14, label)

                cx_bar += bar_w + gap

            y -= bar_area_h + 28

        # Rodapé
        cv.setLineWidth(0.3); cv.setStrokeColor(rlc.HexColor('#CCCCCC'))
        cv.line(ML,y,MR,y)
        cv.setFont('Helvetica',6.5); cv.setFillColor(rlc.HexColor('#AAAAAA'))
        cv.drawCentredString(ML+MW/2,y-10,
            f'CB Engenharia  ·  {mes}/{ano}  ·  {TOTAL_UHS} unidades totais  ·  Verde ≥75%  ·  Amarelo ≥40%  ·  Vermelho <40%')


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
        page_y = draw_ficha(cv, page_y, team, mes, ano, preco_override) - GAP
        on_page += 1

    cv.save()
    buf.seek(0)
    return buf.read()


def gerar_relatorio(dados_frentes, logo_path):
    """
    Gera o relatório consolidado PDF a partir dos dados do /dashboard-dados.
    dados_frentes: lista retornada pelo endpoint /dashboard-dados
    """
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors as rlc
    from reportlab.pdfgen import canvas as rl_canvas
    import io

    PW, PH = landscape(A4)
    TOTAL_UHS = 444

    # Constrói estrutura: frente -> mes -> uhs
    # e frente -> preco (estimado pela prod_bruta / total)
    frentes_dados = []
    for d in dados_frentes:
        if not d.get('ok'): continue
        hist = {h['label']: h['uhs'] for h in d.get('historico', [])}
        total = d.get('total', 0)
        valor = d.get('valor_bruto', 0)
        preco = round(valor / total) if total > 0 else 1250
        frentes_dados.append({
            'nome':  d['nome'],
            'hist':  hist,
            'total': total,
            'valor': valor,
            'preco': preco,
        })

    if not frentes_dados:
        # Sem dados — retorna PDF vazio com mensagem
        buf = io.BytesIO()
        cv = rl_canvas.Canvas(buf, pagesize=landscape(A4))
        cv.setFont('Helvetica-Bold', 14)
        cv.drawCentredString(PW/2, PH/2, 'Nenhum dado disponível')
        cv.save(); buf.seek(0); return buf.read()

    # Todos os meses presentes no histórico (union)
    meses_set = []
    for fd in frentes_dados:
        for m in fd['hist']:
            if m not in meses_set:
                meses_set.append(m)
    # Ordena cronologicamente (formato MMM/AA)
    from datetime import datetime
    def mes_key(s):
        try:
            abbrs = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
            p = s.split('/')
            return int(p[1])*100 + abbrs.index(p[0][:3])+1
        except: return 0
    meses_set.sort(key=mes_key)

    PAGE_SIZE = 5
    PAGES = [frentes_dados[i:i+PAGE_SIZE] for i in range(0, len(frentes_dados), PAGE_SIZE)]
    total_pages = len(PAGES)

    BG_HDR  = rlc.HexColor('#1A1A1A')
    BG_ALT  = rlc.HexColor('#F5F5F5')
    LGRAY   = rlc.HexColor('#DDDDDD')
    MGRAY   = rlc.HexColor('#AAAAAA')
    LGREEN  = rlc.HexColor('#C8F135')
    AMBER   = rlc.HexColor('#F9A825')
    RED     = rlc.HexColor('#C62828')
    BLACK   = rlc.black; WHITE = rlc.white

    def pc(pct):
        return LGREEN if pct>=75 else AMBER if pct>=40 else RED if pct>0 else MGRAY

    def brl(v):
        if v==0: return 'R$ -'
        s = f"{abs(v):,.0f}".replace(',','.')
        return f"R$ {s}"

    buf = io.BytesIO()
    cv  = rl_canvas.Canvas(buf, pagesize=landscape(A4))

    for pi, page_frentes in enumerate(PAGES):
        ML=20; MR=PW-20; TW=MR-ML
        y = PH-20
        NF = len(page_frentes)
        is_last = (pi == total_pages-1)

        COL_MES   = 38
        COL_VALOR = 78
        COL_F     = (TW - COL_MES - COL_VALOR) / NF
        ROW_HDR   = 42
        ROW_H     = 15

        def cx(fi): return ML + COL_MES + fi*COL_F
        def cx_val(): return ML + COL_MES + NF*COL_F

        # Header documento
        cv.setFillColor(BG_HDR)
        cv.rect(ML, y-44, TW, 44, fill=1, stroke=0)
        if logo_path and os.path.exists(logo_path):
            cv.drawImage(logo_path, ML+5, y-38, width=32, height=32,
                        preserveAspectRatio=True, mask='auto')
        cv.setFillColor(WHITE)
        cv.setFont('Helvetica-Bold',12)
        cv.drawCentredString(ML+TW/2, y-16, 'RELATÓRIO CONSOLIDADO DE PRODUÇÃO')
        cv.setFont('Helvetica',7.5)
        cv.drawCentredString(ML+TW/2, y-27, 'LOTEAMENTO JOSE BERNARDINO I e II  ·  TODAS AS FRENTES DE SERVIÇO')
        cv.setFont('Helvetica',6)
        cv.drawRightString(MR-3, y-38, f'PQO - Anexo A  |  Revisão: 02  |  Pág. {pi+1}/{total_pages}')
        y -= 52

        # Header tabela
        cv.setFillColor(BG_HDR)
        cv.rect(ML, y-ROW_HDR, TW, ROW_HDR, fill=1, stroke=0)
        cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold',8)
        cv.drawCentredString(ML+COL_MES/2, y-ROW_HDR/2-3, 'Mês')

        for fi, fd in enumerate(page_frentes):
            x = cx(fi)
            cv.setStrokeColor(rlc.HexColor('#333'))
            cv.setLineWidth(0.3); cv.line(x,y,x,y-ROW_HDR)
            total_f = fd['total']; pct_f = total_f/TOTAL_UHS*100
            falt_f  = TOTAL_UHS-total_f
            cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold',8)
            cv.drawCentredString(x+COL_F/2, y-10, fd['nome'])
            cv.setFillColor(pc(pct_f)); cv.setFont('Helvetica-Bold',8)
            cv.drawCentredString(x+COL_F/2, y-21, f'{total_f}/{TOTAL_UHS}')
            cv.setFont('Helvetica',7)
            cv.drawCentredString(x+COL_F/2, y-32, f'{pct_f:.0f}%  |  falta {falt_f}')

        cv.setStrokeColor(rlc.HexColor('#333')); cv.setLineWidth(0.3)
        cv.line(cx_val(),y,cx_val(),y-ROW_HDR)
        cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold',8)
        cv.drawCentredString(cx_val()+COL_VALOR/2, y-16, 'Prod. Bruta')
        cv.drawCentredString(cx_val()+COL_VALOR/2, y-27, 'do Mês')
        y -= ROW_HDR

        # Linhas de mês
        for mi, mes in enumerate(meses_set):
            dados_m = {fd['nome']: fd['hist'].get(mes,0) for fd in page_frentes}
            # valor do mês = soma de TODAS as frentes (para consistência)
            valor_m = sum(fd['hist'].get(mes,0)*fd['preco'] for fd in frentes_dados)
            tem = any(v>0 for v in dados_m.values())

            bg = BG_ALT if mi%2==0 else WHITE
            cv.setFillColor(bg)
            cv.rect(ML, y-ROW_H, TW, ROW_H, fill=1, stroke=0)
            cv.setStrokeColor(LGRAY); cv.setLineWidth(0.2)
            cv.line(ML, y-ROW_H, MR, y-ROW_H)

            cv.setFillColor(BLACK if tem else MGRAY)
            cv.setFont('Helvetica-Bold' if tem else 'Helvetica', 7.5)
            cv.drawCentredString(ML+COL_MES/2, y-ROW_H/2-3, mes)

            for fi, fd in enumerate(page_frentes):
                x=cx(fi); uhs=dados_m[fd['nome']]
                cv.setStrokeColor(LGRAY); cv.setLineWidth(0.2)
                cv.line(x,y,x,y-ROW_H)
                if uhs>0:
                    alpha=min(0.08+(uhs/TOTAL_UHS)*0.5,0.55)
                    cv.setFillColorRGB(0x2E/255,0x7D/255,0x32/255,alpha=alpha)
                    cv.rect(x+0.5,y-ROW_H+0.5,COL_F-1,ROW_H-1,fill=1,stroke=0)
                    cv.setFillColor(BLACK); cv.setFont('Helvetica-Bold',8)
                    cv.drawCentredString(x+COL_F/2, y-ROW_H/2-3, str(uhs))
                else:
                    cv.setFillColor(LGRAY); cv.setFont('Helvetica',7.5)
                    cv.drawCentredString(x+COL_F/2, y-ROW_H/2-3, '—')

            x=cx_val()
            cv.setStrokeColor(LGRAY); cv.setLineWidth(0.2)
            cv.line(x,y,x,y-ROW_H)
            if valor_m>0:
                cv.setFillColor(BLACK); cv.setFont('Helvetica',7.5)
                cv.drawCentredString(x+COL_VALOR/2, y-ROW_H/2-3, brl(valor_m))
            else:
                cv.setFillColor(LGRAY); cv.setFont('Helvetica',7)
                cv.drawCentredString(x+COL_VALOR/2, y-ROW_H/2-3, '—')
            y -= ROW_H

        # Linha total por frente
        tot_h=18
        cv.setFillColor(rlc.HexColor('#2A2A2A'))
        cv.rect(ML,y-tot_h,TW,tot_h,fill=1,stroke=0)
        cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold',7.5)
        cv.drawString(ML+5, y-tot_h/2-3, 'Total por frente')
        for fi,fd in enumerate(page_frentes):
            x=cx(fi)
            cv.setStrokeColor(rlc.HexColor('#444')); cv.setLineWidth(0.3)
            cv.line(x,y,x,y-tot_h)
            cv.setFillColor(pc(fd['total']/TOTAL_UHS*100))
            cv.setFont('Helvetica-Bold',7.5)
            cv.drawCentredString(x+COL_F/2, y-tot_h/2+1, str(fd['total']))
            cv.setFont('Helvetica',6.5)
            cv.drawCentredString(x+COL_F/2, y-tot_h/2-5, brl(fd['valor']))
        x=cx_val()
        cv.setStrokeColor(rlc.HexColor('#444')); cv.setLineWidth(0.3)
        cv.line(x,y,x,y-tot_h)
        valor_all = sum(fd['valor'] for fd in frentes_dados)
        cv.setFillColor(LGREEN); cv.setFont('Helvetica-Bold',8)
        cv.drawCentredString(x+COL_VALOR/2, y-tot_h/2-3, brl(valor_all))

        # Rodapé
        if is_last:
            FOOTER_H=36
            cv.setFillColor(BG_HDR)
            cv.rect(ML,22,TW,FOOTER_H,fill=1,stroke=0)
            cv.setFillColor(LGREEN)
            cv.rect(ML,22,6,FOOTER_H,fill=1,stroke=0)
            cv.setFillColor(WHITE); cv.setFont('Helvetica-Bold',9)
            cv.drawString(ML+14, 22+FOOTER_H-14, 'TOTAL GERAL DE PRODUÇÃO BRUTA — TODAS AS FRENTES')
            cv.setFillColor(LGREEN); cv.setFont('Helvetica-Bold',18)
            cv.drawRightString(MR-10, 22+12, brl(valor_all))
            cv.setFillColor(MGRAY); cv.setFont('Helvetica',7)
            cv.drawString(ML+14, 22+8, 'CB Engenharia  ·  Loteamento Jose Bernardino I e II  ·  444 unidades por frente')
        else:
            cv.setStrokeColor(LGRAY); cv.setLineWidth(0.3)
            cv.line(ML,18,MR,18)
            cv.setFont('Helvetica',6); cv.setFillColor(MGRAY)
            cv.drawCentredString(ML+TW/2, 9, 'CB Engenharia  ·  Loteamento Jose Bernardino I e II  ·  444 unidades por frente')

        if not is_last:
            cv.showPage()

    cv.save(); buf.seek(0)
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
        # Map paths to HTML files
        path_map = {
            '/': 'dashboard.html',
            '/dashboard': 'dashboard.html',
            '/contencao': 'contencao.html',
            '/inst_radier': 'inst_radier.html',
            '/lona_malha': 'lona_malha.html',
            '/conc_radier': 'conc_radier.html',
            '/inst_reg': 'inst_reg.html',
            '/graute_inf': 'graute_inf.html',
            '/graute_sup': 'graute_sup.html',
            '/telhado': 'telhado.html',
            '/inst_hidro': 'inst_hidro.html',
            '/alvenaria': 'alvenaria.html',
            '/acabamento': 'acabamento.html',
            '/gesso': 'gesso.html',
            '/contrapiso': 'contrapiso.html',
            '/caixinha': 'caixinha.html',
            '/peitoril': 'peitoril.html',
            '/esquadrias': 'esquadrias.html',
            '/cabeamento': 'cabeamento.html',
            '/impermea': 'impermea.html',
            '/ceramica': 'ceramica.html',
        }
        if self.path in path_map:
            html_path = os.path.join(base, path_map[self.path])
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

        # Endpoint dashboard: consolida dados de todas as frentes
        if self.path == '/dashboard-dados':
            FRENTES = [
                ('contencao',   'Contenção'),
                ('inst_radier', 'Instalações de Radier'),
                ('lona_malha',  'Lona, Espaçador e Malha'),
                ('conc_radier', 'Concretagem de Radier'),
                ('inst_reg',    'Instalação de Registros'),
                ('graute_inf',  'Graute Inferior'),
                ('graute_sup',  'Graute Superior'),
                ('telhado',     'Telhado'),
                ('inst_hidro',  'Inst. Hidrossanitárias'),
                ('alvenaria',   'Alvenaria de Vedação'),
                ('acabamento',  'Acabamento'),
                ('gesso',       'Gesso'),
                ('contrapiso',  'Contrapiso'),
                ('caixinha',    'Caixinha'),
                ('peitoril',    'Peitoril'),
                ('esquadrias',  'Esquadrias'),
                ('cabeamento',  'Cabeamento'),
                ('impermea',    'Impermeabilização'),
                ('ceramica',    'Cerâmica'),
            ]
            TOTAL_UHS = 444
            resultado = []
            for slug, nome in FRENTES:
                state_path = os.path.join(base, f'estado_{slug}.json')
                if not os.path.exists(state_path):
                    resultado.append({'slug':slug,'nome':nome,'ok':False})
                    continue
                try:
                    with open(state_path,'r',encoding='utf-8') as f:
                        estado = json.load(f)
                    livro = estado.get('livro', [])
                    # Meses fechados — ordenados
                    fechados = sorted([m for m in livro if m['status']=='closed'],
                                      key=lambda m: m['id'])
                    # Mês aberto
                    aberto = next((m for m in livro if m['status']=='open'), None)
                    todos = fechados + ([aberto] if aberto else [])

                    # Total UHs executadas (fechados + aberto atual)
                    def uhs_mes(mes):
                        return sum(
                            len(r['lots']) for t in mes.get('teams',[])
                            for r in t.get('rows',[])
                        )

                    total_exec = sum(uhs_mes(m) for m in todos)
                    pct = round(total_exec / TOTAL_UHS * 100, 1)

                    # Último mês consolidado
                    ultimo_fecha = fechados[-1] if fechados else None
                    ultimo_nome  = f"{ultimo_fecha['mes']}/{ultimo_fecha['ano']}" if ultimo_fecha else '—'
                    ultimo_uhs   = uhs_mes(ultimo_fecha) if ultimo_fecha else 0

                    # Projeção: baseada na velocidade do último mês fechado
                    restantes = TOTAL_UHS - total_exec
                    if ultimo_uhs > 0 and restantes > 0:
                        meses_proj = -(-restantes // ultimo_uhs)  # ceil division
                        proj = f'{meses_proj} mês{"es" if meses_proj>1 else ""}'
                    elif restantes <= 0:
                        proj = 'Concluído'
                    else:
                        proj = 'Sem dados'

                    # Valor financeiro bruto total
                    valor_bruto = 0
                    for mes in todos:
                        preco = mes.get('preco', 1250)
                        valor_bruto += uhs_mes(mes) * preco

                    resultado.append({
                        'slug':       slug,
                        'nome':       nome,
                        'ok':         True,
                        'total':      total_exec,
                        'pct':        pct,
                        'restantes':  restantes,
                        'ultimo_mes': ultimo_nome,
                        'ultimo_uhs': ultimo_uhs,
                        'projecao':   proj,
                        'valor_bruto':valor_bruto,
                        'historico':  [
                            {'label': m['mes'][:3]+'/'+m['ano'][-2:],
                             'uhs':   uhs_mes(m)}
                            for m in todos
                        ],
                    })
                except Exception as e:
                    resultado.append({'slug':slug,'nome':nome,'ok':False,'erro':str(e)})

            resp = json.dumps(resultado, ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_cors()
            self.send_header('Content-Length', str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
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
        if self.path.startswith('/carregar-estado'):
            # Support ?servico=slug query param
            servico = 'ceramica'
            if '?' in self.path:
                qs = self.path.split('?', 1)[1]
                for part in qs.split('&'):
                    if part.startswith('servico='):
                        servico = part.split('=', 1)[1]
            fname = f'estado_{servico}.json'
            state_path = os.path.join(base, fname)
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
        if self.path not in ('/gerar-pdf', '/salvar-estado', '/gerar-relatorio'):
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        # ── Gerar relatório consolidado ───────────────────────────────────────────
        if self.path == '/gerar-relatorio':
            try:
                dados = json.loads(body)
                pdf_bytes = gerar_relatorio(dados, LOGO_PATH if os.path.exists(LOGO_PATH) else None)
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
                resp = json.dumps({'ok': False, 'error': str(e), 'trace': traceback.format_exc()}).encode()
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_cors()
                self.send_header('Content-Length', str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            return

        # ── Salvar estado ─────────────────────────────────────────────────────
        if self.path == '/salvar-estado':
            try:
                estado = json.loads(body)
                servico = estado.get('servico', 'ceramica')
                fname = f'estado_{servico}.json'
                state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
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

        if self.path == '/gerar-relatorio':
            try:
                dados = json.loads(body)
                logo  = LOGO_PATH if os.path.exists(LOGO_PATH) else None
                pdf_bytes = gerar_relatorio_consolidado(dados, logo)
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
                resp = json.dumps({'ok': False, 'error': str(e), 'trace': traceback.format_exc()}).encode()
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
    threading.Timer(1.0, lambda: webbrowser.open(f'http://localhost:{PORT}/dashboard')).start()
    server.serve_forever()

# ─── GERADOR DO RELATÓRIO CONSOLIDADO ─────────────────────────────────────────
def gerar_relatorio_consolidado(dados_frentes, logo_path):
    import io
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as rl_canvas

    PW, PH = landscape(A4)
    TOTAL_UHS = 444

    FRENTES_FULL = [d['nome'] for d in dados_frentes if d.get('ok')]
    FRENTES_SLUG = [d['slug'] for d in dados_frentes if d.get('ok')]

    # Collect all months across all services, sorted
    meses_set = set()
    for d in dados_frentes:
        if d.get('ok'):
            for h in d.get('historico', []):
                meses_set.add(h['label'])
    MESES = sorted(meses_set, key=lambda m: (
        int(m.split('/')[1]),
        ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'].index(m.split('/')[0])
    ))

    # Build data matrix: dados[mes][nome_frente] = uhs
    DADOS = {mes: {f: 0 for f in FRENTES_FULL} for mes in MESES}
    PRECO = {}
    for d in dados_frentes:
        if not d.get('ok'): continue
        nome = d['nome']
        for h in d.get('historico', []):
            if h['label'] in DADOS:
                DADOS[h['label']][nome] = h['uhs']
        # estimate price from valor_bruto / total
        total = d.get('total', 0)
        valor = d.get('valor_bruto', 0)
        PRECO[nome] = round(valor / total) if total > 0 else 1250

    def brl(v):
        if v == 0: return 'R$ -'
        return 'R$ ' + f"{abs(v):,.0f}".replace(',','.')

    PAGE_SIZE = 5  # frentes per page
    pages = [FRENTES_FULL[i:i+PAGE_SIZE] for i in range(0, len(FRENTES_FULL), PAGE_SIZE)]
    total_pages = len(pages)

    buf = io.BytesIO()
    cv  = rl_canvas.Canvas(buf, pagesize=landscape(A4))

    for pi, frentes_page in enumerate(pages):
        is_last = (pi == total_pages - 1)
        _draw_relatorio_page(cv, frentes_page, FRENTES_FULL, MESES, DADOS, PRECO,
                             TOTAL_UHS, logo_path, brl, pi+1, total_pages, is_last)
        if not is_last:
            cv.showPage()

    cv.save()
    buf.seek(0)
    return buf.read()


def _draw_relatorio_page(cv, frentes_page, all_frentes, MESES, DADOS, PRECO,
                         TOTAL_UHS, logo_path, brl, page_num, total_pages, is_last):
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib import colors

    PW, PH = landscape(A4)
    ML = 20; MR = PW - 20; TW = MR - ML
    y = PH - 20
    NF = len(frentes_page)
    NM = len(MESES)

    COL_MES   = 40
    COL_VALOR = 80
    COL_F     = (TW - COL_MES - COL_VALOR) / NF

    ROW_HDR = 42
    ROW_H   = 14

    BG_HDR  = colors.HexColor('#1A1A1A')
    BG_ALT  = colors.HexColor('#F5F5F5')
    LGRAY   = colors.HexColor('#DDDDDD')
    MGRAY   = colors.HexColor('#AAAAAA')
    LGREEN  = colors.HexColor('#C8F135')
    AMBER   = colors.HexColor('#F9A825')
    RED     = colors.HexColor('#C62828')
    GREEN   = colors.HexColor('#2E7D32')
    BLACK   = colors.black
    WHITE   = colors.white

    def cx(fi): return ML + COL_MES + fi * COL_F
    def cx_val(): return ML + COL_MES + NF * COL_F

    # ── HEADER ────────────────────────────────────────────────────────────────
    cv.setFillColor(BG_HDR)
    cv.rect(ML, y-44, TW, 44, fill=1, stroke=0)
    if logo_path and os.path.exists(logo_path):
        cv.drawImage(logo_path, ML+5, y-38, width=32, height=32,
                     preserveAspectRatio=True, mask='auto')
    cv.setFillColor(WHITE)
    cv.setFont('Helvetica-Bold', 12)
    cv.drawCentredString(ML+TW/2, y-16, 'RELATÓRIO CONSOLIDADO DE PRODUÇÃO')
    cv.setFont('Helvetica', 7.5)
    cv.drawCentredString(ML+TW/2, y-27, 'LOTEAMENTO JOSE BERNARDINO I e II  ·  TODAS AS FRENTES DE SERVIÇO')
    cv.setFont('Helvetica', 6)
    cv.drawRightString(MR-3, y-38, f'PQO - Anexo A  |  Revisão: 02  |  Pág. {page_num}/{total_pages}')
    y -= 52

    # ── CABEÇALHO DA TABELA ───────────────────────────────────────────────────
    cv.setFillColor(BG_HDR)
    cv.rect(ML, y-ROW_HDR, TW, ROW_HDR, fill=1, stroke=0)

    cv.setFillColor(WHITE)
    cv.setFont('Helvetica-Bold', 8)
    cv.drawCentredString(ML + COL_MES/2, y - ROW_HDR/2 - 3, 'Mês')

    for fi, frente in enumerate(frentes_page):
        x = cx(fi)
        cv.setStrokeColor(colors.HexColor('#333')); cv.setLineWidth(0.3)
        cv.line(x, y, x, y-ROW_HDR)

        total_f = sum(DADOS[m][frente] for m in MESES)
        pct_f   = total_f / TOTAL_UHS * 100
        falt_f  = TOTAL_UHS - total_f
        pc = LGREEN if pct_f>=75 else AMBER if pct_f>=40 else RED if pct_f>0 else MGRAY

        cv.setFillColor(WHITE)
        cv.setFont('Helvetica-Bold', 8)
        cv.drawCentredString(x+COL_F/2, y-11, frente)
        cv.setFillColor(pc)
        cv.setFont('Helvetica-Bold', 8)
        cv.drawCentredString(x+COL_F/2, y-23, f'{total_f}/{TOTAL_UHS}')
        cv.setFont('Helvetica', 7)
        cv.drawCentredString(x+COL_F/2, y-34, f'{pct_f:.0f}%  |  falta {falt_f}')

    # Coluna valor
    x = cx_val()
    cv.setStrokeColor(colors.HexColor('#333')); cv.setLineWidth(0.3)
    cv.line(x, y, x, y-ROW_HDR)
    cv.setFillColor(WHITE)
    cv.setFont('Helvetica-Bold', 8)
    # Se última página: "Prod. Bruta Total" (todas frentes); senão só esta página
    label_val = 'Prod. Bruta' if is_last else 'Prod. Bruta'
    cv.drawCentredString(x+COL_VALOR/2, y-17, label_val)
    cv.setFont('Helvetica', 7)
    cv.drawCentredString(x+COL_VALOR/2, y-28, '(mês)')
    y -= ROW_HDR

    # ── LINHAS DE MÊS ─────────────────────────────────────────────────────────
    # Totais por coluna (frente) para linha de totais
    col_totals = {f: 0 for f in frentes_page}
    col_valores = {f: 0 for f in frentes_page}
    valor_grand_total = 0

    for mi, mes in enumerate(MESES):
        dados_m  = DADOS[mes]
        valor_m  = sum(dados_m[f] * PRECO.get(f,1250) for f in all_frentes)
        tem      = any(dados_m[f] > 0 for f in frentes_page)

        bg = BG_ALT if mi%2==0 else WHITE
        cv.setFillColor(bg)
        cv.rect(ML, y-ROW_H, TW, ROW_H, fill=1, stroke=0)
        cv.setStrokeColor(LGRAY); cv.setLineWidth(0.2)
        cv.line(ML, y-ROW_H, MR, y-ROW_H)

        cv.setFillColor(BLACK if tem else MGRAY)
        cv.setFont('Helvetica-Bold' if tem else 'Helvetica', 7.5)
        cv.drawCentredString(ML+COL_MES/2, y-ROW_H/2-2.5, mes)

        for fi, frente in enumerate(frentes_page):
            x   = cx(fi)
            uhs = dados_m[frente]
            cv.setStrokeColor(LGRAY); cv.setLineWidth(0.2)
            cv.line(x, y, x, y-ROW_H)
            col_totals[frente]  += uhs
            col_valores[frente] += uhs * PRECO.get(frente, 1250)
            if uhs > 0:
                alpha = 0.07 + (uhs/TOTAL_UHS)*0.5
                cv.setFillColorRGB(0x2E/255, 0x7D/255, 0x32/255, alpha=min(alpha,0.55))
                cv.rect(x+0.5, y-ROW_H+0.5, COL_F-1, ROW_H-1, fill=1, stroke=0)
                cv.setFillColor(BLACK)
                cv.setFont('Helvetica-Bold', 8)
                cv.drawCentredString(x+COL_F/2, y-ROW_H/2-2.5, str(uhs))
            else:
                cv.setFillColor(LGRAY)
                cv.setFont('Helvetica', 7)
                cv.drawCentredString(x+COL_F/2, y-ROW_H/2-2.5, '—')

        # Valor do mês (total de todas frentes)
        x = cx_val()
        cv.setStrokeColor(LGRAY); cv.setLineWidth(0.2)
        cv.line(x, y, x, y-ROW_H)
        if valor_m > 0:
            cv.setFillColor(BLACK)
            cv.setFont('Helvetica', 7)
            cv.drawCentredString(x+COL_VALOR/2, y-ROW_H/2-2.5, brl(valor_m))
            valor_grand_total += valor_m
        else:
            cv.setFillColor(LGRAY)
            cv.setFont('Helvetica', 7)
            cv.drawCentredString(x+COL_VALOR/2, y-ROW_H/2-2.5, '—')

        y -= ROW_H

    # ── LINHA DE TOTAIS POR FRENTE ────────────────────────────────────────────
    TOTAL_ROW_H = 18
    cv.setFillColor(colors.HexColor('#2A2A2A'))
    cv.rect(ML, y-TOTAL_ROW_H, TW, TOTAL_ROW_H, fill=1, stroke=0)
    cv.setFillColor(WHITE)
    cv.setFont('Helvetica-Bold', 7.5)
    cv.drawString(ML+5, y-TOTAL_ROW_H/2-3, 'Total por frente')

    for fi, frente in enumerate(frentes_page):
        x = cx(fi)
        cv.setStrokeColor(colors.HexColor('#444')); cv.setLineWidth(0.3)
        cv.line(x, y, x, y-TOTAL_ROW_H)
        cv.setFillColor(LGREEN)
        cv.setFont('Helvetica-Bold', 8)
        cv.drawCentredString(x+COL_F/2, y-10, str(col_totals[frente]))
        cv.setFillColor(MGRAY)
        cv.setFont('Helvetica', 6.5)
        cv.drawCentredString(x+COL_F/2, y-TOTAL_ROW_H+4, brl(col_valores[frente]))

    # Coluna valor: total geral de todas as frentes no período
    x = cx_val()
    cv.setStrokeColor(colors.HexColor('#444')); cv.setLineWidth(0.3)
    cv.line(x, y, x, y-TOTAL_ROW_H)
    total_todas = sum(
        sum(DADOS[m][f] * PRECO.get(f,1250) for f in all_frentes)
        for m in MESES
    )
    cv.setFillColor(LGREEN)
    cv.setFont('Helvetica-Bold', 8)
    cv.drawCentredString(x+COL_VALOR/2, y-TOTAL_ROW_H/2-3, brl(total_todas))

    y -= TOTAL_ROW_H + 6

    # ── CAIXA DE RODAPÉ (última página) ───────────────────────────────────────
    if is_last:
        FOOTER_H = 32
        footer_y = 18
        cv.setFillColor(BG_HDR)
        cv.rect(ML, footer_y, TW, FOOTER_H, fill=1, stroke=0)
        cv.setFillColor(MGRAY)
        cv.setFont('Helvetica', 7)
        cv.drawString(ML+12, footer_y+FOOTER_H-11, 'TOTAL GERAL DE PRODUÇÃO BRUTA — TODAS AS FRENTES')
        cv.setFillColor(LGREEN)
        cv.setFont('Helvetica-Bold', 18)
        cv.drawString(ML+12, footer_y+8, brl(total_todas))
        # rodapé info
        cv.setFillColor(MGRAY)
        cv.setFont('Helvetica', 6)
        cv.drawRightString(MR-8, footer_y+8,
            'CB Engenharia  ·  Loteamento Jose Bernardino I e II  ·  444 unidades por frente')
    else:
        cv.setStrokeColor(LGRAY); cv.setLineWidth(0.3)
        cv.line(ML, 18, MR, 18)
        cv.setFont('Helvetica', 6); cv.setFillColor(MGRAY)
        cv.drawCentredString(ML+TW/2, 10,
            'CB Engenharia  ·  Loteamento Jose Bernardino I e II  ·  444 unidades por frente')

