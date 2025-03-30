import streamlit as st
import database as db
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="Controle de Leitura Ativa do Taz",
    page_icon="📚",
    layout="wide"
)

# --- Funções Auxiliares para o Dashboard ---
def calculate_stats(books_df, logs_df):
    stats = {}
    current_year = datetime.now().year

    # Filtrar livros concluídos no ano atual
    books_df_copy = books_df.copy()
    books_df_copy['end_date'] = pd.to_datetime(books_df_copy['end_date'], errors='coerce')
    concluidos_ano = books_df_copy[
        (books_df_copy['status'] == 'concluído') &
        (books_df_copy['end_date'].dt.year == current_year)
    ]
    stats['livros_concluidos_ano'] = len(concluidos_ano)

    # Livros lendo atualmente
    stats['livros_lendo'] = len(books_df[books_df['status'] == 'lendo'])

    # Páginas lidas no ano atual
    logs_df_copy = logs_df.copy()
    if not logs_df_copy.empty:
        logs_df_copy['log_date'] = pd.to_datetime(logs_df_copy['log_date'])
        logs_ano = logs_df_copy[logs_df_copy['log_date'].dt.year == current_year]
        stats['paginas_lidas_ano'] = logs_ano['pages_read'].sum()

        # Média de páginas por dia no ano
        if not logs_ano.empty:
            dias_com_leitura = logs_ano['log_date'].dt.date.nunique()
            stats['media_paginas_dia_ano'] = stats['paginas_lidas_ano'] / dias_com_leitura if dias_com_leitura > 0 else 0
        else:
            stats['media_paginas_dia_ano'] = 0
    else:
        stats['paginas_lidas_ano'] = 0
        stats['media_paginas_dia_ano'] = 0


    # Gêneros mais lidos (considerando concluídos no ano)
    if not concluidos_ano.empty:
        stats['generos_mais_lidos'] = concluidos_ano['genre'].value_counts()
    else:
        stats['generos_mais_lidos'] = pd.Series(dtype='int64')

    return stats

def plot_pages_per_month(logs_df):
    if logs_df.empty:
        return None
    current_year = datetime.now().year
    logs_df['log_date'] = pd.to_datetime(logs_df['log_date'])
    logs_ano = logs_df[logs_df['log_date'].dt.year == current_year].copy() # Filtra ano atual

    if logs_ano.empty:
        return None

    logs_ano['month'] = logs_ano['log_date'].dt.month
    pages_per_month = logs_ano.groupby('month')['pages_read'].sum().reset_index()

    # Garante que todos os meses até o atual estejam presentes
    all_months = pd.DataFrame({'month': range(1, datetime.now().month + 1)})
    pages_per_month = pd.merge(all_months, pages_per_month, on='month', how='left').fillna(0)

    # Mapear número do mês para nome abreviado
    month_map = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                 7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    pages_per_month['month_name'] = pages_per_month['month'].map(month_map)

    fig = px.bar(pages_per_month, x='month_name', y='pages_read',
                 title=f'Páginas Lidas por Mês ({current_year})',
                 labels={'month_name': 'Mês', 'pages_read': 'Páginas Lidas'},
                 text_auto=True)
    fig.update_layout(xaxis={'categoryorder':'array', 'categoryarray':list(month_map.values())[:datetime.now().month]})
    return fig

def plot_genre_distribution(books_df):
    current_year = datetime.now().year
    books_df_copy = books_df.copy()
    books_df_copy['end_date'] = pd.to_datetime(books_df_copy['end_date'], errors='coerce')
    concluidos_ano = books_df_copy[
        (books_df_copy['status'] == 'concluído') &
        (books_df_copy['end_date'].dt.year == current_year)
    ]

    if concluidos_ano.empty or concluidos_ano['genre'].isnull().all():
         st.info(f"Nenhum livro com gênero definido concluído em {current_year} para exibir o gráfico.")
         return None

    genre_counts = concluidos_ano['genre'].value_counts().reset_index()
    genre_counts.columns = ['genre', 'count']

    # Tratar gêneros vazios ou nulos como 'Não especificado'
    genre_counts['genre'] = genre_counts['genre'].fillna('Não especificado').replace('', 'Não especificado')
    genre_counts = genre_counts.groupby('genre')['count'].sum().reset_index() # Agrupa novamente caso haja '' e NaN

    fig = px.pie(genre_counts, names='genre', values='count',
                 title=f'Distribuição por Gênero (Livros Concluídos em {current_year})',
                 hole=0.3) # Gráfico de rosca
    fig.update_traces(textposition='inside', textinfo='percent+label')
    return fig

# --- Layout do Dashboard ---
st.title("📚 Controle de Leitura Ativa do Taz")
st.markdown("---")

# Carregar dados
all_books_df = db.get_all_books()
all_logs_df = db.get_reading_log() # Carrega todos os logs

