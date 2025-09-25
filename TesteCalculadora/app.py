from flask import Flask, render_template, request, jsonify
import math
import os

app = Flask(__name__)

# Configuração para encontrar a pasta de templates
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app.template_folder = template_dir


# --- Funções Auxiliares e de Cálculo ---

def parse_input_value(value_str):
    """Converte a entrada do utilizador (com . ou ,) para float."""
    if not isinstance(value_str, str) or not value_str.strip():
        return 0.0
    return float(value_str.replace('.', '').replace(',', '.'))

def calculate_future_value(rate, nper, pv):
    """Calcula o Valor Futuro (VF), replicando a função FV do Excel."""
    if rate < 0 or nper < 0: return 0
    return pv * math.pow(1 + rate, nper)

def calculate_pmt(rate, nper, pv):
    if nper <= 0 or pv < 0: return 0
    # Se a taxa é zero, a parcela é uma simples divisão (parcela nominal)
    if rate == 0:
        return pv / nper
    # Caso contrário, calcula a parcela com juros
    return (pv * rate) / (1 - math.pow(1 + rate, -nper))

# --- Rotas da Aplicação Web ---

@app.route('/')
def index():
    """Serve a página principal da calculadora."""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """Recebe os dados do formulário, calcula e retorna o resultado."""
    try:
        data = request.get_json()

        # --- 1. Coleta dos Dados de Entrada ---
        valor_lote = parse_input_value(data.get('valor_lote'))
        ato = parse_input_value(data.get('ato'))
        prazo_meses_str = data.get('prazo_meses', '0').strip()
        prazo_meses = int(prazo_meses_str) if prazo_meses_str else 0
        taxa_anual = parse_input_value(data.get('taxa_anual')) / 100
        parcela_aprovada_input = parse_input_value(data.get('parcela_aprovada'))
        
        iniciais = data.get('iniciais', [])
        soma_iniciais = sum(parse_input_value(val) for val in iniciais if val and val.strip())
        qtde_iniciais = len([val for val in iniciais if val and val.strip()])

        if valor_lote <= 0 or prazo_meses <= 0 or parcela_aprovada_input <= 0:
             # Permitimos taxa anual zero, então a verificação foi removida daqui
            if taxa_anual < 0:
                raise ValueError("A taxa anual não pode ser negativa.")
            if not (valor_lote > 0 and prazo_meses > 0 and parcela_aprovada_input > 0):
                 raise ValueError("Os campos de valor do lote, prazo e parcela aprovada devem ser preenchidos com valores positivos.")

        # --- 2. Cálculos Financeiros com a nova lógica ---
        valor_financiado_inicial = valor_lote - ato - soma_iniciais

        if valor_financiado_inicial <= 0:
            return jsonify({
                'status': 'success', 'approved': True,
                'message': 'PROPOSTA APROVADA!',
                'details': 'O valor das entradas já quita o lote.'
            })

        # Se a taxa for zero, o cálculo da parcela será nominal. Se não, será com juros.
        if taxa_anual == 0:
            taxa_mensal = 0
            principal_para_parcelas = valor_financiado_inicial # Sem juros, o valor não é "atualizado"
        else:
            taxa_mensal_raw = (1 + taxa_anual)**(1/12) - 1
            taxa_mensal = round(taxa_mensal_raw, 8)
            principal_para_parcelas = calculate_future_value(rate=taxa_mensal, nper=qtde_iniciais, pv=valor_financiado_inicial)
        
        parcela_calculada = calculate_pmt(rate=taxa_mensal, nper=prazo_meses, pv=principal_para_parcelas)

        # --- 3. Formatação e Comparação ---
        f_parcela_aprovada = f"{parcela_aprovada_input:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        f_parcela_calculada = f"{parcela_calculada:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        approved = parcela_aprovada_input >= parcela_calculada
        
        if approved:
            message = 'PROPOSTA APROVADA'
            details = f'A parcela de R$ {f_parcela_aprovada} é suficiente. (Parcela necessária: R$ {f_parcela_calculada})'
        else:
            message = 'PROPOSTA REPROVADA'
            details = f'A parcela calculada de R$ {f_parcela_calculada} é MAIOR que a aprovada de R$ {f_parcela_aprovada}.'
            
        return jsonify({
            'status': 'success', 'approved': approved,
            'message': message, 'details': details
        })

    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro interno no servidor. Verifique os valores.'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)