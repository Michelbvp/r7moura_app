import streamlit as st
from supabase import create_client, Client
import google.generativeai as genai
import pandas as pd
import PyPDF2
import docx
import io
import json
import secrets
import string
import urllib.parse
import re
from datetime import datetime

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E CONEXÕES
# ==========================================
st.set_page_config(
    page_title="Gestão de Treinamento Seguro - LGPD",
    page_icon="🛡️",
    layout="wide"
)

@st.cache_resource
def init_connection() -> Client:
    """Conexão padrão submetida às políticas de RLS (Row Level Security)."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Erro crítico ao conectar ao Supabase: {e}")
        st.stop()

def init_admin_connection() -> Client:
    """Conexão privilegiada (Service Role) restrita a operações de backend, IAM e Auditoria."""
    try:
        url = st.secrets["SUPABASE_URL"]
        service_key = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
        return create_client(url, service_key)
    except Exception as e:
        st.error(f"Erro ao inicializar conexão administrativa: {e}")
        st.stop()

supabase = init_connection()

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.warning(f"Chave da API Gemini não configurada corretamente: {e}")

# ==========================================
# 2. FUNÇÕES UTILITÁRIAS E INTEGRAÇÃO IA
# ==========================================
def gerar_senha_temporaria(tamanho: int = 10) -> str:
    """Gera senha criptograficamente segura (biblioteca secrets) para primeiro acesso."""
    alfabeto = string.ascii_letters + string.digits + "!@#$%&*"
    while True:
        senha = ''.join(secrets.choice(alfabeto) for _ in range(tamanho))
        if (any(c.islower() for c in senha)
                and any(c.isupper() for c in senha)
                and any(c.isdigit() for c in senha)):
            return senha

def extrair_texto_arquivo(bytes_arquivo: bytes, nome_arquivo: str) -> str:
    """Extrai texto em memória (RAM) sem salvar arquivos físicos em disco (LGPD)."""
    texto = ""
    try:
        if nome_arquivo.lower().endswith(".pdf"):
            leitor = PyPDF2.PdfReader(io.BytesIO(bytes_arquivo))
            for pagina in leitor.pages:
                texto += (pagina.extract_text() or "") + "\n"
        elif nome_arquivo.lower().endswith(".docx"):
            doc = docx.Document(io.BytesIO(bytes_arquivo))
            for p in doc.paragraphs:
                texto += p.text + "\n"
    except Exception as e:
        st.error(f"Erro ao ler arquivo: {e}")
    return texto.strip()

def limpar_json_ia(texto_resposta: str):
    """Remove blocos markdown de resposta da IA e converte em objeto JSON."""
    texto_limpo = re.sub(r"```json\s*|\s*```", "", texto_resposta).strip()
    return json.loads(texto_limpo)

def analisar_dados_gemini(texto_anamnese: str) -> dict:
    """Extrai dados cadastrais e resumo clínico estruturado a partir da anamnese."""
    try:
        modelo = genai.GenerativeModel("gemini-3.5-flash-lite")
        prompt = f"""
        Você é um assistente de triagem clínica e esportiva.
        Analise o texto da anamnese abaixo e extraia os dados estritamente no seguinte formato JSON:
        {{
            "nome": "Nome completo do aluno",
            "email": "email@dominio.com",
            "telefone": "Apenas números com DDD",
            "motivo_contato": "Resumo objetivo do histórico clínico, lesões, dores e objetivos do aluno"
        }}
        Se algum campo não for encontrado, retorne string vazia "". Retorne APENAS o JSON válido.
        
        Texto da Anamnese:
        {texto_anamnese}
        """
        resposta = modelo.generate_content(prompt)
        return limpar_json_ia(resposta.text)
    except Exception as e:
        st.error(f"Falha ao processar anamnese com IA: {e}")
        return {}

def propor_treino_gemini(contexto_clinico: str, diretrizes: str) -> list:
    """Gera proposta de treino estruturada em lista de dicionários considerando histórico clínico."""
    try:
        modelo = genai.GenerativeModel("gemini-3.5-flash-lite")
        prompt = f"""
        Atue como um treinador especialista em biomecânica e reabilitação.
        Com base no histórico clínico evolutivo do aluno e nas diretrizes do professor, elabore uma rotina de exercícios segura.
        
        Histórico Clínico do Aluno:
        {contexto_clinico}
        
        Diretrizes do Professor:
        {diretrizes}
        
        Retorne APENAS um array JSON válido contendo a lista de exercícios no seguinte formato exato:
        [
            {{
                "Exercicio": "Nome do exercício",
                "Series": "3",
                "Repeticoes": "12",
                "Carga_Sugerida": "Moderada / Peso corporal",
                "Descanso": "60s",
                "Observacoes_Seguranca": "Cuidado biomecânico específico"
            }}
        ]
        """
        resposta = modelo.generate_content(prompt)
        return limpar_json_ia(resposta.text)
    except Exception as e:
        st.error(f"Falha ao gerar treino com IA: {e}")
        return []

def gerar_alerta_ia_monotonia(indice_monotonia: float, dores: str) -> str:
    """Gera recomendação técnica rápida para índices elevados de monotonia e dor."""
    try:
        modelo = genai.GenerativeModel("gemini-3.5-flash-lite")
        prompt = (
            f"O aluno apresentou índice de monotonia de treinamento de {indice_monotonia} (Alto Risco > 2.0) "
            f"e relatou as seguintes dores na semana: '{dores}'. "
            f"Em no máximo 2 frases diretas, sugira uma ação prática de ajuste de carga para o professor."
        )
        resposta = modelo.generate_content(prompt)
        return resposta.text.strip()
    except Exception:
        return "Recomenda-se redução imediata de volume/intensidade (Deload) e reavaliação articular."

def renderizar_botao_whatsapp(nome_aluno: str, telefone: str):
    """Renderiza botão de notificação rápida via WhatsApp sem expor dados sensíveis na URL."""
    if not telefone:
        st.caption("ℹ️ Aluno sem telefone cadastrado para envio via WhatsApp.")
        return
    num_limpo = re.sub(r"\D", "", str(telefone))
    if not num_limpo.startswith("55") and len(num_limpo) in [10, 11]:
        num_limpo = "55" + num_limpo
    mensagem = (
        f"Olá, {nome_aluno}! Seu novo planejamento de treino já está disponível no sistema. "
        f"Acesse sua conta para conferir e registrar seus feedbacks!"
    )
    url_zap = f"https://wa.me/{num_limpo}?text={urllib.parse.quote(mensagem)}"
    st.link_button("📲 Notificar Aluno via WhatsApp", url_zap)

# ==========================================
# 3. GESTÃO DE SESSÃO E AUTENTICAÇÃO
# ==========================================
def init_session_state():
    chaves = ["autenticado", "usuario_id", "perfil", "nome_usuario", "precisa_trocar_senha"]
    for k in chaves:
        if k not in st.session_state:
            st.session_state[k] = False if k in ["autenticado", "precisa_trocar_senha"] else None

def realizar_login(email: str, password: str) -> bool:
    try:
        resposta_auth = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password})
        if resposta_auth.user:
            resposta_perfil = supabase.table("usuarios").select(
                "id, nome, perfil, precisa_trocar_senha"
            ).eq("auth_id", resposta_auth.user.id).execute()
            
            if resposta_perfil.data:
                dados = resposta_perfil.data[0]
                st.session_state.autenticado = True
                st.session_state.usuario_id = dados["id"]
                st.session_state.perfil = dados["perfil"]
                st.session_state.nome_usuario = dados["nome"]
                st.session_state.precisa_trocar_senha = bool(dados.get("precisa_trocar_senha", False))
                return True
            else:
                st.error("Usuário autenticado, mas registro não encontrado na tabela de perfis.")
                return False
    except Exception:
        st.error("Falha no login. Verifique suas credenciais.")
        return False

def realizar_logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

def tela_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.title("🛡️ Acesso ao Sistema")
        st.caption("Ambiente seguro protegido por RBAC e em conformidade com a LGPD.")
        with st.form("form_login"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                if email and senha:
                    if realizar_login(email, senha):
                        st.rerun()
                else:
                    st.warning("Informe seu e-mail e senha.")

# ==========================================
# 4. SEGURANÇA DE SENHAS (1º ACESSO E SIDEBAR)
# ==========================================
def tela_troca_senha_obrigatoria():
    """Gatekeeper: Bloqueia o acesso aos painéis enquanto o usuário estiver com senha provisória."""
    st.title("🔒 Troca Obrigatória de Senha")
    st.warning(
        "Por questões de segurança da informação e conformidade (LGPD), você está utilizando uma senha provisória "
        "e precisa definir uma senha pessoal definitiva antes de acessar o sistema."
    )
    
    with st.form("form_primeiro_acesso", clear_on_submit=True):
        senha_provisoria = st.text_input("Senha Provisória (Atual)", type="password")
        nova_senha = st.text_input(
            "Nova Senha Definitiva", 
            type="password", 
            help="Mínimo de 8 caracteres. Não pode ser igual à senha provisória."
        )
        confirma_senha = st.text_input("Confirmar Nova Senha", type="password")
        
        if st.form_submit_button("Definir Senha e Acessar Sistema", type="primary", use_container_width=True):
            if not senha_provisoria or not nova_senha or not confirma_senha:
                st.warning("Preencha todos os campos.")
            elif nova_senha != confirma_senha:
                st.error("A nova senha e a confirmação não coincidem.")
            elif len(nova_senha) < 8:
                st.warning("A nova senha deve ter no mínimo 8 caracteres.")
            elif nova_senha == senha_provisoria:
                st.error("A nova senha não pode ser igual à senha provisória.")
            else:
                try:
                    admin_supabase = init_admin_connection()
                    resp_user = admin_supabase.table("usuarios").select(
                        "email, auth_id"
                    ).eq("id", st.session_state.usuario_id).execute()
                    
                    if not resp_user.data:
                        st.error("Erro ao localizar registro do usuário.")
                        return
                        
                    email_u = resp_user.data[0]["email"]
                    auth_id_u = resp_user.data[0]["auth_id"]
                    
                    # 1. Valida se a senha provisória digitada está correta
                    try:
                        supabase.auth.sign_in_with_password({"email": email_u, "password": senha_provisoria})
                    except Exception:
                        st.error("❌ Senha provisória incorreta.")
                        return
                        
                    # 2. Atualiza a senha no Supabase Auth
                    admin_supabase.auth.admin.update_user_by_id(auth_id_u, {"password": nova_senha})
                    
                    # 3. Desativa a trava na tabela pública
                    admin_supabase.table("usuarios").update({
                        "precisa_trocar_senha": False
                    }).eq("id", st.session_state.usuario_id).execute()
                    
                    # 4. Registra na Trilha de Auditoria
                    admin_supabase.table("auditoria_lgpd").insert({
                        "usuario_id": st.session_state.usuario_id,
                        "acao": "Troca Obrigatória de Senha (1º Acesso)",
                        "dados_contexto": f"Titular ({st.session_state.perfil.upper()}) substituiu a senha provisória"
                    }).execute()
                    
                    st.session_state.precisa_trocar_senha = False
                    st.success("✅ Senha definitiva configurada! Carregando seu painel...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao processar troca de senha: {e}")

def secao_alterar_propria_senha():
    """Componente de autoatendimento na Sidebar para troca espontânea de senha."""
    with st.sidebar.expander("🔑 Alterar Minha Senha"):
        with st.form("form_troca_propria_senha", clear_on_submit=True):
            senha_atual = st.text_input("Senha Atual", type="password")
            nova_senha = st.text_input("Nova Senha", type="password", help="Mínimo de 8 caracteres.")
            confirma_senha = st.text_input("Confirmar Nova Senha", type="password")
            
            if st.form_submit_button("Atualizar Senha", use_container_width=True):
                if not senha_atual or not nova_senha or not confirma_senha:
                    st.warning("Preencha todos os campos.")
                elif nova_senha != confirma_senha:
                    st.error("A nova senha e a confirmação não coincidem.")
                elif len(nova_senha) < 8:
                    st.warning("A nova senha deve ter no mínimo 8 caracteres.")
                elif nova_senha == senha_atual:
                    st.warning("A nova senha deve ser diferente da senha atual.")
                else:
                    try:
                        admin_supabase = init_admin_connection()
                        resp_user = admin_supabase.table("usuarios").select(
                            "email, auth_id"
                        ).eq("id", st.session_state.usuario_id).execute()
                        
                        if not resp_user.data:
                            st.error("Perfil não localizado para validação.")
                            return
                            
                        email_usuario = resp_user.data[0]["email"]
                        auth_id_usuario = resp_user.data[0]["auth_id"]
                        
                        # Reautenticação obrigatória contra sequestro de sessão
                        try:
                            supabase.auth.sign_in_with_password({
                                "email": email_usuario, 
                                "password": senha_atual
                            })
                        except Exception:
                            st.error("❌ Senha atual incorreta. Alteração negada.")
                            return
                            
                        admin_supabase.auth.admin.update_user_by_id(
                            auth_id_usuario, 
                            {"password": nova_senha}
                        )
                        
                        admin_supabase.table("auditoria_lgpd").insert({
                            "usuario_id": st.session_state.usuario_id,
                            "acao": "Autoalteração de Senha",
                            "dados_contexto": f"Titular ({st.session_state.perfil.upper()}) redefiniu a própria senha"
                        }).execute()
                        
                        st.success("✅ Senha atualizada com sucesso!")
                    except Exception as e:
                        st.error(f"Erro ao atualizar senha: {e}")

# ==========================================
# 5. PAINEL DO ADMINISTRADOR
# ==========================================
def painel_admin():
    st.title("Painel do Administrador")
    st.markdown("Gestão centralizada de acessos, credenciais e conformidade (LGPD).")
    
    if st.session_state.perfil != "admin":
        st.error("Acesso Negado.")
        st.stop()

    aba_lista, aba_novo, aba_auditoria = st.tabs([
        "👥 Usuários", 
        "➕ Novo Usuário", 
        "🛡️ Auditoria"
    ])
    
    admin_supabase = init_admin_connection()
    
    try:
        resp_usuarios = admin_supabase.table("usuarios").select(
            "id, auth_id, nome, email, telefone, perfil, precisa_trocar_senha, criado_em"
        ).execute()
        dados_usuarios = resp_usuarios.data if resp_usuarios.data else []
    except Exception as e:
        st.error(f"Erro ao carregar usuários: {e}")
        dados_usuarios = []

    # -----------------------------------------------------
    # ABA 1: Listagem, Edição, Senha e Exclusão de Usuários
    # -----------------------------------------------------
    with aba_lista:
        st.subheader("Usuários Cadastrados")
        if not dados_usuarios:
            st.info("Nenhum usuário encontrado.")
        else:
            df_usuarios = pd.DataFrame(dados_usuarios).drop(columns=["id", "auth_id"], errors="ignore")
            st.dataframe(
                df_usuarios, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "nome": "Nome",
                    "email": "E-mail",
                    "telefone": "Telefone",
                    "perfil": "Perfil",
                    "precisa_trocar_senha": "Senha Provisória Ativa?",
                    "criado_em": st.column_config.DatetimeColumn("Criado em", format="DD/MM/YYYY")
                }
            )
            
            st.divider()
            st.subheader("⚙️ Gerenciar Usuário Selecionado")
            
            mapa_selecao = {
                f"{u['nome']} ({u['email']} - {u['perfil'].upper()})": u 
                for u in dados_usuarios
            }
            chave_escolhida = st.selectbox(
                "Selecione um usuário para editar dados, redefinir senha ou excluir:", 
                options=list(mapa_selecao.keys())
            )
            u_sel = mapa_selecao[chave_escolhida]
            eh_proprio_admin = (u_sel["id"] == st.session_state.usuario_id)
            
            col_edicao, col_exclusao = st.columns([2, 1])
            
            # --- EDIÇÃO DE DADOS, PERFIL E RESET DE SENHA ---
            with col_edicao:
                with st.form("form_editar_usuario"):
                    st.markdown("#### ✏️ Alterar Cadastro e Credenciais")
                    c1, c2 = st.columns(2)
                    
                    ed_nome = c1.text_input("Nome Completo", value=u_sel.get("nome") or "")
                    ed_email = c1.text_input("E-mail", value=u_sel.get("email") or "")
                    ed_tel = c2.text_input("Telefone", value=u_sel.get("telefone") or "")
                    
                    perfis_opcoes = ["aluno", "professor", "admin"]
                    idx_perfil = perfis_opcoes.index(u_sel["perfil"]) if u_sel.get("perfil") in perfis_opcoes else 0
                    ed_perfil = c2.selectbox(
                        "Perfil de Acesso", 
                        options=perfis_opcoes, 
                        index=idx_perfil,
                        disabled=eh_proprio_admin,
                        help="Você não pode rebaixar o seu próprio perfil de Administrador ativo."
                    )
                    
                    st.markdown("---")
                    st.caption(
                        "🔑 **Redefinição de Senha (Opcional):** Se preenchida, o usuário será obrigado a trocá-la no próximo login."
                    )
                    nova_senha = st.text_input(
                        "Nova Senha Provisória (mínimo 6 caracteres)", 
                        type="password", 
                        placeholder="Deixe em branco para manter a senha atual"
                    )
                    
                    if st.form_submit_button("💾 Salvar Alterações"):
                        if not ed_nome.strip() or not ed_email.strip():
                            st.warning("Nome e E-mail não podem ficar vazios.")
                        elif nova_senha and len(nova_senha) < 6:
                            st.warning("A nova senha deve ter pelo menos 6 caracteres.")
                        else:
                            try:
                                alteracoes_log = []
                                if ed_nome != u_sel.get("nome"): alteracoes_log.append(f"Nome: {u_sel.get('nome')} -> {ed_nome}")
                                if ed_email != u_sel.get("email"): alteracoes_log.append(f"Email: {u_sel.get('email')} -> {ed_email}")
                                if ed_tel != u_sel.get("telefone"): alteracoes_log.append("Telefone atualizado")
                                if ed_perfil != u_sel.get("perfil"): alteracoes_log.append(f"Perfil: {u_sel.get('perfil')} -> {ed_perfil}")
                                
                                auth_id_alvo = u_sel.get("auth_id")
                                
                                if auth_id_alvo:
                                    atributos_auth = {
                                        "email": ed_email.strip(),
                                        "email_confirm": True,
                                        "user_metadata": {"nome": ed_nome.strip()}
                                    }
                                    if nova_senha:
                                        atributos_auth["password"] = nova_senha
                                        alteracoes_log.append("Senha redefinida pelo Admin (Troca obrigatória ativada)")
                                        
                                    admin_supabase.auth.admin.update_user_by_id(auth_id_alvo, atributos_auth)
                                elif nova_senha:
                                    novo_auth = admin_supabase.auth.admin.create_user({
                                        "email": ed_email.strip(),
                                        "password": nova_senha,
                                        "email_confirm": True,
                                        "user_metadata": {"nome": ed_nome.strip()}
                                    })
                                    if novo_auth.user:
                                        auth_id_alvo = novo_auth.user.id
                                        alteracoes_log.append("Credencial Auth criada e senha provisória definida")
                                
                                dados_update_usuario = {
                                    "auth_id": auth_id_alvo,
                                    "nome": ed_nome.strip(),
                                    "email": ed_email.strip(),
                                    "telefone": ed_tel.strip(),
                                    "perfil": ed_perfil
                                }
                                if nova_senha:
                                    dados_update_usuario["precisa_trocar_senha"] = True
                                
                                admin_supabase.table("usuarios").update(dados_update_usuario).eq("id", u_sel["id"]).execute()
                                
                                resumo_alt = " | ".join(alteracoes_log) if alteracoes_log else "Revalidação cadastral sem mudança de valores"
                                admin_supabase.table("auditoria_lgpd").insert({
                                    "usuario_id": st.session_state.usuario_id,
                                    "acao": "Alteração de Usuário (Admin)",
                                    "dados_contexto": f"Alvo: {ed_email.strip()} | Mudanças: {resumo_alt}"
                                }).execute()
                                
                                st.success("✅ Dados atualizados com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao atualizar usuário: {e}")

            # --- EXCLUSÃO DE USUÁRIO ---
            with col_exclusao:
                st.markdown("#### 🗑️ Exclusão de Conta")
                if eh_proprio_admin:
                    st.info("🔒 Por segurança, você não pode excluir a sua própria conta de Administrador ativa.")
                else:
                    st.warning(
                        f"A exclusão removerá permanentemente **{u_sel['nome']}** e seus treinos/feedbacks vinculados."
                    )
                    confirmar_del = st.checkbox(
                        "Confirmo a exclusão definitiva deste registro", 
                        key=f"del_{u_sel['id']}"
                    )
                    
                    if st.button("🚨 Excluir Usuário", type="primary", use_container_width=True):
                        if not confirmar_del:
                            st.error("Marque a caixa de confirmação acima antes de excluir.")
                        else:
                            try:
                                admin_supabase.table("auditoria_lgpd").insert({
                                    "usuario_id": st.session_state.usuario_id,
                                    "acao": "Exclusão de Usuário (Admin)",
                                    "dados_contexto": f"Excluído: {u_sel['nome']} | Email: {u_sel['email']} | Perfil: {u_sel['perfil']}"
                                }).execute()
                                
                                admin_supabase.table("usuarios").delete().eq("id", u_sel["id"]).execute()
                                
                                if u_sel.get("auth_id"):
                                    admin_supabase.auth.admin.delete_user(u_sel["auth_id"])
                                    
                                st.success(f"Usuário {u_sel['nome']} excluído com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao excluir usuário: {e}")

    # -----------------------------------------------------
    # ABA 2: Criação de Novo Usuário
    # -----------------------------------------------------
    with aba_novo:
        st.subheader("Cadastrar Novo Acesso")
        with st.form("form_novo_usuario", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                novo_nome = st.text_input("Nome Completo")
                novo_email = st.text_input("E-mail")
            with col2:
                novo_telefone = st.text_input("Telefone")
                novo_perfil = st.selectbox("Perfil", ["aluno", "professor", "admin"])
            
            if st.form_submit_button("Criar Usuário"):
                if novo_nome and novo_email:
                    senha_prov = gerar_senha_temporaria()
                    try:
                        novo_auth = admin_supabase.auth.admin.create_user({
                            "email": novo_email.strip(), 
                            "password": senha_prov, 
                            "email_confirm": True, 
                            "user_metadata": {"nome": novo_nome.strip()}
                        })
                        if novo_auth.user:
                            admin_supabase.table("usuarios").update({
                                "perfil": novo_perfil, 
                                "telefone": novo_telefone.strip(), 
                                "criado_por": st.session_state.usuario_id,
                                "precisa_trocar_senha": True
                            }).eq("auth_id", novo_auth.user.id).execute()
                            
                            admin_supabase.table("auditoria_lgpd").insert({
                                "usuario_id": st.session_state.usuario_id,
                                "acao": f"Criação de Usuário ({novo_perfil})", 
                                "dados_contexto": f"Nome: {novo_nome.strip()} | Email: {novo_email.strip()}"
                            }).execute()
                            
                            st.success(f"✅ Usuário {novo_nome} criado com sucesso!")
                            st.info(f"🔑 **Senha Provisória (Troca obrigatória no 1º login):** `{senha_prov}`")
                    except Exception as e:
                        st.error(f"Erro: {e}")
                else:
                    st.warning("Preencha Nome e E-mail.")

    # -----------------------------------------------------
    # ABA 3: Trilha de Auditoria (Alunos, Treinos e Gestão)
    # -----------------------------------------------------
    with aba_auditoria:
        st.subheader("Trilha de Auditoria e Rastreabilidade")
        st.caption("Registro imutável de inclusões, evoluções clínicas, treinos, feedbacks, senhas e exclusões.")
        
        if st.button("🔄 Atualizar Logs de Auditoria"):
            st.rerun()
            
        try:
            resp_logs = admin_supabase.table("auditoria_lgpd").select("*").execute()
            logs = resp_logs.data if resp_logs.data else []
        except Exception as e:
            st.error(f"Erro ao carregar trilha de auditoria: {e}")
            logs = []

        if not logs:
            st.info("Nenhum evento de auditoria registrado até o momento.")
        else:
            mapa_responsaveis = {
                u["id"]: f"{u['nome']} ({u['perfil'].upper()})" 
                for u in dados_usuarios
            }
            
            df_logs = pd.DataFrame(logs)
            df_logs["responsavel"] = df_logs["usuario_id"].map(mapa_responsaveis).fillna("Usuário Excluído / Sistema")
            
            col_data = next((c for c in ["data_hora", "criado_em", "created_at"] if c in df_logs.columns), None)
            if col_data:
                df_logs = df_logs.sort_values(by=col_data, ascending=False)
                
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_resp = st.multiselect(
                    "Filtrar por Responsável:", 
                    options=df_logs["responsavel"].unique()
                )
            with col_f2:
                filtro_acao = st.multiselect(
                    "Filtrar por Tipo de Evento:", 
                    options=df_logs["acao"].unique()
                )
                
            if filtro_resp:
                df_logs = df_logs[df_logs["responsavel"].isin(filtro_resp)]
            if filtro_acao:
                df_logs = df_logs[df_logs["acao"].isin(filtro_acao)]
                
            colunas_exibicao = ["responsavel", "acao", "dados_contexto"]
            config_colunas = {
                "responsavel": "Usuário Responsável",
                "acao": "Ação / Evento",
                "dados_contexto": "Detalhes da Operação (O que foi Incluído / Alterado / Excluído)"
            }
            
            if col_data:
                colunas_exibicao.insert(0, col_data)
                config_colunas[col_data] = st.column_config.DatetimeColumn(
                    "Data e Hora", 
                    format="DD/MM/YYYY HH:mm:ss"
                )
                
            st.dataframe(
                df_logs[colunas_exibicao],
                use_container_width=True,
                hide_index=True,
                column_config=config_colunas
            )

# ==========================================
# 6. PAINEL DO PROFESSOR
# ==========================================
def painel_professor():
    st.title("Painel do Professor")
    st.markdown("Gerencie alunos, elabore treinamentos e monitore resultados.")
    
    if st.session_state.perfil != "professor":
        st.error("Acesso Negado. Você não tem privilégios de professor.")
        st.stop()

    aba_lista, aba_cadastro, aba_treinos, aba_monit = st.tabs([
        "👥 Lista de Alunos", 
        "📄 Cadastrar Aluno", 
        "🏋️ Gerar Treinos", 
        "📈 Monitoramento"
    ])
    
    admin_supabase = init_admin_connection()
    
    # -----------------------------------------------------
    # ABA 1: Lista de Alunos Cadastrados
    # -----------------------------------------------------
    with aba_lista:
        st.subheader("Alunos Cadastrados")
        try:
            resp_alunos = supabase.table("usuarios").select(
                "nome, email, telefone, criado_em"
            ).eq("perfil", "aluno").execute()
            if resp_alunos.data:
                st.dataframe(
                    resp_alunos.data, 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "nome": "Nome do Aluno",
                        "email": "E-mail",
                        "telefone": "Telefone / WhatsApp",
                        "criado_em": st.column_config.DatetimeColumn("Cadastrado em", format="DD/MM/YYYY")
                    }
                )
            else:
                st.info("Nenhum aluno cadastrado até o momento.")
        except Exception as e:
            st.error(f"Erro ao carregar a lista: {e}")

    # -----------------------------------------------------
    # ABA 2: Cadastrar Aluno (Manual ou via IA)
    # -----------------------------------------------------
    with aba_cadastro:
        st.subheader("Novo Aluno (Geração de Credenciais)")
        st.markdown("Preencha os dados manualmente ou envie uma ficha de Anamnese para extração assistida por IA.")
        
        arq = st.file_uploader("Preenchimento Inteligente (Upload de PDF/DOCX da Anamnese)", type=["pdf", "docx"])
        if arq and st.button("🧠 Processar com IA"):
            txt = extrair_texto_arquivo(arq.read(), arq.name)
            if txt:
                dados_extraidos = analisar_dados_gemini(txt)
                if dados_extraidos: 
                    st.session_state.dados_ia = dados_extraidos
                    st.success("Dados extraídos com sucesso! Revise os campos abaixo.")
        
        d = st.session_state.get("dados_ia", {})
        
        with st.form("form_novo_aluno", clear_on_submit=True):
            st.markdown("### Dados de Cadastro")
            c1, c2 = st.columns(2)
            nome_aluno = c1.text_input("Nome Completo", value=d.get("nome", ""), max_chars=100)
            email_aluno = c1.text_input("E-mail do Aluno", value=d.get("email", ""))
            tel_aluno = c2.text_input("Telefone (WhatsApp)", value=d.get("telefone", ""))
            motivo = st.text_area("Motivo do Contato / Histórico Clínico Inicial (LGPD)", value=d.get("motivo_contato", ""))
            
            if st.form_submit_button("Cadastrar e Gerar Senha"):
                if nome_aluno and email_aluno:
                    senha_prov = gerar_senha_temporaria()
                    try:
                        novo_auth = admin_supabase.auth.admin.create_user({
                            "email": email_aluno.strip(), 
                            "password": senha_prov, 
                            "email_confirm": True, 
                            "user_metadata": {"nome": nome_aluno.strip()}
                        })
                        
                        if novo_auth.user:
                            # Perfil fixado (hardcoded) como 'aluno' e trava de troca de senha ativada
                            admin_supabase.table("usuarios").update({
                                "perfil": "aluno", 
                                "telefone": tel_aluno.strip(), 
                                "motivo_contato": motivo.strip(),
                                "criado_por": st.session_state.usuario_id,
                                "precisa_trocar_senha": True
                            }).eq("auth_id", novo_auth.user.id).execute()
                            
                            admin_supabase.table("auditoria_lgpd").insert({
                                "usuario_id": st.session_state.usuario_id,
                                "acao": "Professor cadastrou Aluno", 
                                "dados_contexto": f"Nome: {nome_aluno.strip()} | Email: {email_aluno.strip()}"
                            }).execute()
                            
                            st.success(f"✅ Aluno **{nome_aluno}** cadastrado com sucesso!")
                            st.info(f"🔑 **Senha Temporária do Aluno (Troca obrigatória no 1º acesso):** `{senha_prov}`")
                            
                            if "dados_ia" in st.session_state:
                                del st.session_state.dados_ia
                    except Exception as e:
                        st.error(f"Erro na criação: {e}")
                else:
                    st.warning("Os campos Nome e E-mail são obrigatórios.")

    # -----------------------------------------------------
    # ABA 3: Evolução Clínica, Geração e Gestão de Treinos
    # -----------------------------------------------------
    with aba_treinos:
        try:
            lista_alunos = supabase.table("usuarios").select(
                "id, nome, telefone, motivo_contato"
            ).eq("perfil", "aluno").execute().data
        except Exception: 
            lista_alunos = []
        
        if lista_alunos:
            mapa_alunos = {a["nome"]: a for a in lista_alunos}
            # Adicionamos uma key única baseada no contexto para estabilizar o selectbox
            nome_aluno_selecionado = st.selectbox(
                "Selecione o Aluno", 
                list(mapa_alunos.keys()), 
                key="select_aluno_treinos"
            )
            aluno = mapa_alunos[nome_aluno_selecionado]
            
            st.markdown("### 📋 Histórico Clínico e Objetivos (Somente Adição)")
            contexto_atual = aluno.get("motivo_contato") or "Nenhum histórico registrado inicialmente."
            st.info(contexto_atual)
            
            with st.expander("➕ Adicionar nova evolução/observação clínica"):
                nova_observacao = st.text_area(
                    "Digite a nova informação (Será anexada permanentemente ao histórico atual):", 
                    key=f"input_evolucao_{aluno['id']}"
                )
                
                if st.button("Salvar Evolução Clínica", key=f"btn_salvar_ev_{aluno['id']}"):
                    if nova_observacao.strip():
                        data_hoje = datetime.now().strftime("%d/%m/%Y %H:%M")
                        contexto_atualizado = f"{contexto_atual}\n\n[{data_hoje} - Nova Evolução]: {nova_observacao.strip()}"
                        
                        try:
                            supabase.table("usuarios").update({
                                "motivo_contato": contexto_atualizado
                            }).eq("id", aluno["id"]).execute()
                            
                            admin_supabase.table("auditoria_lgpd").insert({
                                "usuario_id": st.session_state.usuario_id,
                                "acao": "Evolução Clínica Adicionada", 
                                "dados_contexto": f"Aluno: {aluno['nome']} | Adição em {data_hoje}"
                            }).execute()
                            
                            st.success("Evolução clínica anexada com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar histórico: {e}")
                    else:
                        st.warning("Escreva a nova observação antes de salvar.")
            
            st.divider()
            
            # --- SEÇÃO DE GERENCIAMENTO DE TREINOS COM ISOLAMENTO DE CONTAINER ---
            st.markdown("### ⚙️ Gerenciar Treinos Cadastrados do Aluno")
            
            # Container exclusivo para o aluno selecionado, evitando conflito no DOM ao trocar de aluno
            with st.container(key=f"container_treinos_{aluno['id']}"):
                try:
                    treinos_aluno = supabase.table("treinos").select(
                        "id, titulo_treino, diretrizes, exercicios, ativo, criado_em"
                    ).eq("aluno_id", aluno["id"]).execute().data
                except Exception:
                    treinos_aluno = []
                    
                if treinos_aluno:
                    mapa_treinos_prof = {
                        f"{t['titulo_treino']} (Criado em: {t['criado_em'][:10]})": t 
                        for t in treinos_aluno
                    }
                    escolha_treino_str = st.selectbox(
                        "Selecione o treino para alterar ou excluir:", 
                        list(mapa_treinos_prof.keys()),
                        key=f"select_treino_aluno_{aluno['id']}"
                    )
                    t_sel = mapa_treinos_prof[escolha_treino_str]
                    
                    st.markdown(f"#### Editando: **{t_sel['titulo_treino']}**")
                    
                    # Chaves puramente estáticas vinculadas ao ID fixo do treino selecionado
                    novo_titulo = st.text_input("Título do Treino", value=t_sel["titulo_treino"], key=f"titulo_box_{t_sel['id']}")
                    novas_diretrizes = st.text_area("Diretrizes", value=t_sel.get("diretrizes") or "", key=f"dir_box_{t_sel['id']}")
                    
                    st.markdown("**Exercícios da Ficha:**")
                    df_exercicios_atuais = pd.DataFrame(t_sel["exercicios"]) if t_sel.get("exercicios") else pd.DataFrame(columns=["Exercicio", "Series", "Repeticoes"])
                    
                    exercicios_editados = st.data_editor(
                        df_exercicios_atuais, 
                        num_rows="dynamic", 
                        use_container_width=True,
                        key=f"editor_tabela_{t_sel['id']}"
                    )
                    
                    col_btn_alt, col_btn_exc = st.columns(2)
                    
                    if col_btn_alt.button("💾 Atualizar Treino", key=f"btn_upd_acao_{t_sel['id']}", use_container_width=True):
                        try:
                            lista_exercicios_atualizada = exercicios_editados.to_dict(orient="records")
                            supabase.table("treinos").update({
                                "titulo_treino": novo_titulo.strip(),
                                "diretrizes": novas_diretrizes.strip(),
                                "exercicios": lista_exercicios_atualizada
                            }).eq("id", t_sel["id"]).execute()
                            
                            admin_supabase.table("auditoria_lgpd").insert({
                                "usuario_id": st.session_state.usuario_id,
                                "acao": "Alteração de Treino",
                                "dados_contexto": f"Aluno: {aluno['nome']} | Treino atualizado: {novo_titulo.strip()}"
                            }).execute()
                            
                            st.success("✅ Treino atualizado com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao atualizar treino: {e}")
                            
                    if col_btn_exc.button("🚨 Excluir Treino", key=f"btn_del_acao_{t_sel['id']}", use_container_width=True):
                        try:
                            supabase.table("treinos").delete().eq("id", t_sel["id"]).execute()
                            
                            admin_supabase.table("auditoria_lgpd").insert({
                                "usuario_id": st.session_state.usuario_id,
                                "acao": "Exclusão de Treino",
                                "dados_contexto": f"Aluno: {aluno['nome']} | Treino excluído: {t_sel['titulo_treino']}"
                            }).execute()
                            
                            st.success("🗑️ Treino excluído com sucesso!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir treino: {e}")
                else:
                    st.info("Este aluno ainda não possui treinos cadastrados.")
                
            st.divider()
            
            # --- SEÇÃO DE CRIAÇÃO DE NOVO TREINO VIA IA ---
            st.markdown("### 🧠 Gerar Nova Rotina com IA")
            titulo = st.text_input("Título do Novo Treino", key=f"novo_tit_treino_{aluno['id']}")
            diretrizes = st.text_area("Diretrizes para a IA (Ex: Foco em hipertrofia, evitar impacto)", key=f"nova_dir_treino_{aluno['id']}")
            
            if st.button("🧠 Gerar Proposta com IA", key=f"btn_gerar_ia_{aluno['id']}"):
                if titulo:
                    with st.spinner("Analisando o histórico clínico e gerando planejamento..."):
                        treino = propor_treino_gemini(contexto_atual, diretrizes)
                        if treino:
                            st.session_state.update({
                                "tr_ed": treino, 
                                "tit_ed": titulo, 
                                "al_id": aluno["id"], 
                                "al_tel": aluno["telefone"], 
                                "dir_ed": diretrizes, 
                                "al_nome": aluno["nome"]
                            })
                else: 
                    st.warning("Informe o título do treino.")
            
            if "tr_ed" in st.session_state:
                st.markdown("#### 🛠️ Revisão e Ajustes Finais do Novo Treino")
                # Key exclusiva para o editor do novo treino gerado pela IA
                rev = st.data_editor(
                    st.session_state.tr_ed, 
                    num_rows="dynamic", 
                    use_container_width=True,
                    key="editor_novo_treino_ia"
                )
                
                if st.button("💾 Salvar Novo Treino Atribuído", key="btn_salvar_novo_treino_ia"):
                    try:
                        if isinstance(rev, pd.DataFrame):
                            rev_data = rev.to_dict(orient="records")
                        else:
                            rev_data = rev
                            
                        supabase.table("treinos").insert({
                            "aluno_id": st.session_state.al_id, 
                            "professor_id": st.session_state.usuario_id,
                            "titulo_treino": st.session_state.tit_ed, 
                            "diretrizes": st.session_state.dir_ed,
                            "exercicios": rev_data
                        }).execute()
                        
                        admin_supabase.table("auditoria_lgpd").insert({
                            "usuario_id": st.session_state.usuario_id,
                            "acao": "Inclusão de Treino",
                            "dados_contexto": f"Aluno: {st.session_state.al_nome} | Treino: {st.session_state.tit_ed} ({len(rev_data)} exercícios)"
                        }).execute()
                        
                        st.success("✅ Treino salvo e auditado com sucesso!")
                        renderizar_botao_whatsapp(st.session_state.al_nome, st.session_state.al_tel)
                        del st.session_state.tr_ed
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Erro: {e}")
        else:
            st.info("Nenhum aluno cadastrado. Acesse a aba 'Cadastrar Aluno' para iniciar.")

    # -----------------------------------------------------
    # ABA 4: Monitoramento (Monotonia e Risco)
    # -----------------------------------------------------
    with aba_monit:
        if st.button("🔄 Atualizar Relatório de Monotonia"):
            try:
                dados = supabase.table("feedbacks").select(
                    "id, data_execucao, duracao_minutos, pse_borg, carga_treinamento, dores_relatadas, usuarios(nome), treinos(titulo_treino)"
                ).execute().data
                if dados:
                    for l in dados:
                        l["nome"] = l["usuarios"]["nome"] if l.get("usuarios") else "Aluno"
                        if l.get("carga_treinamento") is None:
                            l["carga_treinamento"] = (l.get("duracao_minutos") or 0) * (l.get("pse_borg") or 0)
                            
                    df = pd.DataFrame(dados)
                    df["data_execucao"] = pd.to_datetime(df["data_execucao"])
                    df["sem"] = df["data_execucao"].dt.isocalendar().week
                    
                    res = df.groupby(["nome", "sem"]).agg(
                        sess=("id", "count"), 
                        media=("carga_treinamento", "mean"),
                        std=("carga_treinamento", "std"), 
                        dores=("dores_relatadas", lambda x: " | ".join(x.dropna().unique()))
                    ).reset_index()
                    
                    res["std"] = res["std"].fillna(1).replace(0, 1)
                    res["monotonia"] = (res["media"] / res["std"]).round(2)
                    
                    for _, row in res.iterrows():
                        if row["monotonia"] > 2.0:
                            st.error(f"🚨 ALTO RISCO: {row['nome']} (Monotonia: {row['monotonia']})")
                            st.info(f"🧠 IA: {gerar_alerta_ia_monotonia(row['monotonia'], row['dores'])}")
                        elif row["monotonia"] >= 1.5: 
                            st.warning(f"⚠️ ATENÇÃO: {row['nome']} (Monotonia: {row['monotonia']})")
                        else: 
                            st.success(f"✅ NORMAL: {row['nome']} (Monotonia: {row['monotonia']})")
                        st.divider()
                else:
                    st.info("Sem feedbacks registrados pelos alunos.")
            except Exception as e: 
                st.error(f"Erro ao processar dados: {e}")

# ==========================================
# 7. ÁREA DO ALUNO
# ==========================================
def area_aluno():
    st.title("🏃 Área de Treinamento")
    st.markdown("Visualize todos os seus treinos ativos e registre sua evolução diária.")
    
    if st.session_state.perfil != "aluno":
        st.error("Acesso Negado.")
        st.stop()

    try:
        # Busca integral de todos os treinos ativos atribuídos a este aluno
        treinos = supabase.table("treinos").select(
            "id, titulo_treino, diretrizes, exercicios"
        ).eq("aluno_id", st.session_state.usuario_id).eq("ativo", True).execute().data
    except Exception as e:
        st.error(f"Erro ao carregar treinos: {e}")
        treinos = []

    if not treinos:
        st.info("Você não possui treinos ativos no momento.")
        return

    mapa = {t["titulo_treino"]: t for t in treinos}
    t_atual = mapa[st.selectbox("Selecione a Rotina do Dia:", list(mapa.keys()))]
    
    if t_atual.get("diretrizes"):
        st.caption(f"**Diretrizes do Professor:** {t_atual['diretrizes']}")
        
    st.dataframe(t_atual["exercicios"], use_container_width=True, hide_index=True)
       
    st.divider()
    st.subheader("📊 Registro de Conclusão e Feedback")
    
    with st.form("fb", clear_on_submit=True):
        c1, c2 = st.columns(2)
        duracao = c1.number_input("Duração (min)", min_value=1, max_value=300, value=60)
        borg = c2.slider("Esforço (PSE Borg)", min_value=0, max_value=10, value=5)
        dores = st.text_area("Sentiu alguma dor atípica? (Opcional)")
        perc = st.text_area("Percepção geral do treino (Opcional)")
        aceite = st.checkbox("Concordo com o compartilhamento destes dados de saúde com meu professor (LGPD)")
        
        if st.form_submit_button("Salvar Feedback"):
            if not aceite:
                st.warning("⚠️ É obrigatório marcar o termo de consentimento (LGPD) para registrar o feedback.")
            else:
                try:
                    supabase.table("feedbacks").insert({
                        "treino_id": t_atual["id"], 
                        "aluno_id": st.session_state.usuario_id,
                        "duracao_minutos": duracao, 
                        "pse_borg": borg, 
                        "dores_relatadas": dores.strip() if dores and dores.strip() else None, 
                        "feedback_percepcao": perc.strip() if perc and perc.strip() else None
                    }).execute()
                    
                    resumo_dor = dores.strip() if (dores and dores.strip()) else "Nenhuma"
                    admin_supabase = init_admin_connection()
                    admin_supabase.table("auditoria_lgpd").insert({
                        "usuario_id": st.session_state.usuario_id,
                        "acao": "Inclusão de Feedback (Aluno)",
                        "dados_contexto": (
                            f"Treino: {t_atual['titulo_treino']} | "
                            f"Duração: {duracao}min | Borg: {borg} | "
                            f"Dor: {resumo_dor} | Consentimento LGPD: Sim"
                        )
                    }).execute()
                    
                    st.success("✅ Treino e feedback registrados com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro ao registrar feedback: {e}")

# ==========================================
# 8. ROTEADOR CENTRAL E FUNÇÃO PRINCIPAL
# ==========================================
def roteador_paineis():
    st.sidebar.title(f"Olá, {st.session_state.nome_usuario}")
    st.sidebar.markdown(f"**Perfil:** {st.session_state.perfil.capitalize()}")
    
    # Interceptador de 1º Acesso / Senha Provisória
    if st.session_state.precisa_trocar_senha:
        st.sidebar.warning("🔒 Aguardando definição de senha definitiva.")
        if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True):
            realizar_logout()
        tela_troca_senha_obrigatoria()
        return

    # Autoatendimento de troca de senha
    secao_alterar_propria_senha()
    
    st.sidebar.divider()
    if st.sidebar.button("🚪 Sair (Logout)", use_container_width=True): 
        realizar_logout()
        
    p = st.session_state.perfil
    if p == "admin": 
        painel_admin()
    elif p == "professor": 
        painel_professor()
    elif p == "aluno": 
        area_aluno()

def main():
    init_session_state()
    if not st.session_state.autenticado:
        tela_login()
    else:
        roteador_paineis()

if __name__ == "__main__":
    main()