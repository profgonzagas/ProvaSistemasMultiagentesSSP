"""
ETAPA 6 -- Os especialistas, cada um com UMA responsabilidade e SÓ as tools de que precisa.

ESQUELETO:
  ETAPA 6.1 -- criar_normas(), criar_escala(), criar_financeiro(), criar_redator()
  ETAPA 6.2 -- criar_coordenador(): usa Normas, Escala e Financeiro como TOOLS (as_tool)

As tools abaixo (PRONTAS) só repassam a chamada ao MCP Server do RH (cliente_mcp.chamar_mcp_async). Dar a cada agente
só as tools dele é o PRIVILÉGIO MÍNIMO (Etapa 9.1); o hook do 🆕 B (etapa10_governanca.py) confere isso em tempo de execução.

REFERÊNCIAS NAS AULAS
  aula4/ex03_agente_as_tool.py                         Coordenador que chama especialistas como tools    <- o mais parecido
  aula2/agente_handoff2.py                             as_tool com tool_name e tool_description
  aula4/ex02_handoff_roteamento.py                     handoff: compare (quem responde no fim?)
  aula7/exemplos/02_agentes_especializados/main.py     uma responsabilidade por agente
  aula7/agentes.py                                     ModelSettings(temperature=0) para respostas mais estáveis
  aula8/exemplos/06_excessive_agency/1_codigo_pronto/main.py   o problema de dar tools DEMAIS a um agente
"""
import json

from agents import Agent, ModelSettings, RunHooks, function_tool

from etapa05_cliente_mcp import chamar_mcp_async
from etapa04_ferramentas import cotacao_usd_brl

CONFIG = ModelSettings(temperature=0)


# ------------------------------------------------------------------ tools (PRONTAS)
@function_tool
async def consultar_normas(tema: str) -> str:
    """Regras da norma interna sobre um tema: férias, prazos, escala, abono, diária, aprovação, saúde ou dados."""
    return json.dumps(await chamar_mcp_async("consultar_normas", {"tema": tema}), ensure_ascii=False)


@function_tool
async def consultar_escala(equipe: str, inicio: str, fim: str) -> str:
    """Afastamentos da equipe que se sobrepõem ao período (AAAA-MM-DD) e o limite de afastados da regra N5."""
    return json.dumps(await chamar_mcp_async("consultar_escala", {"equipe": equipe, "inicio": inicio, "fim": fim}),
                      ensure_ascii=False)


@function_tool
async def tabela_diarias(tipo_destino: str) -> str:
    """Moeda e valor da diária para o tipo de destino: capital, interior ou exterior."""
    return json.dumps(await chamar_mcp_async("tabela_diarias", {"tipo_destino": tipo_destino}), ensure_ascii=False)


@function_tool
async def consultar_remuneracao(matricula: str) -> str:
    """[RESTRITA] Salário-base de um servidor. Só para calcular a venda de férias (N2)."""
    print(f"[tool] consultar_remuneracao({matricula}) EXECUTOU")  # o 🆕 B prova que, barrada, ela NÃO executa
    return json.dumps(await chamar_mcp_async("consultar_remuneracao", {"matricula": matricula}), ensure_ascii=False)


@function_tool
def cotacao_dolar() -> str:
    """Cotação atual do dólar em reais (USD->BRL). Devolve 'indisponível' se a API falhar: nunca invente o câmbio."""
    cotacao = cotacao_usd_brl()
    return f"{cotacao:.4f}" if cotacao else "indisponível"


# ------------------------------------------------------------------ ETAPA 6.1: especialistas
def criar_normas() -> Agent:
    # ETAPA 6.1 -- responsabilidade: dizer QUAIS regras se aplicam e explicá-las. Só a tool consultar_normas.
    return Agent(
        name="Normas",
        instructions=(
            "Você é o especialista em NORMAS do RH. Recebe um pedido (férias, abono ou diária) com os fatos já "
            "levantados e as VIOLAÇÕES OBJETIVAS calculadas pelo sistema. Use consultar_normas (temas: férias, "
            "prazos, escala, abono, diária, aprovação) para buscar as regras do tipo do pedido e responda, em "
            "poucas linhas: quais regras se aplicam (pelo código, ex.: N1, N3), quais foram cumpridas e quais "
            "foram violadas, explicando cada violação em linguagem simples. Quem decide se houve violação é o "
            "sistema: NÃO contradiga a lista de violações objetivas recebida. Não calcule valores e não consulte "
            "a escala. Nunca escreva CPF ou dado de saúde."
        ),
        tools=[consultar_normas],
        model_settings=CONFIG,
    )


def criar_escala() -> Agent:
    # ETAPA 6.1 -- confere a N5 e, se houver conflito, SUGERE outro período. Só a tool consultar_escala.
    return Agent(
        name="Escala",
        instructions=(
            "Você é o especialista em ESCALA do RH. Use consultar_escala com a equipe do servidor e o período "
            "pedido (datas AAAA-MM-DD) e confira a regra N5: na mesma equipe, no máximo limite_afastados "
            "pessoas afastadas no mesmo dia (não conte o próprio servidor). Responda em poucas linhas: quem já "
            "está afastado no período e se há conflito. Se houver conflito, SUGIRA outro período com o MESMO "
            "número de dias, começando DEPOIS do fim do último afastamento em conflito, numa segunda, terça ou "
            "quarta-feira que não seja véspera de feriado (regra N3). Não calcule valores. Nunca escreva CPF "
            "ou dado de saúde."
        ),
        tools=[consultar_escala],
        model_settings=CONFIG,
    )


