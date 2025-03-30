import streamlit as st
import database as db
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Metas e Estatísticas", page_icon="🎯")
st.title("🎯 Metas de Leitura e Estatísticas Detalhadas")

# --- Definição de Metas (Simples, usando session_state para persistir na sessão) ---
st.header("Definir Metas")

# Inicializar metas no session_state se não existirem
if 'goal_books_year' not in st.session_state:
    st.session_state.goal_books_year = 0 # Ou um valor padrão, ex: 12
if 'goal_pages_day' not in st.session_state:
    st.session_state.goal_pages_day = 0 # Ou um valor padrão, ex: 20

col_meta1, col_meta2 = st.columns(2)
with col_meta1:
    goal_books_year_input = st.number_input(
        f"Meta de Livros para {datetime.now().year}",
        min_value=0,
        step=1,
        value=st.session_state.goal_books_year,
        key="goal_books_year_input_key" # Key para evitar resetar com rerun
    )
    # Atualiza o session state quando o valor muda
    if goal_books_year_input != st.session_state.goal_books_year:
        st.session_state.goal_books_year = goal_books_year_input
        st.rerun() # Rerun para atualizar a exibição do progresso

with col_meta2:
    goal_pages_day_input = st.number_input(
        "Meta de Páginas por Dia (Média)",
        min_value=0,
        step=5,
        value=st.session_state.goal_pages_day,
        key="goal_pages_day_input_key"
    )
    if goal_pages_day_input != st.session_state.goal_pages_day:
        st.session_state.goal_pages_day = goal_pages_day_input
        st.rerun()

# --- Acompanhamento de Metas ---
st.header("Acompanhamento das Metas")

# Carregar dados necessários
all_books_df = db.get_all_books()
all_logs_df = db.get_reading_log()
current_year = datetime.now().year

# Calcular progresso
books_df_copy = all_books_df.copy()
books_df_copy['end_date'] = pd.to_datetime(books_df_copy['end_date'], errors='coerce')
livros_concluidos_ano = len(books_df_copy[
    (books_df_copy['status'] == 'concluído') &
    (books_df_copy['end_date'].dt.year == current_year)
])

paginas_lidas_ano = 0
media_paginas_dia = 0
if not all_logs_df.empty:
    logs_df_copy = all_logs_df.copy()
    logs_df_copy['log_date'] = pd.to_datetime(logs_df_copy['log_date'])
    logs_ano = logs_df_copy[logs_df_copy['log_date'].dt.year == current_year]
    if not logs_ano.empty:
        paginas_lidas_ano = logs_ano['pages_read'].sum()
        dias_com_leitura = logs_ano['log_date'].dt.date.nunique()
        media_paginas_dia = paginas_lidas_ano / dias_com_leitura if dias_com_leitura > 0 else 0

col_prog1, col_prog2 = st.columns(2)

with col_prog1:
    st.subheader(f"Progresso Livros ({current_year})")
    if st.session_state.goal_books_year > 0:
        progresso_livros = min(livros_concluidos_ano / st.session_state.goal_books_year, 1.0) # Cap em 100%
        st.progress(progresso_livros, text=f"{livros_concluidos_ano} de {st.session_state.goal_books_year} livros concluídos ({progresso_livros:.1%})")
    else:
        st.info(f"Defina uma meta anual de livros acima. Você concluiu {livros_concluidos_ano} livro(s) este ano.")

with col_prog2:
    st.subheader("Progresso Páginas/Dia")
    if st.session_state.goal_pages_day > 0:
        # Compara a média atual com a meta
        st.metric("Média Atual (dias lidos)", f"{media_paginas_dia:.1f}".replace(".",","))
        if media_paginas_dia >= st.session_state.goal_pages_day:
            st.success(f"Meta de {st.session_state.goal_pages_day} páginas/dia atingida/superada!")
        else:
            st.warning(f"Abaixo da meta de {st.session_state.goal_pages_day} páginas/dia.")
            progresso_paginas = media_paginas_dia / st.session_state.goal_pages_day if st.session_state.goal_pages_day > 0 else 0
            st.progress(min(progresso_paginas, 1.0)) # Mostra barra de progresso até a meta
    else:
        st.info(f"Defina uma meta de páginas por dia acima. Sua média atual é {media_paginas_dia:.1f} pág/dia.")


st.markdown("---")

# --- Estatísticas Detalhadas ---
st.header("Estatísticas Detalhadas")

# Gráfico: Páginas lidas ao longo do tempo (acumulado)
if not all_logs_df.empty:
    logs_df_copy = all_logs_df.sort_values('log_date').copy()
    logs_df_copy['log_date'] = pd.to_datetime(logs_df_copy['log_date'])
    logs_df_copy['cumulative_pages'] = logs_df_copy['pages_read'].cumsum()
    fig_acumulado = px.line(logs_df_copy, x='log_date', y='cumulative_pages',
                           title="Total de Páginas Lidas (Acumulado)",
                           labels={'log_date': 'Data', 'cumulative_pages': 'Total de Páginas Acumuladas'})
    st.plotly_chart(fig_acumulado, use_container_width=True)
