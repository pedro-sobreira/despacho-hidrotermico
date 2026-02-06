import numpy as np
import pandas as pd
from scipy.optimize import minimize
from datetime import datetime

def otimizacao_despacho_iterativo():
    """
    Otimização iterativa com preços sombra da água.
    
    Usa método de Benders/Dantzig-Wolfe:
    1. Otimiza cada mês com preço sombra da água
    2. Calcula novo preço sombra baseado em escassez
    3. Itera até convergência
    """

    # Parâmetros
    p_hidro_min, p_hidro_max = 50, 400  # MW
    p_termo_min, p_termo_max = 100, 600  # MW
    
    coef_perda = 0.0001
    limite_transmissao = 800  # MW
    custo_termo = 50  # $/MWh
    
    volume_inicial = 50  # %
    volume_min = 20  # %
    volume_max = 95  # %
    capacidade_reservatorio = 5000  # MWh
    
    demandas_mensais = np.array([520, 510, 480, 450, 420, 400, 410, 430, 460, 490, 520, 540])
    afluencias_mensais = np.array([800, 780, 720, 650, 550, 480, 500, 550, 650, 750, 800, 850])
    
    n_meses = len(demandas_mensais)
    horas_mes = 720
    meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    print("=" * 120)
    print("OTIMIZAÇÃO ITERATIVA COM PREÇOS SOMBRA DA ÁGUA")
    print("=" * 120)
    print()
    
    # Inicializar preços sombra
    preco_agua = np.zeros(n_meses)
    
    max_iteracoes = 20
    tolerancia = 0.01
    
    for iteracao in range(max_iteracoes):
        print(f"--- Iteração {iteracao + 1} ---")
        
        resultados = []
        volume_atual = volume_inicial * capacidade_reservatorio / 100
        custo_total_anual = 0
        preco_agua_novo = np.zeros(n_meses)
        
        # Otimizar cada mês
        for mes in range(n_meses):
            demanda = demandas_mensais[mes]
            afluencia = afluencias_mensais[mes]
            
            def objetivo_mes(x):
                """
                Minimizar: Custo_termo + Preço_água × Energia_hidro
                
                Se preço_água é alto, usar menos água (mais termo)
                Se preço_água é baixo, usar mais água (menos termo)
                """
                p_hidro, p_termo = x[0], x[1]
                
                custo_termo_mes = p_termo * custo_termo
                energia_hidro = p_hidro * horas_mes
                custo_agua_mes = preco_agua[mes] * energia_hidro
                
                return custo_termo_mes + custo_agua_mes
            
            def restricao_balanco(x):
                p_hidro, p_termo = x[0], x[1]
                perdas = coef_perda * (p_hidro + p_termo)**2
                return (p_hidro + p_termo) - demanda - perdas
            
            def restricao_transmissao(x):
                return limite_transmissao - (x[0] + x[1])
            
            # Inicializar
            p_hidro_init = min(p_hidro_max, demanda * 0.7)
            p_termo_init = max(p_termo_min, demanda * 0.3)
            x0 = np.array([p_hidro_init, p_termo_init])
            
            bounds = [(p_hidro_min, p_hidro_max), (p_termo_min, p_termo_max)]
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
            
            # Calcular novo preço sombra para próximo mês
            # Baseado em quanto de água foi "economizada" ou "gasta"
            if mes < n_meses - 1:
                # Se volume está no máximo, água tem valor baixo (abundância)
                # Se volume está no mínimo, água tem valor alto (escassez)
                proporcao_volume = (volume_novo - volume_min * capacidade_reservatorio / 100) / \
                                 ((volume_max - volume_min) * capacidade_reservatorio / 100)
                
                # Preço sombra = custo_termo × (1 - proporcao_volume)
                # Se volume alto (proporcao=1): preço=0 (água abundante)
                # Se volume baixo (proporcao=0): preço=custo_termo (água escassa)
                preco_agua_novo[mes + 1] = custo_termo * (1 - proporcao_volume)
            
            resultados.append({
                'Mês': meses_nomes[mes],
                'Demanda (MW)': demanda,
                'Afluência (MWh)': afluencia,
                'Preço Água ($/MWh)': preco_agua[mes],
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
        
        # Verificar convergência
        diferenca = np.max(np.abs(preco_agua_novo - preco_agua))
        print(f"Custo Total Anual: ${custo_total_anual:.2f}")
        print(f"Diferença no preço da água: {diferenca:.6f}")
        print()
        
        if diferenca < tolerancia and iteracao > 0:
            print("Convergência atingida!")
            print()
            break
        
        preco_agua = preco_agua_novo
    
    # Exibir resultados finais
    df_resultados = pd.DataFrame(resultados)
    
    print("=" * 120)
    print("RESUMO ANUAL - OTIMIZAÇÃO COM PREÇOS SOMBRA")
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
    arquivo_csv = f"resultados_despacho_iterativo_{timestamp}.csv"
    df_resultados.to_csv(arquivo_csv, index=False)
    print(f"Resultados salvos em: {arquivo_csv}")
    print()
    
    return df_resultados

if __name__ == "__main__":
    resultados = otimizacao_despacho_iterativo()
