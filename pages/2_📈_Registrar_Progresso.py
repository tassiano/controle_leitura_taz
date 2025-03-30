import streamlit as st
import database as db
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Registrar Progresso", page_icon="📈")
st.title("📈 Registrar Progresso de Leitura")

# Selecionar Livro em Andamento
livros_lendo_df = db.get_books_by_status('lendo')

if livros_lendo_df.empty:
    st.warning("Nenhum livro marcado como 'lendo'. Adicione ou atualize o status de um livro em 'Gerenciar Livros'.")
else:
    livros_lendo_dict = dict(zip(livros_lendo_df['id'], livros_lendo_df['title']))
    selected_book_id = st.selectbox(
        "Selecione o livro que você leu:",
        options=list(livros_lendo_dict.keys()),
        format_func=lambda x: livros_lendo_dict[x] # Mostra o título no selectbox
    )

    if selected_book_id:
        book_details = db.get_book_by_id(selected_book_id)
        total_pages = book_details['total_pages']
        pages_read_so_far = db.get_pages_read_for_book(selected_book_id)
        pages_remaining = total_pages - pages_read_so_far

        st.info(f"**{livros_lendo_dict[selected_book_id]}**: {pages_read_so_far} de {total_pages} páginas lidas ({pages_remaining} restantes).")

        with st.form("log_progress_form", clear_on_submit=True):
            log_date = st.date_input("Data da Leitura*", value=datetime.now().date())
            pages_read_today = st.number_input("Páginas Lidas Hoje*", min_value=1, step=1, max_value=pages_remaining if pages_remaining > 0 else None) # Limita ao restante se houver
            notes = st.text_area("Anotações (Opcional)")

            submitted_log = st.form_submit_button("Registrar Leitura")

            if submitted_log:
                if not pages_read_today or pages_read_today <= 0:
                    st.error("Por favor, insira um número válido de páginas lidas.")
                else:
                    try:
                        db.add_log_entry(selected_book_id, log_date, pages_read_today, notes)
                        st.success(f"{pages_read_today} páginas registradas para '{livros_lendo_dict[selected_book_id]}' em {log_date.strftime('%d/%m/%Y')}.")
                        # Opcional: Verificar se o livro foi concluído
                        if pages_read_so_far + pages_read_today >= total_pages:
                            st.balloons()
                            st.info(f"Parabéns! Você terminou '{livros_lendo_dict[selected_book_id]}'! Não se esqueça de atualizar o status para 'concluído' em 'Gerenciar Livros'.")
                    except Exception as e:
                        st.error(f"Erro ao registrar leitura: {e}")

st.markdown("---")

# --- Histórico de Leitura ---
st.header("Histórico Recente de Leitura")

# Filtros (opcional)
show_all = st.checkbox("Mostrar todo o histórico?")
num_recent = st.slider("Número de registros recentes a exibir:", 5, 50, 10, disabled=show_all)

log_df = db.get_reading_log() # Pega todos os logs

if log_df.empty:
    st.info("Nenhum registro de leitura encontrado.")
else:
    log_df_display = log_df.copy()
    log_df_display['log_date'] = log_df_display['log_date'].dt.strftime('%d/%m/%Y') # Formata data
    log_df_display = log_df_display[['log_date', 'book_title', 'pages_read', 'notes']] # Seleciona e reordena
    log_df_display.columns = ['Data', 'Livro', 'Páginas Lidas', 'Anotações']

    if show_all:
        st.dataframe(log_df_display, hide_index=True, use_container_width=True)
    else:
        st.dataframe(log_df_display.head(num_recent), hide_index=True, use_container_width=True)