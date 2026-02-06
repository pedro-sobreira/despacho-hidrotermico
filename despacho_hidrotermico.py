import numpy as np
from scipy.optimize import minimize

def otimizacao_despacho():
    """
    Programa de otimização para despacho hidrotérmico de duas usinas:
    1. Usina Hidrelétrica (UH)
    2. Usina Termoelétrica (UT)
    Conectadas a uma carga através de uma linha de transmissão.
    """

    # Parâmetros do Problema
    demanda = 500  # MW
    custo_termo = 50  # $/MWh (Custo linear simplificado)
    
    # Limites de Geração
    p_hidro_min, p_hidro_max = 50, 400  # MW
    p_termo_min, p_termo_max = 100, 600  # MW
    
    # Parâmetros da Linha de Transmissão (Simplificado: Perdas quadráticas)
    coef_perda = 0.0001  # Perda = coef * (P_total)^2
    limite_transmissao = 800  # MW

    def objetivo(x):
        # x[0] = P_hidro, x[1] = P_termo
        # O objetivo é minimizar o custo da termelétrica (hidro tem custo marginal zero)
        return x[1] * custo_termo

    def restricao_balanco(x):
        p_hidro, p_termo = x[0], x[1]
        perdas = coef_perda * (p_hidro + p_termo)**2
        return (p_hidro + p_termo) - demanda - perdas

    def restricao_transmissao(x):
        return limite_transmissao - (x[0] + x[1])

    # Condições Iniciais
    x0 = [250, 250]
    
    # Definição dos Limites (Bounds)
    bounds = [(p_hidro_min, p_hidro_max), (p_termo_min, p_termo_max)]
    
    # Definição das Restrições
    cons = [
        {'type': 'eq', 'fun': restricao_balanco},
        {'type': 'ineq', 'fun': restricao_transmissao}
    ]

    # Execução da Otimização
    res = minimize(objetivo, x0, method='SLSQP', bounds=bounds, constraints=cons)

    if res.success:
        p_hidro_otimo = res.x[0]
        p_termo_otimo = res.x[1]
        custo_total = res.fun
        perdas = coef_perda * (p_hidro_otimo + p_termo_otimo)**2
        
        print("--- Resultados da Otimização ---")
        print(f"Geração Hidrelétrica: {p_hidro_otimo:.2f} MW")
        print(f"Geração Termoelétrica: {p_termo_otimo:.2f} MW")
        print(f"Perdas na Transmissão: {perdas:.2f} MW")
        print(f"Demanda Atendida: {demanda} MW")
        print(f"Custo Total de Operação: ${custo_total:.2f}")
    else:
        print("Erro na otimização:", res.message)

if __name__ == "__main__":
    otimizacao_despacho()
