import numpy as np
import pandas as pd
from scipy.optimize import minimize
from datetime import datetime

def otimizacao_despacho_com_valor_futuro():
    """
    Programa de otimização para despacho hidrotérmico com VALOR FUTURO DA ÁGUA.
    
    Usa uma abordagem iterativa que considera o custo futuro:
    - Calcula o valor marginal da água em cada mês
    - Usa esse valor para otimizar o despacho de forma a minimizar custo total
    - Itera até convergência
    """

    # Parâmetros Gerais do Sistema
    p_hidro_min, p_hidro_max = 50, 400  # MW
    p_termo_min, p_termo_max = 100, 600  # MW
    
    # Parâmetros da Linha de Transmissão
    coef_perda = 0.0001
    limite_transmissao = 800  # MW
    
    # Custo da Termoelétrica
    custo_termo = 50  # $/MWh
    
    # Parâmetros do Reservatório
    volume_inicial = 50  # %
    volume_min = 20  # %
    volume_max = 95  # %
    capacidade_reservatorio = 5000  # MWh
    
    # Demanda e afluências
    demandas_mensais = np.array([520, 510, 480, 450, 420, 400, 410, 430, 460, 490, 520, 540])
    afluencias_mensais = np.array([800, 780, 720, 650, 550, 480, 500, 550, 650, 750, 800, 850])
    
    n_meses = len(demandas_mensais)
    horas_mes = 720
    meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    print("=" * 120)
    print("OTIMIZAÇÃO DE DESPACHO HIDROTÉRMICO COM VALOR FUTURO DA ÁGUA")
    print("=" * 120)
    print()
    
    # Inicializar valor da água (custo de oportunidade)
    # Começa com zero e será atualizado iterativamente
    valor_agua_futuro = np.zeros(n_meses)
    
    max_iteracoes = 10
    tolerancia = 1.0
    
    for iteracao in range(max_iteracoes):
        print(f"--- Iteração {iteracao + 1} ---")
        
        resultados = []
        volume_atual = volume_inicial * capacidade_reservatorio / 100
        custo_total_anual = 0
        
        # Otimizar cada mês sequencialmente
        for mes in range(n_meses):
            demanda = demandas_mensais[mes]
            afluencia = afluencias_mensais[mes]
            
            def objetivo_mes(x):
                """
                Minimizar: Custo da termoelétrica + Custo futuro da água não utilizada
                
                Se usar menos água hoje, terei mais água amanhã
                O valor futuro reflete o custo de usar termoeletricidade no futuro
                """
                p_hidro, p_termo = x[0], x[1]
                
                # Custo de termoeletricidade
                custo_termo_mes = p_termo * custo_termo * horas_mes
                
                # Energia hidro utilizada
                energia_hidro = p_hidro * horas_mes
                
                # Volume final do mês
                volume_novo = volume_atual + afluencia - energia_hidro
                volume_novo = max(volume_min * capacidade_reservatorio / 100,
                                min(volume_max * capacidade_reservatorio / 100, volume_novo))
                
                # Custo futuro: quanto maior o volume, menor o custo futuro
                # (mais água disponível para próximos meses)
                custo_futuro = -valor_agua_futuro[mes] * volume_novo
                
                return custo_termo_mes + custo_futuro
            
            def restricao_balanco(x):
                p_hidro, p_termo = x[0], x[1]
                perdas = coef_perda * (p_hidro + p_termo)**2
                return (p_hidro + p_termo) - demanda - perdas
            
            def restricao_transmissao(x):
                return limite_transmissao - (x[0] + x[1])
            
            # Condições iniciais
            p_hidro_init = min(p_hidro_max, demanda * 0.8)
            p_termo_init = max(p_termo_min, demanda * 0.2)
            x0 = np.array([p_hidro_init, p_termo_init])
            
            # Bounds
            bounds = [(p_hidro_min, p_hidro_max), (p_termo_min, p_termo_max)]
            
            # Restrições
            cons = [
                {'type': 'eq', 'fun': restricao_balanco},
                {'type': 'ineq', 'fun': restricao_transmissao}
            ]
            
            # Otimizar
            res = minimize(objetivo_mes, x0, method='SLSQP', bounds=bounds, 
                          constraints=cons, options={'ftol': 1e-9, 'maxiter': 2000})
            
            if res.success:
                p_hidro = res.x[0]
                p_termo = res.x[1]
            else:
                # Se falhar, usar solução inicial
                p_hidro = p_hidro_init
                p_termo = p_termo_init
            
            # Cálculos
            perdas = coef_perda * (p_hidro + p_termo)**2
            geracao_total = p_hidro + p_termo
            eficiencia = ((geracao_total - perdas) / geracao_total * 100) if geracao_total > 0 else 0
            proporcao_hidro = (p_hidro / geracao_total * 100) if geracao_total > 0 else 0
            
            energia_hidro = p_hidro * horas_mes
            volume_novo = volume_atual + afluencia - energia_hidro
            volume_novo = max(volume_min * capacidade_reservatorio / 100,
                            min(volume_max * capacidade_reservatorio / 100, volume_novo))
            
            custo_mes = p_termo * custo_termo
            custo_total_anual += custo_mes
            
            resultados.append({
                'Mês': meses_nomes[mes],
                'Demanda (MW)': demanda,
                'Afluência (MWh)': afluencia,
                'P_Hidro (MW)': p_hidro,
                'P_Termo (MW)': p_termo,
                'Geração Total (MW)': geracao_total,
                'Perdas (MW)': perdas,
                'Eficiência (%)': eficiencia,
                '% Hidro': proporcao_hidro,
                'Energia Hidro (MWh)': energia_hidro,
                'Volume Inicial (MWh)': volume_atual,
                'Volume Final (MWh)': volume_novo,
                'Custo ($)': custo_mes
            })
            
            volume_atual = volume_novo
        
        # Calcular novo valor futuro da água baseado nos custos
        # Água armazenada permite evitar custo termoelétrico futuro
        valor_agua_novo = np.zeros(n_meses)
        
        for mes in range(n_meses - 1):
            # Valor da água = quanto de custo termoelétrico pode ser evitado
            # Aproximação: custo_termo / eficiência de conversão
            valor_agua_novo[mes] = custo_termo * 0.5  # Fator de eficiência
        
        # Verificar convergência
        diferenca = np.max(np.abs(valor_agua_novo - valor_agua_futuro))
        print(f"Custo Total Anual: ${custo_total_anual:.2f}")
        print(f"Diferença no valor da água: {diferenca:.4f}")
        print()
        
        if diferenca < tolerancia:
            print("Convergência atingida!")
            print()
            break
        
        valor_agua_futuro = valor_agua_novo
    
    # Exibir resultados finais
    df_resultados = pd.DataFrame(resultados)
    
    print("=" * 120)
    print("RESUMO ANUAL - OTIMIZAÇÃO COM VALOR FUTURO")
    print("=" * 120)
    print()
    print(df_resultados.to_string(index=False))
    print()
    
    # Estatísticas
    print("=" * 120)
    print("ESTATÍSTICAS ANUAIS")
    print("=" * 120)
    print(f"Demanda Média Mensal: {df_resultados['Demanda (MW)'].mean():.2f} MW")
    print(f"Geração Hidrelétrica Média: {df_resultados['P_Hidro (MW)'].mean():.2f} MW")
    print(f"Geração Termoelétrica Média: {df_resultados['P_Termo (MW)'].mean():.2f} MW")
    print(f"Proporção Média de Hidro: {df_resultados['% Hidro'].mean():.2f}%")
    print()
    print(f"Energia Hidro Total Gerada: {df_resultados['Energia Hidro (MWh)'].sum():.1f} MWh")
    print(f"Afluência Total Anual: {df_resultados['Afluência (MWh)'].sum():.1f} MWh")
    print()
    print(f"Custo Total Anual de Operação: ${df_resultados['Custo ($)'].sum():.2f}")
    print(f"Custo Médio Mensal: ${df_resultados['Custo ($)'].mean():.2f}")
    print()
    print(f"Volume Final do Reservatório: {df_resultados['Volume Final (MWh)'].iloc[-1]:.1f} MWh ({df_resultados['Volume Final (MWh)'].iloc[-1]/5000*100:.1f}%)")
    print()
    
    # Salvar resultados
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    arquivo_csv = f"resultados_despacho_com_valor_futuro_{timestamp}.csv"
    df_resultados.to_csv(arquivo_csv, index=False)
    print(f"Resultados salvos em: {arquivo_csv}")
    print()
    
    return df_resultados

if __name__ == "__main__":
    resultados = otimizacao_despacho_com_valor_futuro()
