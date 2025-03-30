import streamlit as st
import database as db
import pandas as pd
from datetime import datetime, date

st.set_page_config(page_title="Gerenciar Livros", page_icon="📚")
st.title("📚 Gerenciar Livros")

# --- Formulário para Adicionar/Editar Livro ---
st.header("Adicionar Novo Livro")

# Usar 'key' diferentes para os widgets do formulário de adição e edição
with st.form("add_book_form", clear_on_submit=True):
    add_title = st.text_input("Título*", key="add_title")
    add_author = st.text_input("Autor(a)*", key="add_author")
    add_genre = st.text_input("Gênero", key="add_genre")
    add_total_pages = st.number_input("Nº Total de Páginas*", min_value=1, step=1, key="add_total_pages")
    add_status = st.selectbox(
        "Status*",
        options=['desejado', 'lendo', 'concluído', 'abandonado'],
        key="add_status"
    )
    # Datas condicionais baseadas no status
    add_start_date = None
    add_end_date = None
    if add_status in ['lendo', 'concluído', 'abandonado']:
         add_start_date = st.date_input("Data de Início", value=None, key="add_start_date") # Permite None
    if add_status in ['concluído', 'abandonado']:
         add_end_date = st.date_input("Data de Conclusão/Abandono", value=None, key="add_end_date") # Permite None

    submitted_add = st.form_submit_button("Adicionar Livro")
    if submitted_add:
        if not add_title or not add_author or not add_total_pages or not add_status:
            st.error("Os campos marcados com * são obrigatórios.")
        else:
            try:
                db.add_book(add_title, add_author, add_genre, add_total_pages, add_status, add_start_date, add_end_date)
                st.success(f"Livro '{add_title}' adicionado com sucesso!")
                # Não precisa de rerun aqui, o Streamlit atualiza na próxima interação ou recarregamento da lista
            except Exception as e:
                st.error(f"Erro ao adicionar livro: {e}")


st.markdown("---")

# --- Lista de Livros Cadastrados ---
st.header("Livros Cadastrados")

books_df = db.get_all_books()

if books_df.empty:
    st.info("Nenhum livro cadastrado ainda.")
else:
    # Selecionar colunas e renomear para exibição amigável
    display_df = books_df[['id', 'title', 'author', 'genre', 'total_pages', 'status', 'start_date', 'end_date']].copy()
    display_df.columns = ['ID', 'Título', 'Autor(a)', 'Gênero', 'Páginas', 'Status', 'Início', 'Fim']
    # Formatar datas para exibição (se não forem NaT)
    for col in ['Início', 'Fim']:
         if col in display_df.columns:
              display_df[col] = pd.to_datetime(display_df[col]).dt.strftime('%d/%m/%Y').replace('NaT', '')

    st.dataframe(display_df, hide_index=True, use_container_width=True)

    st.markdown("---")

    # --- Opções de Edição e Deleção ---
    st.header("Editar ou Deletar Livro")
    book_list = books_df['title'].tolist()
    book_id_map = dict(zip(books_df['title'], books_df['id'])) # Mapa de título para ID

    selected_title_for_action = st.selectbox("Selecione um livro para editar ou deletar:", options=[""] + book_list, key="select_action")

    if selected_title_for_action:
        selected_id = book_id_map[selected_title_for_action]
        selected_book_data = books_df[books_df['id'] == selected_id].iloc[0]

        col_edit, col_delete = st.columns([3, 1]) # Coluna de edição maior

        with col_edit:
             st.subheader(f"Editando: {selected_book_data['title']}")
             # Usar um form para edição também
             with st.form(f"edit_book_form_{selected_id}", clear_on_submit=False): # Não limpar ao submeter para manter os dados pré-preenchidos
                 edit_title = st.text_input("Título*", value=selected_book_data['title'], key=f"edit_title_{selected_id}")
                 edit_author = st.text_input("Autor(a)*", value=selected_book_data['author'], key=f"edit_author_{selected_id}")
                 edit_genre = st.text_input("Gênero", value=selected_book_data['genre'] or "", key=f"edit_genre_{selected_id}")
                 edit_total_pages = st.number_input("Nº Total de Páginas*", value=int(selected_book_data['total_pages']), min_value=1, step=1, key=f"edit_pages_{selected_id}")

                 # Encontrar o índice do status atual para o selectbox
                 status_options = ['desejado', 'lendo', 'concluído', 'abandonado']
                 current_status_index = status_options.index(selected_book_data['status']) if selected_book_data['status'] in status_options else 0

                 edit_status = st.selectbox(
                     "Status*",
                     options=status_options,
                     index=current_status_index,
                     key=f"edit_status_{selected_id}"
                 )

                 # Lógica para datas de início/fim baseado no status SELECIONADO
                 edit_start_date_val = selected_book_data['start_date'] if pd.notna(selected_book_data['start_date']) else None
                 edit_end_date_val = selected_book_data['end_date'] if pd.notna(selected_book_data['end_date']) else None

                 edit_start_date = None
                 if edit_status in ['lendo', 'concluído', 'abandonado']:
                     edit_start_date = st.date_input("Data de Início", value=edit_start_date_val, key=f"edit_start_{selected_id}")

                 edit_end_date = None
                 if edit_status in ['concluído', 'abandonado']:
                     edit_end_date = st.date_input("Data de Conclusão/Abandono", value=edit_end_date_val, key=f"edit_end_{selected_id}")

                 submitted_edit = st.form_submit_button("Salvar Alterações")
                 if submitted_edit:
                     if not edit_title or not edit_author or not edit_total_pages:
                         st.error("Título, Autor(a) e Nº de Páginas são obrigatórios.")
                     else:
                         try:
                             # Certificar que datas sejam None se não aplicável pelo status
                             final_start_date = edit_start_date if edit_status in ['lendo', 'concluído', 'abandonado'] else None
                             final_end_date = edit_end_date if edit_status in ['concluído', 'abandonado'] else None

                             db.update_book(selected_id, edit_title, edit_author, edit_genre, edit_total_pages, edit_status, final_start_date, final_end_date)
                             st.success(f"Livro '{edit_title}' atualizado!")
                             st.rerun() # Força o recarregamento da página para refletir a mudança
                         except Exception as e:
                             st.error(f"Erro ao atualizar livro: {e}")


        with col_delete:
            st.subheader("Deletar Livro")
            st.warning(f"Tem certeza que deseja deletar '{selected_book_data['title']}'? Esta ação não pode ser desfeita e apagará também os registros de leitura associados.", icon="⚠️")
            if st.button("Deletar Livro Permanentemente", key=f"delete_{selected_id}", type="primary"):
                try:
                    db.delete_book(selected_id)
                    st.success(f"Livro '{selected_book_data['title']}' deletado com sucesso.")
                    # Limpa a seleção para evitar erro após deleção
                    st.session_state['select_action'] = ""
                    st.rerun() # Força o recarregamento
                except Exception as e:
                    st.error(f"Erro ao deletar livro: {e}")