else:
    st.info("Nenhum registro de leitura para exibir gráfico acumulado.")


# Gráfico: Leitura por Dia da Semana
if not all_logs_df.empty:
    logs_df_copy = all_logs_df.copy()
    logs_df_copy['log_date'] = pd.to_datetime(logs_df_copy['log_date'])
    logs_df_copy['weekday'] = logs_df_copy['log_date'].dt.day_name(locale='pt_BR.utf8') # Necessário locale pt_BR instalado no sistema ou usar dt.weekday e mapear
    pages_per_weekday = logs_df_copy.groupby('weekday')['pages_read'].sum().reset_index()

    # Ordenar os dias da semana corretamente
    dias_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
    try:
        pages_per_weekday['weekday'] = pd.Categorical(pages_per_weekday['weekday'], categories=dias_ordem, ordered=True)
        pages_per_weekday = pages_per_weekday.sort_values('weekday')

        fig_weekday = px.bar(pages_per_weekday, x='weekday', y='pages_read',
                            title="Total de Páginas Lidas por Dia da Semana",
                            labels={'weekday': 'Dia da Semana', 'pages_read': 'Total de Páginas'})
        st.plotly_chart(fig_weekday, use_container_width=True)
    except Exception as e:
        st.warning(f"Não foi possível gerar gráfico por dia da semana (verifique o locale pt_BR): {e}")
        # Fallback para ordem padrão se locale falhar
        pages_per_weekday = logs_df_copy.groupby(logs_df_copy['log_date'].dt.weekday)['pages_read'].sum().reset_index()
        weekday_map = {0: 'Seg', 1: 'Ter', 2: 'Qua', 3: 'Qui', 4: 'Sex', 5: 'Sáb', 6: 'Dom'}
        pages_per_weekday['weekday_name'] = pages_per_weekday['log_date'].map(weekday_map)
        fig_weekday_fallback = px.bar(pages_per_weekday, x='weekday_name', y='pages_read', title="Páginas por Dia da Semana (Fallback)")
        st.plotly_chart(fig_weekday_fallback, use_container_width=True)


# Outras estatísticas: Livro mais rápido, mais longo, etc. (exemplo)
livros_concluidos_df = all_books_df[all_books_df['status'] == 'concluído'].copy()
if not livros_concluidos_df.empty and 'start_date' in livros_concluidos_df.columns and 'end_date' in livros_concluidos_df.columns:
    livros_concluidos_df['start_date'] = pd.to_datetime(livros_concluidos_df['start_date'], errors='coerce')
    livros_concluidos_df['end_date'] = pd.to_datetime(livros_concluidos_df['end_date'], errors='coerce')
    # Remover linhas onde start ou end date são NaT
    livros_concluidos_df.dropna(subset=['start_date', 'end_date'], inplace=True)

    if not livros_concluidos_df.empty:
        livros_concluidos_df['reading_days'] = (livros_concluidos_df['end_date'] - livros_concluidos_df['start_date']).dt.days + 1 # Adiciona 1 para incluir o dia de início
        # Evitar divisão por zero ou dias negativos
        livros_concluidos_df = livros_concluidos_df[livros_concluidos_df['reading_days'] > 0]

        if not livros_concluidos_df.empty:
            livros_concluidos_df['pages_per_day'] = livros_concluidos_df['total_pages'] / livros_concluidos_df['reading_days']

            st.subheader("Desempenho por Livro (Concluídos)")
            st.dataframe(
                livros_concluidos_df[['title', 'total_pages', 'reading_days', 'pages_per_day']].rename(columns={
                    'title': 'Título', 'total_pages': 'Páginas', 'reading_days': 'Dias de Leitura', 'pages_per_day': 'Média Pág/Dia'
                }).round({'pages_per_day': 1}), # Arredonda média
                hide_index=True, use_container_width=True
            )

            mais_rapido = livros_concluidos_df.loc[livros_concluidos_df['pages_per_day'].idxmax()] if not livros_concluidos_df.empty else None
            mais_longo_tempo = livros_concluidos_df.loc[livros_concluidos_df['reading_days'].idxmax()] if not livros_concluidos_df.empty else None

            col_stat1, col_stat2 = st.columns(2)
            if mais_rapido is not None:
                 with col_stat1:
                     st.metric("Leitura Mais Rápida (Pág/Dia)", f"{mais_rapido['pages_per_day']:.1f}", delta=mais_rapido['title'])
            if mais_longo_tempo is not None:
                 with col_stat2:
                     st.metric("Leitura Mais Longa (Dias)", f"{mais_longo_tempo['reading_days']}", delta=mais_longo_tempo['title'])