# Calcular Estatísticas Gerais
stats = calculate_stats(all_books_df, all_logs_df)

# Exibir Métricas Principais
st.header(f"Resumo de Leitura ({datetime.now().year})")
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Livros Concluídos no Ano", stats['livros_concluidos_ano'])
with col2:
    st.metric("Livros Sendo Lidos", stats['livros_lendo'])
with col3:
    st.metric("Total de Páginas Lidas no Ano", f"{stats['paginas_lidas_ano']:,}".replace(",", "."))
with col4:
    st.metric("Média de Páginas/Dia (dias lidos)", f"{stats['media_paginas_dia_ano']:.1f}".replace(".",","))

st.markdown("---")

# Gráficos e Listas
col_graf1, col_graf2 = st.columns(2)

with col_graf1:
    st.header("Progresso Mensal")
    fig_pages_month = plot_pages_per_month(all_logs_df)
    if fig_pages_month:
        st.plotly_chart(fig_pages_month, use_container_width=True)
    else:
        st.info(f"Nenhuma página registrada em {datetime.now().year} ainda.")

with col_graf2:
    st.header("Gêneros Lidos")
    fig_genre = plot_genre_distribution(all_books_df)
    if fig_genre:
        st.plotly_chart(fig_genre, use_container_width=True)
    # else: # Mensagem já é exibida dentro da função plot_genre_distribution

st.markdown("---")

# Livros em Andamento
st.header("Leituras em Andamento")
livros_lendo = all_books_df[all_books_df['status'] == 'lendo'].copy()

if not livros_lendo.empty:
    livros_lendo['progresso_%'] = 0.0 # Inicializa a coluna

    for index, row in livros_lendo.iterrows():
        paginas_lidas = db.get_pages_read_for_book(row['id'])
        total_paginas = row['total_pages']
        if total_paginas > 0:
            progresso = (paginas_lidas / total_paginas) * 100
            livros_lendo.loc[index, 'progresso_%'] = min(progresso, 100) # Garante que não passe de 100%
        else:
            livros_lendo.loc[index, 'progresso_%'] = 0

    # Formata a coluna de progresso para exibição
    livros_lendo['Progresso'] = livros_lendo['progresso_%'].apply(lambda x: f"{x:.1f}%")

    # Seleciona e renomeia colunas para exibição
    livros_lendo_display = livros_lendo[['title', 'author', 'total_pages', 'Progresso']]
    livros_lendo_display.columns = ['Título', 'Autor(a)', 'Páginas Totais', 'Progresso']

    st.dataframe(livros_lendo_display, hide_index=True, use_container_width=True)

    # Adiciona barras de progresso visualmente (opcional)
    for index, row in livros_lendo.iterrows():
        st.progress(row['progresso_%'] / 100, text=f"{row['title']} ({row['Progresso']})")

else:
    st.info("Nenhum livro marcado como 'lendo' no momento.")

# Adicionar uma seção de recomendações simples (Ex: livros do mesmo gênero desejados)
st.markdown("---")
st.header("Sugestões (Livros Desejados)")
livros_desejados = all_books_df[all_books_df['status'] == 'desejado']

if not livros_desejados.empty:
     # Tenta pegar o gênero do último livro concluído
    livros_concluidos = all_books_df[all_books_df['status'] == 'concluído'].sort_values('end_date', ascending=False, na_position='last')
    genero_recente = None
    if not livros_concluidos.empty and not pd.isna(livros_concluidos.iloc[0]['genre']):
        genero_recente = livros_concluidos.iloc[0]['genre']

    if genero_recente:
        sugestoes = livros_desejados[livros_desejados['genre'] == genero_recente]
        if not sugestoes.empty:
            st.write(f"Baseado no seu último livro concluído ({genero_recente}), talvez você goste de:")
            st.dataframe(sugestoes[['title', 'author', 'genre']].rename(columns={'title':'Título', 'author':'Autor(a)', 'genre':'Gênero'}), hide_index=True, use_container_width=True)
        else:
             st.dataframe(livros_desejados[['title', 'author', 'genre']].rename(columns={'title':'Título', 'author':'Autor(a)', 'genre':'Gênero'}).head(), hide_index=True, use_container_width=True) # Mostra os 5 primeiros desejados
    else:
        # Se não houver histórico ou gênero, apenas mostra alguns desejados
        st.dataframe(livros_desejados[['title', 'author', 'genre']].rename(columns={'title':'Título', 'author':'Autor(a)', 'genre':'Gênero'}).head(), hide_index=True, use_container_width=True)

else:
    st.info("Nenhum livro na sua lista de desejos ainda.")


# st.sidebar.success("Navegue pelas seções acima.")

# Para garantir que as tabelas sejam criadas na primeira execução
db.create_tables()