def criar_financeiro() -> Agent:
    # ETAPA 6.1 -- o ÚNICO agente que vê o salário (consultar_remuneracao).
    return Agent(
        name="Financeiro",
        instructions=(
            "Você é o especialista FINANCEIRO do RH. Calcule o valor do pedido e mostre a conta:\n"
            "- Férias com venda de dias (N2): use consultar_remuneracao; valor = dias_vendidos x salario_base / 30. "
            "O salário-base é dado RESTRITO: escreva a fórmula e o resultado (ex.: '10 dias x salário-base/30 = "
            "R$ 3.166,67'), nunca o valor do salário em si.\n"
            "- Diária (N7): use tabela_diarias com o tipo_destino. Uma diária por dia com pernoite e MEIA diária "
            "no dia do retorno: diárias = (dias corridos - 1) + 0,5. Ex.: 08/06 a 11/06 = 3 + 0,5 = 3,5 diárias. "
            "No exterior o valor é em USD: use cotacao_dolar e converta para reais. Se a cotação vier "
            "'indisponível', escreva o total em USD e 'valor em reais: a calcular' (NUNCA invente o câmbio).\n"
            "- Férias sem venda e abono: responda 'não há valor a pagar'.\n"
            "Responda em poucas linhas, com os números. Nunca escreva CPF ou dado de saúde."
        ),
        tools=[tabela_diarias, consultar_remuneracao, cotacao_dolar],
        model_settings=CONFIG,
    )


def criar_redator() -> Agent:
    # ETAPA 6.1 -- sem tools: escreve o despacho só com os fatos recebidos.
    return Agent(
        name="Redator",
        instructions=(
            "Você é o REDATOR do RH. Escreve o DESPACHO de um pedido de férias, abono ou diária, em português "
            "formal e em no máximo 8 linhas, usando SÓ os fatos recebidos (não invente nada). O despacho precisa "
            "citar: a matrícula do servidor, o período (com a data de início no formato DD/MM/AAAA), as regras "
            "aplicadas pelo código (ex.: N5) e os valores calculados, se houver. A DECISÃO vem pronta nos fatos: "
            "nunca a mude, e escreva-a com a palavra exata 'DEFERIDO' ou 'INDEFERIDO' (ex.: 'Decisão: "
            "INDEFERIDO'). No indeferimento, explique o motivo e inclua a sugestão de novas datas, se houver. "
            "Nunca escreva CPF, CID, salário ou qualquer informação de saúde (N10). Se receber um FEEDBACK "
            "(da validação ou da chefia), reescreva o despacho inteiro corrigindo exatamente o que foi apontado."
        ),
        model_settings=CONFIG,
    )


# ------------------------------------------------------------------ ETAPA 6.2: coordenador
def criar_coordenador(hooks: RunHooks | None = None, tools_extras: list | None = None) -> Agent:
    # ETAPA 6.2 -- os especialistas viram TOOLS do Coordenador (as_tool): ele continua no comando e junta os pareceres.
    #   hooks=hooks: o hook do 🆕 B enxerga também as tools DENTRO de cada especialista.
    #   failure_error_function=None: um erro dentro do especialista interrompe a execução (não vira só um texto).
    return Agent(
        name="Coordenador",
        instructions=(
            "Você coordena a análise de um pedido ao RH e monta um PARECER ÚNICO. Consulte os especialistas "
            "passando a eles TODOS os fatos recebidos (pedido, servidor, período e violações objetivas):\n"
            "- parecer_normas: SEMPRE;\n"
            "- parecer_escala: em férias e abono (regra N5);\n"
            "- parecer_financeiro: SÓ em diária ou em férias com dias_vendidos maior que 0 (abono não tem valor).\n"
            "Depois junte as respostas num parecer curto, com uma seção por especialista consultado. As violações "
            "objetivas recebidas foram calculadas pelo sistema e são a palavra final: não as contradiga. "
            "Nunca escreva CPF, salário ou dado de saúde."
        ),
        tools=[
            criar_normas().as_tool(
                tool_name="parecer_normas",
                tool_description="Especialista em normas: diz quais regras (N1..N10) se aplicam ao pedido e explica as violações.",
                hooks=hooks, failure_error_function=None),
            criar_escala().as_tool(
                tool_name="parecer_escala",
                tool_description="Especialista em escala: confere a regra N5 na equipe e sugere outro período se houver conflito.",
                hooks=hooks, failure_error_function=None),
            criar_financeiro().as_tool(
                tool_name="parecer_financeiro",
                tool_description="Especialista financeiro: calcula a venda de férias (N2) ou as diárias (N7), mostrando a conta.",
                hooks=hooks, failure_error_function=None),
            *(tools_extras or []),
        ],
        model_settings=CONFIG,
    )
