import numpy as np
import pandas as pd
from scipy.optimize import minimize
from datetime import datetime

def otimizacao_despacho_anual():
    """
    Programa de otimização para despacho hidrotérmico de duas usinas ao longo de 12 meses:
    1. Usina Hidrelétrica (UH) - Custo marginal zero
    2. Usina Termoelétrica (UT) - Custo linear
    Conectadas a uma carga através de uma linha de transmissão.
    
    O objetivo é determinar o despacho ótimo para cada mês do ano,
    considerando variações de demanda mensal.
    """

    # Parâmetros Gerais do Sistema
    # Limites de Geração (constantes ao longo do ano)
    p_hidro_min, p_hidro_max = 50, 400  # MW
    p_termo_min, p_termo_max = 100, 600  # MW
    
    # Parâmetros da Linha de Transmissão
    coef_perda = 0.0001  # Perda = coef * (P_total)^2
    limite_transmissao = 800  # MW
    
    # Custo da Termoelétrica (constante ao longo do ano)
    custo_termo = 50  # $/MWh
    
    # Demanda de carga ao longo dos 12 meses (em MW)
    # Simulando variação sazonal: maior no inverno, menor no verão
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
    
    # Nomes dos meses
    meses = list(demandas_mensais.keys())
    
    # Armazenar resultados
    resultados = []
    
    print("=" * 80)
    print("OTIMIZAÇÃO DE DESPACHO HIDROTÉRMICO - ANÁLISE ANUAL (12 MESES)")
    print("=" * 80)
    print()
    
    # Otimizar para cada mês
    for mes, demanda in demandas_mensais.items():
        print(f"--- Otimização para {mes} (Demanda: {demanda} MW) ---")
        
        def objetivo(x):
            # x[0] = P_hidro, x[1] = P_termo
            # Objetivo: minimizar custo da termoelétrica
            return x[1] * custo_termo

        def restricao_balanco(x):
            """Restrição: Geração = Demanda + Perdas"""
            p_hidro, p_termo = x[0], x[1]
            perdas = coef_perda * (p_hidro + p_termo)**2
            return (p_hidro + p_termo) - demanda - perdas

        def restricao_transmissao(x):
            """Restrição: Geração não deve exceder limite de transmissão"""
            return limite_transmissao - (x[0] + x[1])

        # Condições Iniciais (estratégia: maximizar hidro)
        x0 = [min(p_hidro_max, demanda * 0.7), min(p_termo_max, demanda * 0.3)]
        
        # Definição dos Limites (Bounds)
        bounds = [(p_hidro_min, p_hidro_max), (p_termo_min, p_termo_max)]
        
        # Definição das Restrições
        cons = [
            {'type': 'eq', 'fun': restricao_balanco},
            {'type': 'ineq', 'fun': restricao_transmissao}
        ]

        # Execução da Otimização
        res = minimize(objetivo, x0, method='SLSQP', bounds=bounds, constraints=cons, 
                      options={'ftol': 1e-9, 'maxiter': 1000})

        if res.success:
            p_hidro_otimo = res.x[0]
            p_termo_otimo = res.x[1]
            custo_total = res.fun
            perdas = coef_perda * (p_hidro_otimo + p_termo_otimo)**2
            geracao_total = p_hidro_otimo + p_termo_otimo
            eficiencia = ((geracao_total - perdas) / geracao_total * 100) if geracao_total > 0 else 0
            proporcao_hidro = (p_hidro_otimo / geracao_total * 100) if geracao_total > 0 else 0
            
            # Exibir resultados do mês
            print(f"  Geração Hidrelétrica: {p_hidro_otimo:7.2f} MW ({proporcao_hidro:5.1f}%)")
            print(f"  Geração Termoelétrica: {p_termo_otimo:7.2f} MW ({100-proporcao_hidro:5.1f}%)")
            print(f"  Geração Total: {geracao_total:7.2f} MW")
            print(f"  Perdas na Transmissão: {perdas:7.2f} MW")
            print(f"  Eficiência de Transmissão: {eficiencia:6.2f}%")
            print(f"  Custo Total de Operação: ${custo_total:10.2f}")
            print()
            
            # Armazenar resultado
            resultados.append({
                'Mês': mes,
                'Demanda (MW)': demanda,
                'P_Hidro (MW)': p_hidro_otimo,
                'P_Termo (MW)': p_termo_otimo,
                'Geração Total (MW)': geracao_total,
                'Perdas (MW)': perdas,
                'Eficiência (%)': eficiencia,
                '% Hidro': proporcao_hidro,
                'Custo ($)': custo_total
            })
        else:
            print(f"  Erro na otimização: {res.message}")
            print()
    
    # Criar DataFrame com resultados
    df_resultados = pd.DataFrame(resultados)
    
    # Exibir resumo anual
    print("=" * 80)
    print("RESUMO ANUAL")
    print("=" * 80)
    print()
    print(df_resultados.to_string(index=False))
    print()
    
    # Estatísticas anuais
    print("=" * 80)
    print("ESTATÍSTICAS ANUAIS")
    print("=" * 80)
    print(f"Demanda Média Mensal: {df_resultados['Demanda (MW)'].mean():.2f} MW")
    print(f"Demanda Máxima: {df_resultados['Demanda (MW)'].max():.2f} MW ({df_resultados.loc[df_resultados['Demanda (MW)'].idxmax(), 'Mês']})")
    print(f"Demanda Mínima: {df_resultados['Demanda (MW)'].min():.2f} MW ({df_resultados.loc[df_resultados['Demanda (MW)'].idxmin(), 'Mês']})")
    print()
    print(f"Geração Hidrelétrica Média: {df_resultados['P_Hidro (MW)'].mean():.2f} MW")
    print(f"Geração Termoelétrica Média: {df_resultados['P_Termo (MW)'].mean():.2f} MW")
    print(f"Proporção Média de Hidro: {df_resultados['% Hidro'].mean():.2f}%")
    print()
    print(f"Perdas Médias na Transmissão: {df_resultados['Perdas (MW)'].mean():.2f} MW")
    print(f"Eficiência Média de Transmissão: {df_resultados['Eficiência (%)'].mean():.2f}%")
    print()
    print(f"Custo Total Anual de Operação: ${df_resultados['Custo ($)'].sum():.2f}")
    print(f"Custo Médio Mensal: ${df_resultados['Custo ($)'].mean():.2f}")
    print()
    
    # Salvar resultados em arquivo CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo_csv = f"resultados_despacho_{timestamp}.csv"
    df_resultados.to_csv(arquivo_csv, index=False)
    print(f"Resultados salvos em: {arquivo_csv}")
    print()
    
    return df_resultados

if __name__ == "__main__":
    resultados = otimizacao_despacho_anual()
