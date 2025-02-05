import streamlit as st
from supabase import create_client, Client
import datetime
import pandas as pd
import plotly.express as px
import io
from io import BytesIO
from fpdf import FPDF

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


# Função para inserir dados na tabela cadastro_remetente
def inserir_remetente(nome, cpf_cnpj, endereco, contato):
    data = {
        "nome": nome,
        "cpf_cnpj": cpf_cnpj,
        "endereco": endereco,
        "contato": contato
    }
    response = supabase.table("cadastro_remetente").insert(data).execute()
    return response

    
# Função para buscar todos os remetentes cadastrados
def buscar_remetentes():
    response = supabase.table("cadastro_remetente").select("*").execute()
    return response.data if response else []

# Função para buscar todos as ordens para impressão
def buscar_ordens_impressao():
    response = supabase.table("ordens_despacho").select("*").execute()
    return response.data if response else []


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
    
# Função para excluir uma ordem
def excluir_ordem(ordem_id):
    try:
        response = supabase.table("ordens_despacho").delete().eq("id", ordem_id).execute()
        if response:
            st.success("Ordem excluída com sucesso!")
        else:
            st.error("Erro ao excluir a ordem. Tente novamente.")
    except Exception as e:
        st.error(f"Erro ao excluir a ordem: {e}")
        
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

class PDF(FPDF):
    def header(self):
        self.image("logomarca.png", 10, 8, 33)  # Logo at the top left
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "ORDEM DE DESPACHO", 0, 1, "C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Arial", "I", 8)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

    def add_order_details(self, order_data):
        self.set_font("Arial", size=10)
        self.cell(0, 5, f"Remetente: {order_data['remetente']}", ln=True)
        self.cell(0, 5, f"Destinatário: {order_data['destinatario']}", ln=True)
        self.cell(0, 5, f"Endereço: {order_data['endereco_destinatario']}", ln=True)
        self.cell(0, 5, f"Cidade: {order_data['cidade']}", ln=True)
        self.cell(0, 5, f"Frete: {order_data['frete_tipo']}", ln=True)
        self.cell(0, 5, f"Valor do Frete: R$ {order_data['valor_frete']:.2f}", ln=True)
        self.cell(0, 5, f"Número da Nota Fiscal: {order_data['valor_nf']}", ln=True)
        self.cell(0, 5, f"Quantidade de Volumes: {order_data['qtde_volumes']}", ln=True)
        self.cell(0, 5, f"Conteúdo: {order_data['conteudo']}", ln=True)
        self.cell(0, 5, f"Peso: {order_data['peso']} Kg", ln=True)
        self.cell(0, 5, f"Solicitado por: {order_data['solicitado_por']}", ln=True)
        self.cell(0, 5, f"Data: {order_data['data']} - Hora: {order_data['hora']}", ln=True)
        self.ln(5)  # Space before the signature line
        self.cell(0, 10, "__________________________", ln=True)
        self.cell(0, 10, "Assinatura", ln=True)

# Função para alternar o estado de "Pago" para "A Pagar" e vice-versa
def alternar_frete_tipo(ordem_id, estado_atual):
    novo_estado = "A Pagar" if estado_atual == "Pago" else "Pago"
    try:
        response = supabase.table("ordens_despacho").update({"frete_tipo": novo_estado}).eq("id", ordem_id).execute()
        if response:
            st.success(f"Estado alterado com sucesso para: {novo_estado}")
        else:
            st.error("Erro ao atualizar o estado. Tente novamente.")
    except Exception as e:
        st.error(f"Erro ao atualizar o estado: {e}")
        

