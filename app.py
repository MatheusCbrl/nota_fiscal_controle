import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import plotly.express as px

# Configurando a conexão com Supabase
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase: Client = create_client(url, key)

# Dados de login (usuário e senha para autenticação)
USUARIO = st.secrets["login"]["usuario"]
SENHA = st.secrets["login"]["senha"]

@st.cache_resource
def init_supabase() -> Client:
    return create_client(url, key)

supabase = init_supabase()

# Função para salvar ordem no Supabase
def salvar_ordem(data):
    try:
        response = supabase.table("ordens_despacho").insert(data).execute()
        return response
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# Função para buscar ordens de despacho
def buscar_ordens():
    try:
        ordens = supabase.table("ordens_despacho").select("*").execute()
        return pd.DataFrame(ordens.data)
    except Exception as e:
        st.error(f"Erro ao buscar dados: {e}")
        return pd.DataFrame()
    
# Função para mostrar tela de login
def mostrar_login():
    st.title("Login")
    usuario = st.text_input("Usuário:")
    senha = st.text_input("Senha:", type="password")
    if st.button("Entrar"):
        if usuario == USUARIO and senha == SENHA:
            st.session_state.authenticated = True
        else:
            st.error("Usuário ou senha incorretos")
            
# Verificar autenticação
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    mostrar_login()
else:
    aba = st.radio("Escolha a aba para começar: ", ["Cadastro", "Consulta e Relatórios"])
    # Aba de Cadastro
    
    if aba == "Cadastro":
        # Layout do Streamlit
        st.title("Sistema de Ordem de Despacho")
        
        # Campos do formulário
        col1, col2, col3 = st.columns(3)
        with col1:
            remetente = st.text_input("Remetente")
        with col2:
            endereco_remetente = st.text_input("Endereço do Remetente")
        with col3:
            destinatario = st.text_input("Destinatário")
        col1, col2, col3 = st.columns(3)
        with col1:
            endereco_destinatario = st.text_input("Endereço do Destinatário")
        with col2:
            cidade = st.text_input("Cidade")
        with col3:
            frete_tipo = st.selectbox("Tipo de Frete", ["Pago", "A Pagar"])
        col1, col2, col3 = st.columns(3)
        with col1:
            valor_frete = st.number_input("Valor do Frete (R$)", min_value=0.0, step=0.01)
        with col2:
            data_atual = datetime.datetime.now()
            data = st.date_input("Data", value=data_atual.date())
        with col3:
           
            hora = st.time_input("Hora", value=data_atual.time())
        
        conteudo = st.text_area("Conteúdo")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            qtde_volumes = st.number_input("Quantidade de Volumes", min_value=1, step=1)
        with col2:
            valor_nf = st.number_input("Valor da Nota Fiscal", min_value=0.0, step=0.01)
        with col3:
            peso = st.number_input("Peso (Kg)", min_value=0.0, step=0.01)
        with col4:
            solicitado_por = st.text_input("Solicitado Por")
        
        # Botão para salvar
        if st.button("Salvar Ordem"):
            dados_ordem = {
                "remetente": remetente,
                "endereco_remetente": endereco_remetente,
                "destinatario": destinatario,
                "endereco_destinatario": endereco_destinatario,
                "cidade": cidade,
                "frete_tipo": frete_tipo,
                "valor_frete": valor_frete,
                "data": str(data),
                "hora": str(hora),
                "conteudo": conteudo,
                "qtde_volumes": qtde_volumes,
                "valor_nf": valor_nf,
                "peso": peso,
                "solicitado_por": solicitado_por
            }
            response = salvar_ordem(dados_ordem)
            if response:
                st.success("Ordem salva com sucesso!")
        
        # Exibir registros existentes
        #st.subheader("Ordens de Despacho Registradas")
        #try:
        #    ordens = supabase.table("ordens_despacho").select("*").execute()
        #    if ordens.data:
        #        st.table(ordens.data)
        #    else:
        #        st.info("Nenhuma ordem registrada ainda.")
        #except Exception as e:
        #    st.error(f"Erro ao buscar dados: {e}")
    
    # Aba de Consulta e Relatórios
    elif aba == "Consulta e Relatórios":
        st.header("Consulta e Relatórios de Ordens de Despacho")
        # Buscar dados do banco
        df = buscar_ordens()
        
        if not df.empty:
            # Filtros
            st.subheader("Filtros")
            cidades = st.multiselect("Filtrar por Cidade", options=df["cidade"].unique())
            clientes = st.multiselect("Filtrar por Cliente", options=df["remetente"].unique())
            frete_tipo = st.selectbox("Filtrar por Frete", ["Todos", "Pago", "A Pagar"])
            
            # Aplicar filtros
            df_filtrado = df.copy()
            if cidades:
                df_filtrado = df_filtrado[df_filtrado["cidade"].isin(cidades)]
            if clientes:
                df_filtrado = df_filtrado[df_filtrado["remetente"].isin(clientes)]
            if frete_tipo != "Todos":
                df_filtrado = df_filtrado[df_filtrado["frete_tipo"] == frete_tipo]
            
            # Calcular faturamento
            faturamento_total = df_filtrado["valor_frete"].sum()
            st.write(f"**Faturamento Total Filtrado:** R$ {faturamento_total:.2f}")

            # Tabela de resultados filtrados
            st.subheader("Resultados Filtrados")
            st.dataframe(df_filtrado)

            # Gráfico: Fretes Pagos vs Não Pagos
            st.subheader("Gráfico: Fretes Pagos vs Não Pagos")
            if "frete_tipo" in df_filtrado.columns:
                grafico = df_filtrado["frete_tipo"].value_counts().reset_index()
                grafico.columns = ["Tipo de Frete", "Quantidade"]
                fig = px.bar(grafico, x="Tipo de Frete", y="Quantidade", title="Distribuição de Fretes Pagos e Não Pagos", color="Tipo de Frete")
                st.plotly_chart(fig)
        else:
            st.info("Nenhuma ordem registrada no momento.")

with st.sidebar:
      st.image("./logomarca.bmp")
      st.markdown(
          "## Dados de Contato:\n"
          "Fones (54) 3281-4230 / 98410-0000\n"
          "Rua Martin Bratz. 97\n"
          "CEP 95150-000 - Nova Petrópolis - RS\n"
          "CNPJ 03.673./0001-01 - Inscr. Est. 084/0032340\n"
      )
      st.markdown("---")
      st.markdown(
          "## Como Usar:\n"
          "1. Vá respondendo as perguntas📄\n"
          "2. Salve! As perguntas serão salvas no Banco de dados que poderá ser consultada mais tarde💬\n"
      )
      st.markdown("---")
      st.markdown("# Sobre")
      with st.expander("Eng. ML & IA 📖"):
          st.markdown("Matheus Cabral\n\n"
                  "+55 54 99930-7783. ")