import streamlit as st
import database as db
import pandas as pd
import io

st.set_page_config(page_title="Importar/Exportar Dados", page_icon="⚙️")
st.title("⚙️ Importar e Exportar Dados")

# --- Exportar Dados ---
st.header("Exportar Dados")

export_format = st.selectbox("Selecione o formato para exportar:", ["Excel (.xlsx)", "CSV (.csv)"])
export_data_type = st.selectbox("Selecione os dados para exportar:", ["Livros", "Histórico de Leitura", "Ambos"])

if st.button("Exportar Dados"):
    try:
        if export_format == "Excel (.xlsx)":
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                if export_data_type in ["Livros", "Ambos"]:
                    books_df = db.get_all_books()
                    # Converte colunas de data para string antes de exportar para evitar problemas de timezone
                    for col in ['start_date', 'end_date']:
                        if col in books_df.columns:
                             books_df[col] = books_df[col].astype(str) # Converte date/NaT para string
                    books_df.to_excel(writer, sheet_name='Livros', index=False)

                if export_data_type in ["Histórico de Leitura", "Ambos"]:
                    logs_df = db.get_reading_log()
                    # Converte log_date para string
                    if 'log_date' in logs_df.columns:
                        logs_df['log_date'] = logs_df['log_date'].astype(str)
                    logs_df.to_excel(writer, sheet_name='Log_Leitura', index=False)

            st.download_button(
                label="📥 Baixar Arquivo Excel",
                data=output.getvalue(),
                file_name="controle_leitura_taz_export.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            st.success("Dados prontos para download!")

        elif export_format == "CSV (.csv)":
            if export_data_type == "Livros":
                books_df = db.get_all_books()
                for col in ['start_date', 'end_date']:
                     if col in books_df.columns: books_df[col] = books_df[col].astype(str)
                csv_data = books_df.to_csv(index=False).encode('utf-8')
                file_name = "livros_export.csv"
                mime_type = "text/csv"

            elif export_data_type == "Histórico de Leitura":
                logs_df = db.get_reading_log()
                if 'log_date' in logs_df.columns: logs_df['log_date'] = logs_df['log_date'].astype(str)
                csv_data = logs_df.to_csv(index=False).encode('utf-8')
                file_name = "log_leitura_export.csv"
                mime_type = "text/csv"

            elif export_data_type == "Ambos":
                st.warning("A exportação de ambos para CSV gerará arquivos separados. Exporte um de cada vez.")
                # Não fornece botão de download direto para "Ambos" em CSV para evitar confusão.
                csv_data = None
            else:
                 csv_data = None

            if csv_data:
                 st.download_button(
                    label=f"📥 Baixar Arquivo CSV ({export_data_type})",
                    data=csv_data,
                    file_name=file_name,
                    mime=mime_type
                 )
                 st.success("Dados CSV prontos para download!")

    except Exception as e:
        st.error(f"Erro durante a exportação: {e}")


st.markdown("---")

# --- Importar Dados ---
st.header("Importar Livros de CSV")
st.markdown("""
            Faça upload de um arquivo CSV com as seguintes colunas (a ordem não importa, mas os nomes **DEVEM** ser exatos):
            `title`, `author`, `genre`, `total_pages`, `status`, `start_date` (formato YYYY-MM-DD, opcional), `end_date` (formato YYYY-MM-DD, opcional).

            O status deve ser um dos seguintes: `lendo`, `concluído`, `abandonado`, `desejado`.
            """)

uploaded_file = st.file_uploader("Escolha um arquivo CSV", type="csv")

if uploaded_file is not None:
    try:
        # Tenta ler com diferentes delimitadores comuns
        try:
            import_df = pd.read_csv(uploaded_file, sep=',')
        except Exception:
             try:
                 # Reposiciona o ponteiro do arquivo para o início
                 uploaded_file.seek(0)
                 import_df = pd.read_csv(uploaded_file, sep=';')
             except Exception as e:
                 st.error(f"Não foi possível ler o CSV. Verifique o formato e o delimitador (use ',' ou ';'). Erro: {e}")
                 import_df = None # Garante que não prossiga

        if import_df is not None:
            st.write("Pré-visualização dos dados a importar:")
            st.dataframe(import_df.head())

            # Validação básica das colunas obrigatórias
            required_cols = {'title', 'author', 'total_pages', 'status'}
            if not required_cols.issubset(import_df.columns):
                missing_cols = required_cols - set(import_df.columns)
                st.error(f"Colunas obrigatórias ausentes no CSV: {', '.join(missing_cols)}")
            else:
                # Validação dos status
                valid_status = ['lendo', 'concluído', 'abandonado', 'desejado']
                invalid_status_rows = import_df[~import_df['status'].isin(valid_status)]
                if not invalid_status_rows.empty:
                    st.error(f"Status inválidos encontrados nas seguintes linhas (ver pré-visualização): {invalid_status_rows.index.tolist()}. Status válidos são: {', '.join(valid_status)}")

                elif st.button("Confirmar Importação"):
                    imported_count = 0
                    skipped_count = 0
                    error_count = 0
                    existing_books = db.get_all_books() # Para verificar duplicatas (simples, por título e autor)

                    with st.spinner("Importando livros..."):
                        for index, row in import_df.iterrows():
                            # Checagem de duplicata simples
                            is_duplicate = any(
                                (existing_books['title'].str.lower() == str(row['title']).lower()) &
                                (existing_books['author'].str.lower() == str(row['author']).lower())
                            ) if not existing_books.empty else False

                            if is_duplicate:
                                skipped_count += 1
                                continue # Pula duplicatas

                            try:
                                # Tratar datas opcionais - pd.to_datetime pode converter strings vazias ou NaNs para NaT
                                start_date = pd.to_datetime(row.get('start_date'), errors='coerce').date() if 'start_date' in row and pd.notna(row['start_date']) else None
                                end_date = pd.to_datetime(row.get('end_date'), errors='coerce').date() if 'end_date' in row and pd.notna(row['end_date']) else None

                                # Garantir que total_pages seja int
                                total_pages = int(row['total_pages']) if pd.notna(row['total_pages']) else 0
                                if total_pages <= 0:
                                     raise ValueError("Número total de páginas deve ser maior que 0.")

                                # Adicionar ao banco
                                db.add_book(
                                    str(row['title']),
                                    str(row['author']),
                                    str(row.get('genre', '')), # Usa get para coluna opcional
                                    total_pages,
                                    str(row['status']),
                                    start_date,
                                    end_date
                                )
                                imported_count += 1
                            except Exception as e:
                                st.warning(f"Erro ao importar linha {index + 2} (Livro: {row.get('title', 'N/A')}): {e}. Pulando esta linha.")
                                error_count += 1

                    st.success(f"Importação concluída! {imported_count} livros importados.")
                    if skipped_count > 0:
                        st.info(f"{skipped_count} livros pulados (já existentes com mesmo título e autor).")
                    if error_count > 0:
                        st.error(f"{error_count} linhas continham erros e não foram importadas.")
                    # Limpar o uploader após importação bem-sucedida
                    # uploaded_file = None # Não funciona diretamente assim no Streamlit
                    st.info("Atualize a página 'Gerenciar Livros' para ver os novos itens.") # Sugestão ao usuário


    except Exception as e:
        st.error(f"Erro ao processar o arquivo CSV: {e}")