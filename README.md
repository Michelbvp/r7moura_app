# 🛡️ Sistema de Gestão de Treinamento Seguro (RBAC & LGPD)

Aplicação web desenvolvida em **Streamlit** e **Supabase**, projetada para a gestão de treinamentos físicos, anamneses assistidas por Inteligência Artificial (**Google Gemini**), prontuários clínicos com controle estrito de privacidade e trilha completa de auditoria para conformidade com a **LGPD** e padrões de **Governança de TI (ISO/IEC 27001/27002)**.

---

## 🚀 Funcionalidades Principais

*   **Controle de Acesso Baseado em Papéis (RBAC):** Segregação estrita entre perfis de `Admin`, `Professor` e `Aluno`.
*   **Gestão de Identidade e Credenciais (IAM):** Geração criptográfica de senhas temporárias (`secrets`), trava obrigatória de troca no primeiro acesso e autoatendimento seguro na barra lateral com reautenticação obrigatória.
*   **Módulo Administrador:** CRUD completo de usuários, redefinição de credenciais, exclusão controlada em cascata e aba centralizada de **Trilha de Auditoria**.
*   **Módulo Professor:** Listagem de alunos, cadastro assistido por IA (upload de anamneses em PDF/DOCX), evolução clínica em formato **Append-Only** (integridade e imutabilidade de prontuários), geração e gestão de treinos integrados com envio rápido via WhatsApp.
*   **Módulo Aluno:** Visualização de fichas de treino ativas, registro de feedback de conclusão (PSE Borg, duração e dores relatadas) condicionado ao aceite explícito de consentimento (LGPD).
*   **Monitoramento Analítico:** Cálculo automatizado de Monotonia de Treinamento e geração de alertas preventivos de sobrecarga e risco articular via IA.

---

## 🛠️ Tecnologias Utilizadas

*   **Frontend & Interface:** [Streamlit](https://streamlit.io/) (Python)
*   **Banco de Dados & Autenticação:** [Supabase](https://supabase.com/) (PostgreSQL, Row Level Security - RLS, Auth API e Service Role)
*   **Inteligência Artificial:** Google Gemini API (`gemini-1.5-flash`)
*   **Análise e Processamento:** Pandas, PyPDF2 e python-docx (processamento estritamente em memória RAM para privacidade).

---

## 🔒 Arquitetura de Segurança e Conformidade (LGPD)

1.  **Default Deny (RLS):** Todas as tabelas do banco de dados possuem políticas restritivas em nível de linha, impedindo vazamentos de dados entre usuários.
2.  **Trilha de Auditoria Imutável (`auditoria_lgpd`):** Operações críticas (criações, edições, redefinições de senha, treinos e feedbacks) são registradas automaticamente via conexão administrativa (`service_role`).
3.  **Minimização e Privacidade:** Nenhum documento clínico ou anamnese é armazenado fisicamente no servidor.

---

## ⚙️ Configuração do Ambiente Local

### 1. Clonar o Repositório e Instalar Dependências
```bash
git clone <https://github.com/Michelbvp/r7moura_app>
cd <nome-da-pasta-do-projeto>
pip install -r requirements.txt