# Verificar autenticação
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    mostrar_login()
else:
    aba = st.sidebar.radio("Navegação", ["Cadastro","Cadastro de Pessoas", "Consulta e Relatórios", "Filtrar por Cliente"])
    # Aba de Cadastro
    if aba == "Cadastro":
        # Layout do Streamlit
        st.title("Sistema de Ordem de Despacho")
        
        # Pesquisa de Remetente para Cadastro de Notas
        st.subheader("Pesquisar Pessoas")
        remetentes = buscar_remetentes()
        remetente_selecionado = None

        if remetentes:
            remetente_selecionado = st.selectbox(
                "Selecione a Pessoa", 
                options=remetentes, 
                format_func=lambda x: f"{x['nome']}"
            )
        else:
            st.warning("Nenhum cadastrado ainda!")

        # Preenchimento automático do Remetente
        remetente_nome = remetente_selecionado['nome'] if remetente_selecionado else ""
        remetente_endereco = remetente_selecionado['endereco'] if remetente_selecionado else ""

        # Campos do formulário
        col1, col2, col3 = st.columns(3)
        with col1:
            nr_nf = st.text_input("Número da Nota Fiscal")
            remetente = st.text_input("Remetente", value=remetente_nome, disabled=False)
        with col2:
            endereco_remetente = st.text_input("Endereço do Remetente", value=remetente_endereco, disabled=False)
        with col3:
            destinatario = st.text_input("Destinatário", value=remetente_nome, disabled=False)
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
                "solicitado_por": solicitado_por,
                "numero_nf": nr_nf
            }
            response = salvar_ordem(dados_ordem)
            if response:
                st.success("Ordem salva com sucesso!")
                
                # Geração do PDF com duas vias
                pdf = PDF(format="A4")
                pdf.set_auto_page_break(auto=True)
                pdf.add_page()
                pdf.add_order_details(dados_ordem)
                pdf.ln(10)  # Separação para a segunda via
                pdf.add_order_details(dados_ordem)
                
                # Salvar PDF único
                arquivo_pdf_unico = "Relatorio_Clientes_Unico.pdf"
                pdf.output(arquivo_pdf_unico)

                # Botão de download para o PDF gerado
                with open(arquivo_pdf_unico, "rb") as pdf_file:
                   st.download_button(
                       label="Baixar PDF Único",
                       data=pdf_file,
                       file_name=arquivo_pdf_unico,
                       mime="application/pdf",
                   )
    # aba "Cadastro de Pessoas"
    elif aba == "Cadastro de Pessoas":
        st.header("Cadastro de Pessoas")
        with st.form("form_cadastro_remetente"):
            nome = st.text_input("Nome (Obrigatório)", max_chars=255)
            cpf_cnpj = st.text_input("CPF/CNPJ (Opcional)", max_chars=20)
            endereco = st.text_area("Endereço (Opcional)")
            contato = st.text_input("Contato (Opcional)", max_chars=50)
        
            submitted = st.form_submit_button("Cadastrar")
        
            if submitted:
                if not nome:
                    st.error("O campo Nome é obrigatório!")
                else:
                    response = inserir_remetente(nome, cpf_cnpj if cpf_cnpj else None ,endereco if endereco else None, contato if contato else None)
                    if response:
                        st.success("Remetente cadastrado com sucesso!")
                    else:
                        st.error(f"Erro ao cadastrar remetente: {response.json()}")
    
        st.header("Ordens de Despacho Registradas")
        ordens = buscar_ordens()

        if not ordens.empty:
            st.dataframe(ordens)

            ordem_id = st.text_input("ID da Ordem para Excluir")
            if st.button("Excluir Ordem"):
                try:
                    response = supabase.table("ordens_despacho").delete().eq("id", ordem_id).execute()
                    if response:
                        st.success("Ordem excluída com sucesso!")
                    else:
                        st.error("Erro ao excluir a ordem. Verifique o ID.")
                except Exception as e:
                    st.error(f"Erro ao excluir a ordem: {e}")
        else:
            st.warning("Nenhuma ordem registrada.")
            
    # Atualizando a aba "Consulta e Relatórios"
    elif aba == "Consulta e Relatórios":
        
        #Exibir registros existentes
        st.header("Ordens de Despacho Registradas")
        try:
            ordens = supabase.table("ordens_despacho").select("*").execute()
            if ordens.data:
                # Exibir a tabela
                st.table(ordens.data)
                
                # Criar um DataFrame a partir dos dados
                df_ordens = pd.DataFrame(ordens.data)
                
                # Botão para download em Excel
                excel_file = io.BytesIO()
                with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
                    df_ordens.to_excel(writer, sheet_name='Ordens de Despacho', index=False)
                
                excel_file.seek(0)  # Voltar ao início do arquivo para leitura
        
                st.download_button(
                    label="Baixar como Excel",
                    data=excel_file,
                    file_name="ordens_despacho.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("Nenhuma ordem registrada ainda.")
        except Exception as e:
            st.error(f"Erro ao buscar dados: {e}")

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
        
            # Tabela de resultados filtrados com botão para alternar estado
            st.subheader("Resultados Filtrados")
            for index, row in df_filtrado.iterrows():
                st.write(f"**Ordem ID:** {row['id']}")
                st.write(f"**Remetente:** {row['remetente']}")
                st.write(f"**Tipo de Frete:** {row['frete_tipo']}")
                if st.button(f"Alterar para {'Pago' if row['frete_tipo'] == 'A Pagar' else 'A Pagar'}", key=row['id']):
                    alternar_frete_tipo(row['id'], row['frete_tipo'])
        
            # Gráfico: Fretes Pagos vs Não Pagos
            st.subheader("Gráfico: Fretes Pagos vs Não Pagos")
            if "frete_tipo" in df_filtrado.columns:
                grafico = df_filtrado["frete_tipo"].value_counts().reset_index()
                grafico.columns = ["Tipo de Frete", "Quantidade"]
                fig = px.bar(grafico, x="Tipo de Frete", y="Quantidade", title="Distribuição de Fretes Pagos e Não Pagos", color="Tipo de Frete")
                st.plotly_chart(fig)
    # Aba Filtrar por Cliente com Exportação para PDF
    elif aba == "Filtrar por Cliente":
        st.header("Filtrar e Imprimir Informações por Cliente")
        
        # Buscar dados do banco
        clientes = buscar_ordens_impressao()
        df = buscar_ordens()
        
        # Permitir seleção de até dois clientes
        clientes_selecionados = st.multiselect(
            "Selecione até dois clientes para gerar o relatório:",
            options=clientes,
            format_func=lambda x: f"{x['remetente']}",
            max_selections=2
        )

        if st.button("Gerar PDF"):
           if len(clientes_selecionados) == 0:
               st.warning("Por favor, selecione pelo menos um cliente.")
           elif len(clientes_selecionados) > 2:
               st.warning("Selecione no máximo dois clientes.")
           else:
               # Gerar dados filtrados para cada cliente
               pdf = PDF(format="A4")
               pdf.set_auto_page_break(auto=True)
               
               for cliente in clientes_selecionados:
                   df_cliente = buscar_ordens()
                   df_cliente_filtrado = df_cliente[df_cliente["remetente"] == cliente["remetente"]]
        
                   if df_cliente_filtrado.empty:
                       st.warning(f"Não há dados disponíveis para o cliente {cliente['remetente']}.")
                       continue
        
                   pdf.add_page()
                   for _, order in df_cliente_filtrado.iterrows():
                       pdf.add_order_details(order)
        
               # Salvar PDF único
               arquivo_pdf_unico = "Relatorio_Clientes_Unico.pdf"
               pdf.output(arquivo_pdf_unico)
        
               st.success("PDF único gerado com sucesso!")
               with open(arquivo_pdf_unico, "rb") as pdf_file:
                   st.download_button(
                       label="Baixar PDF Único",
                       data=pdf_file,
                       file_name=arquivo_pdf_unico,
                       mime="application/pdf",
                   )
                       



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
