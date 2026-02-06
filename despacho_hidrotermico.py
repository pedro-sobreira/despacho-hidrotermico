import numpy as np
import pandas as pd
from scipy.optimize import minimize, LinearConstraint, Bounds
from datetime import datetime

def otimizacao_despacho_anual_com_afluencias():
    """
    Programa de otimização para despacho hidrotérmico de duas usinas ao longo de 12 meses:
    1. Usina Hidrelétrica (UH) - Custo marginal zero, limitada por afluência
    2. Usina Termoelétrica (UT) - Custo linear
    Conectadas a uma carga através de uma linha de transmissão.
    
    O objetivo é determinar o despacho ótimo para cada mês do ano,
    considerando:
    - Variações de demanda mensal
    - Afluências (disponibilidade de água) mensais
    - Restrições de armazenamento de água
    - Balanço hídrico do reservatório
    """

    # Parâmetros Gerais do Sistema
    p_hidro_min, p_hidro_max = 50, 400  # MW
    p_termo_min, p_termo_max = 100, 600  # MW
    
    # Parâmetros da Linha de Transmissão
    coef_perda = 0.0001  # Perda = coef * (P_total)^2
    limite_transmissao = 800  # MW
    
    # Custo da Termoelétrica
    custo_termo = 50  # $/MWh
    
    # Parâmetros do Reservatório
    volume_inicial = 50  # % da capacidade
    volume_min = 20  # % da capacidade (volume mínimo operativo)
    volume_max = 95  # % da capacidade (volume máximo)
    capacidade_reservatorio = 5000  # MWh
    
    # Demanda de carga ao longo dos 12 meses (em MW)
    demandas_mensais = {
        'Janeiro': 520,
        'Fevereiro': 510,
        'Março': 480,
        'Abril': 450,
        'Maio': 420,
        'Junho': 400,
        'Julho': 410,
        'Agosto': 430,
        'Setembro': 460,
        'Outubro': 490,
        'Novembro': 520,
        'Dezembro': 540
    }
    
    # Afluências mensais (em MWh/mês)
    afluencias_mensais = {
        'Janeiro': 800,
        'Fevereiro': 780,
        'Março': 720,
        'Abril': 650,
        'Maio': 550,
        'Junho': 480,
        'Julho': 500,
        'Agosto': 550,
        'Setembro': 650,
        'Outubro': 750,
        'Novembro': 800,
        'Dezembro': 850
    }
    
    meses = list(demandas_mensais.keys())
    resultados = []
    volume_atual = volume_inicial * capacidade_reservatorio / 100
    
    print("=" * 110)
    print("OTIMIZAÇÃO DE DESPACHO HIDROTÉRMICO COM AFLUÊNCIAS - ANÁLISE ANUAL (12 MESES)")
    print("=" * 110)
    print()
    print(f"Capacidade do Reservatório: {capacidade_reservatorio} MWh")
    print(f"Volume Inicial: {volume_inicial}% ({volume_atual:.1f} MWh)")
    print(f"Volume Mínimo Operativo: {volume_min}% ({volume_min * capacidade_reservatorio / 100:.1f} MWh)")
    print(f"Volume Máximo: {volume_max}% ({volume_max * capacidade_reservatorio / 100:.1f} MWh)")
    print()
    
    # Otimizar para cada mês
    for idx, mes in enumerate(meses):
        demanda = demandas_mensais[mes]
        afluencia = afluencias_mensais[mes]
        
        print(f"--- Otimização para {mes} ---")
        print(f"  Demanda: {demanda} MW")
        print(f"  Afluência: {afluencia} MWh")
        print(f"  Volume do Reservatório no Início: {volume_atual:.1f} MWh ({volume_atual/capacidade_reservatorio*100:.1f}%)")
        
        # Energia disponível = Afluência + Volume armazenado, limitada pelo volume máximo
        energia_disponivel = min(afluencia + volume_atual, volume_max * capacidade_reservatorio / 100)
        
        horas_mes = 720
        p_hidro_max_disponivel = min(p_hidro_max, energia_disponivel / horas_mes)
        
        def objetivo(x):
            """Minimizar custo da termoelétrica"""
            p_hidro, p_termo = x[0], x[1]
            return p_termo * custo_termo

        def restricao_balanco(x):
            """Restrição: Geração = Demanda + Perdas"""
            p_hidro, p_termo = x[0], x[1]
            perdas = coef_perda * (p_hidro + p_termo)**2
            # Retorna zero quando a restrição é satisfeita
            return (p_hidro + p_termo) - demanda - perdas

        def restricao_transmissao(x):
            """Restrição: Geração ≤ Limite de transmissão"""
            return limite_transmissao - (x[0] + x[1])

        # Condições iniciais
        p_hidro_inicial = min(p_hidro_max_disponivel, demanda * 0.6)
        p_termo_inicial = max(p_termo_min, demanda * 0.4)
        x0 = np.array([p_hidro_inicial, p_termo_inicial])
        
        # Bounds
        p_hidro_max_bound = max(p_hidro_min, p_hidro_max_disponivel)
        bounds = Bounds([p_hidro_min, p_termo_min], [p_hidro_max_bound, p_termo_max])
        
        # Restrições
        cons = [
            {'type': 'eq', 'fun': restricao_balanco},
            {'type': 'ineq', 'fun': restricao_transmissao}
        ]

        # Executar otimização
        res = minimize(objetivo, x0, method='SLSQP', bounds=bounds, constraints=cons,
                      options={'ftol': 1e-9, 'maxiter': 2000})

        if res.success:
            p_hidro_otimo = res.x[0]
            p_termo_otimo = res.x[1]
            custo_total = res.fun
            perdas = coef_perda * (p_hidro_otimo + p_termo_otimo)**2
            geracao_total = p_hidro_otimo + p_termo_otimo
            eficiencia = ((geracao_total - perdas) / geracao_total * 100) if geracao_total > 0 else 0
            proporcao_hidro = (p_hidro_otimo / geracao_total * 100) if geracao_total > 0 else 0
            
            # Energia hidrelétrica utilizada
            energia_hidro_mes = p_hidro_otimo * horas_mes
            
            # Balanço hídrico
            volume_novo = volume_atual + afluencia - energia_hidro_mes
            volume_novo = max(volume_min * capacidade_reservatorio / 100,
                            min(volume_max * capacidade_reservatorio / 100, volume_novo))
            
            # Exibir resultados
            print(f"  Geração Hidrelétrica: {p_hidro_otimo:7.2f} MW ({proporcao_hidro:5.1f}%)")
            print(f"  Geração Termoelétrica: {p_termo_otimo:7.2f} MW ({100-proporcao_hidro:5.1f}%)")
            print(f"  Geração Total: {geracao_total:7.2f} MW")
            print(f"  Perdas na Transmissão: {perdas:7.2f} MW")
            print(f"  Eficiência de Transmissão: {eficiencia:6.2f}%")
            print(f"  Energia Hidro Utilizada: {energia_hidro_mes:7.1f} MWh")
            print(f"  Custo Total de Operação: ${custo_total:10.2f}")
            print(f"  Volume do Reservatório no Final: {volume_novo:.1f} MWh ({volume_novo/capacidade_reservatorio*100:.1f}%)")
            print()
            
            # Armazenar resultado
            resultados.append({
                'Mês': mes,
                'Demanda (MW)': demanda,
                'Afluência (MWh)': afluencia,
                'P_Hidro (MW)': p_hidro_otimo,
                'P_Termo (MW)': p_termo_otimo,
                'Geração Total (MW)': geracao_total,
                'Perdas (MW)': perdas,
                'Eficiência (%)': eficiencia,
                '% Hidro': proporcao_hidro,
                'Energia Hidro (MWh)': energia_hidro_mes,
                'Volume Inicial (MWh)': volume_atual,
                'Volume Final (MWh)': volume_novo,
                'Custo ($)': custo_total
            })
            
            volume_atual = volume_novo
            
        else:
            print(f"  Erro na otimização: {res.message}")
            print()
    
    # Criar DataFrame
    df_resultados = pd.DataFrame(resultados)
    
    # Resumo anual
    print("=" * 110)
    print("RESUMO ANUAL")
    print("=" * 110)
    print()
    print(df_resultados.to_string(index=False))
    print()
    
    # Estatísticas
    print("=" * 110)
    print("ESTATÍSTICAS ANUAIS")
    print("=" * 110)
    print(f"Demanda Média Mensal: {df_resultados['Demanda (MW)'].mean():.2f} MW")
    print(f"Demanda Máxima: {df_resultados['Demanda (MW)'].max():.2f} MW ({df_resultados.loc[df_resultados['Demanda (MW)'].idxmax(), 'Mês']})")
    print(f"Demanda Mínima: {df_resultados['Demanda (MW)'].min():.2f} MW ({df_resultados.loc[df_resultados['Demanda (MW)'].idxmin(), 'Mês']})")
    print()
    print(f"Afluência Total Anual: {df_resultados['Afluência (MWh)'].sum():.1f} MWh")
    print(f"Afluência Média Mensal: {df_resultados['Afluência (MWh)'].mean():.1f} MWh")
    print()
    print(f"Geração Hidrelétrica Média: {df_resultados['P_Hidro (MW)'].mean():.2f} MW")
    print(f"Geração Termoelétrica Média: {df_resultados['P_Termo (MW)'].mean():.2f} MW")
    print(f"Proporção Média de Hidro: {df_resultados['% Hidro'].mean():.2f}%")
    print()
    print(f"Energia Hidro Total Gerada: {df_resultados['Energia Hidro (MWh)'].sum():.1f} MWh")
    print(f"Perdas Médias na Transmissão: {df_resultados['Perdas (MW)'].mean():.2f} MW")
    print(f"Eficiência Média de Transmissão: {df_resultados['Eficiência (%)'].mean():.2f}%")
    print()
    print(f"Custo Total Anual de Operação: ${df_resultados['Custo ($)'].sum():.2f}")
    print(f"Custo Médio Mensal: ${df_resultados['Custo ($)'].mean():.2f}")
    print()
    print(f"Volume Final do Reservatório: {df_resultados['Volume Final (MWh)'].iloc[-1]:.1f} MWh ({df_resultados['Volume Final (MWh)'].iloc[-1]/capacidade_reservatorio*100:.1f}%)")
    print()
    
    # Salvar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo_csv = f"resultados_despacho_com_afluencias_{timestamp}.csv"
    df_resultados.to_csv(arquivo_csv, index=False)
    print(f"Resultados salvos em: {arquivo_csv}")
    print()
    
    return df_resultados

if __name__ == "__main__":
    resultados = otimizacao_despacho_anual_com_afluencias()
